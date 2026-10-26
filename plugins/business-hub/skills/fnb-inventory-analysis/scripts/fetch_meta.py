"""预取统一 MCP 网关的业务元数据并落盘为技能级缓存。

主要 Input：--service 服务名（默认 aquilair-mcp，须存在于 .mcp.json）、
--workspace fnb 本体项目 UUID（网关工具的必填 workspace_id）、
--token OAuth Bearer 凭证（缺省按序取环境变量 AQUILAIR_MCP_TOKEN、
.mcp.json 服务条目 headers.Authorization；凭证值不写入日志与缓存）、
--refresh 强制忽略缓存重拉、--url 直接指定 MCP 网关端点（通用拷贝安装时的兜底通道）。
主要 Output：技能目录 .meta-cache/ 下 model.json / rules.json / actions.json
三个元数据文件与 _cache-info.json（含 workspace 归属，不含凭证）；stdout 打印中文摘要。
"""

# 标准库导入
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# ===========一、常量与配置==========
# DEFAULT_SERVICE：统一 MCP 网关在 .mcp.json 中的服务名。
DEFAULT_SERVICE = "aquilair-mcp"
# DEFAULT_WORKSPACE：fnb 本体项目 UUID（「demo（勿动！）」餐饮业库存分析），网关工具必填参数。
DEFAULT_WORKSPACE = "019fd9ed-8715-7000-8f28-0a14f59c5563"
# TOKEN_ENV_VAR：OAuth Bearer 凭证的环境变量名（凭证只从外部传入，不硬编码进代码）。
TOKEN_ENV_VAR = "AQUILAIR_MCP_TOKEN"
# META_TOOLS：要预取的三个元数据工具名 -> 缓存文件名的映射（全部带 workspace_id 参数）。
# model.json 落对象/关系级概要（refCode 映射，约 8KB）——不落 metadata_workspace_model 全量：
# 全量数百 KB，模型按需读缓存文件同样装不进上下文，且会话内直调亦会被工具结果预算截断；
# 属性级 PROP_ refCode 由技能主路径按需 metadata_object_neighborhood(ref_code, depth=0) 拉取。
META_TOOLS = {
    "metadata_list_object_types": "model.json",  # 对象/关系概要（OBJ_/REF_ refCode 映射）
    "metadata_list_rules": "rules.json",  # 规则清单
    "metadata_list_actions": "actions.json",  # 动作清单（fnb 未部署时写占位文件）
}
# ACTIONS_TOOL_NAME：唯一允许 404 容错的工具（model/rules 失败仍中止）。
ACTIONS_TOOL_NAME = "metadata_list_actions"
# ACTIONS_UNAVAILABLE_NOTE：action-service 未部署时的占位 JSON 内容（2026-10-22 实测 404）。
ACTIONS_UNAVAILABLE_NOTE = {
    "status": "unavailable",
    "note": "action-service 未在本 workspace 部署动作（2026-10-22 实测 404）",
}
# REQUEST_TIMEOUT_SECONDS：单次 HTTP 请求超时（秒）。
REQUEST_TIMEOUT_SECONDS = 30
# SCRIPT_VERSION：脚本版本号，写入 _cache-info.json 便于排查缓存由哪版脚本生成。
SCRIPT_VERSION = "2.0.0"


# MCP 配置文件可能采用的两种文件名：多数 Agent Skills 宿主用带点前缀的项目级文件，
# 部分宿主的用户级全局配置不带点（如 WorkBuddy 的 ~/.workbuddy/mcp.json）；两种都纳入候选，
# 技能被拷到任意宿主目录层级都无需再改本脚本。
_MCP_CONFIG_FILENAMES = (".mcp.json", "mcp.json")

# _rpc_id_seq：JSON-RPC 请求 id 递增计数器（通知类消息无 id，不消耗）。
_rpc_id_seq = 0


def _next_rpc_id() -> int:
    """生成下一个 JSON-RPC 请求 id。"""
    global _rpc_id_seq
    _rpc_id_seq += 1
    return _rpc_id_seq


# ===========二、服务地址与凭证解析==========
def _candidate_mcp_json_paths() -> list[Path]:
    """返回 MCP 配置文件的候选查找路径（向上逐级搜索，任意宿主目录层级通吃）。

    排序为「目录由近及远 → 同目录内先 .mcp.json 后 mcp.json」，保证宿主自身的
    项目级配置优先于宿主的全局配置。

    Returns:
        按优先级排列的候选 Path 列表（其中部分可能不存在）。
    """
    # 从脚本所在目录起向上逐级（scripts/ -> 技能目录 -> skills/ -> 宿主包根 -> …… 直至文件系统根），
    # 近处优先：同时覆盖各宿主的项目级配置与用户级全局配置等任意层级。
    here = Path(__file__).resolve().parent
    candidates = [
        directory / file_name
        for directory in (here, *here.parents)
        for file_name in _MCP_CONFIG_FILENAMES
    ]
    candidates += [Path.cwd() / file_name for file_name in _MCP_CONFIG_FILENAMES]  # cwd 兜底（恰在其他仓库根运行时）
    return candidates


def _find_service_entry(service_name: str) -> tuple[Path | None, dict[str, Any] | None]:
    """在候选 .mcp.json 中查找目标服务条目（地址与凭证解析共用）。

    Args:
        service_name: .mcp.json 中 mcpServers 下的服务名。
    Returns:
        (命中的配置文件 Path, 服务条目 dict)；未命中返回 (None, None)。
    """
    for config_path in _candidate_mcp_json_paths():
        if not config_path.is_file():
            continue
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue  # 单个候选文件损坏时跳过，继续找下一个
        entry = config.get("mcpServers", {}).get(service_name)
        if entry:
            return config_path, entry
    return None, None


def resolve_service_url(service_name: str, url_override: str | None) -> str:
    """解析目标 MCP 网关端点地址。

    Args:
        service_name: .mcp.json 中 mcpServers 下的服务名。
        url_override: 命令行 --url 直接指定的端点；非空时优先返回。
    Returns:
        MCP 端点 URL 字符串。
    Raises:
        SystemExit: 未提供 --url 且候选位置找不到含该服务的 .mcp.json 时，以中文提示退出。
    """
    #   1. 显式 --url 直接采用（skill 目录被单独拷贝分发、身边没有 .mcp.json 的场景）
    if url_override:
        print("服务地址来源: --url 参数")
        return url_override
    #   2. 依次查找候选 .mcp.json，取首个含目标服务的条目
    config_path, entry = _find_service_entry(service_name)
    if config_path and entry and entry.get("url"):
        print(f"服务地址来源: {config_path}")
        return entry["url"]
    #   3. 全部落空：给出可操作的修复提示后退出
    print(
        f"错误：未找到含服务「{service_name}」的 .mcp.json"
        "（已从脚本目录向上逐级搜索至文件系统根，并检查了当前工作目录）。"
        "请在插件仓库根附近运行，或用 --url https://<host>/mcp-service/mcp 显式指定。",
        file=sys.stderr,
    )
    raise SystemExit(1)


def resolve_token(token_arg: str | None, service_name: str) -> str:
    """按三通道顺序解析 OAuth Bearer 凭证（凭证值只进请求头，不写日志与缓存）。

    Args:
        token_arg: 命令行 --token 传入的凭证（最高优先级）。
        service_name: .mcp.json 中的服务名（第三通道从其条目 headers.Authorization 取）。
    Returns:
        形如 "Bearer <token>" 的完整 Authorization 头值；裸 token 自动补前缀。
    Raises:
        SystemExit: 三通道均未取到凭证时，打印中文指引（说明网关需鉴权与三个来源）后退出。
    """
    #   1. 三通道按序：--token 参数 > 环境变量 > .mcp.json 条目 headers.Authorization
    token_value: str | None = None
    if token_arg:
        token_value, source = token_arg, "--token 参数"
    elif os.environ.get(TOKEN_ENV_VAR):
        token_value, source = os.environ[TOKEN_ENV_VAR], f"环境变量 {TOKEN_ENV_VAR}"
    else:
        _, entry = _find_service_entry(service_name)
        configured = (entry or {}).get("headers", {}).get("Authorization")
        if configured:
            token_value, source = configured, ".mcp.json headers.Authorization"
    #   2. 三处皆无：给出可操作的中文指引后退出
    if not token_value:
        print(
            "错误：未获取到 OAuth Bearer 凭证（统一网关要求鉴权）。请按以下任一方式提供：\n"
            '  1. 运行时加 --token "<Bearer 凭证>"；\n'
            f"  2. 设置环境变量 {TOKEN_ENV_VAR}；\n"
            f'  3. 在 .mcp.json 服务「{service_name}」条目中配置 headers.Authorization。',
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(f"凭证来源: {source}")  # 只打来源，不打凭证值
    #   3. 统一为完整头值：已带 Bearer 前缀原样返回，裸 token 自动补前缀
    return token_value if token_value.lower().startswith("bearer ") else f"Bearer {token_value}"


# ===========三、MCP 会话握手与工具调用==========
def _extract_payload_text(raw_text: str) -> str:
    """SSE 流式响应兜底：把 data: 行拼接还原为 JSON 文本。

    Args:
        raw_text: HTTP 响应正文原文。
    Returns:
        还原后的 JSON 文本（非 SSE 包裹时原样返回）。
    """
    if raw_text.lstrip().startswith(("event:", "data:")):
        return "".join(
            line[len("data:"):]
            for line in raw_text.splitlines()
            if line.startswith("data:")
        )
    return raw_text


def _post_json(endpoint: str, headers: dict[str, str], payload: dict[str, Any]) -> tuple[str, Any]:
    """POST 一条 JSON-RPC 请求，返回 (响应正文文本, 响应头对象)。

    Args:
        endpoint: MCP 网关端点 URL。
        headers: 本次请求头（含 Authorization；有会话时含 Mcp-Session-Id）。
        payload: JSON-RPC 请求体 dict。
    Returns:
        (响应正文文本, urllib 响应头)，响应头供提取 Mcp-Session-Id。
    Raises:
        RuntimeError: 网络失败或超时（消息含阶段名便于定位，不含凭证）。
    """
    #   1. 组装请求（headers 由调用方传入，凭证不经过本函数日志）
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    #   2. 发送请求并读取响应
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8"), response.headers
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"网络请求失败（{payload.get('method', '?')}）：{exc}") from exc


def _raise_on_rpc_error(raw_text: str, stage: str) -> None:
    """校验 JSON-RPC 响应不含 error 键（SSE 包裹时先还原）。

    Args:
        raw_text: 响应正文（可能为 SSE 包裹）。
        stage: 阶段名（如 initialize），用于错误定位。
    Raises:
        RuntimeError: 响应非法 JSON 或含 JSON-RPC error。
    """
    try:
        rpc_response = json.loads(_extract_payload_text(raw_text))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{stage} 响应不是合法 JSON：{raw_text[:200]}") from exc
    if isinstance(rpc_response, dict) and "error" in rpc_response:
        raise RuntimeError(f"{stage} 返回 JSON-RPC 错误：{rpc_response['error']}")


def establish_session(endpoint: str, token: str) -> dict[str, str]:
    """完成 MCP Streamable HTTP 握手，返回后续请求公共头。

    Args:
        endpoint: MCP 网关端点 URL。
        token: OAuth Bearer 凭证完整头值（只进请求头，绝不写入日志/缓存）。
    Returns:
        公共请求头 dict（Content-Type/Accept/Authorization；网关返回会话时附 Mcp-Session-Id）。
    Raises:
        RuntimeError: 网络失败或 initialize 返回 JSON-RPC 错误。
    """
    #   1. 基础请求头：Bearer 鉴权 + 双格式 Accept（网关可能以 SSE 流返回）
    base_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": token,
    }
    #   2. initialize：协议握手
    init_body = {
        "jsonrpc": "2.0",
        "id": _next_rpc_id(),
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "fnb-fetch-meta", "version": SCRIPT_VERSION},
        },
    }
    init_text, response_headers = _post_json(endpoint, base_headers, init_body)
    _raise_on_rpc_error(init_text, "initialize")
    headers = dict(base_headers)
    #   3. 从响应头取会话 ID（无会话网关不返回该头，后续请求省略即可）
    session_id = response_headers.get("Mcp-Session-Id")
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    #   4. notifications/initialized：通知无 id，响应多为 202 空体，无需解析
    _post_json(endpoint, headers, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    return headers


def call_tool(endpoint: str, headers: dict[str, str], tool_name: str, arguments: dict[str, Any]) -> Any:
    """通过 MCP tools/call 拉取工具内层数据。

    Args:
        endpoint: MCP 网关端点 URL。
        headers: establish_session 返回的公共头（含鉴权与会话）。
        tool_name: 工具名（metadata_list_object_types / metadata_list_rules / metadata_list_actions）。
        arguments: 工具参数 dict（本脚本恒为 {"workspace_id": ...}）。
    Returns:
        工具返回 text 字段解析后的内层数据（通常为 dict）；服务端将来改为纯文本时原样返回 str。
    Raises:
        RuntimeError: 网络失败、响应不是合法 JSON、JSON-RPC 错误或工具级 isError。
    """
    #   1. 组装 tools/call 请求体
    request_body = {
        "jsonrpc": "2.0",
        "id": _next_rpc_id(),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    raw_text, _ = _post_json(endpoint, headers, request_body)
    #   2. 解析外层 JSON-RPC（流式实现可能以 SSE 格式包裹，取 data: 行拼接兜底）
    try:
        rpc_response = json.loads(_extract_payload_text(raw_text))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"外层响应不是合法 JSON：{raw_text[:200]}") from exc
    #   3. 校验 JSON-RPC 层错误与工具级 isError（错误消息截断防超长）
    if "error" in rpc_response:
        raise RuntimeError(f"服务端返回 JSON-RPC 错误：{rpc_response['error']}")
    result = rpc_response.get("result", {})
    result_text = json.dumps(result, ensure_ascii=False)
    if result.get("isError"):
        raise RuntimeError(f"工具 {tool_name} 返回 isError=True：{result_text[:500]}")
    content = result.get("content", [])
    if not content or content[0].get("type") != "text":
        raise RuntimeError(f"工具 {tool_name} 返回无文本内容：{result_text[:200]}")
    #   4. 解析内层 JSON（工具返回为双层 JSON：text 字段里还是 JSON 字符串）
    try:
        return json.loads(content[0]["text"])
    except json.JSONDecodeError:
        return content[0]["text"]


# ===========四、元数据拉取与缓存读写==========
def _is_action_service_absent(error_text: str) -> bool:
    """判断 actions 拉取失败是否属于动作服务未部署（404 / 资源不存在）。

    Args:
        error_text: RuntimeError 的错误消息文本。
    Returns:
        True 表示可写占位文件继续；False 表示按普通失败中止。
    """
    return "404" in error_text or "资源不存在" in error_text


def write_cache(
    cache_dir: Path,
    payloads: dict[str, Any],
    service_name: str,
    endpoint: str,
    workspace_id: str,
) -> dict[str, Any]:
    """把三个元数据 payload 统一写入缓存目录并生成 _cache-info.json。

    Args:
        cache_dir: 缓存目录（技能目录下 .meta-cache）。
        payloads: 工具名到内层数据的映射（actions 未部署时为占位 dict）。
        service_name: 服务名，写入缓存元信息便于核对数据来源。
        endpoint: 实际拉取的 MCP 端点。
        workspace_id: 本次拉取的 workspace，缓存复用判断须一致。
    Returns:
        缓存元信息 dict（含 fetched_at 与各文件统计），供摘要打印复用。
    """
    #   1. 写三个数据文件；统计条目数（对象/规则数），占位文件标记「动作未部署」
    cache_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, dict[str, Any]] = {}
    for tool_name, file_name in META_TOOLS.items():
        payload = payloads[tool_name]
        # formatted：pretty-print 后的 JSON 文本；内层非 JSON（纯文本）时原样保存
        if isinstance(payload, str):
            formatted = payload
        else:
            formatted = json.dumps(payload, ensure_ascii=False, indent=2)
        data_path = cache_dir / file_name
        data_path.write_text(formatted, encoding="utf-8")
        if isinstance(payload, dict) and payload.get("status") == "unavailable":
            items: Any = "动作未部署（占位文件）"
        elif isinstance(payload, (dict, list)):
            items = len(payload)
        else:
            items = None
        stats[file_name] = {"bytes": data_path.stat().st_size, "items": items}
    #   2. 生成缓存元信息（workspace 供复用判断；凭证绝不写入）
    info = {
        "service": service_name,
        "workspace": workspace_id,
        "endpoint": endpoint,
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "script_version": SCRIPT_VERSION,
        "files": stats,
    }
    (cache_dir / "_cache-info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return info


def _print_summary(info: dict[str, Any], refreshed: bool, cache_dir: Path) -> None:
    """打印缓存摘要（关键事件用 ==== 定界，供模型判断是否需要细读文件）。

    Args:
        info: 缓存元信息 dict（write_cache 返回值或 _cache-info.json 内容）。
        refreshed: 本次是否发生网络拉取（False 表示缓存命中，未发请求）。
        cache_dir: 缓存目录绝对路径。
    Returns:
        None。
    """
    state = "已刷新" if refreshed else "缓存命中"
    print(f"====元数据缓存就绪====: {info['service']}（{state}）")
    print(f"服务端点: {info['endpoint']}")
    print(f"workspace: {info.get('workspace', '未记录')}")
    print(f"拉取时间: {info['fetched_at']}")
    for file_name, file_stats in info["files"].items():
        if isinstance(file_stats["items"], str):
            item_label = file_stats["items"]  # 占位文件的特殊说明原样展示
        elif file_stats["items"] is not None:
            item_label = f"{file_stats['items']} 个条目"
        else:
            item_label = "非结构化内容"
        print(f"- {file_name}: {item_label}, {file_stats['bytes'] / 1024:.1f} KB")
    print(f"缓存目录: {cache_dir}")
    print("需要服务端最新数据时加 --refresh 重拉")


# ===========五、命令行入口==========
def main() -> None:
    """命令行入口：缓存完整且服务/工作区一致未要求刷新时直接复用，否则握手拉取并落盘。"""
    parser = argparse.ArgumentParser(description="预取统一 MCP 网关业务元数据并落盘为技能级缓存")
    parser.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help=f".mcp.json 中的服务名（默认 {DEFAULT_SERVICE}）",
    )
    parser.add_argument(
        "--workspace",
        default=DEFAULT_WORKSPACE,
        help=f"本体项目 workspace_id（默认 {DEFAULT_WORKSPACE}，fnb 本体项目）",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="OAuth Bearer 凭证（缺省按序取环境变量 AQUILAIR_MCP_TOKEN / .mcp.json headers.Authorization）",
    )
    parser.add_argument("--refresh", action="store_true", help="忽略现有缓存，强制重新拉取")
    parser.add_argument(
        "--url", default=None, help="直接指定 MCP 网关端点（如 https://host/mcp-service/mcp），跳过 .mcp.json 查找"
    )
    args = parser.parse_args()

    #   1. 定位缓存目录（技能目录下 .meta-cache）
    skill_dir = Path(__file__).resolve().parent.parent
    cache_dir = skill_dir / ".meta-cache"
    cache_info_path = cache_dir / "_cache-info.json"

    #   2. 缓存完整、服务与 workspace 均一致且未要求刷新时直接复用，不发起任何网络请求
    cache_files_exist = all(
        (cache_dir / file_name).is_file() for file_name in META_TOOLS.values()
    )
    if cache_files_exist and cache_info_path.is_file() and not args.refresh:
        info = json.loads(cache_info_path.read_text(encoding="utf-8"))
        if info.get("service") == args.service and info.get("workspace") == args.workspace:
            _print_summary(info, refreshed=False, cache_dir=cache_dir)
            return

    #   3. 解析服务地址与凭证（缺任一即以中文提示退出，不动旧缓存）
    endpoint = resolve_service_url(args.service, args.url)
    token = resolve_token(args.token, args.service)

    #   4. 完成 MCP 握手（initialize -> 取会话 -> notifications/initialized）
    try:
        headers = establish_session(endpoint, token)
    except RuntimeError as exc:
        print(f"错误：MCP 握手失败（{exc}）；旧缓存未改动。", file=sys.stderr)
        raise SystemExit(1)
    print("====MCP 握手完成====: 网关会话已建立")

    #   5. 依序拉取三个元数据工具；actions 未部署（404）写占位文件，model/rules 失败即中止
    payloads: dict[str, Any] = {}
    for tool_name in META_TOOLS:
        try:
            payloads[tool_name] = call_tool(endpoint, headers, tool_name, {"workspace_id": args.workspace})
        except RuntimeError as exc:
            if tool_name == ACTIONS_TOOL_NAME and _is_action_service_absent(str(exc)):
                payloads[tool_name] = ACTIONS_UNAVAILABLE_NOTE
                print(f"====动作服务未部署====: {tool_name} 返回 404/资源不存在，actions.json 写占位文件后继续")
                continue
            print(f"错误：拉取 {tool_name} 失败（{exc}）；旧缓存未改动。", file=sys.stderr)
            raise SystemExit(1)

    #   6. 三个工具全部落盘并打印摘要
    info = write_cache(cache_dir, payloads, args.service, endpoint, args.workspace)
    _print_summary(info, refreshed=True, cache_dir=cache_dir)


if __name__ == "__main__":
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
