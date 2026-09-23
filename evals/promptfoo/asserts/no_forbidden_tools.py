# -*- coding: utf-8 -*-
"""轨迹断言：触发反例用例的「零工具调用」判定（trigger-negative 类机器断言）

用法（promptfoo 断言）：
    - type: python
      value: file://asserts/no_forbidden_tools.py

判定逻辑：按 case_id 映射的禁用工具前缀，检查 tool_calls 中不出现任何匹配项；
纯文本样本（无 tool_calls 结构）视为未调用，直接通过。
返回 GradingResult（pass/score/reason）。

新增触发反例用例时在 FORBIDDEN_PREFIXES 登记即可（领域特定映射，与转换器同思路）。
"""

import json
import re
import sys

# case_id -> 禁用的工具名前缀列表（服务级前缀，兼容全限定与裸名）
FORBIDDEN_PREFIXES = {
    'fnb-009': ('data-service-fnb',),        # 开发请求不得触发 fnb 诊断
    'fnb-016': ('data-service-fnb',),         # 制造域问题不得走 fnb 服务
    'mfg-012': ('data-service-mfg-sandbox',), # 餐饮域问题不得走 mfg 服务
    'mfg-013': ('data-service-mfg-sandbox',), # 开发请求不得触发 mfg 流程
}

# 样本键后缀（-r1..r3 轮次 / -neg、-violation 负样本）——剥离后查映射，与 gen_calibration 一致
SUFFIX_RE = re.compile(r'(-r\d+|-neg|-violation)$')


def judge(output: str, case_id: str = '') -> dict:
    """核心判定：返回 promptfoo GradingResult。"""
    forbidden = FORBIDDEN_PREFIXES.get(case_id)
    if not forbidden:
        return {'pass': False, 'score': 0, 'reason': f'用例 {case_id} 未在 FORBIDDEN_PREFIXES 登记'}

    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {'pass': True, 'score': 1, 'reason': '纯文本样本（无轨迹结构），视为未调用任何工具'}

    if not isinstance(data, dict):
        return {'pass': True, 'score': 1, 'reason': '纯文本样本，视为未调用任何工具'}

    calls = data.get('tool_calls') or []
    hits = [
        str(c.get('tool', ''))
        for c in calls
        if any(str(c.get('tool', '')).startswith(p) or p in str(c.get('tool', '')) for p in forbidden)
    ]
    if hits:
        return {'pass': False, 'score': 0, 'reason': f'出现禁用工具调用: {", ".join(hits[:5])}'}
    return {'pass': True, 'score': 1, 'reason': f'{len(calls)} 次调用中无禁用前缀（{", ".join(forbidden)}）命中'}


def get_assert(output, context=None):
    """promptfoo python 断言入口：从 context.vars 取 case_id（自动剥离轮次/负样本后缀）。"""
    case_id = (context or {}).get('vars', {}).get('case_id', '')
    forbidden = FORBIDDEN_PREFIXES.get(case_id) or FORBIDDEN_PREFIXES.get(SUFFIX_RE.sub('', case_id))
    if not forbidden:
        return {'pass': False, 'score': 0, 'reason': f'用例 {case_id} 未在 FORBIDDEN_PREFIXES 登记'}
    return judge_with(forbidden, output, case_id)


def judge_with(forbidden: tuple, output: str, case_id: str = '') -> dict:
    """按给定禁用前缀执行判定（judge 的参数化形态）。"""
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {'pass': True, 'score': 1, 'reason': '纯文本样本（无轨迹结构），视为未调用任何工具'}

    if not isinstance(data, dict):
        return {'pass': True, 'score': 1, 'reason': '纯文本样本，视为未调用任何工具'}

    calls = data.get('tool_calls') or []
    hits = [
        str(c.get('tool', ''))
        for c in calls
        if any(str(c.get('tool', '')).startswith(p) or p in str(c.get('tool', '')) for p in forbidden)
    ]
    if hits:
        return {'pass': False, 'score': 0, 'reason': f'出现禁用工具调用: {", ".join(hits[:5])}'}
    return {'pass': True, 'score': 1, 'reason': f'{len(calls)} 次调用中无禁用前缀（{", ".join(forbidden)}）命中'}


if __name__ == '__main__':
    # 命令行单测：python asserts/no_forbidden_tools.py '<输出JSON>' '<case_id>'
    print(json.dumps(judge(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''), ensure_ascii=False))
