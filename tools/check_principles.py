"""行为口径治理闸门：以 tools/principles.yaml 为单一事实源校验口径一致性。

主要 Input：tools/principles.yaml（口径锚点 / 影响面 / 禁词变体库）与命令行参数
（--impact <口径id> 列影响面清单；--extra-surface <path> 可多次，追加 WorkBuddy
experts-src 镜像人设一并校验）。
主要 Output：控制台中文巡检报告（====定界，逐口径 PASS/FAIL）+ 进程退出码——
锚点缺失或禁词残留即 1（不降级放行），供 pre-commit / CI 与 WorkBuddy install --check 挂闸。

检查项（口径 × 影响面双向扫描；立项背景与口径数据结构见 principles.yaml 文件头）：
  P0  结构性——yaml 缺失/结构非法/条目缺键、影响面文件不存在
  P1  正向——该口径全部锚点均不在影响面文件在场（口径被删或漂移）
  P2  反向——禁词变体（历史事故旧措辞）残留任一处

镜像规则：--extra-surface 追加的文件与某 hub 侧 /agents/<name>.md 条目同名
（文件名去扩展名比对）时，复用该条目的适配锚点与禁词——WorkBuddy 人设是
hub origin 快照加适配字段，口径同构；不同名则用该口径默认锚点与禁词。

零第三方库：principles.yaml 结构为本脚本自定义的固定两级嵌套，手写解析
（与 tools/lint_skills.py 同款零依赖纪律）——挂闸环境（pre-commit /
WorkBuddy refresh 链路）不必安装 PyYAML。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# LEVEL_ERROR：问题级别——本闸门全部按 ERROR 处理（问题即阻断，无 WARN 放行）
LEVEL_ERROR = "ERROR"
# PRINCIPLES_YAML：口径数据文件（相对 hub 仓根，行为口径唯一事实源）
PRINCIPLES_YAML = Path("tools") / "principles.yaml"
# REQUIRED_KEYS：每条口径的必备键，缺失即 P0 结构性问题
REQUIRED_KEYS = ("anchors", "surfaces", "stale_variants")
# MIRROR_DIR_HINT：hub 侧 agent 人设的路径段——含此段的 surface 有 WorkBuddy 镜像
# （experts-src/<name>/agents/<name>.md），--impact 据此提示改版 checklist 同步面
MIRROR_DIR_HINT = "/agents/"
# INDENT_PRINCIPLES / INDENT_ID / INDENT_KEY / INDENT_ITEM / INDENT_SUB / INDENT_SUB_ITEM：
# principles.yaml 各层级缩进列数（固定结构：顶层 -> 口径 id -> 键 -> 列表项 -> 对象
# 条目子键 -> 子键列表项），手写解析器据此分派
INDENT_PRINCIPLES, INDENT_ID, INDENT_KEY, INDENT_ITEM, INDENT_SUB, INDENT_SUB_ITEM = 0, 2, 4, 6, 8, 10


# ===========一、口径数据加载与条目归一化==========
def _parse_principles_yaml(text: str) -> tuple[dict, list[str]]:
    """手写解析 principles.yaml 的固定结构（零第三方库，见文件头说明）。

    Args:
        text: yaml 文件全文。
    Returns:
        (口径字典 {口径id: {note?, anchors, stale_variants, surfaces}}，结构问题列表)
        ——surfaces 条目为字符串或 {path, anchors, stale_variants, note} 映射；
        遇到非约定缩进/游离行时收集问题（不抛异常，由 P0 兜底阻断）。
    """
    principles: dict = {}
    problems: list[str] = []
    # current_pid：当前口径 id；current_list_key：口径层当前打开的列表键
    # current_entry：对象型 surface 条目；entry_list_key：条目内当前打开的列表键
    current_pid: str | None = None
    current_list_key: str | None = None
    current_entry: dict | None = None
    entry_list_key: str | None = None
    for line_no, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        # 列表项行：口径层（6 列）追加进当前列表；对象条目子列表（10 列）追加进条目
        if content.startswith("- ") or content == "-":
            item = content[1:].strip()
            if indent == INDENT_ITEM:
                if item.startswith("path:"):
                    # 对象型 surface 条目起始：- path: <路径>
                    current_entry = {"path": item.partition(":")[2].strip(), "anchors": [], "stale_variants": [], "note": ""}
                    if current_pid and current_list_key == "surfaces":
                        principles[current_pid]["surfaces"].append(current_entry)
                    else:
                        problems.append(f"P0 第 {line_no} 行：对象条目出现在非 surfaces 列表下")
                    entry_list_key = None
                elif current_pid and current_list_key:
                    principles[current_pid][current_list_key].append(item)  # 字符串条目
                    current_entry = None
                else:
                    problems.append(f"P0 第 {line_no} 行：列表项无归属口径/键")
            elif indent == INDENT_SUB_ITEM and current_entry is not None and entry_list_key:
                current_entry[entry_list_key].append(item)
            else:
                problems.append(f"P0 第 {line_no} 行：非约定缩进的列表项（{indent} 列）")
            continue
        # 键行：按第一个 ASCII 冒号切键值（note 文本内的中文冒号不受影响）
        key, _, value = content.partition(":")
        key, value = key.strip(), value.strip()
        if indent == INDENT_PRINCIPLES:
            if key != "principles":
                problems.append(f"P0 第 {line_no} 行：非约定顶层键 {key!r}（仅允许 principles）")
            current_pid, current_list_key, current_entry = None, None, None
        elif indent == INDENT_ID:
            current_pid, current_list_key, current_entry = key, None, None
            principles.setdefault(current_pid, {})
        elif indent == INDENT_KEY:
            if current_pid is None:
                problems.append(f"P0 第 {line_no} 行：口径键出现在任何口径 id 之前")
                continue
            if value:
                principles[current_pid][key] = value  # note 单行文本
            else:
                principles[current_pid][key] = []  # anchors/stale_variants/surfaces 列表
                current_list_key = key
            current_entry = None
        elif indent == INDENT_SUB and current_entry is not None:
            if value:
                current_entry[key] = value  # 条目内 note 单行文本
            else:
                current_entry[key] = current_entry.get(key) or []
                entry_list_key = key
        else:
            problems.append(f"P0 第 {line_no} 行：非约定缩进的键行（{indent} 列）")
    return principles, problems


def load_principles(repo_root: Path) -> tuple[dict, list[str]]:
    """加载并做结构校验 principles.yaml。

    Args:
        repo_root: hub 仓根目录路径。
    Returns:
        (口径字典 {口径id: 口径配置}，结构性问题列表)——yaml 缺失或结构非法时
        口径字典为空字典，问题列表非空，由调用方按 P0 阻断。
    """
    yaml_path = repo_root / PRINCIPLES_YAML
    if not yaml_path.is_file():
        return {}, [f"P0 口径数据缺失 {yaml_path}（唯一事实源被删/移动？）"]
    principles, problems = _parse_principles_yaml(yaml_path.read_text(encoding="utf-8"))
    if not principles:
        return {}, problems or [f"P0 {PRINCIPLES_YAML} 未解析到任何口径"]
    for pid, spec in principles.items():
        if not isinstance(spec, dict):
            problems.append(f"P0 口径 {pid} 配置非映射（{type(spec).__name__}）")
            continue
        for key in REQUIRED_KEYS:
            if not spec.get(key):
                problems.append(f"P0 口径 {pid} 缺键或为空：{key}")
    return principles, problems


def normalize_surface(spec: str | dict, pid: str) -> dict:
    """把 surfaces 条目（字符串或对象）归一化为统一形态。

    Args:
        spec: yaml 中单条 surface——字符串（相对仓根路径）或含 path/anchors/
            stale_variants/note 的对象（提供即整体替换默认，见 yaml 头注释）。
        pid: 所属口径 id（错误提示定位用）。
    Returns:
        归一化条目 {path, anchors, stale_variants, note}——anchors/stale_variants
        为 None 表示未适配（沿用口径默认）。
    """
    if isinstance(spec, str):
        return {"path": spec, "anchors": None, "stale_variants": None, "note": ""}
    # path 键缺失时占位空串，由文件存在性检查报 P0
    return {
        "path": str(spec.get("path", "")),
        "anchors": list(spec["anchors"]) if spec.get("anchors") else None,
        "stale_variants": list(spec["stale_variants"]) if spec.get("stale_variants") else None,
        "note": str(spec.get("note", "")),
    }


# ===========二、口径校验==========
def check_principle(
    pid: str,
    spec: dict,
    repo_root: Path,
    extra_surfaces: list[Path],
) -> list[tuple[str, str, str]]:
    """对单条口径执行全部影响面的正向锚点 + 反向禁词扫描。

    Args:
        pid: 口径 id。
        spec: 该口径配置（note / anchors / surfaces / stale_variants）。
        repo_root: hub 仓根目录路径。
        extra_surfaces: 追加的镜像人设路径列表（WorkBuddy 端注入，hub 端为空）。
    Returns:
        问题元组列表 (级别, 检查项编号, 中文说明)，无问题时为空列表。
    """
    issues: list[tuple[str, str, str]] = []
    # entries：归一化后的 hub 侧影响面条目
    entries = [normalize_surface(s, pid) for s in spec["surfaces"]]
    # stem_index：hub 侧条目按文件名（去扩展名）索引——镜像人设复用同名条目的适配配置
    stem_index = {Path(e["path"]).stem: e for e in entries if e["path"]}
    # scan_targets：hub 条目 + 镜像条目（镜像仅追加人设文件，复用同名适配或口径默认）
    scan_targets: list[dict] = list(entries)
    for extra in extra_surfaces:
        matched = stem_index.get(extra.stem)
        scan_targets.append({
            "path": str(extra),
            "anchors": matched["anchors"] if matched else None,
            "stale_variants": matched["stale_variants"] if matched else None,
            "note": matched["note"] if matched else "",
        })
    for entry in scan_targets:
        # anchors / stale：本面生效的锚点与禁词（适配覆盖或口径默认）
        anchors = entry["anchors"] or list(spec["anchors"])
        stale = entry["stale_variants"] or list(spec["stale_variants"])
        rel = entry["path"] or "<空路径>"
        surface_path = Path(entry["path"])
        file_path = surface_path if surface_path.is_absolute() else repo_root / surface_path
        if not file_path.is_file():
            issues.append((LEVEL_ERROR, "P0", f"{pid}｜{rel} 影响面文件不存在"))
            continue
        text = file_path.read_text(encoding="utf-8")
        #   1. P1 正向：任一锚点在场即合格，全缺即口径漂移
        # anchor_hint：锚点清单的展示串（报错时指明应回写哪些措辞）
        if not any(anchor in text for anchor in anchors):
            anchor_hint = " / ".join(anchors)
            issues.append((LEVEL_ERROR, "P1", f"{pid}｜{rel} 锚点缺失：任一锚点均不在场（{anchor_hint}）——口径被删或漂移，按 yaml 现行口径回写"))
        #   2. P2 反向：禁词变体出现任一处即旧口径残留
        for variant in stale:
            if variant in text:
                issues.append((LEVEL_ERROR, "P2", f"{pid}｜{rel} 残留旧口径变体：「{variant}」——按 yaml 现行口径改写"))
    return issues


# ===========三、报告输出与集成入口==========
def run_principles_check(
    repo_root: Path,
    extra_surfaces: list[Path] | None = None,
) -> int:
    """执行全量口径巡检，打印中文报告并返回退出码（lint_skills 集成与 CLI 共用）。

    Args:
        repo_root: hub 仓根目录路径。
        extra_surfaces: 追加的镜像人设路径列表（WorkBuddy 端注入）。
    Returns:
        进程退出码：存在任何问题为 1，否则为 0。
    """
    extra_surfaces = extra_surfaces or []
    principles, struct_problems = load_principles(repo_root)
    print("====行为口径巡检（principles.yaml 单一事实源）====")
    # per_principle：逐口径问题列表（P0 结构问题独立成节，不挂在任何口径下）
    per_principle: list[tuple[str, list[tuple[str, str, str]]]] = []
    for pid in sorted(principles):
        spec = principles[pid]
        if any(not spec.get(key) for key in REQUIRED_KEYS):
            continue  # 缺键口径已在结构问题中报 P0，跳过扫描避免二次崩溃
        per_principle.append((pid, check_principle(pid, spec, repo_root, extra_surfaces)))
    error_total = 0
    for pid, issues in per_principle:
        if not issues:
            note = str(principles[pid].get("note", "")).split("——")[0]
            print(f"[PASS] {pid}（{note}）")
            continue
        print(f"[FAIL] {pid}")
        for level, code, message in issues:
            print(f"  ❌ [{level}][{code}] {message}")
            error_total += 1
    if struct_problems:
        print("[FAIL] 结构")
        for message in struct_problems:
            print(f"  ❌ [{LEVEL_ERROR}][P0] {message}")
            error_total += 1
    pass_total = sum(1 for _, issues in per_principle if not issues)
    verdict = "不通过（须修复后交付）" if error_total else "通过"
    scope = f"+镜像 {len(extra_surfaces)} 面" if extra_surfaces else ""
    print(f"====口径巡检汇总====: 口径 {len(per_principle) or len(struct_problems)} 条（PASS {pass_total}）{scope} | ERROR {error_total} | 结论：{verdict}")
    return 1 if error_total else 0


def print_impact(pid: str, repo_root: Path) -> int:
    """打印指定口径的影响面清单（改版 checklist 用）。

    Args:
        pid: 口径 id（须存在于 yaml）。
        repo_root: hub 仓根目录路径。
    Returns:
        进程退出码：口径不存在为 1，否则为 0。
    """
    principles, struct_problems = load_principles(repo_root)
    for message in struct_problems:
        print(f"  ❌ [{LEVEL_ERROR}][P0] {message}")
    if pid not in principles:
        print(f"====影响面清单：{pid} 不存在（可选口径：{' / '.join(sorted(principles))}）====")
        return 1
    spec = principles[pid]
    print(f"====影响面清单：{pid}（{spec.get('note', '')}）====")
    for raw in spec["surfaces"]:
        entry = normalize_surface(raw, pid)
        # adapted：对象条目标注适配锚点，改版时按适配措辞同步
        adapted = f"（适配锚点：{' / '.join(entry['anchors'])}）" if entry["anchors"] else ""
        print(f"  [hub]{adapted} {entry['path']}")
        if MIRROR_DIR_HINT in entry["path"]:
            # mirror：WorkBuddy 镜像人设（install --check 经 --extra-surface 校验）
            name = Path(entry["path"]).stem
            print(f"  [workbuddy 镜像] experts-src/{name}/agents/{name}.md（install_aquilair_team.py --check 一并校验）")
    print("改版 checklist：先改 tools/principles.yaml 口径定义，再逐面同步措辞，最后跑 hub lint_skills.py 与 WorkBuddy install --check 双端闸门")
    return 0


# ===========四、命令行入口==========
def main(argv: list[str] | None = None) -> int:
    """CLI 入口：默认全量巡检；--impact 列影响面；--extra-surface 追加镜像面。

    Args:
        argv: 命令行参数（缺省取 sys.argv[1:]）。
    Returns:
        进程退出码：巡检有问题或口径 id 不存在为 1，否则为 0。
    """
    parser = argparse.ArgumentParser(description="行为口径治理闸门（principles.yaml 单一事实源）")
    parser.add_argument("--impact", metavar="口径ID", help="列出该口径的影响面清单（改版 checklist 用），不执行巡检")
    parser.add_argument("--extra-surface", metavar="PATH", action="append", default=[], help="追加镜像人设一并校验（可多次，WorkBuddy 端用）")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    if args.impact:
        return print_impact(args.impact, repo_root)
    return run_principles_check(repo_root, [Path(p) for p in args.extra_surface])


if __name__ == "__main__":
    sys.exit(main())
