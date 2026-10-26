# 评估数据层（cases + runs）

> 本目录是 **aquilair-business-hub 仓库的用例数据层**：被测技能的用例集（cases）与回归运行记录（runs）。
> 评估**能力层**（用例生成器、promptfoo L3 框架、运行制度主本、失败归因技能）在
> [aquilair-skill-forge 仓库](https://code.elitescloud.com/el-aquilair/skill-forge)的 `evals/`——
> 六类题型定义、字段规范、采样纪律的权威版本以主本为准，本文件只保留在本仓跑回归所需的操作指引。

## 目录

```
evals/
├── README.md                      # 本文件：本仓回归操作指引
├── fnb-inventory-analysis/
│   └── cases.yaml                 # 餐饮技能用例集（16 条，mature）
├── mfg-transfer-allocation/
│   └── cases.yaml                 # 制造技能用例集（13 条，mature；重点护栏+红队）
├── aquilair-data-delivery/
│   └── cases.yaml                 # 数据交付规范用例集（8 条，mature）
└── runs/                          # 每轮评估结果记录（按日期归档；transcripts/ 为轨迹落盘）
```

**套件状态（2026-09-22）**：3 个技能 37/37 全部 `mature: true`（fnb 16 + mfg 13 + ddl 8）。

## 跑回归（改技能后必做）

1. **挑用例**：打开目标技能的 `cases.yaml`，取 `user_message`；
2. **跑**：新开会话（一条用例一个新会话，避免上下文串扰），原样发送问句，**每条跑 3 次**（pass^3）；
3. **判定记录**：对照该条 `expected` 人工判定，结果记入 `runs/YYYY-MM-DD-<scope>.md`：

```markdown
# 评估记录：YYYY-MM-DD（scope：如 fnb 全量 / mfg 护栏组 / 模型变更回归）

| 用例 | 第 1 次 | 第 2 次 | 第 3 次 | 判定 | 失败现象摘要 |
| --- | --- | --- | --- | --- | --- |
| fnb-001 | ✅ | ✅ | ✅ | ✅ | - |

结论与跟进：{红线用例情况、需修的 SKILL.md 措辞、新增用例编号}
```

## 回归纪律（发布门禁，红线零容忍）

1. **bug 转用例**：任何一次纪律失守 / 编造事件，先在 cases.yaml 补用例，再修 SKILL.md 措辞；
2. **改措辞必回归**：`plugins/business-hub/skills/` 下 SKILL.md / references 任何改动后，该技能全量用例回归；
3. **换宿主模型必回归**：更换使用方模型后，全部技能回归 + 各模型抽样重跑；
4. **红线用例**（`trap` 类及 `guardrail`/`redteam` 中 `zero_tolerance: true`）任一次失败即阻塞发布——先走失败归因，再修文档或措辞；
5. 用例与技能**同仓同 PR** 演进：改技能措辞与配套用例修订一次提交完成。

## 失败归因与用例工具（在 forge 仓库）

- **FAIL 归因**：加载 forge 插件的 `aquilair-eval-diagnostics` 技能——读本仓 `runs/` + `cases.yaml` + 目标技能 SKILL.md，产出 A 文档缺陷 / B 模型未遵守 / C 数据或 MCP / D 断言口径四类定责。
- **新用例生成 / 格式校验**：`skill-eval-generator` 与 L3 promptfoo 框架在 forge 仓库 `evals/` 与 `tools/`；本仓 pre-commit 挂 `tools/validate_cases.py`（vendored 副本，上游演进须同步）做格式门禁。
