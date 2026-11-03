# 物料齐套与采购保障

适用于物料原始需求、齐套结果、供应参数、采购方案/计划、最晚采购日、订单跟踪与分配按时保障。业务数值和判定引用当前规则、算法、函数或已保存结果；文中公式用于解释设计，不授权问答层重算。

## 需求与供应追溯

计划与周需求的归属核验 → ForecastSalesDemand → MaterialDemand → MaterialInWarehouse及供应参数 → 库存/采购在途分配 → MaterialKitting与按时保障结果。采购方案与计划另通过各自有效关系组织补缺执行。

- 根需求有forecast_version、week_nr、priority_level，优先级越小越优先。计划与需求缺少明确关联时不能仅按dish_id把全历史需求混入。
- MaterialDemand以dish_demand_nr关联根需求、material_in_wh_code关联物料在仓、bom_key关联BOM行，并保留bom_id/bom_version。
- material_demand_qty为原始物料需求；total_kit_qty及min_kit_time/max_kit_time是齐套结果，不能把原始需求或分配量直接当采购缺口。
- MaterialKitting通过demand_nr回到物料需求，按kit_time和kit_qty解释结果；要取根需求、配方和分配证据时沿需求的有效关系追溯，不假设齐套记录有额外直接Link。
- SupplyDemandAllocation以demand_nr关联物料需求。supply_type=INVENTORY时supply_nr指向库存批次；PURCHASE_IN_TRANSIT时指向采购订单，两者不同时套用。
- MaterialInWarehouse汇总物料×仓库信息，关联采购订单、采购计划、预测需求及物料供应商；汇总值与来源明细不重复计入有效供应。

## 物料供应参数与单位

MaterialSupplier按物料、仓库、供应商读取，核对material_supplier_code（实测主键）、priority_level、replenishment_cycle、lead_time_days、transport_lead_time、min_order_qty、max_order_qty、order_multiple、valid_from、valid_to和is_active。参数存在不代表订单或分配已经按时保障。

Material使用base_uom、purchase_uom、sales_uom、bom_uom及inv_uom_factor、purchase_uom_factor、bom_uom_factor、sales_uom_factor。由已部署程序按明确系数方向统一数量；缺少单位、系数或有效范围时报告待核查，不跨单位相减或凭经验换算。

效期和库存可用性读取shelf_life_days、min_receive_shelf_life、sled_days以及批次expire_date、qc_status、available_qty、frozen_qty、lock_qty，具体筛选和扣减规则按实现核验，不自行推断可用供应量。

## 需求层采购期限

- MaterialDemand.max_lead_time_days设计为MAX(material_supplier.lead_time_days)。必须确认关联路径以及参与计算的物料、仓库、供应商有效集合，不能跨仓或全库求最大值。
- MaterialDemand.max_purchase_date设计为material_demand_date-max_lead_time_days，用于解释需求的最晚采购准备期限。
- material_demand_date为需要的派生属性，但有效输入来源需核验。来源不明确时保留属性语义并报告待核查，不补造日期或恢复无效来源。

## 采购方案与采购计划

PurchaseSolution / PurchasePlan 当前缺正式 code、实例查询通道不稳定（服务端缺陷，工单挂起；2026-11-03 复验 40401/500/不可达交错、期间曾查通返回空态）——每次实时尝试，失败按错误码如实报告；以下字段口径供查询可用时使用。

| 对象/字段 | 业务口径 |
| --- | --- |
| PurchaseSolution | 方案头：solution_code、solution_name、solution_description、strategy_code、create_time |
| 方案到计划 | 按solution_code关联多条PurchasePlan |
| PurchasePlan.net_demand_qty | 采购计划缺口量，须由已实现算法或数据流程提供，不能自行新增需求层字段替代 |
| plan_purchase_qty | 考虑MOQ、整批倍数后的计划采购量；上限和供应分配方式由当前规则确定 |
| lead_time_days | 设计来源为物料供应商采购提前期；按具体计划所选来源核验 |
| max_purchase_date | 要求交货日减采购提前期；公式字段标识必须与元数据一致 |
| confirm_flag / send_flag | 分别表示确认与下发，不能直接等同采购订单已生成 |
| 其他有效信息 | material_code/name、wh_code/name、purchase_plan_code、purchase_plan_nr、solution_code、required_delivery_date、unit_code、supplier_code |

需求层最大提前期和具体采购计划提前期是不同口径，不把两种max_purchase_date混用。方案策略选择、缺口生成、MOQ/倍数调整、成本优化、确认后修改及下发幂等须有当前项目实现；缺少契约时如实说明，不生成所谓最优方案。

修改final_target_sales_qty前核对动作实际写入字段和影响范围。默认值或字段变更不证明周需求、物料需求、方案与已确认计划已自动重算。需要级联操作时按明确规则及授权执行，不擅自更新采购数据。

## 四类订单与分配检查

| 检查 | 主要输入/条件 | 报告 |
| --- | --- | --- |
| 当前交货逾期 | 未取消、未关闭、undelivery_qty>0及已计算current_overdue_days | 已超过要求交期的剩余未交量 |
| 预计交期不满足 | 有效未交订单及expected_delay_days | 预计到货不满足订单要求交期的风险 |
| 采购分配按时保障 | PURCHASE_IN_TRANSIT、CONFIRMED、allocated_qty>0及关联订单 | 哪笔需求能按期获得多少供应、缺口和原因 |
| 发货提醒 | 有效未交、ship_date为空、配置的提醒日和最晚发货日 | 当前已部署提醒阶段及发送凭据 |

当前逾期设计依据当前日期与required_delivery_date，预计延期依据estimated_arrival_date与required_delivery_date；两者不能混用。预计到货为空，或已过期但仍未交完，报告到货时间待确认，不能归为正常保障。

## 采购分配按时保障

1. 从目标计划的有效物料需求范围取已确认采购在途分配，用supply_nr关联PurchaseOrder.purchase_order_nr，核对物料、仓库和订单状态。
2. expected_supply_qty_ontime / expected_gap_qty 当前无此字段（实测，工单挂起）——按时保障判定以 supply_available_date 与 material_demand_date 现算对比展示：可用日晚于需求日取 0 供给，否则取 MIN(supply_available_qty, allocated_qty)；缺口=MAX(0, allocated_qty−按时供给)；现算结果注明「展示口径，判定字段缺失」，不与规则回写值混淆。
3. 订单未超过自己的交期也可能赶不上更早的物料需求日；订单交期与需求保障分开报告。
4. 取消或关闭订单不再贡献有效在途，但其未履约分配仍是供应失效问题，不能通过过滤订单隐藏。
5. 单笔分配有按时供应量不证明全局总量足够；多条分配共用同一供应时须核验算法总量约束或对账结果。

输出分配编号、订单编号、需求编号、物料/仓库、需求日期、供应可用日、分配量、按时供应量和缺口。订单、分配与物料需求三个粒度分别汇总，避免缺口重复累计。

## 提醒、重算与执行边界

- latest_delivery_date设计为required_delivery_date-transport_lead_time；delivery_warning_day再减配置提前提醒天数，参数不能固定为任意天数。
- 提醒窗口、最晚发货与逾期阶段按已部署条件解释；缺少阶段阈值、去重记录或发送动作时，不自行补条件或宣称已经催交。
- ship_date已填写后停止对应未发货提醒，仍可单独跟踪到货风险。
- 供应失效通知、供需重算和计划下发是动作；先核验实现及授权，保存失败或部分成功须明确说明。
- 仓库保障与门店可售分开；有供应仓库或门店销售记录不证明物料已送达门店，没有配送执行证据不作到店承诺。

交付按同单位分组展示需求、齐套、采购期限、订单风险和分配保障，可视化按 aquilair-data-delivery 技能规范执行；字段来源缺口按[facts.md](facts.md)核验。

> 来源：业务方剧本（2026-11-03），正文已按当日实测元数据修订；后续以实时元数据为准。
