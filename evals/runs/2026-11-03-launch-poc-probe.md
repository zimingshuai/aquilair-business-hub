# 实测记录：2026-11-03（scope：新品上市POC-最新版 域接入 P1 实测攒坑）

> 任务：六步流水线第 2 步——MCP 逐工具实测 + 元数据 vs 文档差异对照 + NP009 数据探查。
> 本文件为原始实测记录（数据实态允许落此处，不进技能 references）。
> 配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f（新品上市POC-最新版，v1.4.0，
> publishedAt=2026-11-03 00:37:13，updatedAt=2026-11-03 13:28:42，status=draft）；
> MCP 端点=https://aquilair.idcs.elitescloud.com/mcp-service/mcp；通道=临时探针脚本（token 不落任何产出）。

## 一、调用统计（真实调用 73 次 + tools/list 1 次）

| 工具 | 次数 | 结果概要 |
| --- | --- | --- |
| tools/list | 1 | 19 工具清单 + inputSchema 全量记录 |
| list_workspaces | 2 | 本项目 status=draft（发布后有修订）；存在相近名「新品上市POC—V2.0」(01a15c77 之外的另一个项目) 等易混项目 |
| metadata_workspace_model | 1 | 21 entities / 27 relations / 30 rules / 15 actions / 0 algorithms / 8 functions，560KB 完整返回未截断 |
| metadata_list_object_types | 1 | 21 类型，含 attrCount |
| metadata_list_actions | 1 | 15 动作，仅 refCode+name+description，**无 apiName** |
| metadata_list_rules | 1 | 30 规则，含 6 条【待处理】 |
| metadata_list_algorithms | 1 | **空清单**（content=[]） |
| metadata_object_neighborhood | 4 | DishLaunchPlan / MaterialKitting / SupplyDemandAllocation / PurchaseOrder，depth=1 全部成功 |
| objects_query | 51 | DSL 探针 30 + 21 实体计数扫描；语法方言详见第三节 |
| objects_get | 3 | NP009→40402；refCode 形态→40402；未命名实体→40402 |
| objects_links | 1 | NP009→40402（表空无实例可验证正常形态） |
| objects_relation_counts | 4 | **4 种参数形态全部 42200**（含 inputSchema 自述形态），标记待核查 |
| objects_list_branches | 1 | 仅 main（branchId=0），无沙箱分支 |
| actions_task_status | 1 | 假 task_id→400「actionTaskId 期望 UUID」（ruleaction-service 在线） |
| objects_save / objects_delete / objects_edit / objects_create_branch / objects_delete_branch / actions_run | 0 | 红线：只记录 inputSchema，一律未执行 |

## 二、数据实态（main 分支）

**21 个实体全部 totalCount=0——项目已发布但未灌数据**。NP009（青提冰茶 926001）全链实例
（计划→门店→齐套→物料需求→供需分配→采购订单→风险）探查无法进行，标记「待数据灌入后执行」。
佐证：①21 实体 include_total_count 逐个确认为字符串 "0"；②分支仅 main，无其他分支藏数据；
③objects_get NP009 → 40402 对象不存在。
两解释并存（无法进一步区分）：(a) 数据未导入；(b) workspace status=draft（发布后 11:40/13:28
又有修订未发布），数据侧是否受未发布修订影响未知。已作为遗留问题上报总监工。

## 三、objects_query DSL 探针矩阵（本项目方言，51 次实测）

| # | 用例 | 语法 | 结果 |
| --- | --- | --- | --- |
| Q1 | 裸 base 无 filter | object_set={"type":"base","objectType":"DishLaunchPlan"} | ✅ 成功（与旧项目 422 相反） |
| Q2 | filter 包裹无 where | {"type":"filter","objectSet":{...base...}} | ❌ 42200（filter 必须带 where） |
| Q3 | filter+where(operator 键) | where={"property","operator":"eq","value"} | ❌ 42200（不接受 operator 键） |
| W3 | filter+where(type 键) ✅ | where={"type":"eq","property","value"} | ✅ **正确方言** |
| W4 | where operator 键复验 | Dish 实体 | ❌ 42200 |
| V2 | base 节点内嵌 where | {"type":"base","objectType",...,"where"} | ❌ 42200 |
| W5/W6 | and / or + children | {"type":"and","children":[...]} | ✅ |
| W7 | not + children | {"type":"not","children":[...]} | ❌ 42201「not 条件缺少 child」 |
| W14 | not + child（单数） | {"type":"not","child":{...}} | ✅ **本项目特有** |
| W8 | in + value 数组 | {"type":"in","property","value":["a","b"]} | ✅ |
| W12 | gt 数值 | {"type":"gt","property","value":100000} | ✅ |
| W19 | neq+lte 组合 | and children 内 | ✅ |
| W13 | containsAnyTerm | {"type":"containsAnyTerm","property","value":"青提"} | ✅ 语法接受（表空无法验值行为） |
| W9/W10 | select 正常/臆造属性 | ["plan_id","bogus_field"] | 正常✅ / 臆造❌ 42201 未知属性 |
| W18 | property 用 PROP_ refCode | {"type":"eq","property":"PROP_...","value"} | ❌ 42201（**与旧项目相反，只认属性 code**） |
| V1 | include_total_count | 裸 base + include_total_count | ✅ totalCount 返回**字符串** "0" |
| W20 | page 参数 | page:2 | ❌ pydantic 拒绝（分页只认 page_token） |
| W16/W17/W21/W22 | order_by 4 形态 | 对象值式/数组式/单对象式/fields-orders | ❌ 全 42200 或 pydantic 拒——**排序当前不可用** |
| V3/W11 | objectType 用 refCode（正式实体） | OBJ_EEC4903403DF466B | ✅ 被接受（totalCount="0"） |
| W0/W1 | 未命名实体 code / refCode | entity_6f5d573a / OBJ_8EED09B98A53470B | ❌ 40401 未知对象类型（**两种都不行**） |
| W2 | 臆造实体 code | DishLaunchPlanX | ❌ 40401 |
| V4/V5 | objects_get NP009（code/refCode） | — | ❌ 40402 对象不存在（表空） |
| W15 | objects_get 未命名实体 | entity_01e7964c/PP001 | ❌ 40402（get 无法区分类型不可查 vs 实例不存在；query 才给 40401） |
| T3 | objects_links NP009 | — | ❌ 40402（表空） |
| T4a-d | relation_counts 4 形态 | inputSchema 自述/rel code/relation_code 键/真实 REF_ | ❌ 全 42200，待核查 |
| T5 | actions_task_status 假 id | — | ❌ 400「actionTaskId 期望 UUID」（服务在线） |

## 四、元数据 vs entity-v2-clean.md 差异对照（关键行）

### 实体级

- 文档保留 20 实体全部在系统；文档废弃 6 实体（ReplenishmentPeriod/StoreOrder/ForecastSalesTrace/
  InventoryLevelByDay/MaterialInStoreListing/MaterialInWhListing）系统均不存在 ✅。
- **4 实体无正式 code（entity_ 生成名）**：HistorySalesByDay→entity_6f5d573a、PurchasePlan→entity_01e7964c、
  PurchaseSolution→entity_a9f8fc9f、「系统」→entity_9b77ae51（文档无此实体，3 属性：launch_plan_id/
  system_time/system_date，挂接 DishLaunchPlan）→ **均不可经 objects_query/get 查询（40401/40402）**。
- PurchaseSolution 系统仅 5 属性（solution_code/solution_name/solution_description/strategy_code/create_time），
  与文档一致但与旧项目 InitialPurchaseSolution 完全不同物。

### 属性级（差异报告全文见临时区 diff-report2.txt，此处关键行）

| 实体 | 差异 | 影响 |
| --- | --- | --- |
| MaterialSupplier | 文档主键 strategy_code；**系统主键 material_supplier_code**，系统另有 material_in_wh_code，无 strategy_code | objects_get/关联口径要害 |
| SupplyDemandAllocation | 文档保留的 expected_supply_qty_ontime / expected_gap_qty **系统不存在** | 供应按时保障判定（S06）无字段承载 |
| MaterialInWarehouse | 文档保留 available_inventory_qty/dii/idd/inventory_holding_cost/remain_forecast_sales_qty **系统全缺** | 库存指标链路字段缺口 |
| DishLaunchPlan | 系统多 is_new_plan（文档无）；划线废弃的 plan_start_date/plan_end_date/actual_average_sales_qty/forecast_first_month_sales_qty **系统仍在** | 文档删除线未同步系统；引用需双核对 |
| ReferenceDishBinding | 划线废弃 9 个系数属性（price_coef/marketing_amount_coef/forecast_average_sales_qty 等）**系统全部仍在**，对应规则 2 条标【待处理】 | 系数链路「字段在、规则未定稿」 |
| ForecastSalesDemand | 划线 due_date/unfulfill_qty_for_opt/unfulfill_cost_for_opt **系统仍在** | 同上 |
| MaterialDemand | 划线 net_demand_qty/material_demand_date/demand_priority_level **系统仍在**（规则 RULE_B86E790E6「计算物料需求的物料缺口量」存在） | 净需求字段可用但靠规则回写 |
| BOM | 系统多 freeze_time（文档无） | 冻结 BOM 动作的时间戳落点 |

### 关系级（文档 31 条 Link vs 系统 27 关系）

- 系统缺：Dish.history_sales_by_day（**历史销量实体成孤岛**）、DishLaunchPlan.ref_launch_plan 自关联、
  MaterialInWarehouse.purchase_orders / purchase_plan / forecast_sales_demand 3 条。
- 系统多：entity_9b77ae51→DishLaunchPlan「上市计划系统」（文档无）。
- 其余文档 Link 均有系统关系对应（含 ForecastSalesDemand→MaterialDemand rel_f6c38aa9「饮品需求」）。

### 规则与动作

- 30 规则中 6 条标【待处理】：计划结束日期/计划开始日期/当前交货逾期天数/价格系数/营销费用系数/饮品上市事项执行状态。
- 15 动作全部 enabled=true，**但 apiName 全部为 null**，metadata_list_actions 也不返回 apiName——
  actions_run（要求 action_api_name）当前无有效入参来源（对照旧项目 409 坑的新形态：本项目是 apiName 缺失，非发布状态问题）。
- **无「检查上市齐套」类动作/函数**（旧项目 fn_check_launch_readiness/fn_recalculate_readiness_deadlines/
  fn_evaluate_purchase_solution_costs 均不存在）。8 函数为：set_bom_status、fn_recommend_reference_dishes、
  fn_calculate_reference_seasonality、fn_aggregate_reference_launch_sales、create_material_demand、
  allocate_supply_to_demand、create_purchase_plan、create_forecast_sales_demand_by_week。
- 算法清单空（无首批采购方案生成/成本测算算法承载）。

## 五、接口坑清单（现象→复现→处置建议）

1. **DSL 方言与旧项目全面不同**：裸 base 可用（旧项目 422）；filter 必须带 where（旧项目可无）；
   where 算子放 `type` 键（旧项目 operator 键）；not 用 `child` 单数（旧项目 children）；
   property 只认属性 code（旧项目 PROP_ refCode 兼容）。复现：Q1-Q3/W3/W4/W7/W14/W18。
   处置：技能手册按本项目方言写，禁照搬旧 facts；同宿主双技能并存时方言表分技能维护。
2. **未命名实体 4 个不可查**：entity_ 前缀 code 与 OBJ_ refCode 均 40401。复现：W0/W1。
   处置：开工单补正式 code；补齐前历史销量/采购计划/采购方案查询无承载，涉及场景如实声明。
3. **objects_get 对未命名实体报 40402（对象不存在）而非 40401（类型不存在）**：无法从报错区分
   「类型不可查」与「实例不存在」。复现：W15 vs W0。处置：类型可查性判断用 objects_query（给 40401）。
4. **order_by 四种合理形态全部 422**：对象值式/数组式/pydantic 拒/单对象式/fields-orders。复现：W16-W22。
   处置：客户端排序；开工单问询正确语法（或确认功能未上线）。
5. **objects_relation_counts 全形态 42200**：inputSchema 自述形态也失败。复现：T4a-d。
   处置：标记待核查（数据灌入后复验）；当前以 objects_links / 冗余字段 query 替代。
6. **actions_run 无 apiName 来源**：动作 enabled 但 apiName=null，list 不返回 apiName。处置：开工单；
   未修前技能不承诺动作执行。
7. **totalCount 是字符串**："0" 而非 0。复现：V1。处置：解析时按字符串处理。
8. **相近命名项目陷阱**：存在「新品上市POC—V2.0」「新品上市保障（废弃）」等，本项目是
   「新品上市POC-最新版」。处置：workspace_id 逐字核对，禁止按名称模糊匹配。
9. **workspace status=draft**：v1.4.0 发布后又有修订（13:28 最后更新）。处置：动作执行前置检查
   发布状态；数据空态与 draft 状态的因果关系待总监工与平台侧核实。
10. **objects_query 的 MCP description 为空**：DSL 用法无内嵌文档。处置：技能侧自备方言表（facts.md）。

## 六、遗留问题（上报总监工）

1. **main 分支 0 数据**——NP009 全链探查待数据灌入后补做；P2（SKILL.md）不受阻（铁律主要来自
   接口行为实测，已足量），但评估用例（P3）将依赖数据。
2. **未命名实体不可查（含 HistorySalesByDay）**——参考品历史销量查询无承载，影响 S02 场景演示口径。
3. **relation_counts / order_by 待核查**。
4. **storyline 素材基于旧项目实体名**（NewDishLaunchPlan/ReadinessUnit/SubReadinessUnit/
   NewDishLaunchStore/LaunchRisk 等）——本项目模型无这些实体，六类齐套在本项目以 DishLaunchItem
   （上市事项，16 属性含 pre_item_codes 依赖/execution_status/max_plan_completion_time）承载，
   上市风险无实体承载（文档规则区三规则名空壳）。剧本草稿已按本项目实体重写映射，待总监工确认。
