"""通用整链执行器：读取模型编排的动作清单（plan.json），照单逐条 fire，出错即停。

职责边界（2026-10-29 与用户定稿）：脚本只当「跑腿的」——不认识任何业务剧本，
不决定跑什么、跑几步、什么顺序；清单由模型按技能规则现场编排，出确认卡时生成
（清单 = 卡面「动作链」的机器可读版，用户确认卡即确认清单，所见即所执行）。
场景变化（更多决策维度、不同链序、不同开关组合）只影响清单内容，脚本零改动。
脚本不做任何业务计算；回查由模型按汇总中的主键清单经 MCP 并行完成。

清单格式（plan.json）：
{
  "semantic": "推演链-110122",               // 可选：triggerKey 语义前缀
  "steps": [
    {"action": "action_010", "branch": "sb-…-nosub-buy",
     "instances": ["STRAT-SUB"],             // 简写：默认挂策略实体；或写 [{"entity":"OBJ_…","ids":[…]}]
     "note": "世界3关替代"},
    {"action": "action_005", "branch": "sb-…-nosub-buy",
     "params": {"check_batch": "CHK-…"}, "note": "⑤替代"}
  ]
}

用法：
  python scripts/run_plan.py --plan plan.json             # 确认卡通过后执行
  python scripts/run_plan.py --plan plan.json --dry-run   # 只打印将执行的序列，不发请求
退出码：0 全部成功；1 中途失败（输出含已完成步骤与失败现场）；2 清单/配置缺失。
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fire_action as fa  # noqa: E402  同目录复用 fire/解析/状态能力


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def load_plan(path: str) -> dict:
    """读入并结构校验清单；不合格即报错退出（清单由模型生成，错误要能一眼定位）。"""
    raw = Path(path).read_text(encoding="utf-8") if path != "-" else sys.stdin.read()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"❌ 清单不是合法 JSON：{exc}")
    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list) or not plan["steps"]:
        raise SystemExit("❌ 清单格式：{\"semantic\": …(可选), \"steps\": [ … ]}，steps 必须是非空数组")
    for index, step in enumerate(plan["steps"], 1):
        if not isinstance(step, dict) or not isinstance(step.get("action"), str) or not step["action"]:
            raise SystemExit(f"❌ 第 {index} 步缺「action」字段（动作编码，如 action_005）")
        if "params" in step and not isinstance(step["params"], dict):
            raise SystemExit(f"❌ 第 {index} 步 params 必须是对象（callerParams）")
        if "branch" in step and step["branch"] is not None and not isinstance(step["branch"], str):
            raise SystemExit(f"❌ 第 {index} 步 branch 必须是字符串（缺省=生产 main）")
        inst = step.get("instances", [])
        if not isinstance(inst, list) or any(not isinstance(x, (str, dict)) for x in inst):
            raise SystemExit(f"❌ 第 {index} 步 instances 必须是数组（元素为主键字符串或 {{entity,ids}} 对象）")
    return plan


def normalize_instances(raw: list, default_entity: str) -> list[dict]:
    """把清单里的 instances 简写规范化为 ruleaction 的 [{entityRefCode, instanceIds}] 结构。"""
    groups: dict[str, list[str]] = {}
    for item in raw:
        if isinstance(item, str):
            groups.setdefault(default_entity, []).append(item)
        else:  # {"entity": "OBJ_…", "ids": […]}
            groups.setdefault(item.get("entity", default_entity), []).extend(
                str(x) for x in item.get("ids", []))
    return [{"entityRefCode": entity, "instanceIds": ids} for entity, ids in groups.items()]


def main() -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(description="xgimi-sdb 通用整链执行器（照单跑腿，不含业务剧本）")
    parser.add_argument("--plan", required=True, help="清单文件路径（plan.json），- 读 stdin")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的序列，不发请求")
    parser.add_argument("--workspace", default=fa.DEFAULT_WORKSPACE)
    parser.add_argument("--account", help="X-User-Account（否则走解析链）")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--no-state", action="store_true", help="本次不更新 run-state.json")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    semantic_prefix = plan.get("semantic") or "plan"

    # 统一规划：给每步编号、规范化 instances
    plan_steps = []
    for index, step in enumerate(plan["steps"], 1):
        plan_steps.append({
            "seq": index,
            "action": step["action"],
            "branch": step.get("branch"),
            "params": step.get("params", {}),
            "note": step.get("note", ""),
            "instances": normalize_instances(step.get("instances", []), fa.STRATEGY_ENTITY_REF),
        })

    if args.dry_run:
        print(f"dry-run：清单共 {len(plan_steps)} 步")
        for step in plan_steps:
            extra = f"（{step['note']}）" if step["note"] else ""
            inst = f" 关闭/更新 {step['instances']}" if step["instances"] else ""
            print(f"  #{step['seq']:02d} {step['action']} @ {step['branch'] or 'main（生产）'}{inst} {extra}")
        return 0

    account = fa.resolve_account(args.account)
    if not account:
        print("❌ 执行账号未配置：python scripts/fire_action.py --save-account <邮箱>")
        return 2

    summary: dict = {"plan": semantic_prefix, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": []}
    for step in plan_steps:
        payload = fa.build_payload(step["action"], step["params"], step["branch"], args.workspace,
                                   f"{semantic_prefix}-{step['seq']:02d}", [], fa.STRATEGY_ENTITY_REF)
        if step["instances"]:
            payload["instances"] = step["instances"]
        status_code, resp = fa.do_fire(payload, account, args.timeout)
        resp = fa.normalize_resp(resp) if isinstance(resp, dict) else resp
        keys = fa.extract_primary_keys(resp) if isinstance(resp, dict) else []
        ok = isinstance(resp, dict) and resp.get("acceptance") == "ACCEPTED" and str(resp.get("executionStatus") or "").upper() in fa.SUCCESS_STATES
        fa.update_state(step["branch"], step["action"], keys)
        summary["steps"].append({"seq": step["seq"], "action": step["action"], "branch": step["branch"],
                                 "note": step["note"], "ok": ok, "http": status_code, "primary_keys": keys})
        if not ok:
            summary["stopped_at"] = {"seq": step["seq"], "action": step["action"],
                                     "response": resp if isinstance(resp, dict) else str(resp)[:400]}
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"❌ 第 {step['seq']:02d} 步 {step['action']} 未成功（HTTP {status_code}）——按红线 6：不自动重试，先回查再向用户说明。")
            print("判定建议：platform.md §3 错误分诊表；引擎失败（500）如实报告。")
            return 1

    summary["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"✅ 清单 {len(plan_steps)} 步全部执行完成。下一步：按主键清单并行回查（objects_query 带 branch、实体 code）→ 勾稽自洽 → 交付。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
