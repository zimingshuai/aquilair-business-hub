# 关键动作场景剧本

> 本文件由 SKILL.md 按需引入：用户要求修改计划、切换策略、双沙箱分支对比、生产与沙箱分支对比、或选定执行方案时读取。凡经 `actions_run` 执行 Action 的步骤，动作现状与已知服务端缺陷见 SKILL.md 工具节——执行前先实测再承诺，失败如实报告，禁止用查询到的历史方案数据冒充新生成的方案。

## 场景 1：修改计划数量

用户提出「调整调拨计划数量」时：

1. 用 `objects_query` 查询该 `transfer_plan_code`、所属 `solution_code`、当前 `total_qty` 与状态；核验目标数量为非负数。计划或所属方案已完成/已废弃 → 拒绝修改并说明原因。
2. 准备默认沙箱分支（会话无可复用分支时先 `objects_create_branch`），输出确认卡：动作链 `modify_plan -> evaluate_solution`，逐项展示「当前数量 -> 目标数量」、所属方案、执行环境（默认沙箱分支）、评估将被刷新。
3. 确认后按卡上环境经 `actions_run` 执行 `modify_plan(transfer_plan_code, total_qty)`，立即用 `objects_query`（显式传 `branch`）回查计划数量，确认其他计划字段未改变。
4. 再执行 `evaluate_solution(solution_code)`，回查 `TransferOptSolutionEvaluation` 的总调拨成本、总运输距离、总运输天数、总需求缺货成本。
5. 不得调用 `modify_material_in_plant_stock` 代替；不得称 `evaluate_solution` 重新生成了方案。

## 场景 2：策略切换并重新生成

用户明确要求「停用当前策略、启用另一策略、再生成方案」时：

> **动作链口径（最小必要集）**：仅当用户明确要求停用某策略时才纳入 `disable_strategy`；
> 用户仅说「用 X 策略生成」时，动作链为 `enable_strategy(X)` → `run_supply_demand_allocation`
> （若 X 已启用，则仅 `run_supply_demand_allocation`），不主动追加 disable。
> 执行前先回查策略启停状态，按实际需要确定最终动作链并原样写进确认卡。

1. 回查两个策略当前状态（`objects_query`，按当前分析上下文选择 branch），核对要停用和启用的策略编码。
2. 准备默认沙箱分支（会话无可复用分支时先 `objects_create_branch`），输出确认卡：将在沙箱分支内依次执行 `disable_strategy` → `enable_strategy` → `run_supply_demand_allocation`（均经 `actions_run`）。
3. 确认后在**同一沙箱分支**依次执行三个 Action，每个调用显式传 `branch`=该分支名。
4. 回查策略状态、方案、计划和评估，报告新旧方案的编号、状态与评估指标，不假定生成结果固定。

## 场景 3：双沙箱分支 What-if 对比

用户要求「在沙箱里跑一下这两个方案」——**必须用两个独立沙箱分支**，不能在同一沙箱分支连续执行两套方案：

1. `objects_create_branch` 分别创建成本优先、时效优先两个比较沙箱分支（创建无需确认），记录各自分支名。
2. 在每个分支内回查并设置该方案所需策略启停状态，再 `run_supply_demand_allocation` 生成对应候选方案。
3. 分别定位各自分支中要执行的 Solution，`confirm_solution` → 回查已选定状态 → `execute_solution`。
4. 分别用 `objects_query` 显式传各自 `branch` 查询执行后的 `MaterialInPlant`、`TransferOptimizationSolution`、`TransferPlan`：每个工厂物料的 `onhand_inventory_qty`、剩余缺货量、方案与计划状态；可再用 `objects_compare_branch` 查看各分支相对生产（main）的对象增删改辅助定位差异。
5. 输出比较结论后，`objects_delete_branch` 删除仅为本次比较创建的两个沙箱分支（破坏性，须确认），并说明结果是**临时 What-if 结果，不是生产事实**。

不得把一个分支的查询结果、策略状态或方案编号用于另一个分支；顺序创建的分支基准时刻可能不同，对比时注明。

## 场景 4：生产分支与沙箱分支只读对比

分别读取两分支快照：`objects_query` 查生产（`branch="main"`）与沙箱分支（显式传分支名），辅以 `objects_compare_branch` 查看沙箱分支相对父分支（main）的对象增删改；按数据来源、快照时间、策略启停状态、方案状态、库存、剩余缺货逐项对比。清楚标注「生产分支（main）」与「沙箱分支（名称）」；**不得把沙箱分支执行后的库存称为生产库存**。

## 场景 5：选定并执行方案

用户说「我选某方案，确认执行」且方案编号明确时：

1. 用 `objects_query` 查询目标 Solution 当前状态、关联 Plan、源/目标工厂相关物料库存与缺货。
2. **即使原话包含「确认执行」也必须先出卡**：默认沙箱分支；卡上写明——会废弃其他待确认方案、按计划变更两端库存、模型没有出库/在途/入库事件；用户指定生产环境时额外强调不可逆。
3. 确认后同环境经 `actions_run` 执行 `confirm_solution(solution_code)`；回查目标方案已选定、其 Plan 已确认、其他待确认方案已废弃。
4. 执行 `execute_solution(solution_code)`；回查方案与计划已完成、源工厂库存扣减、目标工厂库存增加、剩余缺货。
5. 执行后重新读取所有方案/计划状态及涉及物料缺货量。
