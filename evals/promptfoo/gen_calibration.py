# -*- coding: utf-8 -*-
"""生成 rubric 校准对拍配置（L3 语义层对拍）

用法：
    python gen_calibration.py        # 重新生成 calibration-samples.json 与 promptfooconfig.calibration.yaml

对拍设计：
    正样本 = B 侧真实 transcript（meta.pass=true，即 B 人审结论）
    负样本 = 按历史真实失败现象复刻（samples/calibration-negatives.json，meta.pass=false）
    rubric = 对应用例的 expected（「以 expected 为准」的机器化——judge 拿 expected 判 reply）
    对拍判定 = promptfoo 断言结果（rubric 符合与否）与 meta.pass 的一致率

生成物：
    samples/calibration-samples.json     # 30 份对拍样本（真实 24 + 负 6，键含轮次/负后缀）
    promptfooconfig.calibration.yaml     # 自包含对拍配置（replay provider + 方舟评审）
"""

import io
import json
import re
from pathlib import Path

import yaml

from set_rubric_model import resolve_model

BASE_DIR = Path(__file__).resolve().parent
EVALS_DIR = BASE_DIR.parent

# 用例集与真实 transcript 来源（与 convert_cases.py 同源登记）
SKILL_CASE_FILES = {
    'fnb-inventory-analysis': 'fnb-inventory-analysis/cases.yaml',
    'mfg-transfer-allocation': 'mfg-transfer-allocation/cases.yaml',
    'aquilair-data-delivery': 'aquilair-data-delivery/cases.yaml',
}
TRANSCRIPT_FILE = EVALS_DIR / 'runs' / 'transcripts' / '2026-09-22-ddl成熟轮.json'
NEGATIVES_FILE = BASE_DIR / 'samples' / 'calibration-negatives.json'

# 样本键 -> case_id 的后缀剥离规则（-r1..r3 / -neg / -violation）
SUFFIX_RE = re.compile(r'(-r\d+|-neg|-violation)$')

# 评审模型（与 promptfooconfig.rubric.yaml 一致：火山方舟 OpenAI 兼容，key 走 ARK_API_KEY）；
# 模型名经 set_rubric_model.resolve_model 同源解析（命令行参数 > ARK_RUBRIC_MODEL > 单点默认值）
RUBRIC_PROVIDER = {
    'id': 'openai:chat:{}'.format(resolve_model(None)),
    'config': {
        'apiBaseUrl': 'https://ark.cn-beijing.volces.com/api/v3',
        'apiKeyEnvar': 'ARK_API_KEY',
    },
}

# 评审背景说明（judge 视野适配层——首轮对拍发现的三类系统性分歧的修正）：
# ① 图表以文件路径/文件名/内联引用（SVG/PNG/HTML/Mermaid）交付即视为已配图（评审对象是回复文本，非渲染结果）；
# ② 确认卡类用例为两段式协议（段1 出卡等待确认 → 用户已确认 → 段2 执行与汇报），
#    不得把「段1 说等待确认、段2 已执行」判为矛盾；
# ③ 评审者没有工具返回可比对，回复内数值自洽即视为满足，不作负向推断。
RUBRIC_CONTEXT = (
    '【评审背景】你评审的是一个数据分析助手的回复文本。图表若以文件路径/文件名/内联引用（SVG/PNG/HTML/Mermaid）'
    '形式交付即视为已配图，不要求内嵌渲染结果；确认卡类回复为两段式（段1 出卡等待确认、用户已确认、'
    '段2 执行与汇报），不得把两段并存判为矛盾；你无法访问工具原始返回，回复内数值自洽即视为满足，'
    '不得因无法核对而判不满足。\n【评审标准】'
)
# 输出格式指令（与 promptfoo 默认 JSON 评分格式一致——非 JSON 会被记为 error 而非判负；
# 注意：措辞里不得出现「true 或 false」这类会被模型照抄进 JSON 的字样，中文「或」会破坏解析）
RUBRIC_FORMAT = (
    '\n【输出格式】只输出一个 minified JSON 对象（不要代码块、不要任何多余文字）：'
    '{"pass": <布尔值>, "score": <0到5的整数>, "reason": "<简要理由>"}。'
    'pass 表示是否符合上述评审标准：完全或基本符合取真，明显违反或缺失取假；score 大于等于 4 对应取真。'
)

# 个别用例的措辞适配（expected 中 judge 无法核验/过严字面要求的放宽转写）
CASE_RUBRIC_OVERRIDES = {
    # 指标组合按实际返回为准（满足率并非所有方案评估都有）
    'ddl-002': '多方案对比交付：有对比图表（分组柱状图等）；每个方案标注环境来源（生产/沙箱），'
               '不混用两侧数据；评估指标按返回内容呈现（如成本/天数/缺货成本），不强求特定指标名。',
    # 口径四要素按实际存在的要素判断，不为凑全四项而判负
    'ddl-001': '四段式交付：结论段在全文最前；有口径说明（来源/时间/范围等要素按实际呈现）；'
               '有横向条形图或其文件引用；明细表仓库写「中文名称（编码）」；洞察落到建议动作。',
    # Top N：明细行数值按 reply 摘要视野判断（图文件承载的信息以 reply 说明为准，B 人审看 staging 全量）
    'ddl-006': 'Top N 交付：有横向条形图及其文件引用；洞察区分「超储压库存」与「缺货补货」两类处置，'
               '且缺货条目不压库存（有视觉强调更佳）；明细包含分类维度（ABC）与库存/水位类字段——'
               'reply 未逐一复述每一行数值不算缺失，只要列结构或图表说明表明已包含；'
               '图上标签按 reply 的图说明判断是否为「中文名称（编码）」。',
    # 数值一致性改为回复内自洽（judge 无工具返回）
    'ddl-007': '图上数值与明细表数值一致（回复内自洽即可）；图上名称用「中文名称（编码）」；'
               '有口径/来源说明。',
    # 确认卡不可逆提示按环境区分（SKILL.md 口径：沙箱卡声明可删除丢弃即可，生产卡才须强调不可逆）
    'ddl-008': '确认卡类交付为两段式（段1 出卡等待确认、用户已确认、段2 执行与汇报）：出卡本身豁免'
               '配图；确认卡含默认沙箱环境与动作链，不可逆性按环境判断——沙箱卡声明可删除/可丢弃即达标，'
               '生产卡须强调不可逆；确认后的汇报若含数据结论（如执行前后库存变化）须配图。',
}


def build_rubric(case_id: str, expected: str) -> str:
    """对拍 rubric = 背景说明 + 用例标准（个别适配优先于原始 expected）+ 输出格式。"""
    standard = CASE_RUBRIC_OVERRIDES.get(case_id, expected)
    return RUBRIC_CONTEXT + standard + RUBRIC_FORMAT


def load_case_index() -> dict:
    """读全部用例集，返回 case_id -> {user_message, expected}。"""
    index = {}
    for rel in SKILL_CASE_FILES.values():
        with io.open(EVALS_DIR / rel, encoding='utf-8') as f:
            for case in yaml.safe_load(f)['tests']:
                index[case['id']] = {
                    'user_message': case['user_message'],
                    'expected': case['expected'],
                }
    return index


def main() -> None:
    """合并对拍样本并生成自包含 promptfoo 配置。"""
    cases = load_case_index()

    with io.open(TRANSCRIPT_FILE, encoding='utf-8') as f:
        positives = json.load(f)
    with io.open(NEGATIVES_FILE, encoding='utf-8') as f:
        negatives = json.load(f)
    samples = {**positives, **negatives}

    # 校验：每份样本都能映射到用例（rubric 来源）
    for key, sample in samples.items():
        case_id = SUFFIX_RE.sub('', key)
        assert case_id in cases, f'{key} 找不到对应用例 {case_id}'
        assert 'pass' in sample.get('meta', {}), f'{key} 缺 meta.pass（对拍锚点）'

    out_samples = BASE_DIR / 'samples' / 'calibration-samples.json'
    with io.open(out_samples, 'w', encoding='utf-8') as f:
        json.dump(samples, f, ensure_ascii=False, indent=1)

    tests = []
    for key in samples:
        case_id = SUFFIX_RE.sub('', key)
        case = cases[case_id]
        tests.append({
            'description': f'calib:{key}',
            'vars': {
                'case_id': key,  # 直接以完整样本键为 case_id，replay provider 精确命中
                'user_message': case['user_message'],
                'rubric': build_rubric(case_id, case['expected']),
                'expected_pass': bool(samples[key]['meta']['pass']),
            },
            'assert': [{'type': 'llm-rubric', 'value': '{{rubric}}'}],
        })

    config = {
        'description': f'aquilair L3 rubric 校准对拍（{len(tests)} 条：真实 {len(positives)} + 负样本 {len(negatives)}）',
        'prompts': ['{{user_message}}'],
        'providers': [{
            'id': 'file://replay_provider.py',
            'label': 'replay-对拍样本',
            'config': {'samples': 'samples/calibration-samples.json'},
        }],
        'defaultTest': {'options': {'provider': RUBRIC_PROVIDER}},
        'tests': tests,
    }
    out_config = BASE_DIR / 'promptfooconfig.calibration.yaml'
    with io.open(out_config, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, width=200)

    print(f'[OK] 对拍样本 {len(samples)} 份 -> {out_samples.name}')
    print(f'[OK] 对拍配置 {len(tests)} 条 -> {out_config.name}')
    print(f'     正样本（B 人审 pass）{len(positives)} / 负样本（预期 fail）{len(negatives)}')


if __name__ == '__main__':
    main()
