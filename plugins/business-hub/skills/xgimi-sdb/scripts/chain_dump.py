# -*- coding: utf-8 -*-
"""基线全链 dump：按「替代+采购」口径离线串跑 ①→⑧，输出各环节明细数字（文档/验收用）。

用法（批次/BOM 版本不预置，执行前实时确认——FC-29）：
  python chain_dump.py --batch CHK-… --base-bom <基准版> --target-bom <目标版> [--now <ISO时间>]

依赖：--func-dir 下各函数目录（<fn>/main.py）与 aquilair.py；凭证由宿主环境提供。
注意（FC-33）：⑤ 账本只返回新增行，本脚本已按 o4+o5 合并，勿改回整覆盖。
"""
import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict

DEF_FUNC_DIR = r"D:\09_Elitesland\Aquiliar\极米本体设计\models\jimi-supply-demand-balance\functions"

ap = argparse.ArgumentParser()
ap.add_argument("--func-dir", default=DEF_FUNC_DIR)
ap.add_argument("--workspace", default="01a166d2-36f7-7000-919b-458392a14236")
ap.add_argument("--batch", required=True)
ap.add_argument("--base-bom", required=True)
ap.add_argument("--target-bom", required=True)
ap.add_argument("--now", required=True, help="ISO 时间，如 2026-11-03T23:59:00")
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


bx = load_mod("bom_explode", "d_bx")
al = load_mod("supply_demand_allocation", "d_al")
sf = load_mod("substitute_fill", "d_sf")
rk = load_mod("risk_identify", "d_rk")
ss = load_mod("strategy_simulate", "d_ss")
sc = load_mod("scheme_compose", "d_sc")
bd = load_mod("bom_check_diff", "d_bd")

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


ENTS = ["BOMHeader", "BOMItem", "Material", "SalesOrder", "BatchInventory", "PurchaseOrder",
        "BOMAlter", "SupplierMaterial", "SupplyDemandObjective", "SupplyDemandStrategy"]
inputs = {e: json.loads(json.dumps(load_all(e, "main"), default=str)) for e in ENTS}

o1 = bd.solve(inputs, {"base_bom_code": args.base_bom, "target_bom_code": args.target_bom,
                       "now": NOW, "check_batch_id": BATCH})
inputs.update({k: v for k, v in o1.items() if k != "_log"})
print("### ① 点检 %d 条" % len(o1["BOMCheckList"]))
for r in o1["BOMCheckList"]:
    print("   ", r.get("material_code"), r.get("diff_type"), r.get("change_direction") or "", r.get("alt_material_code") or "")

p = {"check_batch_id": BATCH, "now": NOW}
o3 = bx.solve(inputs, dict(p, base_bom=args.base_bom, target_bom=args.target_bom))
inputs.update(o3)
print("\n### ③ 需求 %d 行" % len(o3["MaterialRequirement"]))
seen = set()
for r in o3["MaterialRequirement"]:
    m = r["material_code"]
    if m in seen:
        continue
    seen.add(m)
    print("   ", m, "gross", r["gross_demand_qty"], "lvl", r["bom_level"])

o4 = al.solve(inputs, p)
inputs.update(o4)
for r in inputs["MaterialRequirement"]:
    a = float(r.get("available_stock_qty") or 0) + float(r.get("in_transit_qty") or 0)
    n = max(0.0, float(r.get("gross_demand_qty") or 0) - a)
    r["total_available_qty"] = a
    r["net_shortage_qty"] = n
    r["remaining_shortage_qty"] = n
print("\n### ④ 分配 %d 笔" % len(o4["SupplyDemandAllocation"]))
for a in o4["SupplyDemandAllocation"][:8]:
    print("    ALC %-28s %-8s ref=%-10s qty=%-6s dl=%s" % (
        a["allocation_id"][-24:], a.get("supply_type"), a.get("supply_ref_id"),
        a.get("allocated_qty"), a.get("demand_line_id")))
print("    req_id 样例:", [r["req_id"] for r in o3["MaterialRequirement"]][:3])
agg = defaultdict(lambda: [0, 0, 0, 0])
for r in inputs["MaterialRequirement"]:
    m = r["material_code"]
    agg[m][0] += float(r.get("gross_demand_qty") or 0)
    agg[m][1] += float(r.get("available_stock_qty") or 0)
    agg[m][2] += float(r.get("in_transit_qty") or 0)
    agg[m][3] += float(r.get("remaining_shortage_qty") or 0)
for m, v in sorted(agg.items()):
    print("    %-12s 需求 %6.0f 现货 %6.0f 在途 %6.0f 净缺口 %6.0f" % (m, v[0], v[1], v[2], v[3]))

o4_allocs = list(o4["SupplyDemandAllocation"])
o5 = sf.solve(inputs, p)
inputs.update(o5)
# FC-33：⑤ 账本只含新增行，必须与 ④ 合并
inputs["SupplyDemandAllocation"] = o4_allocs + list(o5["SupplyDemandAllocation"])
for r in inputs["MaterialRequirement"]:
    a = (float(r.get("available_stock_qty") or 0) + float(r.get("in_transit_qty") or 0)
         + float(r.get("alt_consume_qty_main_unit") or 0))
    n = max(0.0, float(r.get("gross_demand_qty") or 0) - a)
    r["total_available_qty"] = a
    r["net_shortage_qty"] = n
    r["remaining_shortage_qty"] = n
print("\n### ⑤ 替代")
for r in inputs["MaterialRequirement"]:
    if float(r.get("alt_consume_qty_main_unit") or 0) > 0:
        print("    %-10s 订单 %-12s 主料补 %6.0f 替代料耗 %6.0f 剩余缺口 %6.0f"
              % (r["material_code"], r.get("sales_order_nr"), float(r["alt_consume_qty_main_unit"]),
                 float(r.get("alt_consume_qty_alt_unit") or 0), float(r["remaining_shortage_qty"])))
for l in o5["_log"]:
    print("    ·", l)

o6 = rk.solve(inputs, p)
inputs["InventoryRisk"] = o6["InventoryRisk"]
print("\n### ⑥ 风险 %d 条" % len(o6["InventoryRisk"]))
for r in o6["InventoryRisk"]:
    print("    %-10s %s %s 数量 %6.0f × %5s = %9.0f" % (
        r["material_code"], r["risk_type"], r["risk_source"], float(r["risk_qty"]),
        r.get("unit_cost"), float(r.get("risk_amount") or 0)))

o7 = ss.solve(inputs, dict(p, penalty_rate=0.1))
inputs["StrategyResult"] = o7["StrategyResult"]
print("\n### ⑦ 策略 %d 条" % len(o7["StrategyResult"]))
for r in o7["StrategyResult"]:
    d = json.loads(r["detail"])
    if d.get("kind") == "purchase":
        print("    采购 %-10s 缺口 %6.0f 下单 %6.0f 单价 %5s 支出 %8.0f 供应商 %s" % (
            r["material_code"], d.get("shortage_qty") or 0, d.get("order_qty") or 0,
            d.get("unit_price"), d.get("purchase_amt") or 0, d.get("recommended_supplier_code")))
    else:
        print("    替代 %-10s 主料量 %6.0f × %5s = %8.0f" % (
            r["material_code"], d.get("sub_qty") or 0, d.get("unit_cost"), float(r["improve_amount"] or 0)))

o8 = sc.solve(inputs, p)
print("\n### ⑧ 方案")
ov = {}
for r in o8["SchemeObjectiveValue"]:
    if not r.get("material_code"):
        ov[r["objective_code"]] = r["value"]
    else:
        print("    %-20s %-10s %10.1f" % (r["objective_code"], r["material_code"], r["value"]))
for k, v in sorted(ov.items()):
    print("    [汇总] %-20s %10.1f" % (k, v))
for l in o8["_log"]:
    print("    ·", l)
