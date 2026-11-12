"""勾稽机械核对：对 objects_query 返回的明细行做加总/分组加总/守恒校验。

SKILL.md 展示层边界允许的「由 N 行明细加总」由本脚本代算——模型只读结论，不心算
（speed：替代模型逐步算术；正确性：确定性计算无算错）。核对通过=静默继续，FAIL=停下说明。

输入：--file rows.json（objects_query 输出 {"records":[{"properties":{…}}]} 或纯对象数组；
properties 键 = 属性 code）。缺省读 stdin。
模式（可组合）：
  --sum <attr>                    对属性求和
  --group-by <attr> --sum <attr>  按属性分组求和
  --conservation <gross>,<allocated>,<shortage>
                                  逐行校验 毛需求 ≈ 已分配 + 剩余缺口（--tolerance 相对容差，默认 0.005）
  --filter <attr>=<value>         先做包含过滤（剔除小计/合计行等非明细行）
输出：中文报告 + 每项 PASS/FAIL；存在 FAIL 退出码 1，否则 0。
"""

import argparse
import json
import sys
from pathlib import Path


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def load_rows(path: str | None) -> list[dict]:
    """读入并展平记录：兼容 objects_query 输出与纯数组；properties 展平到顶层。"""
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("records") or []
    rows: list[dict] = []
    for record in data:
        if not isinstance(record, dict):
            continue
        props = record.get("properties")
        row = dict(props) if isinstance(props, dict) else dict(record)
        rows.append(row)
    return rows


def to_number(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def fmt(value: float) -> str:
    return f"{value:,.4f}".rstrip("0").rstrip(".") if value == value else "NaN"


def main() -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(description="xgimi-sdb 勾稽机械核对")
    parser.add_argument("--file", help="明细 JSON 文件路径（缺省读 stdin）")
    parser.add_argument("--sum", dest="sum_attr", help="求和的属性 code")
    parser.add_argument("--group-by", dest="group_attr", help="分组属性 code（配 --sum）")
    parser.add_argument("--conservation", help="守恒三属性：毛需求,已分配,剩余缺口")
    parser.add_argument("--filter", dest="filter_expr", metavar="ATTR=VALUE", help="包含过滤（剔非明细行）")
    parser.add_argument("--tolerance", type=float, default=0.005, help="守恒相对容差（默认 0.005）")
    args = parser.parse_args()

    if not args.sum_attr and not args.conservation:
        parser.error("至少给一个模式：--sum 或 --conservation")

    rows = load_rows(args.file)
    if args.filter_expr:
        attr, _, value = args.filter_expr.partition("=")
        rows = [r for r in rows if str(r.get(attr.strip())) == value.strip()]
    print(f"明细行数：{len(rows)}")

    failures = 0

    if args.sum_attr:
        values = [to_number(r.get(args.sum_attr)) for r in rows]
        bad = [r for r, v in zip(rows, values) if v is None]
        total = sum(v for v in values if v is not None)
        verdict = "PASS" if not bad else "FAIL"
        failures += 1 if bad else 0
        print(f"[{verdict}] 加总 {args.sum_attr} = {fmt(total)}（由 {len(rows) - len(bad)} 行明细加总）")
        for row in bad:
            print(f"  ⚠️ 非数值行（请剔小计/合计行或核对属性 code）：{ {k: row[k] for k in list(row)[:3]} }")

    if args.sum_attr and args.group_attr:
        groups: dict[str, float] = {}
        for row in rows:
            value = to_number(row.get(args.sum_attr))
            if value is None:
                continue
            groups[str(row.get(args.group_attr))] = groups.get(str(row.get(args.group_attr)), 0.0) + value
        print(f"[PASS] 分组加总 {args.sum_attr} by {args.group_attr}（{len(groups)} 组）：")
        for key in sorted(groups, key=groups.get, reverse=True):
            print(f"    {key}: {fmt(groups[key])}")

    if args.conservation:
        gross_attr, allocated_attr, shortage_attr = [a.strip() for a in args.conservation.split(",")]
        violations: list[str] = []
        checked = 0
        for index, row in enumerate(rows):
            gross = to_number(row.get(gross_attr))
            allocated = to_number(row.get(allocated_attr))
            shortage = to_number(row.get(shortage_attr))
            if gross is None or allocated is None or shortage is None:
                continue
            checked += 1
            residual = abs(gross - (allocated + shortage))
            if residual > args.tolerance * max(abs(gross), 1.0):
                key = row.get("material_code") or row.get("material") or f"第 {index + 1} 行"
                violations.append(f"{key}: 毛需求 {fmt(gross)} ≠ 已分配 {fmt(allocated)} + 缺口 {fmt(shortage)}")
        verdict = "PASS" if checked and not violations else "FAIL"
        if not checked:
            failures += 1
            print(f"[FAIL] 守恒校验无可用行——核对属性 code 是否正确（{args.conservation}）")
        else:
            failures += len(violations)
            print(f"[{verdict}] 守恒校验（{gross_attr} = {allocated_attr} + {shortage_attr}，{checked} 行）：")
            for item in violations:
                print(f"  ⚠️ {item}")

    if failures:
        print(f"结论：FAIL（{failures} 项不符）——按 SKILL.md 红线：停下向用户说明，不继续对比。")
        return 1
    print("结论：PASS——核对通过，静默继续。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
