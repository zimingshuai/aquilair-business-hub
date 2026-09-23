# -*- coding: utf-8 -*-
"""cases.yaml -> promptfoo tests YAML 转换器（L3 POC）

用法：
    python convert_cases.py                     # 转换全部技能用例集
    python convert_cases.py fnb                 # 只转换 fnb-inventory-analysis

输入：../<技能名>/cases.yaml（字段规范见 evals/README.md）
输出：tests_<技能名>.yaml（与本文件同目录，供 promptfooconfig.yaml 引用）

映射规则：
    id            -> description（promptfoo 结果表标识，保留原编号便于对照 runs 记录）
    user_message  -> vars.user_message（prompt 模板变量）
    expected      -> vars.expected（供 llm-rubric / 人工评审引用，不作断言）
    type/zero_tolerance/mature/source -> vars.*（保留元数据，判定分组用）
    assert[]      -> assert[]（type/value 原样转译；空断言跳过——由 rubric/人工判）

断言类型对照（assert 草稿为 promptfoo 语法，转换时不改语义）：
    contains / contains-any / not-contains 等 promptfoo 原生支持，原样透传。
"""

import io
import sys
from pathlib import Path

import yaml

# 脚本所在目录（evals/promptfoo/），用例集在上级目录的技能子目录
BASE_DIR = Path(__file__).resolve().parent
EVALS_DIR = BASE_DIR.parent

# 技能名 -> 用例集相对路径（新增技能在此登记即可接入转换）
SKILL_CASE_FILES = {
    'fnb-inventory-analysis': 'fnb-inventory-analysis/cases.yaml',
    'mfg-transfer-allocation': 'mfg-transfer-allocation/cases.yaml',
    'aquilair-data-delivery': 'aquilair-data-delivery/cases.yaml',
}

# promptfoo tests 文件里需要透传到 vars 的用例元数据字段
META_FIELDS = ('type', 'zero_tolerance', 'mature', 'source')


def convert_case(case: dict) -> dict:
    """单条用例 -> promptfoo test 条目；无断言的用例返回 None（跳过）。"""
    asserts = case.get('assert') or []
    if not asserts:
        return None
    entry = {
        'description': case['id'],
        'vars': {
            'case_id': case['id'],
            'user_message': case['user_message'],
            'expected': case['expected'],
            'case_type': case['type'],
        },
        'assert': asserts,
    }
    for field in META_FIELDS:
        if case.get(field) is not None:
            entry['vars'][field] = case[field]
    return entry


def convert_skill(skill: str) -> Path:
    """转换一个技能的用例集，返回输出文件路径。"""
    src = EVALS_DIR / SKILL_CASE_FILES[skill]
    out = BASE_DIR / f'tests_{skill}.yaml'
    with io.open(src, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    tests, skipped = [], []
    for case in data['tests']:
        entry = convert_case(case)
        if entry is None:
            skipped.append(case['id'])
        else:
            tests.append(entry)
    with io.open(out, 'w', encoding='utf-8') as f:
        yaml.safe_dump({'tests': tests}, f, allow_unicode=True, sort_keys=False, width=120)
    print(f'[OK] {skill}: {len(tests)} 条转出, {len(skipped)} 条无断言跳过({", ".join(skipped) or "-"}) -> {out.name}')
    return out


def main() -> None:
    """命令行入口：无参转全部，传技能名只转一个。"""
    targets = sys.argv[1:] or list(SKILL_CASE_FILES)
    for skill in targets:
        if skill not in SKILL_CASE_FILES:
            print(f'[WARN] 未知技能名 {skill}，可选: {", ".join(SKILL_CASE_FILES)}')
            continue
        convert_skill(skill)


if __name__ == '__main__':
    main()
