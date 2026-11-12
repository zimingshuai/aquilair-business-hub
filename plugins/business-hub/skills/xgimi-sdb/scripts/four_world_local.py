# -*- coding: utf-8 -*-
"""四世界本地重算：读平台 main 基础数据 + 沙箱点检批次，离线串跑 ③→⑧ 对比 2×2。

用法（批次/BOM 版本不预置，执行前实时确认——FC-29）：
  python four_world_local.py --batch CHK-… --branch sb-… --base-bom <基准版> --target-bom <目标版> [--now <ISO时间>]

依赖：--func-dir 下各函数目录（<fn>/main.py）与 aquilair.py；凭证由宿主环境提供。
注意（FC-33）：⑤ 账本只返回新增行，本脚本已按 o4+o5 合并，勿改回整覆盖。
"""
import argparse
import importlib.util
import json
import os
import sys
from dataclasses import asdict

DEF_FUNC_DIR = r"D:\09_Elitesland\Aquiliar\极米本体设计\models\jimi-supply-demand-balance\functions"

ap = argparse.ArgumentParser()
ap.add_argument("--func-dir", default=DEF_FUNC_DIR)
ap.add_argument("--workspace", default="01a166d2-36f7-7000-919b-458392a14236")
ap.add_argument("--batch", required=True)
ap.add_argument("--branch", required=True, help="读取点检批次所在沙箱分支")
ap.add_argument("--base-bom", required=True)
ap.add_argument("--target-bom", required=True)
ap.add_argument("--now", required=True, help="ISO 时间，如 2026-11-03T23:55:00")
args = ap.parse_args()

FUNC_DIR = args.func_dir
sys.path.insert(0, FUNC_DIR)
from aquilair import WorkspaceClient  # noqa: E402


def load_mod(fn, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(FUNC_DIR, fn, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bx = load_mod("bom_explode", "m_bx")
al = load_mod("supply_demand_allocation", "m_al")
sf = load_mod("substitute_fill", "m_sf")
rk = load_mod("risk_identify", "m_rk")
ss = load_mod("strategy_simulate", "m_ss")
sc = load_mod("scheme_compose", "m_sc")

BATCH = args.batch
NOW = args.now
c = WorkspaceClient(workspace_id=args.workspace)


def load_all(ent, br):
    out, t = [], None
    ep = getattr(c.objects, ent)
    while True:
        p = ep.load(page_size=100, page_token=t, branch=br)
        out += p.data
        if not p.next_page_token:
            return [asdict(x) for x in out]
        t = p.next_page_token


BASE_ENTS = ["BOMHeader", "BOMItem", "Material", "SalesOrder", "BatchInventory",
             "PurchaseOrder", "BOMAlter", "SupplierMaterial", "SupplyDemandObjective",
             "SupplyDemandStrategy"]
base = {e: load_all(e, "main") for e in BASE_ENTS}
chk = [x for x in load_all("CheckBatch", args.branch) if x["check_batch_id"] == BATCH]
bcl = [x for x in load_all("BOMCheckList", args.branch) if x["check_batch_id"] == BATCH]
if not chk:
    sys.exit("批次 %s 在分支 %s 未找到，先用 --batch/--branch 指定" % (BATCH, args.branch))

WORLDS = [
    ("双关（不替代不采购）", False, False),
    ("只替代", True, False),
    ("只采购", False, True),
    ("双开", True, True),
]

for name, use_sub, use_buy in WORLDS:
    strats = json.loads(json.dumps(base["SupplyDemandStrategy"], default=str))
    for s in strats:
        if s["strategy_code"] == "STRAT-SUB":
            s["is_active"] = "是" if use_sub else "否"
        if s["strategy_code"] == "STRAT-PURCHASE":
            s["is_active"] = "是" if use_buy else "否"
    inputs = {k: json.loads(json.dumps(v, default=str)) for k, v in base.items()}
    inputs["SupplyDemandStrategy"] = strats
    inputs["CheckBatch"] = chk
    inputs["BOMCheckList"] = bcl
    inputs["MaterialRequirement"] = []
    inputs["SupplyDemandAllocation"] = []
    p = {"check_batch_id": BATCH, "now": NOW}

    o3 = bx.solve(inputs, dict(p, base_bom=args.base_bom, target_bom=args.target_bom))
    inputs.update(o3)
    o4 = al.solve(inputs, p)
    inputs.update(o4)
    # 平台规则重算（④ 后）：total_available / net_shortage / remaining_shortage
    for r in inputs["MaterialRequirement"]:
        avail = float(r.get("available_stock_qty") or 0) + float(r.get("in_transit_qty") or 0)
        net = max(0.0, float(r.get("gross_demand_qty") or 0) - avail)
        r["total_available_qty"] = avail
        r["net_shortage_qty"] = net
        r["remaining_shortage_qty"] = net
    o4_allocs = list(o4["SupplyDemandAllocation"])
    o5 = sf.solve(inputs, p)
    inputs.update(o5)
    # FC-33：⑤ 账本只含新增行，必须与 ④ 合并
    inputs["SupplyDemandAllocation"] = o4_allocs + list(o5["SupplyDemandAllocation"])
    # 平台规则重算（⑤ 后）：替代补入后剩余缺口
    for r in inputs["MaterialRequirement"]:
        avail = (float(r.get("available_stock_qty") or 0) + float(r.get("in_transit_qty") or 0)
                 + float(r.get("alt_consume_qty_main_unit") or 0))
        net = max(0.0, float(r.get("gross_demand_qty") or 0) - avail)
        r["total_available_qty"] = avail
        r["net_shortage_qty"] = net
        r["remaining_shortage_qty"] = net
    o6 = rk.solve(inputs, p)
    inputs["InventoryRisk"] = o6["InventoryRisk"]
    o7 = ss.solve(inputs, dict(p, penalty_rate=0.1))
    inputs["StrategyResult"] = o7["StrategyResult"]
    o8 = sc.solve(inputs, p)

    ov = {}
    for r in o8["SchemeObjectiveValue"]:
        if not r.get("material_code"):
            ov[r["objective_code"]] = r["value"]
    dead = sum(float(r["risk_qty"]) for r in o6["InventoryRisk"] if r["risk_type"] == "呆滞")
    gap = sum(float(r["risk_qty"]) for r in o6["InventoryRisk"] if r["risk_type"] == "缺口")
    buy_amt = sum(float(r["improve_amount"] or 0) for r in o7["StrategyResult"] if json.loads(r["detail"]).get("kind") == "purchase")
    buy_qty = sum(float(json.loads(r["detail"]).get("buy_qty") or 0) for r in o7["StrategyResult"] if json.loads(r["detail"]).get("kind") == "purchase")
    sub_amt = sum(float(r["improve_amount"] or 0) for r in o7["StrategyResult"] if json.loads(r["detail"]).get("kind") == "substitute")
    sub_qty = sum(float(json.loads(r["detail"]).get("alt_qty") or 0) for r in o7["StrategyResult"] if json.loads(r["detail"]).get("kind") == "substitute")
    alt_rows = [(r["material_code"], float(r["alt_consume_qty_main_unit"] or 0)) for r in inputs["MaterialRequirement"] if float(r["alt_consume_qty_main_unit"] or 0) > 0]
    print("=" * 70)
    print(name)
    print("  按期交付 %s 台 / 延迟 %s 台" % (ov.get("OBJ-ON-TIME-QTY"), ov.get("OBJ-DELAY-QTY")))
    print("  方案口径：剩余缺口 %s 件 / 呆滞 %s 件 / 采购 %s 件 %.0f 元"
          % (ov.get("OBJ-SHORTAGE-QTY"), ov.get("OBJ-DEADSTOCK-QTY"),
             ov.get("OBJ-PURCHASE-QTY"), ov.get("OBJ-PURCHASE-AMT") or 0))
    print("  风险清单：缺口 %d 件 / 呆滞 %d 件" % (gap, dead))
    print("  替代记账 %.0f 件 / %.0f 元 | 替代行 %s" % (sub_qty, sub_amt, alt_rows))
    for r in o7["StrategyResult"]:
        d = json.loads(r["detail"])
        if d.get("kind") == "purchase":
            print("     采购 %-10s %6.0f 件 × %-5s = %8.0f 元" % (
                r["material_code"], float(d.get("purchase_qty") or d.get("buy_qty") or 0),
                d.get("unit_cost"), float(r["improve_amount"] or 0)))
        elif d.get("kind") == "substitute":
            print("     替代 %-10s 主料量 %6.0f × %-5s = %8.0f 元" % (
                r["material_code"], float(d.get("sub_qty") or d.get("alt_qty") or 0),
                d.get("unit_cost"), float(r["improve_amount"] or 0)))
    for line in o8["_log"]:
        if "瓶颈" in line or "订单" in line or "贡献" in line:
            print("   ", line)
