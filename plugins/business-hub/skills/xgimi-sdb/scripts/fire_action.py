"""fire 动作执行器：构 payload（UTF-8）→ HTTP fire → 解析写入主键 → 维护会话状态。

xgimi-sdb 全部动作执行的标准通道（契约见 references/platform.md §0~§3；脚本只编排与解析，
不做任何业务计算）。相比手写 curl+Python 两步，本脚本一次完成且规避中文编码坑。

用法：
  python scripts/fire_action.py --save-account <邮箱>          # 账号一次配置，永久复用
  python scripts/fire_action.py --action action_001 \
      --param base_bom=<实时发现的基准BOM> --param target_bom=<目标BOM>
  python scripts/fire_action.py --action action_003 --param check_batch=CHK-…
  python scripts/fire_action.py --action action_010 --branch sb-110122-nosub-buy --strategy-close STRAT-SUB
退出码：0 成功（含 duplicate 幂等命中）；1 执行失败；2 配置缺失。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 平台常量（出处：knowledge/FACT-CARDS.md FC-11/FC-24）
DEFAULT_WORKSPACE = "01a166d2-36f7-7000-919b-458392a14236"
FIRE_ENDPOINT = "https://aquilair.idcs.elitescloud.com/ruleaction/v1/api/ruleaction/triggers/fire"
STRATEGY_ENTITY_REF = "OBJ_1E4852DDA44243F8"  # SupplyDemandStrategy（fire instances 用 refCode）
# 账号解析链：--account 参数 > 环境变量 AQUILAIR_USER_ACCOUNT > 工作区 .aquilair/config.json
ACCOUNT_ENV = "AQUILAIR_USER_ACCOUNT"


def _utf8_console() -> None:
    """Windows 控制台强制 UTF-8 输出，避免中文报告乱码。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _aquilair_dir() -> Path:
    """工作区配置目录：当前工作目录下 .aquilair/（跨会话持久）。"""
    return Path.cwd() / ".aquilair"


def _config_path() -> Path:
    return _aquilair_dir() / "config.json"


def _state_path() -> Path:
    return _aquilair_dir() / "run-state.json"


def resolve_account(cli_value: str | None) -> str | None:
    """账号解析链：CLI 参数 > 环境变量 > 配置文件；都无则返回 None。"""
    if cli_value:
        return cli_value
    env = os.environ.get(ACCOUNT_ENV, "").strip()
    if env:
        return env
    cfg = _config_path()
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return (data.get("user_account") or "").strip() or None
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_account(email: str) -> Path:
    """把账号写入配置文件，一次配置永久复用。"""
    d = _aquilair_dir()
    d.mkdir(parents=True, exist_ok=True)
    cfg = _config_path()
    data = {}
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data["user_account"] = email
    data["workspace_id"] = data.get("workspace_id", DEFAULT_WORKSPACE)
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def build_payload(action: str, params: dict, branch: str | None, workspace: str,
                  semantic: str, instance_ids: list[str], instance_entity: str) -> dict:
    """构造 fire payload（骨架见 platform.md §1；branch 顶层字段缺省即 main——沙箱必带）。"""
    instances: list[dict] = []
    if instance_ids:
        instances = [{"entityRefCode": instance_entity, "instanceIds": list(instance_ids)}]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    trigger_key = f"fire-{semantic}-{stamp}"
    payload = {
        "projectApiName": workspace,
        "source": "agent",
        "triggerKey": trigger_key,
        "traceId": f"{trigger_key}-trace",
        "trigger": {"type": "ACTION", "actionApiName": action},
        "instances": instances,
        "callerParams": params,
    }
    if branch:
        payload["branch"] = branch
    return payload


def do_fire(payload: dict, account: str, timeout: int) -> tuple[int, dict | str]:
    """发送 fire 请求并解析响应；返回 (http_status, 解析结果 dict 或原文 str)。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        FIRE_ENDPOINT, data=body, method="POST",
        headers={"X-User-Account": account, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return resp.status, (json.loads(text) if text.strip() else {})
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text)
        except json.JSONDecodeError:
            return exc.code, text
    except urllib.error.URLError as exc:
        return 0, f"网络错误：{exc.reason}"


SUCCESS_STATES = {"SUCCESS", "SUCCEEDED", "COMPLETED"}
FAIL_STATES = {"FAILED", "REJECTED", "ERROR"}


def normalize_resp(resp: dict) -> dict:
    """兼容两种响应外壳：顶层扁平（旧）与 {"code":0,"data":{...}}（v1.4x 网关包装）。"""
    if not isinstance(resp, dict):
        return resp
    data = resp.get("data")
    if isinstance(data, dict) and ("executionStatus" in data or "executionResult" in data):
        out = dict(data)
        state = str(out.get("executionStatus") or "").upper()
        if not out.get("acceptance"):
            if state in SUCCESS_STATES:
                out["acceptance"] = "ACCEPTED"
            elif state in FAIL_STATES:
                out["acceptance"] = "REJECTED"
        return out
    return resp


def extract_primary_keys(resp: dict) -> list[str]:
    """提取全部写入主键：兼容 dataService 列表（旧）与 steps[].dataWriteSummary.editResults（新）。"""
    keys: list[str] = []
    items = (resp.get("executionResult") or {}).get("items") or []
    for item in items:
        ds = item.get("dataService")
        entries = ds if isinstance(ds, list) else ([ds] if isinstance(ds, dict) else [])
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            pk = entry.get("primaryKey")
            if isinstance(pk, str):
                keys.append(pk)
            for record in entry.get("records") or []:
                if isinstance(record, dict) and record.get("primaryKey"):
                    keys.append(str(record["primaryKey"]))
        for step in item.get("steps") or []:
            summary = step.get("dataWriteSummary") or {}
            for edit in summary.get("editResults") or []:
                if isinstance(edit, dict) and edit.get("primaryKey"):
                    keys.append(str(edit["primaryKey"]))
    seen: set[str] = set()
    unique = [k for k in keys if not (k in seen or seen.add(k))]
    return unique


def update_state(branch: str | None, action: str, primary_keys: list[str]) -> None:
    """维护 .aquilair/run-state.json：最新批次/分支/动作史（上下文压缩后的恢复现场用）。"""
    try:
        d = _aquilair_dir()
        d.mkdir(parents=True, exist_ok=True)
        state = {}
        if _state_path().is_file():
            state = json.loads(_state_path().read_text(encoding="utf-8"))
        if branch:
            state["last_branch"] = branch
            branches = state.setdefault("branches", [])
            if branch not in branches:
                branches.append(branch)
        state["last_action"] = action
        state["last_fire_ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
        batches = [k for k in primary_keys if k.startswith("CHK-")]
        if batches:
            state["last_batch"] = batches[0]
        history = state.setdefault("history", [])
        history.append({"ts": state["last_fire_ts"], "action": action,
                        "branch": branch, "keys": primary_keys[:20]})
        state["history"] = history[-50:]
        _state_path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # 状态文件失败不阻塞执行结果


def report(resp_status: int, resp: dict | str, action: str, branch: str | None,
           primary_keys: list[str]) -> int:
    """按 platform.md §3 分诊输出中文结果报告，返回进程退出码。"""
    print(f"== fire {action}（branch={branch or 'main（生产）'}）HTTP {resp_status} ==")
    if not isinstance(resp, dict):
        print(f"响应非 JSON：{str(resp)[:500]}")
        print("判定建议：网络/网关层异常，如实报告，不自动重试写操作。")
        return 1
    acceptance = resp.get("acceptance")
    status = resp.get("executionStatus")
    duplicate = resp.get("duplicate")
    print(f"acceptance={acceptance} executionStatus={status} duplicate={duplicate}")
    if primary_keys:
        print(f"写入主键（{len(primary_keys)}）：")
        for key in primary_keys:
            print(f"  - {key}")
    if duplicate is True:
        print("判定建议：幂等命中（同 triggerKey 已执行过）——回查已有写入，不重发。")
        return 0
    if acceptance == "ACCEPTED" and str(status or "").upper() in SUCCESS_STATES:
        print("判定建议：执行完成——按上述主键回查（objects_query 用实体 code）。")
        return 0
    if acceptance == "REJECTED" or status == "REJECTED":
        missing = resp.get("missingRequiredParams")
        reason = resp.get("rejectReason")
        print(f"missingRequiredParams={missing} rejectReason={reason}")
        if missing and any(str(m).startswith("X") for m in missing):
            print("判定建议：X 类占位符 = 平台配置回退（历史兼容条款），如实告知用户，禁止猜测传值。")
        else:
            print("判定建议：参数被拒——核对 platform.md §2 必填参速查表后重新走确认卡。")
        return 1
    if acceptance is None and status is None:
        raw = json.dumps(resp, ensure_ascii=False)
        print(f"原始响应（{len(raw)} 字符）：{raw[:800]}")
    print("判定建议：按 platform.md §3 错误分诊表处理；HTTP 500=引擎失败（0 写入），如实报告。")
    return 1


def main() -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(description="xgimi-sdb fire 动作执行器")
    parser.add_argument("--save-account", metavar="EMAIL", help="写入账号配置（一次配置永久复用）")
    parser.add_argument("--show-config", action="store_true", help="显示当前配置与状态文件位置")
    parser.add_argument("--action", help="动作编码（action_00N 或 ACT_…）")
    parser.add_argument("--param", action="append", default=[], metavar="K=V", help="callerParams 必填参，可重复")
    parser.add_argument("--params-json", help="callerParams 直接给 JSON 串（含中文时推荐）")
    parser.add_argument("--branch", help="沙箱分支名（缺省=生产 main；沙箱执行必带）")
    parser.add_argument("--strategy-close", action="append", default=[], metavar="STRAT-CODE",
                        help="关闭策略开关（action_010 专用，可重复；须配 --branch）")
    parser.add_argument("--instance", action="append", default=[], metavar="CODE",
                        help="更新类动作的目标实例主键（可重复）")
    parser.add_argument("--instance-entity", default=STRATEGY_ENTITY_REF, help="instances 实体 refCode")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="workspace UUID")
    parser.add_argument("--account", help="X-User-Account（否则走解析链）")
    parser.add_argument("--semantic", help="triggerKey 业务语义名（默认用动作名）")
    parser.add_argument("--timeout", type=int, default=180, help="HTTP 超时秒数")
    parser.add_argument("--dump-payload", metavar="PATH", help="调试：把 payload 落盘")
    parser.add_argument("--no-state", action="store_true", help="本次不更新 run-state.json")
    args = parser.parse_args()

    if args.save_account:
        cfg = save_account(args.save_account)
        print(f"✅ 账号已写入 {cfg}——后续 fire 不再询问邮箱。")
        return 0
    if args.show_config:
        account = resolve_account(None)
        print(f"账号：{account or '（未配置——python scripts/fire_action.py --save-account <邮箱>）'}")
        print(f"配置文件：{_config_path()}")
        print(f"状态文件：{_state_path()}")
        state = _state_path()
        if state.is_file():
            data = json.loads(state.read_text(encoding="utf-8"))
            print(f"现场：last_batch={data.get('last_batch')} last_branch={data.get('last_branch')} branches={data.get('branches')}")
        return 0
    if not args.action:
        parser.error("--action 必填（或使用 --save-account / --show-config）")

    account = resolve_account(args.account)
    if not account:
        print("❌ 执行账号未配置。配置一次即可永久复用：")
        print("   python scripts/fire_action.py --save-account <邮箱>")
        print("   （或设置环境变量 AQUILAIR_USER_ACCOUNT）")
        return 2

    params: dict = {}
    for item in args.param:
        key, _, value = item.partition("=")
        params[key.strip()] = value
    if args.params_json:
        params.update(json.loads(args.params_json))

    instance_ids = list(args.instance) + list(args.strategy_close)
    action = args.action
    if args.strategy_close and action == "action_010" and not args.branch:
        print("❌ 开关写入必须 --branch 定向沙箱（缺省即 main，漏带=写生产开关）。")
        return 2

    payload = build_payload(action, params, args.branch, args.workspace,
                            args.semantic or action, instance_ids, args.instance_entity)
    if args.dump_payload:
        Path(args.dump_payload).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"payload 已落盘 {args.dump_payload}")

    status_code, resp = do_fire(payload, account, args.timeout)
    resp = normalize_resp(resp) if isinstance(resp, dict) else resp
    primary_keys = extract_primary_keys(resp) if isinstance(resp, dict) else []
    if not args.no_state:
        update_state(args.branch, action, primary_keys)
    return report(status_code, resp, action, args.branch, primary_keys)


if __name__ == "__main__":
    sys.exit(main())
