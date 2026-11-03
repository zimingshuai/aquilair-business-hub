# 业务语义卡（launch-dynamic-assurance）

> 只载元数据查不到的业务口径编译；实体/属性/关系清单以 `metadata_list_*` 实时返回为唯一权威，本卡不维护副本。
> 出处标注约定：【文档】=素材文档章节（entity-v2-clean.md 简称 E2 / poc-business-background.md 简称 BG /
> np009-demo-storyline.md 简称 SL / actions-and-functions.md 简称 AF）；【元数据 refCode】=本项目实时元数据；
> 【实测】=2026-11-03 MCP 实测。配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f。

## 一、业务链（一个新品从立项到上市的全链）

计划立项（DishLaunchPlan）→ 参考品绑定（ReferenceDishBinding）→ 参考品历史销量聚合（HistorySalesByDay，
**实体当前不可查**【实测 40401】）→ 首月经营目标 vs 预测基准 → 周粒度预测需求（ForecastSalesDemand，
4 条周需求）→ BOM 展开物料需求（MaterialDemand）→ 库存/在途供需分配（SupplyDemandAllocation）→
物料齐套（MaterialKitting）→ 采购计划（entity_01e7964c 采购计划，**不可查**【实测】）→ 采购订单跟踪
（PurchaseOrder）。上市准备工作以**上市事项**（DishLaunchItem）跟踪执行与依赖。【BG 2.2/3.x，实测模型】

关键口径：
- **计划就绪日 = 计划上市日**（业务确认口径；源数据 planned_ready_date 为空时按 plan_launch_date 说明）
  【SL 一】。
- 首月经营目标（target_first_month_sales_qty）≠ 首月需求预测基准值（forecast_first_month_sales_qty）——
  前者是经营目标，后者由参考品系数推导【BG 3.2】。两字段系统均存在【实测】。
- 预测需求拆 4 条周需求，需求交期=各周周初日期【E2 二.首月需求拆分】。
- 上市前保障聚焦**供应商到仓库**，不含仓库到门店末端配送【BG 1.3】。

## 二、判定链语义

### 上市事项执行状态（本项目「六类齐套」的承载形态）

- 六类齐套工作以 DishLaunchItem 上市事项承载（以实时元数据为准）：item_type 标事项类型（如 BOM 冻结/
  采购计划确认/库存更新/门店上架）、pre_item_codes 前置依赖、execution_status 执行状态、
  max_plan_completion_time 最晚允许完成时间（按上市就绪倒排）【E2 一.DishLaunchItem】。
- 执行状态判定（规则【待处理】，引用时注明）：latest_actual_completion_time 非空且 ≤ 计划完成时间=已完成；
  非空但 > 计划=延期完成；为空=未完成【E2 二.上市事项.执行状态，RULE_40E295A0E】。
- 六类归纳口径：商品/配方/物料/供应/仓配/门店与营销——按 item_type 实际取值归类（以实时查询为准）。

### 上市风险

- 上市风险**无独立实体承载**【实测模型】；文档规则区「上市事项延期/未完成风险/物料未齐套风险/
  采购订单延期到货风险」三条为空壳【E2 二.上市风险】。
- 风险现状的表达路径：上市事项延期/未完成 ← DishLaunchItem 状态；物料缺口 ← MaterialDemand
  net_demand_qty（字段在、靠规则回写，规则 RULE_B86E790E6 在册）；到货延期 ← PurchaseOrder
  current_overdue_days/expected_delay_days（后者规则 RULE_901C611902 在册）。

### 采购订单跟踪判定（规则在册，口径如下）

- 交货逾期：未取消、未关闭、undelivery_qty>0 且逾期天数>0【E2 二.采购订单跟踪.订单交货逾期检查，RULE_D106C1119】。
- 预计延期：expected_delay_days=MAX(0, estimated_arrival_date − required_delivery_date)【同上，RULE_901C611902】。
- 预计到达日期为空或已过而未交完=「预计到达日期待确认」，不判为正常保障【同上】。
- 发货提醒窗：latest_delivery_date=required_delivery_date−transport_lead_time（RULE_17C6D16FC）；
  delivery_warning_day=latest_delivery_date−提前提醒天数（配置参数）（RULE_62EC96518）【E2 二.采购订单跟踪】。
- 供应按时保障（S06 口径）：供应可用日期须同时不晚于上市日与物料需求日期，第二层不过=不能承诺按时
  保障【SL S06（该场景整体标废弃，但两层判定口径仍可作解释框架）；字段 expected_supply_qty_ontime/
  expected_gap_qty 系统缺失【实测】，需现算并注明】。

## 三、决策枚举（均出自文档描述；元数据 enumValues 全空【实测】）

| 字段 | 枚举 | 出处 |
| --- | --- | --- |
| SupplyDemandAllocation.supply_type | INVENTORY（仓库库存）/ PURCHASE_IN_TRANSIT（采购在途） | E2 一.SupplyDemandAllocation |
| SupplyDemandAllocation.allocation_status | PLANNED / CONFIRMED / CANCELLED | E2 同上 |
| Dish.fulfillment_type | MADE_TO_ORDER（现制）/ DIRECT_SALE（外购直售） | E2 一.Dish |
| Dish.dish_status | 草稿 / 正常 / 停用 | E2 同上 |
| Dish.publish_status | 未发布 / 已发布 / 变更未发布（发布≠门店可售） | E2 同上 |
| BOM.bom_type | 研发版 / 正式计划版 | E2 一.BOM |
| BOM.status | 草稿态 / 冻结态 | E2 同上 |
| BOM.output_type | 饮品 / 半成品 | E2 同上 |
| DishLaunchPlan.plan_type | 全新品 / 季节品 | E2 一.DishLaunchPlan |
| DishLaunchItem.execution_freq | NONE（一次性）/ DAILY / WEEKLY | E2 一.DishLaunchItem |
| DishLaunchItem.execution_status | NOT_STARTED / IN_PROGRESS / COMPLETED / BLOCKED | E2 同上 |
| ReferenceDishBinding.bind_type | 参考品 / 类比品 | E2 一.ReferenceDishBinding |

## 四、编码字典（单据号编码规则与锚点口径；数值不作事实源）

- 单据号前缀：NP=上市计划 / MD-=物料需求 / PO-=采购订单 / SQ-=采购方案——回显前与工具返回原值逐字核对。
- 计划编码 NP009=青提冰茶上市计划（dish_id=926001）【SL 一】——演示设定值（T=2026-11-15、首月目标
  300000 杯、300 家门店）不作事实源，数值以实时查询为准。
- 【实测】当前 main 分支 0 实例——编码均未在系统出现，回答时以实时查询为准。

## 五、规则公式口径（引用时以 metadata_list_rules 实时清单核对 refCode 与【待处理】标记）

### 预测基准链（新品需求）

- 预测新品首月均店销量 = 参考品上市实际均店销量 × 参考品季节系数 × 价格系数 × 门店系数 × 营销费用系数
  【E2 一.ReferenceDishBinding.derived；均店销量规则 RULE_D5194A61B，**价格系数规则【待处理】RULE_45A2FFE94、
  营销费用系数规则【待处理】RULE_58208B24A**】。
- 价格系数 =(新品定价 ÷ 参考品均价)^价格弹性系数；营销费用系数 =1+0.4×ln(新品营销预算 ÷ 参考品实际
  营销费用)【E2 同上】。
- 季节系数 = 参考品过去 1–3 年各月总销量 ÷ 全年月均销量再平滑；全年均值为 0 或数据不足=不可计算
  【E2 二.参考品季节系数计算，动作 ACT_A8F6AEFC5B2D4BCF】。
- 首月需求拆分：周占比=参考品周销量 ÷ 四周总销量；新品周需求=首月经营目标×周占比；交期=周初日期
  【E2 二.首月需求拆分，函数 create_forecast_sales_demand_by_week】。
- 上市实际均店销量 = 首月实销 ÷ 目标门店数量【RULE_C5533C12FA6F46DB】。

### 物料齐套与净需求

- 物料需求按根需求-BOM 物料维度生成（多层半成品递归展开；需求与供应的物料/仓库/单位必须一致；
  分配不超需求剩余、不超来源扣除已有有效分配后的剩余）【AF 计算物料齐套，函数 allocate_supply_to_demand】。
- 净需求/物料缺口量 net_demand_qty=毛需求−总齐套量（字段在系统、规则 RULE_B86E790E6 在册）【E2+元数据】。
- 数量齐够但到得晚：单独表达时间不满足，不混入数量缺口【AF 同上】。
- 最晚下发采购日期 = 物料需求日期 − 最大采购提前期（MAX(material_supplier.lead_time_days)）
  【RULE_7924127E9（最大采购提前期）；RULE_F8D3E2843（最晚下发采购日期）**enabled=false 当前停用**——
  引用时核对实时 enabled 状态】。

### 逾期/延期（采购订单）

- current_overdue_days=MAX(0, 当前日期−required_delivery_date)【E2 属性 derived；计算规则【待处理】RULE_908B6B443】。
- expected_delay_days=MAX(0, estimated_arrival_date−required_delivery_date)【RULE_901C611902】。
- estimated_arrival_date=order_date+lead_time_days【E2 属性 derived】。

### 采购方案（能力边界提醒）

- 首批采购：净需求>0 的物料按首批比例/提前期/MOQ/订货倍数/供应商约束生成候选方案；先判断满足需求日期
  再比较成本【AF 生成首批采购方案】【实测：本项目无算法注册、无成本测算函数，方案生成链路当前无承载】。
- PurchaseSolution 系统仅 5 个基础字段（无目标测算字段）【实测元数据】——成本测算结果无落点，引用时说明。

## 六、动作与函数在册清单（实时状态以 metadata_list_actions 为准；全部 apiName=null【实测】）

15 动作要点：创建新品上市计划/修改首月经营目标/生成预测需求（首月拆分）/生成物料需求/计算物料齐套/
生成采购计划/推荐新品参考品/更新参考品首月销量/更新参考品季节系数/冻结BOM版本/更新冻结BOM实际完成
时间/更新检查基础数据实际完成时间/修改饮品上市事项执行状态/【待处理】订单交货逾期通知/【待处理】
预计到达不满足交期提醒【实测 02-actions.json】。8 函数见 facts.md 服务端状态节。
**无检查上市齐套/重排齐套时间/成本测算动作**【实测】——被要求执行时如实说明无承载。
