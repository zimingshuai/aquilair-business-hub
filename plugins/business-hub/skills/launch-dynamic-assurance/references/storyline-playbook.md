# 问法意图路由与场景剧本（launch-dynamic-assurance）

> 配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f（新品上市POC-最新版，每次调用逐字核对；
> 网关下有「新品上市POC—V2.0」「新品上市保障（废弃）」等相近名项目，禁止按名称模糊匹配）。
> DSL 方言见 facts.md「objects_query 的 ObjectSet DSL」（where 算子放 type 键、not 用单数 child、
> property 只认属性 code）；业务语义与规则公式见 domain-model.md；物料/采购下钻与上市事项诊断的
> 分步剧本见 material-purchase.md、readiness-playbook.md（业务方原文收录+实测校注）。
> 【实测】2026-11-03 main 分支 21 实体 0 实例：实例问题先探规模（include_total_count=true，
> totalCount 是字符串），空态如实报「数据未灌入」，禁用 NP009 演示值冒充查询结果。

## 一、问法意图路由表（自然语言问法 → 意图类 → 查询路径与口径）

用法三步：① 用户问法（口语、近义、简略说法都可能出现）先按「典型问法变体」列归入
意图类——命中任一变体或其近义即入类，不苛求字面一致；② 按该类「查询路径要点」组织探查
（实体与属性 code 均为实测实名，臆造字段报 42201 时用元数据核对）；③ 「口径与坑」列引用的
章节按需加载。复合问法（一句话含多个意图）拆类分别回答；归不进任何类的问法回到探查循环
（元数据先行→规划路径→取实例→足以回答即停），不硬套本表；拆类后每类按需加载「口径与坑」
列所引 references 章节再作答，不在表内就地展开。

| 意图类 | 典型问法变体（口语/近义/简略） | 查询路径要点（实体+关联字段，实测实名） | 口径与坑（详见所引章节） |
| --- | --- | --- | --- |
| 计划概览与口径 | 「现在有啥新品要上」「NP009 是个啥计划」「上市计划都什么情况」「这计划打算什么时候上」「就绪日定了没」「铺多少家店」 | DishLaunchPlan（plan_id 精确过滤或裸 base）select：plan_id/plan_name/dish_id/plan_launch_date/planned_ready_date/target_store_count/target_first_month_sales_qty/plan_status/plan_version；门店级下钻 DishInStore（dish_id 关联）+Store | 计划就绪日=计划上市日（业务口径，planned_ready_date 空时按此说明，不声称源数据已填写）；forecast_first_month_sales_qty 是预测基准不是经营目标（文档划线但系统字段在）；plan_status 无定义枚举，展示原值不解读【domain-model「一、业务链」】 |
| 进度与事项状态 | 「进度咋样」「搞到哪一步了」「哪些事项卡住了」「还差啥没搞」「BOM 冻结了没」「这事项归谁负责」 | DishLaunchItem 按 launch_plan_id 过滤 select：item_code/item_name/item_type/operator/plan_completion_time/max_plan_completion_time/latest_actual_completion_time/execution_status/pre_item_codes/execution_freq | 六类齐套=item_type 归纳口径；pre_item_codes 是编码列表字符串，客户端展开成 DAG 再排；四类问题分开（数据缺失/业务未完成/读取异常/配置缺失），空集合≠通过【readiness-playbook「诊断步骤」「四类问题」】 |
| 时间与倒排 | 「啥时候必须搞定」「最晚啥时候完成」「还剩几天」「倒排时间给我看看」「死线是哪天」 | DishLaunchItem 的 plan_completion_time/max_plan_completion_time/latest_actual_completion_time；物料侧 MaterialDemand.max_purchase_date/max_lead_time_days | max_plan_completion_time=不影响上市的最晚允许完成≠上市日；需求层 max_purchase_date=material_demand_date−max_lead_time_days（max_lead_time_days=MAX(关联供应商 lead_time_days)，不跨仓全库求最大）；重排倒排计算动作无承载，只读已存排期【domain-model「五、物料齐套与净需求」；readiness-playbook「周期与时间」】 |
| 齐套与缺口排查 | 「料齐了没」「还差啥料」「有没有缺口」「缺多少、哪个仓缺」「啥时候能齐」 | ForecastSalesDemand（dish_id 锁本计划预测版本）→ MaterialDemand（dish_demand_nr 关联；material_demand_qty/total_kit_qty/net_demand_qty/material_demand_date）→ MaterialKitting（demand_nr；kit_qty/kit_time） | 毛需求/齐套量/净需求按【物料×仓库×需求】粒度；net_demand_qty 是规则回写值（规则在册），引用注「计算回写」不自行计算；数量齐但到得晚单独表达时间不满足，不混入数量缺口【material-purchase「需求与供应追溯」】 |
| 供需分配 | 「库存和在途怎么分的」「分配了没、确认了没」「每笔需求能拿到多少」「库存够不够扣」「在途算进来了吗」 | SupplyDemandAllocation 按 demand_nr select：allocation_nr/supply_type/supply_nr/supply_available_date/supply_available_qty/allocated_qty/allocation_status | supply_type 两枚举不同时套用（INVENTORY→supply_nr 指库存批次/PURCHASE_IN_TRANSIT→指采购订单）；枚举出自业务文档（enumValues 全空）；expected_supply_qty_ontime/expected_gap_qty 系统缺失→supply_available_date 与需求日期现算对比并注明字段缺失【domain-model「三、决策枚举」；facts「元数据缺陷」】 |
| 采购方案与计划 | 「采购跟得上来吗」「打算买多少」「采购计划下了没」「最晚啥时候得下单」「MOQ 是多少」「确认/下发了没有」 | 净需求>0 的 MaterialDemand → 采购计划/方案实体（entity_ 未命名，objects_query 40401 不可查【实测】，涉及时如实声明无承载）→ MaterialSupplier 策略参数（material_code+wh_code 过滤） | 需求层与计划层 max_purchase_date 是两种口径不混用；confirm_flag/send_flag≠采购订单已生成；方案生成/成本测算无算法承载，只做缺口×策略参数的可行性说明，不虚构方案【material-purchase「采购方案与采购计划」；facts「服务端状态与能力边界」】 |
| 订单到货跟踪 | 「料到了没」「订单到货了吗」「还有多少没交」「会不会延期」「预计哪天能到」「供应商靠谱吗」 | PurchaseOrder 按 material_code 过滤 select：purchase_order_nr/supplier_code/required_delivery_date/estimated_arrival_date/total_order_qty/undelivery_qty/status/current_overdue_days/expected_delay_days | 当前逾期与预计延期两种口径不混用（一个看当前日期、一个看预计到达日期）；estimated_arrival_date 为空或已过仍未交完=「到货时间待确认」，不归为正常保障；催交/提醒动作无执行凭据不虚称已催【material-purchase「四类订单与分配检查」「提醒、重算与执行边界」】 |
| 风险与放行判断 | 「能不能按时上」「有啥风险没」「会不会赶不上上市」「现在能放行上市吗」「还差什么才能上」 | 三路径汇总：DishLaunchItem 按 execution_status 汇总（未完成/延期=当前阻断项）+ MaterialDemand 净缺口现状 + PurchaseOrder 异常字段；plan_status 读原值 | 风险=可追溯的事项/缺口/订单异常清单，无独立风险实体、不是风险标签；放行结论须六类事项全部完成+无未解缺口才可给出，否则列剩余条件；不为演示效果把计划说成可上市【domain-model「二、上市风险」】 |
| 目标调整影响 | 「目标定 300000 杯合理吗」「目标要不要调」「调目标会影响啥」「预测跟目标差多少」 | DishLaunchPlan select target_first_month_sales_qty 与 forecast_first_month_sales_qty 两字段分别取值对比；参考链 ReferenceDishBinding（new_launch_plan_id 过滤）→参考计划实例（ref_launch_plan_id 中转）读 actual_sales_qty/actual_sales_qty_by_w1~w4 | 口径三分离：首月经营目标（人工设定）/预测基准（参考品系数推导）/分周预测需求三者不同源不混用；差额与偏差率注明计算口径，不代用户调目标；无级联重算规则时不宣称周需求/采购已同步【domain-model「一、业务链」「五、预测基准链」】 |
| BOM 与菜品档案 | 「配方什么版本」「BOM 啥状态」「菜品发布了没」「这菜是现制还是外购」「参考品绑的谁」 | BOM（bom_type/status/output_type/bom_version；freeze_time【实测在】）+ Dish（dish_status/publish_status/fulfillment_type）+ ReferenceDishBinding（bind_type/binding_version/ref_dish_id） | bom_type 研发版/正式计划版、status 草稿态/冻结态；发布≠门店可售（publish_status 变更未发布口径）；枚举均出自业务文档；系数类规则【待处理】引用时注明【domain-model「三、决策枚举」「五、预测基准链」】 |
| 供应参数与单位效期 | 「这料的供应商是谁」「提前期多久」「最小起订量多少」「订货倍数多少」「保质期多长」「单位怎么换算」 | MaterialSupplier（主键 material_supplier_code【实测】/supplier_code/lead_time_days/transport_lead_time/min_order_qty/max_order_qty/order_multiple/valid_from/valid_to/is_active）+ Material（base_uom/purchase_uom/bom_uom/sales_uom 与各系数）+ 批次 expire_date/qc_status/available_qty/frozen_qty/lock_qty | 参数存在≠订单或分配已按时保障；缺单位/系数/有效范围时报待核查，不跨单位相减或凭经验换算；效期与可用量扣减规则按实现核验不自行推断【material-purchase「物料供应参数与单位」】 |
| 上市门店与渠道准备 | 「哪些店上这个新品」「门店准备得咋样」「门店上架了没」「首批铺多少家」「目标区域有哪些」 | DishLaunchPlan.target_region_ids/target_store_count（汇总）→ DishInStore 按 dish_id（sale_status）+ Store（门店档案） | 档案发布≠门店可售（publish_status 口径）；有供应仓库或门店销售记录不证明物料已送达门店——仓库保障与门店可售分开，无配送执行证据不作到店承诺【material-purchase「提醒、重算与执行边界」；readiness-playbook「常见问题路径」】 |
| 元数据与能力边界 | 「这项目都有啥实体」「规则都有哪些」「动作是什么情况」「这字段啥意思」「你能帮我改数据吗」 | metadata_list_object_types / metadata_list_rules / metadata_list_actions / metadata_list_algorithms 四清单；属性级用 metadata_object_neighborhood 核对实名 | 清单以实时元数据为唯一权威，不引记忆值或快照；【待处理】规则逐条注明；动作 apiName 全 null、算法清单空——不承诺执行与测算【facts「服务端状态与能力边界」】 |

复合问法拆解示例（一句话多意图 → 拆类分别回答）：

- 「NP009 能不能按时上？还差啥料？」→ 风险与放行判断 + 齐套与缺口排查（涉在途再加订单到货跟踪）。
- 「进度咋样，采购跟得上来吗？」→ 进度与事项状态 + 采购方案与计划 + 订单到货跟踪。
- 「目标 300000 杯会不会定高了？现在料齐了没？」→ 目标调整影响 + 齐套与缺口排查。
- 「六类齐套分别啥状态，物料那块卡在谁那了？」→ 进度与事项状态 + 齐套与缺口排查。
- 「哪些店上、门店那边准备咋样？」→ 上市门店与渠道准备 + 进度与事项状态。
- 「都有哪些实体？参考品历史销量能查吗？」→ 元数据与能力边界（HistorySalesByDay 不可查如实声明）。

## 二、典型场景索引（S01~S07，细查路径见对应意图类与所引剧本）

| 场景 | 核心问法 | 一句路径（对应意图类） |
| --- | --- | --- |
| S01 计划总览 | 「帮我看看目前的新品上市计划」 | DishLaunchPlan 计划卡：编码/名称/新品/上市日/门店数/首月目标/状态+可下钻指引（计划概览与口径） |
| S02 目标评估 | 「首月经营目标是否需要调整」 | 目标 vs 预测基准两字段分别取值对比+参考链证据，附「目标调整需人工确认」（目标调整影响） |
| S03 齐套倒排 | 「六类齐套分别什么时候前要完成」 | DishLaunchItem 按 item_type 归纳+pre_item_codes 展开 DAG+时间轴（计划/最晚/实际）（进度与事项状态+时间与倒排） |
| S04 物料缺口 | 「物料齐套情况如何？有没有缺口」 | 预测版本→物料需求→分配→齐套，按物料×仓库矩阵输出，缺口可追溯需求编号（齐套与缺口排查+供需分配） |
| S05 采购建议 | 「缺料物料有哪些可行采购方案」 | 净需求×供应商策略参数做交期可行性说明（能否满足需求日期、MOQ/倍数约束），方案生成无算法承载如实声明（采购方案与计划） |
| S06 到货可行性 | 「这些料能否按期到货」 | supply_available_date vs 需求日期现算对比并注明字段缺失+订单 expected_delay_days/undelivery_qty 两层判定（供需分配+订单到货跟踪） |
| S07 风险放行 | 「有哪些风险？能否按期上市」 | 事项/缺口/订单异常三路径汇总→证据（实体/编号/字段）→剩余条件与建议动作（风险与放行判断） |

## 三、通用纪律（每类意图都适用）

- **锁计划再下钻**：多计划并存先确认唯一计划（plan_id 或 dish_id 与用户问法逐字核对）再查关联链；
  计划/菜品/物料/仓库名用「中文名（编码）」双写；单据号（NP/PO-/MD-/SQ-）与工具返回原值
  逐字核对后才引用。
- **元数据先行**：实体/属性/关系/规则清单以 metadata_* 实时返回为唯一权威，不引记忆值或快照；
  枚举口径以元数据+业务文档出处为权威（enumValues 全空）。
- **空态如实**：先探实例规模（include_total_count=true，totalCount 是字符串先转型再比较），0 实例
  报「数据未灌入」并交代这是查询结论；禁用 NP009 文档演示值（300000 杯/300 家/T=2026-11-15）
  冒充查询结果。
- **查无结果≠不存在**：空态期查无实例时把「查无结果」与「数据未灌入」分开表述，不断言业务对象
  不存在；待核查≠已确认不满足，不把系统故障报成业务未完成。
- **迭代与终止**：报错按码自纠（42200→查 DSL 结构；42201→核对属性实名；40401→确认类型可查性，
  entity_ 未命名实体 4 个不可查如实声明）；终止判据=足以回答即停，不穷尽数据。
- **引用不重算**：状态与数值引用回写字段+规则名（【待处理】规则注明）；展示层求和/差额注明
  计算口径；把「解释」变「造数」是违规。
- **输出与可视化**：先结论后证据，逐条标来源（实体.属性/规则 refCode/文档口径）；数据类交付
  强制配可视化（aquilair-data-delivery 两档），只回纯文本表格=违规。
- **故事线素材不作事实源**：NP009 演示设定值（300000 杯/300 家/T=2026-11-15）不作事实源，数值一律
  以实时查询为准；HistorySalesByDay/PurchasePlan/PurchaseSolution 等未命名实体当前不可查（工单挂起），
  涉及时如实声明、聚合值走参考计划实例字段；检查上市齐套/重排倒排/方案生成等动作与算法无注册承载，
  被要求执行时如实说明。
