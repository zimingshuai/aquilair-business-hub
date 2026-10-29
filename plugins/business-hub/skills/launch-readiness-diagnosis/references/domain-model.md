# 新品上市域模型速查（业务文档编译版 + 10-29 元数据刷新）

> 出处：`docs/新品上市业务背景与功能说明.md`（飞书 wiki 2026-10-23 拉取）+ MCP 元数据 2026-10-29 刷新（37 实体/49 关系/37 规则）。
> 本文件是业务文档与元数据的编译摘录；**字段与规则细节以 MCP 元数据（metadata_list_*）为唯一权威**，两者冲突时以元数据为准并记录到 facts.md。

## 业务链总览（五大模块）

```
新品分型(3.1) → 新品需求(3.2) → 六类齐套(3.3) → 首批采购(3.4) → 上市前保障(3.5)
  参考品绑定      周粒度预测需求     倒排+状态判断     物料齐套计算+方案     齐套状态+到货跟踪
                                                    （规则层已建，执行动作未注册）
```

计划时间范围：以计划上市日 **T** 为基准，默认 **T-28 至 T+28**（可配置参数）。

## 六类齐套（ReadinessUnit）与上游约束

| 齐套单元 | 工作范围 | 上游约束（业务文档） |
| --- | --- | --- |
| 商品齐套 | 商品基础信息、销售规格及上市范围等准备 | 无 |
| 配方齐套 | BOM 配方及冻结/发布准备 | 无 |
| 仓配齐套 | 门店与上游供应仓库覆盖关系确认 | 无 |
| 物料齐套 | 基于预测需求、BOM、库存及在途计算物料齐套时间与数量 | 商品、配方、仓配齐套、门店与营销齐套 |
| 供应齐套 | 供应商向仓库交付及到仓可用保障 | 物料齐套 |
| 门店与营销齐套 | 门店上架、设备及培训等已定义准备情况 | 商品齐套 |

**状态判断链**：时间轴滚动 → 子齐套项齐套状态判断规则 → SubReadinessUnit.readiness_status → 齐套单元齐套状态判断规则 → ReadinessUnit.readiness_status（规则明确：**所有子齐套项均齐套，齐套单元才视为齐套**）→ 新品上市前计划通过状态判断规则 → NewDishLaunchPlan.plan_status（数据实态枚举：「执行中 / 已完成」，完整判断分支仍未定义）。

**上市决策枚举（10-29 新权威依据）**：上市风险实体（entity_f44ddbf6）描述明确——六类齐套整体检查结果支撑上市决策，枚举为**「通过、有条件通过、延期」**。回答「能否上市」时以此为准组织（结合风险台账的 open 风险），不再说「整体判定无依据」。

**时间倒排**：从 NewDishLaunchPlan.planned_ready_date 倒推六类 ReadinessUnit 的 max_readiness_start_date / max_readiness_end_date。子齐套项排期（plan_readiness_start/end_date、operator_code 负责人）由业务人员安排；子齐套自动倒排规则本体仍未定义。⚠️ 已知脏数据：计划的 plan_start_date / plan_end_date 被存为数值序列（如 20261087）。

**编码体系（实例实测）**：Q0001 商品齐套 / Q0002 配方齐套 / Q0003 物料齐套 / Q0004 供应齐套 / Q0005 仓配齐套 / Q0006 门店与营销齐套；`readiness_status` 中文枚举「已齐套 / 未齐套」。**上游依赖以实例数据（upstream/downstream_readiness_unit_list）为准**，与文档上表存在出入（Q0001 上游=Q0002、Q0003 上游缺 Q0002、Q0002 下游自指——差异见 facts.md，属待业务确认的数据问题）。

## 核心实体分组（37 实体，10-29 实测全集）

| 模块 | 实体 |
| --- | --- |
| 计划与菜品 | NewDishLaunchPlan（36 属性，含计划上市日/就绪日/首月目标/预测基准值/plan_status）、Dish、DishCategory、DishSpecification（销售规格）、NewDishLaunchStore（计划首发门店明细）、NewDishLaunchTest（上市测试） |
| 门店与供应 | Store（14）、Warehouse、Supplier、SupplyNetwork、SupplyRouting（13）、SalesOrder（14）、DishInStore（门店菜品）、DishListing（菜品上架）、ProductListing（物料上架） |
| 新品分型/需求 | ReferenceDishBinding（21 属性，系数族已回写）、HistorySalesByDay、ForecastSalesDemand（13） |
| 齐套与风险 | ReadinessUnit（20，**10-29 起正式挂接计划**：rel_9008e4bc 所属新品上市计划 n:1）、SubReadinessUnit（23，operator/排期/状态字段族）、**上市风险 entity_f44ddbf6（18 属性，已入元数据清单）**：risk_category 一级风险域（按期上市风险）承接六类齐套整体检查；risk_type 二级明细（商品/BOM/物料/供应/仓配/门店与营销）；关联触发单元与子项；risk_status（已关闭/评估）、risk_level（次要…）、risk_owner、mitigation_plan、discovered/resolve_date——**齐套诊断的现成问题台账，处理顺序表直接引用** |
| 配方/物料 | BOM（20）、Product（22）、ProductCategory、BatchInventory、MaterialDemand（21：毛需求/总齐套量/**物料净需求为派生属性**）、MaterialKitting（14）、SupplyDemandAllocation（14）、单位转换（entity_f4c32f47） |
| 采购 | InitialPurchaseStrategy（15）、InitialPurchaseObjective（4）、InitialPurchaseSolution（6，description 错位待修）、PurchasePlan（21，**采购成本规则已建**）、PurchaseOrder（18，在途/交付字段族） |
| 补货（存量业务） | InventoryBusinessStrategy、ReplenishmentStrategy、ReplenishmentPeriod（13） |

> 实例规模（10-26 盘点 + 10-29 部分复核，全量见 facts.md）：HistorySalesByDay 18.24 万（大表）、ProductListing 6504、NewDishLaunchStore 1000、Store 688、SubReadinessUnit 28、NewDishLaunchPlan 9、ReadinessUnit 6、上市风险 4（NP009）、Dish 5；ForecastSalesDemand 仅 1 条（文档口径应 4 条周粒度，数据不完整）。

**关键关系（10-29 新增 5 条）**：ReadinessUnit→NewDishLaunchPlan（所属新品上市计划）；NewDishLaunchPlan→上市风险（1:n）；上市风险→ReadinessUnit/SubReadinessUnit（触发单元/子项）；SupplyRouting→SupplyNetwork；SalesOrder→Dish。齐套链导航：计划 →links→ 风险台账 →关联字段→ 单元/子项（objects_links 对计划可用、对 ReadinessUnit 仍空）。

## 规则清单（37 条，10-29 大版本；以 metadata_list_rules 名称为准）

**参考品与预测族（生效）**：参考品季节系数/销售均价/上市实际均店销量/营销费用/新品销售定价/新品营销预算读取（6 条「获取…」）；预测新品首月均店销量（=上市实际均店销量×季节×价格×门店×营销费用系数）；首月需求预测基准值；上市实际均店销量（=首月实销/目标门店数）；计划的参考品历史上市计划编码/参考品菜品编码读取（2 条）；预测销售需求的交期。

**齐套时间与读取族（生效）**：齐套环节的计划/实际齐套开始时间（=子齐套最早值）、计划/实际齐套结束时间（=最晚值）共 4 条；**齐套单元的新品上市计划日/就绪日/计划开始时间读取（3 条）**；**子齐套的计划编码/上市计划日/就绪日/计划开始时间读取（4 条）**——齐套与子齐套对象已系统性挂接计划字段。

**物料需求族（生效）**：物料需求日期（=菜品需求日期）、物料需求优先级（=菜品需求优先级）、**物料净需求（=毛需求−总齐套量，派生属性，10-29 实例未回写值）**。

**首批采购与成本族（10-29 新增，规则层已建）**：预测销售需求的优化后缺货量（MAX(0, 预测需求−满足量)）、优化后缺货成本（×单位成本）；销售订单的优化后缺货成本；**采购计划的采购成本（=计划总量×单位成本）**。⚠️ 执行动作与优化算法仍无（algorithms 空、无方案生成动作）——「读得到成本规则、跑不了方案生成」。

**子项检查展开（10-29 新增）**：「更新子齐套-上市计划已明确新品的检查情况」——子项级检查规则开始逐条落地（六类全量展开仍缺）。

**其他**：门店的供应仓库编码（主供唯一）、补货周期的补货频次。

**【待处理】族（仍 6 条，引用必须注明）**：价格系数、营销费用系数、齐套状态触发规则、子齐套状态触发规则、计划开始日期、计划结束日期。

> 业务文档中的大颗粒规则名（齐套单元最大计划齐套时间计算规则、新品上市前计划通过状态判断规则、物料齐套计算规则、首批采购规则、采购方案成本测算规则、新品参考品推荐规则、预测需求拆分规则、供需优先级规则）与实测规则名不一一对应——回答以实测规则名为准，文档名仅作业务背景理解。注意：价格/营销系数规则虽标【待处理】，但 ReferenceDishBinding 实例已回写系数值（price_coef 1.88 等）——引用值时注明「实例已回写、规则待定稿」。
