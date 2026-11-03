# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""把模型经 MCP 连接器取回的元数据四清单固化为技能级缓存（纯存档脚本）。

架构说明：数据由模型经宿主 MCP 连接器调用 metadata_* 四清单工具获取——天然带宿主 OAuth
授权，本脚本进程不持有任何凭证、不发起任何网络请求，只负责校验、固化与规范化。

主要 Input：位置参数=包装 JSON 文件路径（缺省 "-" 读 stdin）；--workspace 可选记录数据归属。
包装格式（各键值=对应工具返回 content[0].text 的原样 JSON；算法清单空时可传 null）：
  {"object_types": <object_types 返回>, "rules": <rules 返回>,
   "actions": <actions 返回>, "algorithms": <algorithms 返回或 null>}
主要 Output：技能目录 .meta-cache/ 下 model.json / rules.json / actions.json / algorithms.json
与 _cache-info.json（service、workspace、fetched_at、各文件字节数与条目数；不含任何凭证）；
stdout 打印中文摘要。校验失败即报错退出，不写半截、不破坏旧缓存。
"""

# 标准库导入
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ===========一、常量与配置==========
# SERVICE_NAME：数据来源的 MCP 服务名（写入 _cache-info.json 便于核对，非业务数据值）。
SERVICE_NAME = "aquilair-mcp-servers"
# CACHE_DIR_NAME：技能目录下的缓存目录名（与 SKILL.md 约定一致，运行时生成不入库）。
CACHE_DIR_NAME = ".meta-cache"
# KEY_TO_FILE：包装 JSON 四键 -> 缓存文件名的映射（model.json 存 list_object_types 全量，
# 含 object_types 与 link_types 两个清单）。
KEY_TO_FILE = {
    "object_types": "model.json",
    "rules": "rules.json",
    "actions": "actions.json",
    "algorithms": "algorithms.json",
}
# ALGORITHMS_EMPTY_NOTE：算法清单为 null 或空时的占位 JSON 内容（空文件无信息量）。
ALGORITHMS_EMPTY_NOTE = {"status": "empty", "note": "本项目未注册算法"}
# SCRIPT_VERSION：脚本版本号，写入 _cache-info.json 便于排查缓存由哪版脚本生成。
SCRIPT_VERSION = "2.0.0"


# ===========二、输入读取与校验==========
def read_wrapper(source: str) -> dict[str, Any]:
    """读取并解析包装 JSON（文件路径或 "-" 表示 stdin）。

    Args:
        source: 包装 JSON 文件路径；"-" 时从 stdin 读取。
    Returns:
        解析后的顶层 dict。
    Raises:
        SystemExit: 读取失败或不是合法 JSON / 顶层不是 dict 时，以中文提示退出。
    """
    #   1. 读取原始文本（stdin 统一按 UTF-8 解码，防 Windows 管道乱码）→ 解析 JSON → 校验顶层
    try:
        raw_text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"错误：无法读取输入文件 {source}（{exc}）。", file=sys.stderr)
        raise SystemExit(1)
    try:
        wrapper = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"错误：输入不是合法 JSON（{exc}）；应为四键包装结构，见 --help 说明。", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(wrapper, dict):
        print("错误：包装 JSON 顶层必须是对象（四键结构），见 --help 说明。", file=sys.stderr)
        raise SystemExit(1)
    return wrapper


def validate_payloads(wrapper: dict[str, Any]) -> dict[str, Any]:
    """校验四键结构与数据形态，返回键到落盘内容的映射（算法空清单归一为占位）。

    Args:
        wrapper: read_wrapper 返回的顶层 dict（四键；algorithms 允许 null）。
    Returns:
        键到落盘内容的映射（object_types/rules/actions 原样；algorithms 空时为占位 dict）。
    Raises:
        SystemExit: 任一键缺失、为 null（algorithms 除外）或形态不符时，以中文提示退出。
    """
    #   1. 四键必须齐全（algorithms 允许 null，其余三键缺失或为 null 均视为无效）
    payloads: dict[str, Any] = {}
    for key in KEY_TO_FILE:
        value = wrapper.get(key)
        if value is None and key != "algorithms":
            print(f"错误：包装 JSON 缺少有效键「{key}」（不可缺失或为 null）。", file=sys.stderr)
            raise SystemExit(1)
        payloads[key] = value
    #   2. object_types：必须是 dict 且含非空 object_types 键（list_object_types 返回形态）
    ot = payloads["object_types"]
    if not isinstance(ot, dict) or not isinstance(ot.get("object_types"), list) or not ot["object_types"]:
        print("错误：object_types 必须是含非空「object_types」清单的对象（metadata_list_object_types 原样返回）。", file=sys.stderr)
        raise SystemExit(1)
    #   3. rules/actions：必须是可计数的 list/dict（实测为纯 list，防御 dict 包装形态）
    for key in ("rules", "actions"):
        if not isinstance(payloads[key], (list, dict)):
            print(f"错误：「{key}」必须是 list 或 dict（对应清单工具的原样返回）。", file=sys.stderr)
            raise SystemExit(1)
    #   4. algorithms：null 或空清单归一为占位说明；非空 list/dict 照常落盘
    alg = payloads["algorithms"]
    if alg is None or isinstance(alg, (list, dict)) and len(alg) == 0:
        payloads["algorithms"] = ALGORITHMS_EMPTY_NOTE
        print("====算法清单为空====: algorithms.json 写占位说明")
    elif not isinstance(alg, (list, dict)):
        print("错误：「algorithms」为 null、空清单或 list/dict 之一（非空时不可为其他类型）。", file=sys.stderr)
        raise SystemExit(1)
    return payloads


def count_items(key: str, payload: Any) -> int:
    """统计单个清单的条目数（供 _cache-info.json 与摘要使用）。

    Args:
        key: 包装 JSON 的键名（object_types/rules/actions/algorithms）。
        payload: 该键的落盘内容（占位 dict 已由 validate_payloads 归一）。
    Returns:
        条目数；无法计数时返回 0。
    """
    # 占位说明不数条目（status=empty 标记）；object_types 取内层清单长度（顶层还有 link_types）；其余直接计数
    if isinstance(payload, dict) and payload.get("status") == "empty":
        return 0
    return len(payload["object_types"]) if key == "object_types" else (len(payload) if isinstance(payload, (list, dict)) else 0)


# ===========三、原子落盘与摘要==========
def write_cache(cache_dir: Path, payloads: dict[str, Any], workspace: str | None) -> dict[str, Any]:
    """把四份数据文件与 _cache-info.json 原子写入缓存目录（半截失败不破坏旧缓存）。

    Args:
        cache_dir: 缓存目录（技能目录下 .meta-cache）。
        payloads: validate_payloads 返回的键到落盘内容映射。
        workspace: 可选 workspace_id（仅记录归属，不影响写入内容）。
    Returns:
        缓存元信息 dict（_cache-info.json 同一份内容），供摘要打印复用。
    Raises:
        SystemExit: 任一临时文件写入失败时清理全部临时文件后退出（旧缓存不动）。
    """
    #   1. 先在内存中组装全部目标文本与统计（字节提前算好，_cache-info.json 与数据文件同批写）
    cache_dir.mkdir(parents=True, exist_ok=True)
    texts: dict[str, str] = {
        file_name: json.dumps(payloads[key], ensure_ascii=False, indent=2)
        for key, file_name in KEY_TO_FILE.items()
    }
    info: dict[str, Any] = {
        "service": SERVICE_NAME,
        "workspace": workspace,
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "script_version": SCRIPT_VERSION,
        "files": {
            file_name: {
                "bytes": len(texts[file_name].encode("utf-8")),
                "items": count_items(key, payloads[key]),
            }
            for key, file_name in KEY_TO_FILE.items()
        },
    }
    texts["_cache-info.json"] = json.dumps(info, ensure_ascii=False, indent=2)
    #   2. 全部先写 .tmp 临时文件（任一失败即清理所有 tmp 并退出，不触碰正式文件）
    tmp_pairs: list[tuple[Path, Path]] = []
    try:
        for file_name, text in texts.items():
            tmp_path = cache_dir / f"{file_name}.tmp"
            tmp_path.write_text(text, encoding="utf-8")
            tmp_pairs.append((tmp_path, cache_dir / file_name))
    except OSError as exc:
        for tmp_path, _ in tmp_pairs:
            tmp_path.unlink(missing_ok=True)
        print(f"错误：写临时文件失败（{exc}）；已放弃写入，旧缓存未改动。", file=sys.stderr)
        raise SystemExit(1)
    #   3. 临时文件全部就绪后逐一原子重命名（os.replace 同目录内原子生效）
    for tmp_path, final_path in tmp_pairs:
        os.replace(tmp_path, final_path)
    return info


def print_summary(info: dict[str, Any], cache_dir: Path) -> None:
    """打印缓存摘要（关键事件 ==== 定界，逐文件条目数，供模型判断是否细读文件）。

    Args:
        info: write_cache 返回的缓存元信息 dict。
        cache_dir: 缓存目录绝对路径。
    Returns:
        None。
    """
    print("====元数据缓存就绪====")
    for file_name, file_stats in info["files"].items():
        note = "（占位：本项目未注册算法）" if file_name == "algorithms.json" and file_stats["items"] == 0 else ""
        print(f"- {file_name}: {file_stats['items']} 个条目{note}, {file_stats['bytes'] / 1024:.1f} KB")
    print(f"service: {info['service']}  workspace: {info['workspace'] or '未提供'}")
    print(f"fetched_at: {info['fetched_at']}")
    print(f"缓存目录: {cache_dir}")


# ===========四、命令行入口==========
def main() -> None:
    """命令行入口：读取包装 JSON -> 校验四键 -> 原子落盘 -> 打印中文摘要。"""
    parser = argparse.ArgumentParser(
        description=(
            "元数据四清单存档脚本（纯存档，零网络零凭证）：数据由模型经宿主 MCP 连接器调用 "
            "metadata_* 四清单工具获取——天然带宿主 OAuth 授权，本脚本只负责把四段返回 "
            "content[0].text 的原样 JSON 固化为 .meta-cache/ 缓存"
        ),
        epilog=(
            "使用示例：\n"
            "  1. 模型先调四清单工具（带 workspace_id），把四段返回拼成包装 JSON 文件：\n"
            '     {"object_types": {...}, "rules": [...], "actions": [...], "algorithms": null}\n'
            "  2. python scripts/save_meta.py 包装文件.json --workspace <workspace_id>\n"
            "  3. 后续会话直接读 .meta-cache/ 缓存省往返；_cache-info.json 的 fetched_at 超 7 天重拉"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", nargs="?", default="-", help="包装 JSON 文件路径（缺省读 stdin）")
    parser.add_argument("--workspace", default=None, help="数据归属的 workspace_id（可选，仅记入 _cache-info.json）")
    args = parser.parse_args()

    #   1. 定位缓存目录（技能目录下 .meta-cache）→ 校验 → 原子落盘 → 摘要
    cache_dir = Path(__file__).resolve().parent.parent / CACHE_DIR_NAME
    wrapper = read_wrapper(args.source)
    payloads = validate_payloads(wrapper)
    info = write_cache(cache_dir, payloads, args.workspace)
    print_summary(info, cache_dir)


if __name__ == "__main__":
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    main()
