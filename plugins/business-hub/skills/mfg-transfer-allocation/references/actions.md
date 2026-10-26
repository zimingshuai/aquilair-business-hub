# 业务 Action 参考（执行前必读）

> **接口现状（2026-10-22）**：动作执行已迁移至统一网关 `aquilair-mcp:actions_run`（必填 `workspace_id`，参数 `action_id` + `parameters` + `branch`）。action-service 当前未在本 workspace 部署任何动作（实测 404 资源不存在），本表 8 个 Action 的参数与确认规则**保留备用、待服务端就绪即生效**；就绪前涉及生成/评估/确认/执行调拨的请求须如实说明待部署，禁止用查询到的历史方案数据冒充新生成的方案。

> 本文件由 SKILL.md 按需引入：准备执行任何动作（`actions_run`）前读取。**如实时元数据（`metadata_list_actions`）与下表冲突，以实时元数据为准**；元数据发现动作不自动扩充允许范围。

## Action 清单

| Action | 已知作用 | 关键限制 |
| --- | --- | --- |
| `disable_strategy(strategy_code)` | 停用策略 | 写操作，须确认后执行 |
| `enable_strategy(strategy_code)` | 启用策略 | 写操作，须确认后执行 |
| `run_supply_demand_allocation(strategy_code)` | 调用注册的供需调拨算法，生成候选方案 | **先回查策略启停状态**，不能假定接口自动校验；不得自行模拟算法或捏造结果 |
| `modify_plan(transfer_plan_code, total_qty)` | 仅修改指定 `TransferPlan.total_qty` | `total_qty` 必须非负；只允许未执行的候选方案；修改后必须重新评估所属方案 |
| `evaluate_solution(solution_code)` | 汇总方案下调拨计划，生成/更新 `TransferOptSolutionEvaluation` | 只刷新评估，**不重新生成**路由或计划；用于 `modify_plan` 后 |
| `confirm_solution(solution_code)` | 所选方案待确认→已选定；其计划→已确认；**其他待确认方案及计划→废弃** | 确认卡必须说明会废弃其他待确认方案 |
| `execute_solution(solution_code)` | 已选定方案和已确认计划→已完成；按计划数量扣减源工厂、增加目标工厂 `onhand_inventory_qty` | 生产环境执行属**不可逆真实业务写入**；确认卡必须说明库存会变化且无出库/在途/入库事件模型 |
| `modify_material_in_plant_stock(...)` | 直接改工厂物料库存 | 不得用它伪装「修改调拨计划数量」；仅用户明确要求改库存且逐字段确认时可用 |

## 动态生成 ID：分阶段确认

生成方案后才知道 `solution_code`——**不能**先给「生成并执行任意新方案」这种无限授权卡：

1. 第一阶段确认卡：只覆盖生成动作（如 `run_supply_demand_allocation`）。
2. 返回并回查真实方案编号后，再出**绑定具体 `solution_code`** 的执行确认卡。

参数已确定且前置条件完整的动作链（如 `modify_plan -> evaluate_solution`、`confirm_solution -> execute_solution`）可一次确认，执行层仍逐步回查。

## 串行与回查

- 同一确认内的 Action 串行执行：前一项成功并回查后才执行下一项，不并发调用多个 Action。
- 每步回查对象：策略→启停状态；方案→状态；计划→数量与状态；执行→两端工厂 `onhand_inventory_qty` 与剩余缺货。
- 不得以执行成功响应替代查询证据。
