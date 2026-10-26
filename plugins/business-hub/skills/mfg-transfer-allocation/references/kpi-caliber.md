# 实体映射与 KPI 口径边界

> 本文件由 SKILL.md 按需引入：用户询问评估数字的算法（总调拨成本/运输天数/缺货成本怎么算），或需要按问题类型选择查询实体时读取。
>
> **出处说明**：本域开发于溯源区设立（2026-09-28）之前，源文档未留档，以下口径出处均为实测元数据（`get_meta_objects` / `get_meta_rules` / 实例回放验证；2026-10-22 接口迁移至统一网关，工具映射见 SKILL.md），标注格式见仓库 `aquilair-knowledge/sources/README.md`（知识库源文档区随技能 zip 一并分发）。业务方补充口径文档后，落位 `aquilair-knowledge/sources/mfg/` 并替换为文档出处。

## 实体与问题映射表

| 用户问题 | 优先查询实体 | 说明 |
| --- | --- | --- |
| 哪些工厂缺货 | `Plant`、`MaterialInPlant` | 用实例原始 `unfulfill_sales_qty`，同时列出无缺货工厂 |
| 其他工厂可调出量 | `MaterialInPlant`、必要时 `Plant`/`Material` | 只展示工具或元数据已定义的库存与可调出字段；**没有可调出量字段时不得由库存自行扣减推算** |
| 方案数量、策略、状态 | `TransferOptimizationSolution`、`TransferOptimizationStrategy` | 从当前作用域读取，不使用固定示例编号 |
| 计划从哪到哪、物料、数量 | `TransferPlan`，必要时关联 `Plant`、`Material` | 展示起点、终点、物料、数量、状态 |
| 路由如何选择 | `PlantTransferRouting`、`TransferOptObjectiveInStrategy`、`TransferOptimizationStrategy` | 说明工具返回的路由、目标及指标关系；没有算法细节就说明缺失 |
| 方案评估 | `TransferOptSolutionEvaluation` | 总调拨成本、总运输距离、总运输天数、总需求缺货成本**必须直接读取评估实体** |
| 可用策略 | `TransferOptimizationStrategy`、`TransferOptObjectiveInStrategy` | 展示启停状态、优化目标和优先级 |
| 执行后状态 | `TransferOptimizationSolution`、`TransferPlan`、`MaterialInPlant` | 回查方案/计划状态、两端库存和剩余缺货 |

## 公式与口径边界（Gotchas）

- `TransferOptSolutionEvaluation` 是方案 KPI 的**唯一事实来源**：不得把各计划 `total_cost` 相加冒充评估值 `total_cost`；两者不一致时并列说明「评估口径与逐计划合计不同，元数据未提供折算规则」。（来源：实测 2026-09-16，get_meta_objects 字段释义 + 评估实体与计划实体数值比对）
- 总运输天数：仅当元数据明确为各计划 `lead_days` 合计时才可表述为「各段运输天数合计」；**不得**说成最长端到端时效。（来源：实测 2026-09-16，get_meta_objects 口径释义）
- 「总需求缺货成本/总调拨成本怎么算」：只有元数据或实体提供公式、参数和明细时才展示公式；否则报告当前数值及来源，并明确「当前元数据未提供可还原的计算公式/折算系数」。（来源：实测 2026-09-16，get_meta_rules 衍生属性口径）
- **不得**把路由的 `unit_cost`、`lead_days` 或距离自行代入推导总成本、缺货成本或最优性。（来源：实测 2026-09-16，路由实体字段释义确认无折算规则）
