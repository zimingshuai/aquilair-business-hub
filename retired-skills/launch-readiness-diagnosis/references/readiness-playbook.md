# 六类齐套诊断剧本（查询模板集 + 方法论）

> 适用问题：上市准备情况、哪些没齐套、为什么没齐套、什么阻塞、该先处理什么、复查结果。
> 模板是**快路径不是唯一路径**：固化的是查询路径与业务口径（随本体版本演进），不快照任何数据实态——
> 一切实时返回为准。任一模板步骤报 42201/42200 → 用 `metadata_object_neighborhood` 核对实名重试一次，
> 仍失败 → 脱离模板，走 SKILL.md 探查循环第 ④ 步自由迭代。
> 通用规则：objects_query 一律用实体 code + 属性 code（DSL 骨架见 facts.md）；标 ∥ 的步骤无依赖、应并行发；
> **select 只放模板/元数据确认过的字段名——不确定就省略 select 取全属性**（模板期实测：剩余报错几乎全部是 select 臆造字段名）；
> 数据值、枚举现查现引；方法论各节（四类判别/依赖追溯/处理顺序）对模板输出同样强制。

## 模板索引

| 用户问法 | 模板 |
| --- | --- |
| 任何点名计划/新品的问题（前置） | T0 锁定计划 |
| 六类齐套怎么样 / 上市准备情况 / 出图 | T1 六类总览 |
| 为什么没过 / 被什么卡住 / 阻塞 | T2 阻塞溯源 |
| 上市时间能否保住 / 硬性限制 / 倒排 | T3 倒排硬限制 |
| 物料齐套情况 / 物料缺口 | T4 物料缺口（细节见 material-purchase.md） |
| 门店清单准备好了吗 / 门店营销 | T5 门店与营销 |

### T0 锁定计划（全部模板前置）

1. `objects_query NewDishLaunchPlan`，where `eq plan_status="执行中"` → 唯一执行中计划即锁定，记下 `plan_id / dish_id / plan_launch_date / planned_ready_date / target_store_count`；多条 → 列候选停（计划唯一性铁律）。
2. 用户点名具体名称且步骤 1 不唯一时：`objects_query Dish`，where `containsAnyTerm dish_name={单词}`（**用「青提」别用「青提冰茶」**，多词不命中）→ `dish_id` → `objects_query NewDishLaunchPlan`，where `eq dish_id={dish_id}`。

DSL 完整示例（其余模板 where 片段同骨架）：
`{"type":"filter","objectSet":{"type":"base","objectType":"NewDishLaunchPlan"},"where":{"type":"eq","property":"plan_status","value":"执行中"}}`

坑：plan_status 枚举经历过中文化（「执行中/已完成」），现查现引不硬编码；模糊检索空结果 ≠ 不存在，换单词或全量 9 条目检兜底。

### T1 六类齐套状态总览

口径：状态一律取回写值不重判；超期 = 数据内 `current_date` − `max_readiness_end_date`（明示模拟时间轴基准）；单元齐套 = 其子项全部齐套；单元回写与行级数值矛盾 → 并列不裁决，列待业务确认。

| # | 调用 | 拿什么 |
| --- | --- | --- |
| 0 | T0 | plan_id、dish_id |
| 1 ∥2 | `objects_query ReadinessUnit`，where `in readiness_unit_code=[Q0001..Q0006]` | 六类状态、`current_date`、`max_readiness_*`、upstream/downstream 依赖字段值 |
| 2 ∥1 | `objects_query SubReadinessUnit`，where `in readiness_unit_code=[同上]` | 子项明细；判定依据直接引 `sub_readiness_desc` 原文 |
| 3 | `objects_links NewDishLaunchPlan {plan_id}` | 风险台账：risk_owner / risk_status / mitigation_plan 直接引用 |
| 4 可选 | `objects_query MaterialDemand`，where `eq dish_id={dish_id}` | 行级毛/齐/净，用于矛盾核验与 Top 物料（转 T4） |

坑：步骤 1/2 **勿按 plan_id 过滤**——该关联字段实测可能全空，恒用 readiness_unit_code in 六类；「能否上市」按权威枚举组织档位（通过/有条件通过/延期），不替业务拍板；交付按 SKILL.md 四段式 + data-delivery 两档。

### T2 阻塞溯源（为什么没过 / 被什么卡住）

前置：T0 + T1 已取数（复用，不重查）。

1. 从 T1 结果定位未齐套单元与其未通过子项（`sub_readiness_desc` 原文 = 判定口径第一来源，直接引用）。
2. 依赖归因：用 T1 已取的 `upstream/downstream_readiness_unit_list` 字段值——上游已齐套 → **自身未完成，非上游阻塞**；仅硬性前置依赖才算阻塞，表述用「问题子项 → 依赖路径（列编码）→ 受影响单元」。
3. 风险台账（T1 已取）引用 owner / 缓解措施 / 状态；台账未覆盖处如实注明无期限数据。
4. 可选：T4 行级核验（单元回写 vs 行级缺口矛盾）。

口径：**用户前提可能错**（说 X 没过而实际已过）→ 纠正前提并解释误认来源，转向真正未过的单元；依赖边自指/缺边/与业务文档矛盾 → 列待业务确认；Q0004 与 Q0006 无依赖边时标可并行，不编造固定串行顺序。

### T3 倒排时间与硬性限制（上市时间能否保住）

| # | 调用 | 拿什么 |
| --- | --- | --- |
| 0 | T0 + T1 | 计划日期、六类 max_readiness_* / current_date |
| 1 | `objects_query PurchaseOrder`（全量或按 wh_code 过滤） | 在途订单：`required_delivery_date` / `delivered_qty`，及派生字段直接读值——`current_overdue_days`（当前逾期）/ `expected_delay_days`（预计延期）/ `estimated_arrival_date`（预计到达） |
| 2 | T1 的 SubReadinessUnit | `plan_readiness_start/end_date` vs `actual_*`（排期 vs 实际） |

口径：倒排时间只引用 `max_readiness_*` 系统回写值（非自行推算）；**逾期/延期天数直接读派生字段并注规则名，不展示层重算**（空值=未回写，注明）；硬性限制表述须带依赖边 + 时间证据；就绪日双口径（计划表 planned_ready_date vs 齐套层 planned_ready_date）如实并列。

坑：日期字段可能是数值序列脏值（如 20261087）——先判格式，脏值引原值注明勿换算；派生字段元数据 `isDerived: true` 可作引用前的核对依据。

### T4 物料缺口（薄卡，链路细节见 material-purchase.md）

1. `objects_query MaterialDemand`，where `eq dish_id={dish_id}` → 全行毛/齐/净（`gross_demand_qty / total_kit_qty / net_demand_qty`）。
2. `objects_query Product`，where `in product_code=[步骤 1 行内 material_code 去重]` → 中文名/规格。

口径：净 = 毛 − 齐（**派生属性可能未回写**，空则按公式展示层计算并注明「派生未回写」）；行明细 >20 行展示最相关前 10 并说明可展开；单元级回写与行级矛盾 → 待业务确认不裁决。

坑：MaterialDemand **无物料名称字段**（只有 material_code，仓库名 wh_name 倒是有）——必须步骤 2 补名，物料字段名是 `material_code` 对 `Product.product_code`，两侧不同名。

### T5 门店与营销准备

1. `objects_query SubReadinessUnit`，where `eq readiness_unit_code=Q0006` → 六子项状态，判定口径引用 `sub_readiness_desc` 原文（门店范围/档案/营业/培训/设备/可售）。
2. 门店清单**双路探测**：`objects_query NewDishLaunchStore`，where `eq dish_id={dish_id}` → 空再试 `eq plan_id={plan_id}` → 仍空再 `objects_query DishInStore`，where `eq dish_id={dish_id}` → 全空 = 数据缺失（四分类口径，非业务未完成），给记录级证据（过滤条件 + totalCount=0）。
3. 有清单时与 `target_store_count`（T0 已取）双源对照条数；可抽验 `Store` 档案状态。

坑：NewDishLaunchStore 的关联键历史上挂过 P 系历史编码（与当前 NP 系不一致）——所以双路探测、两键都试，勿一次空查询就断言无数据；Store 档案存在 `#N/A` 类脏值时如实注明。

## 子项信息表（每条子项至少交代）

| 信息 | 要求 |
| --- | --- |
| 子项身份 | 计划标识、父单元编码、子项编码及名称 |
| 检查规则 | 实际使用的条件、适用对象、阈值和版本；无版本时注明未提供 |
| 检查结果 | 通过 / 不通过 / 待核查 |
| 问题类别 | 数据缺失 / 业务未完成 / 读取异常 / 规则或关联配置缺失 |
| 原因与证据 | 实体、记录主键、字段、观测值、期望值及可用记录链接 |
| 覆盖情况 | 适用记录数、已检查数、未通过数及无法核查的范围 |

## 四类问题判别（不得混淆）

| 类别 | 判别特征 | 结果 | 示例 |
| --- | --- | --- | --- |
| 数据缺失 | 查询成功且覆盖完整，规则要求的记录/字段确实不存在或为空；规则要求必须存在 → 不通过 | 不通过 | 全部适用销售规格中有一个未维护价格 |
| 业务未完成 | 记录存在，但审批、发布、数量、有效期等条件不满足 | 不通过 | 审批中、已停用、供应数量不足 |
| 读取异常 | 接口失败、权限不足、分页未取全等导致无法判断 | 待核查 | 查询超时、部分门店数据未返回 |
| 规则/关联配置缺失 | 不知道检查哪个对象、如何连接或用什么通过标准 | 待核查 | 子项未绑定判断规则 |

要点：读取异常与配置缺失只能报「待核查」，**不得说成条件已满足，也不得说成已确认不满足**；待核查≠业务没做完，不得误导用户去「催业务」。

## 依赖追溯（什么才算「阻塞」）

- 依赖图来自当前单元/子项的**有效上下游关系**（upstream/downstream 字段值 / objects_links / 元数据关系定义），只有明确的**硬性前置依赖**才能认定「阻塞」；相关数据或共同归属 ≠ 先后依赖。
- 区分「自身条件未满足」与「受上游影响」：下游未完成的原因不能仅凭上游未完成推定，必须有依赖边 + 实际检查证据。
- 表述格式：**问题子项 → 依赖路径（列编码）→ 受影响单元/子项**；无依赖定义时只列「待确认影响」。
- 检查依赖数据本身的质量：自关联、循环、悬空编码、上下游不一致——发现异常时报告无法可靠排序的部分，不自行修复关系、不编造六类齐套固定串行顺序（上游约束语义见 domain-model.md）。
- 任一关键子项待核查时，相关单元**不能宣称已确认齐套**；区分「本次报告结论」与「系统已存状态」，不擅自增加状态枚举。

## 处理顺序（先修检查，再修业务）

1. 先指出妨碍可靠检查的读取异常/规则配置问题（否则后面的诊断不可靠）。
2. 业务问题：优先处理**已确认的上游根因**，再处理受其阻塞的下游事项。
3. 可比较事项间结合：明确依赖、截止时间、影响对象范围、系统提供的负责人排序；**优先查上市风险台账（经计划 objects_links 获取）**——每条风险自带 risk_owner、risk_status（已关闭/评估）、mitigation_plan、discovered/resolve_date，处理顺序表直接引用；台账未覆盖的事项，没有工期/负责人/依赖信息时如实注明，不凭空承诺完成日期或指定人员。
4. 可并行的事项明确标注并行，不把独立问题强行排成串行。
5. 每项建议说清：处理什么、证据在哪、会解除哪条阻塞、处理后复查什么。
