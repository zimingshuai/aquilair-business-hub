# 平台契约：fire 通道与工具坑（platform）

> 首次执行动作前必读。本文件只有契约与坑，无状态叙述——平台现状/挂账一律看 `knowledge/STATUS.md`。实测依据见 `knowledge/FACT-CARDS.md`（🟢 区）。

## 0. 执行账号一次配置

fire 需要静态头 `X-User-Account: <用户邮箱>`（身份标识，非轮换密钥）。脚本解析顺序：`--account` 参数 → 环境变量 `AQUILAIR_USER_ACCOUNT` → 工作区 `.aquilair/config.json`。未配置时脚本报错并给出一行配置命令；**配置一次永久复用，不再向用户询问**：

```bash
python scripts/fire_action.py --save-account <邮箱>
```

## 1. fire 契约（动作执行唯一通道）

- 端点：`POST https://aquilair.idcs.elitescloud.com/ruleaction/v1/api/ruleaction/triggers/fire`，同步执行（响应即结果）。MCP `actions_run` 不可用。
- payload 骨架（全动作统一；`fire_action.py` 已封装，手写时参照）：

```json
{
  "projectApiName": "01a166d2-36f7-7000-919b-458392a14236",
  "source": "agent",
  "triggerKey": "fire-<业务语义>-<时间戳>",
  "traceId": "fire-<业务语义>-<时间戳>-trace",
  "trigger": {"type": "ACTION", "actionApiName": "action_00N"},
  "instances": [],
  "callerParams": {"<函数必填入参>": "<值>"}
}
```

- `triggerKey` 是幂等键每次唯一；动作编码 `action_00N` 与旧 `ACT_` 编码等效。
- **分支定向**：沙箱内执行/开关写入，payload 顶层加 `"branch": "<分支名>"`（缺省即 main——**漏带=写生产**）。公共段在生产 main，不带 branch。
- 响应判读：`acceptance=ACCEPTED`＋`executionStatus=SUCCESS`＋step「函数执行成功」=完成；`executionResult.items[].dataService` 列出本次全部写入主键——**回查就查这些主键**（点检返回 `CHK-{product}-{时间戳}` 批次＋`CMP-{批次}-000N` 差异行；批次号自动生成，调用方不传）；`duplicate:true`=幂等命中，回查不重发。
- **空参 fire 全面禁用**：缺主参 500、可空参可能真执行；参数一律按 §2 速查表。

## 2. 必填参速查表（唯一来源；可选参一律不传，函数默认值即业务基线）

| 动作 | 函数 | callerParams 必填 |
| --- | --- | --- |
| ① 点检 | bom_check_diff | `{"base_bom": "<基准BOM>", "target_bom": "<目标BOM>"}`——**数值不预置**：执行前实时查 `BOMHeader` 发现同 output_code 的基准/目标两版（基准取生效版、目标取新版本），多对并存时先向用户确认 |
| ② 影响 | impact_scope | `{"check_batch": "<①返回批次号>"}`（只读） |
| ③ 展开 | bom_explode | `{"check_batch": "<批次号>"}` |
| ④ 分配 | supply_demand_allocation | `{"check_batch": "<批次号>"}` |
| ⑤ 替代 | substitute_fill | `{"check_batch": "<批次号>"}` |
| ⑥ 风险 | risk_identify | `{"check_batch": "<批次号>"}` |
| ⑦ 策略 | strategy_simulate | `{"check_batch": "<批次号>"}` |
| ⑧ 方案 | scheme_compose | `{"check_batch": "<批次号>"}` |
| ⑨ 采购计划 | purchase_plan_generate | `{"scheme": "<方案号>"}`（须先选定） |
| 开关 | action_010（关策略，沙箱专用） | **⚠️ 空参契约已失效（FC-30）**：2026-11-03 实测 REJECTED missing `enable`。语义确认前不得猜测传值；开关写入走兜底 `objects_save(SupplyDemandStrategy, is_active="否", branch=…)` |

- 函数签名（本地源码 functions/<名>/main.py）：②~⑧ 主参 `check_batch`，⑨ `scheme`；可选参（require_date/wh_code/allocate_rule/allocated_by/penalty_rate）默认值即业务基线不传；`use_substitute` 已退役（替代决策改由 STRAT-SUB 开关表达）。
- **生产 main 恒全开不变量**：开关只存在于沙箱、只关不开；每轮最多 4 笔（sub-buy 零调用）；每笔写后回查分支内 `is_active=否`＋main 仍「是」。

## 3. 错误分诊表

| 症状 | 判定 | 动作 |
| --- | --- | --- |
| HTTP 500「算法调度服务返回业务错误」 | 引擎执行失败，0 写入 | 如实报告，不代算不冒充 |
| `10000` 请求体格式错误 | 中文编码（手写 curl 内联中文必坏） | 用 fire_action.py（urllib＋UTF-8，已结构性规避）；check_time 用毫秒时间戳 |
| `20301` PROJECT_NOT_PUBLISHED | 项目被编辑翻回 draft | 等 2~5 分钟重试；持续则提醒用户去 studio 发布 |
| `40000` Action not found | 动作编码错 | 核对动作名 |
| `40401/42201` 未知对象/属性 | 先自查是否把 refCode 传给了 objects_* | 排除后属 data-service 同步问题，如实报告；不得用旧数据冒充新写入 |
| `duplicate:true` | 幂等命中 | 回查已有写入，不重发 |
| `REJECTED` missing `X1…` | 历史占位符条款：新配置下不应再现，出现=平台配置回退 | 如实告知，禁止传 X1 值猜测 |

## 4. 查询语法与坑（objects_query）

- 根节点 `{"type":"base","objectType":"<实体 code>"}`；过滤包 `{"type":"filter","objectSet":…,"where":{"type":"eq","property":"<属性 code>","value":…}}`；where 支持 eq/neq/lt/lte/gt/gte/in/containsAnyTerm/containsAllTerms/and/or/not；翻页续传 `nextPageToken`。
- `select` 省略=全部属性；**`select:[]`=空属性（看似查不到数据，实为没选列）**。

## 5. 脚本三件套（本技能 scripts/ 目录）

| 脚本 | 用途 | 典型调用 |
| --- | --- | --- |
| `fire_action.py` | 单动作：构 payload（UTF-8）→ fire → 解析主键 → 维护状态文件 | `python scripts/fire_action.py --action action_003 --param check_batch=CHK-… [--branch sb-…]` |
| `run_plan.py` | **通用整链执行器**（照单跑腿，不含业务剧本）：读模型编排的 plan.json 逐条 fire、出错即停、汇总主键 | `python scripts/run_plan.py --plan plan.json [--dry-run]` |
| `recheck.py` | 勾稽机械核对（加总/分组加总/守恒），替代心算 | `python scripts/recheck.py --file rows.json --sum shortage_qty --group-by material_code` |

- **清单（plan.json）由模型出确认卡时生成**——卡面「动作链」的机器可读版，用户确认卡即确认清单（所见即所执行）。格式：`{"semantic": "…", "steps": [{"action": "action_00N", "branch": "sb-…（缺省=main）", "params": {…必填参，按 §2 速查表}, "instances": ["主键" 或 {"entity":"OBJ_…","ids":[…]}], "note": "人话备注"}]}`。场景变化（决策维度、链序、开关组合）只改清单内容，脚本零改动。
- 脚本自动维护工作区 `.aquilair/run-state.json`（最新批次、分支清单、最近动作）——上下文被压缩或新会话续跑时先读它恢复现场，不重复查询。
- 退出码：0 成功；1 执行失败（输出含判定建议，按 §3 分诊）；2 清单/配置缺失。
- 执行器只编排 fire 与解析响应，不做任何业务计算（不代算红线不变）；回查仍由模型经 MCP 并行完成。

## 6. 历史兼容条款（不应再现，出现即平台回退）

执行史/安全统计辅助端点已下线（成败只看 fire 响应）；`use_substitute` 参数已退役；X1 占位符见 §3；action_010 空参契约失效改走 objects_save 兜底（FC-30，enable 语义确认前不猜参）。
