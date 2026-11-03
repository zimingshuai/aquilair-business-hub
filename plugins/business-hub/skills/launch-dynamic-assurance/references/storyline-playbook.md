# 查询剧本（launch-dynamic-assurance）——NP009 演示故事线映射

> 按 np009-demo-storyline.md 场景组织，实体/属性 code 已按本项目实测元数据重铸（storyline 原文用旧项目
> 实体名 NewDishLaunchPlan/ReadinessUnit/SubReadinessUnit/NewDishLaunchStore/LaunchRisk——本项目均不存在，
> 映射见各场景「口径与坑」）。配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f。
> 【实测】2026-11-03 main 分支 0 实例：模板为数据灌入后即用形态；当前空态按 facts.md「服务端状态」节如实报告。
> DSL 方言见 facts.md（where 算子放 type 键、not 用 child、property 只认属性 code）。

## S01 新品上市计划（「帮我看看目前的新品上市计划」）

- 查询路径：
  1. `objects_query` DishLaunchPlan 裸 base（计划数少可直接全量；多则按需过滤）
     `{"type":"filter","objectSet":{"type":"base","objectType":"DishLaunchPlan"},"where":{"type":"eq","property":"plan_id","value":"NP009"}}`
  2. select：plan_id / plan_name / dish_id / dish_name / plan_launch_date / planned_ready_date /
     target_store_count / target_first_month_sales_qty / plan_status / plan_version
  3. 下钻门店：本项目无 NewDishLaunchStore——门店范围看 target_region_ids / target_store_count
     （汇总口径）；门店级明细走 DishInStore（dish_id 关联）+ Store。
- 口径与坑：**计划就绪日=计划上市日**（planned_ready_date 空时按业务口径说明，不声称源数据已填写）；
  forecast_first_month_sales_qty 是预测基准**不是**经营目标（文档曾划线但系统字段在【实测】）。
- 输出要点：计划卡（编码/名称/新品/上市日/门店数/首月目标/状态）+「可继续下钻事项、物料、采购」指引。

## S02 首月经营目标评估（「首月经营目标是否需要调整」）

- 查询路径：
  1. DishLaunchPlan 取 target_first_month_sales_qty 与 forecast_first_month_sales_qty（select 两字段对比）。
  2. 参考依据：ReferenceDishBinding 按 new_launch_plan_id=计划 plan_id 过滤（select：ref_dish_id /
     ref_launch_plan_id / bind_type / binding_version）。
  3. 参考品首月实销与四周实销在**参考计划实例**（DishLaunchPlan 按 ref_launch_plan_id 精确取）上读
     actual_sales_qty / actual_sales_qty_by_w1~w4；HistorySalesByDay 明细当前不可查【实测 40401】。
- 口径与坑：差额=目标−预测基准、偏差率=差额/预测基准，**展示计算口径不代用户调目标**；无自动调整阈值，
  不凭空给「应调成 X」；参考品绑定缺失或历史数据缺失时直接说明无法可靠评估。
- 输出要点：目标 vs 基准对照、偏差、参考链（绑定→参考计划→实销四周），附「目标调整需人工确认」。

## S03 齐套工作倒排（「六类齐套分别什么时候前要完成」）

- 查询路径：
  1. DishLaunchItem 按 launch_plan_id 过滤（select：item_code / item_name / item_type / operator /
     plan_completion_time / max_plan_completion_time / latest_actual_completion_time / execution_status /
     pre_item_codes / execution_freq）。
  2. 依赖链：pre_item_codes 是编码列表字符串——客户端展开成 DAG 再按 max_plan_completion_time 排。
- 口径与坑：本项目无 ReadinessUnit 六类实体——**六类是事项类型归纳口径**（商品/配方/仓配/物料/供应/
  门店与营销，演示码 Q0001~Q0006 属旧口径），以 item_type 实际取值为准归类；max_plan_completion_time
  是「不影响上市的最晚允许完成」，**不是**统一都等于上市日；重排计算动作（旧 fn_recalculate_）本项目
  无承载【实测】，只读已存排期不自行倒排。
- 输出要点：事项时间轴（计划 vs 最晚 vs 实际）、负责人、依赖、延期标记；「待处理」执行状态规则引用时注明。

## S04 物料齐套与缺口（「物料齐套情况如何？有没有缺口」）

- 查询路径：
  1. ForecastSalesDemand 按 dish_id=926001 过滤（select：forecast_version / demand_nr / wh_code /
     demand_qty / unit_code / week_nr / priority_level）——先锁定本计划预测版本。
  2. MaterialDemand 按 dish_demand_nr ∈ 上述 demand_nr（where type=in，value 传数组）select：
     demand_nr / material_code / wh_code / material_demand_qty / total_kit_qty / net_demand_qty /
     material_demand_date（在册） / max_lead_time_days / max_purchase_date。
  3. SupplyDemandAllocation 按 demand_nr 同法（select：allocation_nr / supply_type / supply_nr /
     supply_available_date / supply_available_qty / allocated_qty / allocation_status）。
  4. MaterialKitting 按 demand_nr（select：material_kitting_nr / material_code / wh_code / demand_date /
     kit_qty / kit_time）。
- 口径与坑：毛需求/齐套量/净需求按【物料×仓库×需求】粒度；net_demand_qty 靠规则回写（引用值注明
  「计算回写」）；历史缺料风险（LR- 演示码）本项目无 LaunchRisk 实体——用事项状态+净需求现状表达，
  不引用旧风险码；「历史风险已关闭」与「当前有缺口」不矛盾要分开说。
- 输出要点：齐套矩阵（物料×仓库：毛需求/已齐套/净缺口/最早齐套时间）、缺口明细可追溯需求编号。

## S05 首批采购建议（「缺料物料有哪些可行采购方案」）

- 查询路径：
  1. 承接 S04 净需求>0 的 MaterialDemand。
  2. 采购计划 entity_01e7964c（采购计划）**当前不可查**【实测 40401】——采购计划/方案（entity_a9f8fc9f）
     明细暂无法展示，如实声明。
  3. 策略参数 MaterialSupplier 按 material_code+wh_code 过滤（select：material_supplier_code（主键，
     非 strategy_code【实测】）/ supplier_code / lead_time_days / min_order_qty / max_order_qty /
     order_multiple / valid_from / valid_to / is_active）。
  4. 在途参考 PurchaseOrder 按 material_code 过滤（select：purchase_order_nr / supplier_code /
     required_delivery_date / estimated_arrival_date / total_order_qty / undelivery_qty / status）。
- 口径与坑：**输出是采购建议/候选口径而非已下达订单**；本项目无方案生成算法/成本测算函数【实测】——
  只能做「缺口×策略参数」的可行性说明（能否满足需求日期、MOQ/倍数约束），不虚构完整方案与成本对比；
  先判断交期满足再谈成本。
- 输出要点：缺口物料清单×可用供应商策略（提前期/MOQ/倍数）×交期可行性判断（max_purchase_date 对比
  今日）+「完整方案生成当前无算法承载」声明。

## S06 供应到货可行性（素材已整体标废弃——保留两层判定口径）

- 素材标注废弃原因相关字段缺失：expected_supply_qty_ontime / expected_gap_qty 系统不存在【实测】。
- 若被问到「能否按期到货」：口径改为 SupplyDemandAllocation.supply_available_date 与需求日期
  （MaterialDemand.material_demand_date 在册）现算对比，输出「晚 X 天」并注明判定字段缺失；
  PurchaseOrder 侧用 expected_delay_days（规则在册）与 undelivery_qty。两层判定口径（不晚于上市日且
  不晚于需求日）仍适用。

## S07 上市风险与放行（「有哪些风险？能否按期上市」）

- 查询路径：
  1. DishLaunchItem 全量按 launch_plan_id：execution_status 汇总（未完成/延期事项=当前阻断项）。
  2. MaterialDemand 净缺口现状（S04 路径）。
  3. PurchaseOrder 在途异常（status / expected_delay_days / current_overdue_days）。
  4. DishLaunchPlan.plan_status 读计划状态（本体未定义状态枚举【BG 3.5.1】，展示原值不解读枚举）。
- 口径与坑：本项目无 LaunchRisk 实体与风险聚合/分级/自动关闭规则【实测】——**风险=可追溯的事项/缺口/
  订单异常清单**，不是风险标签；plan_status 枚举口径未定义，不自行补充通过/不通过枚举；「已关闭风险」
  与「当前阻断」分开表述；**不为演示效果把计划说成可上市**——放行结论必须六类事项全部完成+无未解缺口
  才能给出，否则列剩余条件。
- 输出要点：阻断项清单（事项延期/物料缺口/到货异常）→ 证据（实体/编号/字段）→ 剩余条件与建议动作，
  附「风险实体当前无承载，以上为数据事实汇总」。

## 通用空态与验收提示

- 每场景先探实例规模（include_total_count），空态如实报告「数据未灌入」，**禁止**用 NP009 文档演示值
  （300000 杯/300 家/T=2026-11-15）冒充查询结果【实测 0 实例】。
- 下钻终止判据=足以回答即停；报错按 facts.md 方言表自纠（42200 查结构 / 42201 查实名 / 40401 查类型）。
- 单据号/编码逐字核对后再引用；输出先结论后证据，逐条标来源（实体.属性 / 规则 refCode / 文档口径）。
