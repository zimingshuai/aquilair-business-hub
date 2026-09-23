# -*- coding: utf-8 -*-
"""promptfoo 文件回放 provider（L3 POC）

用途：按 case_id 从样本 JSON 读取预置输出返回给断言引擎——
用于断言校准（不调 LLM、不调 MCP，纯回放）。
样本来源：B 侧评估 transcript（L3 落地后自动落盘）或按回归报告记录构造的形态代表样本。

promptfoo file provider 接口：call_api(prompt, context) -> {output: str}
context["vars"] 含转换器注入的 case_id 等变量。

样本文件格式（由 provider config 的 samples 路径指定，不硬编码）：
{
  "fnb-001": "完整回复文本...",
  "fnb-004": "...",
  "mfg-002": {"reply": "回复文本", "tool_calls": [{"tool": "...", "args": {...}, "phase": "..."}]}
}
含 tool_calls 的样本序列化为 JSON 输出（供 python 自定义断言做顺序判定）。
"""

import json
import os
from pathlib import Path

# 样本路径优先级：provider config（SAMPLES 环境变量由 promptfoo 传入）> 环境变量 > 同目录默认
_DEFAULT_SAMPLES = str(Path(__file__).parent / 'samples' / 'default-samples.json')


def call_api(prompt, options=None, context=None):
    """promptfoo 调用入口：按 case_id 回放样本输出。

    promptfoo python provider 的实参形态为 call_api(prompt, options, context)：
    options 为 provider 选项对象（含 YAML 里 providers[].config 的内容），context 含 vars 等。
    """
    opts = options or {}
    if isinstance(opts, dict):
        cfg = opts.get('config') or (opts if 'samples' in opts else {})
    else:
        cfg = {}
    samples_path = cfg.get('samples') or os.environ.get('PROMPTFOO_SAMPLES') or _DEFAULT_SAMPLES

    with open(samples_path, encoding='utf-8') as f:
        samples = json.load(f)

    case_id = (context or {}).get('vars', {}).get('case_id', '')
    # 键匹配：优先精确命中；未命中时按 -r1/-r2/-r3 顺序取真实 transcript 的轮次样本
    # （B 侧 transcript 落盘键为 <case_id>-r<N>，报告约定轮次选择由本 provider 处理）
    key = case_id if case_id in samples else next(
        (f'{case_id}-r{n}' for n in (1, 2, 3) if f'{case_id}-r{n}' in samples), ''
    )
    if not key:
        return {
            'output': None,
            'error': f'样本缺失: {case_id}(-r1..r3) 不在 {samples_path}（先补样本或跳过该用例）',
        }

    sample = samples[key]
    if isinstance(sample, dict):
        # 轨迹类样本：整体序列化为 JSON，供 contains 断言与 python 顺序断言共用
        output = json.dumps(sample, ensure_ascii=False)
    else:
        output = sample
    return {'output': output, 'raw': output}
