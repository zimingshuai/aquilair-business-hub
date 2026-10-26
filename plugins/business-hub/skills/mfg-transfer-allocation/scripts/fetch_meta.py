"""预取 MCP 统一网关的业务元数据并落盘为技能级缓存。

主要 Input：--service 服务名（默认 aquilair-mcp，须存在于 .mcp.json）、
--workspace 本体项目 UUID（默认 mfg 制造业工厂调拨项目）、--token Bearer 凭证
（缺省按 环境变量 AQUILAIR_MCP_TOKEN / .mcp.json 条目 headers.Authorization 顺序兜底）、
--refresh 强制忽略缓存重拉、--url 直接指定 MCP 端点（通用拷贝安装时的兜底通道）。
主要 Output：技能目录 .meta-cache/ 下 model.json / rules.json / actions.json
三个元数据文件与 _cache-info.json（记录 workspace_id，不含凭证）；stdout 打印中文摘要。
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
# DEFAULT_SERVICE：统一网关在 .mcp.json 中的服务名（所有 mfg/fnb 域工具都挂在该服务下）。
DEFAULT_SERVICE = "aquilair-mcp"
# DEFAULT_WORKSPACE：mfg 本体项目「demo（勿动！！）」制造业工厂调拨的 workspace UUID，所有工具调用必填。
DEFAULT_WORKSPACE = "01a03bb7-2da4-7000-8dcf-1fb48f6f7fc9"
# META_TOOLS：要预取的三个元数据工具名 -> 缓存文件名的映射（共同必填参数 workspace_id）。
# model.json 落对象/关系级概要（refCode 映射，约 8KB）——不落 metadata_workspace_model 全量：
# 全量数百 KB，模型按需读缓存文件同样装不进上下文，且会话内直调亦会被工具结果预算截断；
# 属性级 PROP_ refCode 由技能主路径按需 metadata_object_neighborhood(ref_code, depth=0) 拉取。
META_TOOLS = {
    "metadata_list_object_types": "model.json",  # 对象/关系概要（OBJ_/REF_ refCode 映射）
    "metadata_list_rules": "rules.json",  # 规则清单
    "metadata_list_actions": "actions.json",  # 动作清单（未部署时写占位文件）
}
# TOKEN_ENV_VAR：Bearer 凭证的环境变量名（凭证三通道之二）。
TOKEN_ENV_VAR = "AQUILAIR_MCP_TOKEN"
# ACTIONS_PLACEHOLDER：action-service 未部署时写入 actions.json 的占位内容。
ACTIONS_PLACEHOLDER = {
    "status": "unavailable",
    "note": "action-service 未在本 workspace 部署动作（2026-10-22 实测 404）",
}
# UNAVAILABLE_MARKERS：判定「动作资源不存在（404 类）」的错误文案特征，大小写不敏感子串匹配。
UNAVAILABLE_MARKERS = ("404", "not found", "unavailable", "不存在")
# REQUEST_TIMEOUT_SECONDS：单次 HTTP 请求超时（内网服务，秒）。
REQUEST_TIMEOUT_SECONDS = 30
# SCRIPT_VERSION：脚本版本号，写入 _cache-info.json 便于排查缓存由哪版脚本生成。
SCRIPT_VERSION = "2.0.0"

# MCP 配置文件可能采用的两种文件名：多数 Agent Skills 宿主用带点前缀的项目级文件，
# 部分宿主的用户级全局配置不带点（如 WorkBuddy 的 ~/.workbuddy/mcp.json）；两种都纳入候选，
# 技能被拷到任意宿主目录层级都无需再改本脚本。
_MCP_CONFIG_FILENAMES = (".mcp.json", "mcp.json")


# ===========二、服务地址与凭证解析==========
def _candidate_mcp_json_paths() -> list[Path]:
    """返回 MCP 配置文件的候选查找路径（向上逐级搜索，任意宿主目录层级通吃）。

    排序为「目录由近及远 → 同目录内先 .mcp.json 后 mcp.json」，保证宿主自身的
    项目级配置优先于宿主的全局配置。

    Returns:
        按优先级排列的候选 Path 列表（其中部分可能不存在）。
    """
    # 从脚本所在目录起向上逐级（scripts/ -> 技能目录 -> skills/ -> 宿主包根 -> …… 直至文件系统根），
    # 近处优先：覆盖各类宿主的插件根/包根/用户级技能目录层级，各宿主无需再改本脚本。
    here = Path(__file__).resolve().parent
    candidates = [
        directory / file_name
        for directory in (here, *here.parents)
        for file_name in _MCP_CONFIG_FILENAMES
    ]
    candidates += [Path.cwd() / file_name for file_name in _MCP_CONFIG_FILENAMES]  # cwd 兜底（恰在其他仓库根运行时）
    return candidates


def _find_service_entry(service_name: str, quiet: bool = False) -> dict | None:
    """返回首个含目标服务的 .mcp.json 服务条目。

    Args:
        service_name: .mcp.json 中 mcpServers 下的服务名。
        quiet: 是否抑制「服务配置来源」日志（同一次运行内多处取配置时避免重复打印）。
    Returns:
        服务条目 dict（含 url/headers 等字段）；找不到时返回 None。
    """
    for config_path in _candidate_mcp_json_paths():
        if not config_path.is_file():
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config.get("mcpServers", {}).get(service_name)
        if entry:
            if not quiet:
                print(f"服务配置来源: {config_path}")
            return entry
    return None


def resolve_service_url(service_name: str, url_override: str | None) -> str:
    """解析目标 MCP 服务端点地址。

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
    #   2. 从候选 .mcp.json 条目取 url
    entry = _find_service_entry(service_name)
    if entry and entry.get("url"):
        return entry["url"]
    #   3. 全部落空：给出可操作的修复提示后退出
    print(
        f"错误：未找到含服务「{service_name}」的 .mcp.json"
        "（已从脚本目录向上逐级搜索至文件系统根，并检查了当前工作目录）。"
        "请在插件仓库根附近运行，或用 --url https://<host>/mcp 显式指定。",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _normalize_authorization(value: str) -> str:
    """把凭证值规范为 Authorization 头完整值（缺 Bearer 前缀时补上）。

    Args:
        value: 裸 token 或已含 Bearer 前缀的头值。
    Returns:
        形如 "Bearer xxx" 的 Authorization 头值。
    """
    value = value.strip()
    if value.lower().startswith("bearer "):
        return value
    return f"Bearer {value}"


def resolve_token(token_arg: str | None, service_name: str) -> str:
    """按三通道顺序解析 Bearer 凭证：--token > 环境变量 > .mcp.json headers.Authorization。

    Args:
        token_arg: 命令行 --token 传入的凭证（最高优先级）。
        service_name: .mcp.json 中的服务名（用于读取条目 headers.Authorization）。
    Returns:
        Authorization 头完整值；凭证值本身不进任何日志与缓存文件。
    Raises:
        SystemExit: 三通道皆无凭证时，以中文提示退出。
    """
    #   1. 命令行 --token
    if token_arg:
        print("凭证来源: --token 参数")
        return _normalize_authorization(token_arg)
    #   2. 环境变量 AQUILAIR_MCP_TOKEN
    env_token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if env_token:
        print(f"凭证来源: 环境变量 {TOKEN_ENV_VAR}")
        return _normalize_authorization(env_token)
    #   3. .mcp.json 条目 headers.Authorization（宿主可能把凭证写进配置）
    entry = _find_service_entry(service_name, quiet=True)
    header_auth = ((entry or {}).get("headers") or {}).get("Authorization", "")
    if header_auth.strip():
        print("凭证来源: .mcp.json headers.Authorization")
        return _normalize_authorization(header_auth)
    #   4. 皆无：统一网关要求 OAuth Bearer 鉴权，缺凭证无法握手
    print(
        f"错误：未获取到 Bearer 凭证（已按序检查 --token 参数、环境变量 {TOKEN_ENV_VAR}、"
        ".mcp.json 条目 headers.Authorization）。统一网关要求 OAuth Bearer 鉴权，"
        "请通过 --token 传入或先设置环境变量。",
        file=sys.stderr,
    )
    raise SystemExit(1)


# ===========三、MCP 握手与工具调用==========
def _post_rpc(
    endpoint: str, authorization: str, session_id: str | None, payload: dict
) -> tuple[str, Any]:
    """发送单个 JSON-RPC 请求并返回原始响应文本与响应头。

    Args:
        endpoint: MCP 端点 URL。
        authorization: Authorization 头完整值（Bearer 凭证，每个请求都携带）。
        session_id: MCP 会话 ID；None 表示握手阶段或服务端未下发会话。
        payload: JSON-RPC 请求体。
    Returns:
        (原始响应文本, 响应头映射)；响应可能为 SSE 流格式，由上层解析。
    Raises:
        RuntimeError: 网络失败或 HTTP 错误（错误文案含状态码与响应体片段，供上层识别 404 等）。
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": authorization,
    }
    # 会话头：统一网关为有会话模式，initialize 响应下发 Mcp-Session-Id，后续请求须回带
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8"), response.headers
    except urllib.error.HTTPError as exc:
        # HTTPError 需读响应体片段：404 类错误的占位判型依赖正文特征（如「资源不存在」）
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:300]
        except OSError:
            body = ""
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}：{body}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"网络请求失败：{exc}") from exc


def _parse_rpc_result(raw_text: str, tool_name: str) -> Any:
    """解析 tools/call 响应并取出内层数据。

    Args:
        raw_text: 服务端原始响应文本（流式实现可能以 SSE 格式包裹，取 data: 行拼接兜底）。
        tool_name: 工具名（用于错误提示定位）。
    Returns:
        工具返回 text 字段解析后的内层数据（通常为 dict）；服务端返回纯文本时原样返回 str。
    Raises:
        RuntimeError: 响应不是合法 JSON、JSON-RPC 层报错或工具级 isError。
    """
    payload_text = raw_text
    if raw_text.lstrip().startswith(("event:", "data:")):
        payload_text = "".join(
            line[len("data:"):]
            for line in raw_text.splitlines()
            if line.startswith("data:")
        )
    try:
        rpc_response = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"外层响应不是合法 JSON：{payload_text[:200]}") from exc
    if "error" in rpc_response:
        raise RuntimeError(f"服务端返回 JSON-RPC 错误：{rpc_response['error']}")
    result = rpc_response.get("result", {})
    if result.get("isError"):
        raise RuntimeError(f"工具 {tool_name} 返回 isError=True：{result}")
    content = result.get("content", [])
    if not content or content[0].get("type") != "text":
        raise RuntimeError(f"工具 {tool_name} 返回无文本内容：{result}")
    # 内层为双层 JSON：text 字段里还是 JSON 字符串；解析失败按纯文本原样返回
    try:
        return json.loads(content[0]["text"])
    except json.JSONDecodeError:
        return content[0]["text"]


def open_session(endpoint: str, authorization: str) -> str | None:
    """执行 MCP 完整握手：initialize（带凭证）→ 记录 Mcp-Session-Id → notifications/initialized。

    Args:
        endpoint: MCP 端点 URL。
        authorization: Authorization 头完整值。
    Returns:
        服务端下发的 Mcp-Session-Id；未下发（无会话模式）时返回 None。
    Raises:
        RuntimeError: 握手阶段网络或协议失败。
    """
    #   1. initialize：统一网关要求带 Authorization 初始化
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "aquilair-fetch-meta", "version": SCRIPT_VERSION},
        },
    }
    _, init_headers = _post_rpc(endpoint, authorization, None, init_payload)
    session_id = init_headers.get("Mcp-Session-Id")
    #   2. notifications/initialized：完成握手（通知无 id、无响应体，发出即算成功）
    _post_rpc(
        endpoint,
        authorization,
        session_id,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    print(f"====MCP 握手完成====: 会话 {'已建立' if session_id else '无会话 ID（服务端未下发）'}")
    return session_id


def call_tool(
    endpoint: str,
    authorization: str,
    session_id: str | None,
    tool_name: str,
    arguments: dict,
) -> Any:
    """调用指定 MCP 工具并返回内层数据。

    Args:
        endpoint: MCP 端点 URL。
        authorization: Authorization 头完整值。
        session_id: 握手取得的会话 ID（可为 None）。
        tool_name: 工具名（三个 metadata_* 工具之一）。
        arguments: 工具参数（本脚本恒为 {"workspace_id": ...}）。
    Returns:
        工具返回的内层数据。
    Raises:
        RuntimeError: 网络、协议或工具级错误。
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    raw_text, _ = _post_rpc(endpoint, authorization, session_id, payload)
    return _parse_rpc_result(raw_text, tool_name)


# ===========四、元数据拉取与缓存读写==========
def _is_unavailable_error(message: str) -> bool:
    """判定错误文案是否属于「动作资源不存在（404 类）」，用于 actions 占位降级判型。

    Args:
        message: RuntimeError 的错误文案（含状态码或响应体片段）。
    Returns:
        命中任一特征返回 True。
    """
    lowered = message.lower()
    return any(marker in lowered for marker in UNAVAILABLE_MARKERS)


def fetch_meta_payloads(
    endpoint: str, authorization: str, workspace_id: str
) -> tuple[dict[str, Any], set[str]]:
    """握手后依次拉取三个元数据工具。

    Args:
        endpoint: MCP 端点 URL。
        authorization: Authorization 头完整值。
        workspace_id: 本体项目 UUID（三个工具的共同必填参数）。
    Returns:
        (工具名到内层数据的映射, 写入占位的工具名集合)。
    Raises:
        RuntimeError: model/rules 任一失败，或 actions 失败且不属于 404 类——
            由调用方中止且不动旧缓存。
    """
    session_id = open_session(endpoint, authorization)
    payloads: dict[str, Any] = {}
    unavailable_tools: set[str] = set()
    for tool_name in META_TOOLS:
        try:
            payloads[tool_name] = call_tool(
                endpoint,
                authorization,
                session_id,
                tool_name,
                {"workspace_id": workspace_id},
            )
            print(f"====元数据拉取成功====: {tool_name}")
        except RuntimeError as exc:
            # actions 404/资源不存在 -> 写占位说明并继续；model/rules 失败或其他错误 -> 整体中止
            if tool_name == "metadata_list_actions" and _is_unavailable_error(str(exc)):
                payloads[tool_name] = dict(ACTIONS_PLACEHOLDER)
                unavailable_tools.add(tool_name)
                print(f"====动作元数据不可用====: {tool_name}（{exc}），已写占位说明")
                continue
            raise
    return payloads, unavailable_tools


def write_cache(
    cache_dir: Path,
    payloads: dict[str, Any],
    service_name: str,
    endpoint: str,
    workspace_id: str,
    unavailable_tools: set[str],
) -> dict[str, Any]:
    """把三个元数据 payload 统一写入缓存目录并生成 _cache-info.json。

    Args:
        cache_dir: 缓存目录（技能目录下 .meta-cache）。
        payloads: 工具名到内层数据的映射（三个工具须已全部就绪，含占位）。
        service_name: 服务名，写入缓存元信息便于核对数据来源。
        endpoint: 实际拉取的 MCP 端点。
        workspace_id: 本次拉取的本体项目 UUID（缓存复用按它判断归属）。
        unavailable_tools: 写入占位的工具名集合（摘要中标注「未部署」）。
    Returns:
        缓存元信息 dict（含 workspace_id 与各文件统计），供摘要打印复用。
    """
    #   1. 写三个数据文件；items 为内层 JSON 顶层条目数（对象数/规则数/动作数），占位文件不计数
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
        is_placeholder = tool_name in unavailable_tools
        stats[file_name] = {
            "bytes": data_path.stat().st_size,
            "items": None
            if is_placeholder
            else (len(payload) if isinstance(payload, (dict, list)) else None),
            "unavailable": is_placeholder,
        }
    #   2. 生成缓存元信息（workspace 供复用判断归属，键名与 fnb 技能副本一致；凭证绝不写入）
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
    print(f"workspace: {info.get('workspace', '未知（旧缓存）')}")
    print(f"拉取时间: {info['fetched_at']}")
    for file_name, file_stats in info["files"].items():
        if file_stats.get("unavailable"):
            print(f"- {file_name}: 动作未部署占位说明, {file_stats['bytes'] / 1024:.1f} KB")
        elif isinstance(file_stats.get("items"), str):
            # items 为字符串时是占位说明文案（如手工落盘缓存），原样打印不加「个条目」后缀
            print(f"- {file_name}: {file_stats['items']}, {file_stats['bytes'] / 1024:.1f} KB")
        else:
            item_label = (
                f"{file_stats['items']} 个条目" if file_stats["items"] is not None else "非结构化内容"
            )
            print(f"- {file_name}: {item_label}, {file_stats['bytes'] / 1024:.1f} KB")
    print(f"缓存目录: {cache_dir}")
    print("需要服务端最新数据时加 --refresh 重拉")


# ===========五、命令行入口==========
def main() -> None:
    """命令行入口：缓存完整（服务与 workspace 均一致）且未要求刷新时直接复用，否则握手拉取并落盘。"""
    parser = argparse.ArgumentParser(description="预取 MCP 统一网关业务元数据并落盘为技能级缓存")
    parser.add_argument("--service", default=DEFAULT_SERVICE, help=f".mcp.json 中的服务名（默认 {DEFAULT_SERVICE}）")
    parser.add_argument(
        "--workspace", default=DEFAULT_WORKSPACE,
        help=f"本体项目 workspace UUID（默认 mfg 制造业工厂调拨项目 {DEFAULT_WORKSPACE}）",
    )
    parser.add_argument("--refresh", action="store_true", help="忽略现有缓存，强制重新拉取")
    parser.add_argument("--url", default=None, help="直接指定 MCP 端点（如 https://host/mcp），跳过 .mcp.json 查找")
    parser.add_argument("--token", default=None, help="Bearer 凭证（缺省按环境变量 AQUILAIR_MCP_TOKEN / .mcp.json 顺序兜底）")
    args = parser.parse_args()

    #   1. 定位缓存目录（技能目录下 .meta-cache）
    skill_dir = Path(__file__).resolve().parent.parent
    cache_dir = skill_dir / ".meta-cache"
    cache_info_path = cache_dir / "_cache-info.json"

    #   2. 缓存完整、归属服务与 workspace 均一致且未要求刷新时直接复用，不发起任何网络请求
    cache_files_exist = all(
        (cache_dir / file_name).is_file() for file_name in META_TOOLS.values()
    )
    if cache_files_exist and cache_info_path.is_file() and not args.refresh:
        info = json.loads(cache_info_path.read_text(encoding="utf-8"))
        if (
            info.get("service") == args.service
            and info.get("workspace") == args.workspace
        ):
            _print_summary(info, refreshed=False, cache_dir=cache_dir)
            return

    #   3. 解析服务地址与凭证（凭证值不进日志与缓存），握手拉取；任一必要工具失败即中止且不动旧缓存
    endpoint = resolve_service_url(args.service, args.url)
    authorization = resolve_token(args.token, args.service)
    try:
        payloads, unavailable_tools = fetch_meta_payloads(
            endpoint, authorization, args.workspace
        )
    except RuntimeError as exc:
        print(f"错误：元数据拉取失败（{exc}）；旧缓存未改动。", file=sys.stderr)
        raise SystemExit(1)

    #   4. 三个工具全部就绪（含 actions 占位）后统一落盘并打印摘要
    info = write_cache(
        cache_dir, payloads, args.service, endpoint, args.workspace, unavailable_tools
    )
    _print_summary(info, refreshed=True, cache_dir=cache_dir)


if __name__ == "__main__":
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
