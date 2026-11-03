# 问法意图路由（launch-dynamic-assurance）

> 本文件只做问法→意图归类与路由；行为纪律见 SKILL.md 铁律，DSL 方言见 facts.md，
> 字段与路径细节见 domain-model.md 与 material-purchase.md、readiness-playbook.md 两个分步剧本。
> 配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f（新品上市POC-最新版，每次调用逐字核对；
> 网关下有「新品上市POC—V2.0」「新品上市保障（废弃）」等相近名项目，禁止按名称模糊匹配）。
> 数据状态以实时探查为准（2026-11-03 傍晚观测到 NP009 演示数据灌入）：实例问题先探规模
> （include_total_count=true，totalCount 是字符串），数值以查询返回为准，禁用文档演示值冒充。

## 问法意图路由表（自然语言问法 → 意图类 → 查询路径与口径）

用法：① 问法（口语、近义、简略说法都可能出现）按「典型问法变体」列归类——命中任一变体或其
近义即入类，不苛求字面一致；② 按该类「查询路径要点」组织探查，「口径与坑」列所引章节按需加载。
复合问法（一句话含多个意图）拆类分别回答；归不进任何类的问法回到探查循环，不硬套本表。

| 意图类 | 典型问法变体（口语/近义/简略） | 查询路径要点（入口实体+关键关联） | 口径与坑（详见所引章节） |
| --- | --- | --- | --- |
| 计划概览与口径 | 「现在有啥新品要上」「NP009 是个啥计划」「上市计划都什么情况」「这计划打算什么时候上」「就绪日定了没」「铺多少家店」 | DishLaunchPlan（plan_id 精确过滤或裸 base）；门店级下钻 DishInStore（dish_id 关联）+Store | 计划就绪日=计划上市日（业务口径，planned_ready_date 空时按此说明，不声称源数据已填写）；forecast_first_month_sales_qty 是预测基准不是经营目标（文档划线但系统字段在）；plan_status 无定义枚举，展示原值不解读【domain-model「一、业务链」】 |
| 进度与事项状态 | 「进度咋样」「搞到哪一步了」「哪些事项卡住了」「还差啥没搞」「BOM 冻结了没」「这事项归谁负责」 | DishLaunchItem 按 launch_plan_id 过滤→item_type 归纳 | 六类齐套=item_type 归纳口径；pre_item_codes 是编码列表字符串，客户端展开成 DAG 再排；四类问题分开（数据缺失/业务未完成/读取异常/配置缺失），空集合≠通过【readiness-playbook「诊断步骤」「四类问题」】 |
| 时间与倒排 | 「啥时候必须搞定」「最晚啥时候完成」「还剩几天」「倒排时间给我看看」「死线是哪天」 | DishLaunchItem（launch_plan_id 过滤）取计划/最晚/实际完成时间；物料侧 MaterialDemand 最晚采购日与提前期 | max_plan_completion_time=不影响上市的最晚允许完成≠上市日；需求层 max_purchase_date=material_demand_date−max_lead_time_days（max_lead_time_days=MAX(关联供应商 lead_time_days)，不跨仓全库求最大）；重排倒排计算动作无承载，只读已存排期【domain-model「五、物料齐套与净需求」；readiness-playbook「周期与时间」】 |
| 齐套与缺口排查 | 「料齐了没」「还差啥料」「有没有缺口」「缺多少、哪个仓缺」「啥时候能齐」 | ForecastSalesDemand（dish_id 锁本计划预测版本）→MaterialDemand（dish_demand_nr 关联）→MaterialKitting（demand_nr 关联） | 毛需求/齐套量/净需求按【物料×仓库×需求】粒度；net_demand_qty 是规则回写值（规则在册），引用注「计算回写」不自行计算；数量齐但到得晚单独表达时间不满足，不混入数量缺口【material-purchase「需求与供应追溯」】 |
| 供需分配 | 「库存和在途怎么分的」「分配了没、确认了没」「每笔需求能拿到多少」「库存够不够扣」「在途算进来了吗」 | SupplyDemandAllocation 按 demand_nr 过滤 | supply_type 两枚举不同时套用（INVENTORY→supply_nr 指库存批次/PURCHASE_IN_TRANSIT→指采购订单）；枚举出自业务文档（enumValues 全空）；expected_supply_qty_ontime/expected_gap_qty 系统缺失→supply_available_date 与需求日期现算对比并注明字段缺失【domain-model「三、决策枚举」；facts「元数据缺陷」】 |
| 采购方案与计划 | 「采购跟得上来吗」「打算买多少」「采购计划下了没」「最晚啥时候得下单」「MOQ 是多少」「确认/下发了没有」 | 净需求>0 的 MaterialDemand→采购计划/方案实体（entity_ 未命名，查询通道不稳定【实测】：实时尝试，失败按错误码如实报告）→MaterialSupplier 策略参数（material_code+wh_code 过滤） | 需求层与计划层 max_purchase_date 是两种口径不混用；confirm_flag/send_flag≠采购订单已生成；方案生成/成本测算无算法承载，只做缺口×策略参数的可行性说明，不虚构方案【material-purchase「采购方案与采购计划」；facts「服务端状态与能力边界」】 |
| 订单到货跟踪 | 「料到了没」「订单到货了吗」「还有多少没交」「会不会延期」「预计哪天能到」「供应商靠谱吗」 | PurchaseOrder 按 material_code 过滤 | 当前逾期与预计延期两种口径不混用（一个看当前日期、一个看预计到达日期）；estimated_arrival_date 为空或已过仍未交完=「到货时间待确认」，不归为正常保障；催交/提醒动作无执行凭据不虚称已催【material-purchase「四类订单与分配检查」「提醒、重算与执行边界」】 |
| 风险与放行判断 | 「能不能按时上」「有啥风险没」「会不会赶不上上市」「现在能放行上市吗」「还差什么才能上」 | 三路径汇总：DishLaunchItem 按 execution_status 汇总（未完成/延期=当前阻断项）+MaterialDemand 净缺口现状+PurchaseOrder 异常字段；plan_status 读原值 | 风险=可追溯的事项/缺口/订单异常清单，无独立风险实体、不是风险标签；放行结论须六类事项全部完成+无未解缺口才可给出，否则列剩余条件；不为演示效果把计划说成可上市【domain-model「二、上市风险」】 |
| 目标调整影响 | 「目标定 300000 杯合理吗」「目标要不要调」「调目标会影响啥」「预测跟目标差多少」 | DishLaunchPlan 目标与预测基准两字段分别取值对比；ReferenceDishBinding（new_launch_plan_id 过滤）→参考计划实例（ref_launch_plan_id 中转）读实际销量与分周 | 口径三分离：首月经营目标（人工设定）/预测基准（参考品系数推导）/分周预测需求三者不同源不混用；差额与偏差率注明计算口径，不代用户调目标；无级联重算规则时不宣称周需求/采购已同步【domain-model「一、业务链」「五、预测基准链」】 |
| BOM 与菜品档案 | 「配方什么版本」「BOM 啥状态」「菜品发布了没」「这菜是现制还是外购」「参考品绑的谁」 | BOM 状态与版本（freeze_time【实测在】）+Dish 发布与履约状态+ReferenceDishBinding 绑定关系 | bom_type 研发版/正式计划版、status 草稿态/冻结态；发布≠门店可售（publish_status 变更未发布口径）；枚举均出自业务文档；系数类规则【待处理】引用时注明【domain-model「三、决策枚举」「五、预测基准链」】 |
| 供应参数与单位效期 | 「这料的供应商是谁」「提前期多久」「最小起订量多少」「订货倍数多少」「保质期多长」「单位怎么换算」 | MaterialSupplier（主键 material_supplier_code【实测】，material_code+wh_code 定位）+Material 多单位与系数+库存批次效期与可用量 | 参数存在≠订单或分配已按时保障；缺单位/系数/有效范围时报待核查，不跨单位相减或凭经验换算；效期与可用量扣减规则按实现核验不自行推断【material-purchase「物料供应参数与单位」】 |
| 上市门店与渠道准备 | 「哪些店上这个新品」「门店准备得咋样」「门店上架了没」「首批铺多少家」「目标区域有哪些」 | DishLaunchPlan 目标区域与门店数（汇总）→DishInStore（dish_id 关联，sale_status）+Store 门店档案 | 档案发布≠门店可售（publish_status 口径）；有供应仓库或门店销售记录不证明物料已送达门店——仓库保障与门店可售分开，无配送执行证据不作到店承诺【material-purchase「提醒、重算与执行边界」；readiness-playbook「常见问题路径」】 |
| 元数据与能力边界 | 「这项目都有啥实体」「规则都有哪些」「动作是什么情况」「这字段啥意思」「你能帮我改数据吗」 | metadata_list_object_types / metadata_list_rules / metadata_list_actions / metadata_list_algorithms 四清单；属性级用 metadata_object_neighborhood 核对实名 | 清单以实时元数据为唯一权威，不引记忆值或快照；【待处理】规则逐条注明；动作 apiName 已填充但执行受项目发布态约束（draft 时 409）、算法清单空——不承诺执行与测算【facts「服务端状态与能力边界」】 |

复合问法拆解示例（一句话多意图 → 拆类分别回答）：

- 「NP009 能不能按时上？还差啥料？」→ 风险与放行判断 + 齐套与缺口排查（涉在途再加订单到货跟踪）。
- 「目标 300000 杯会不会定高了？现在料齐了没？」→ 目标调整影响 + 齐套与缺口排查。
