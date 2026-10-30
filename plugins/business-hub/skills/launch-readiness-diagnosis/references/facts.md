# 接口行为手册（aquilai-mcp × 新品上市保障）

> 本手册只记**服务端与数据侧行为**：DSL 正确语法、工具行为、服务状态、元数据缺陷、数据侧行为模式。
> **不快照任何数据实态**——数值、条数、状态、规模、回写与否一律以本次 `objects_query` 实时结果为准；
> 实体/属性/关系/规则清单以 `metadata_list_*` 实时返回为唯一权威，本手册不维护副本。
> 铁律修改必须先有实测证据；脏数据/数据问题条目挂工单，服务端修复后即删。

## 接入与认证

- 网关：`https://aquilair.idcs.elitescloud.com/mcp-service/mcp`（多项目，所有工具显式传 workspace_id）。
- **workspace**：新品上市保障 `01a15c77-4e87-7000-880f-1d637582e3b1`——逐字核对 uuid；列表存在同名「（废弃）」「（测试…）」项目，禁止按名称模糊匹配。
- OAuth2：DCR 仅开放公开应用（client_credentials 拒绝，机器应用走人工注册）；token 端点必须 `application/x-www-form-urlencoded`（发 JSON 返回 401 空 body）。
- 宿主挂载：ZCode 经连接器授权后直用；豆包 Work 已挂载（工具前缀 `mcp__aquilai_mcp_servers__`）；`actions_list`、`compare_branch` 未挂载（本技能不依赖）。

## objects_query 的 ObjectSet DSL（正确语法）

- **filter 包裹结构**（裸 base 查询现返回 422，全量语义也必须 filter 包裹）：
  `object_set={"type":"filter","objectSet":{"type":"base","objectType":"<实体 code>"},"where":{...}}`
- where 键名是 **`property`**（属性 code；PROP_ refCode 兼容但用 code 省一步），不是 `field`；组合条件用 `{"type":"and|or|not","children":[...]}`（children 不是 nodes）。
- 算子：eq / neq / lt / lte / gt / gte / in / containsAnyTerm（模糊）/ containsAllTerms；contains 系不能出现在 or/not 组合中。**containsAnyTerm 分词受限（2026-10-30 回归实测）**：多词值（如「青提冰茶」「冰茶」）可能不命中而单词（「青提」「草莓」）命中——模糊检索空结果时先换单词重试并对照全量核对，勿据此断言实体不存在；负向结论以全量目检为准。
- **select 传属性 code 数组**（PROP_ refCode 与臆造名报 42201 未知属性）；字段名严格校验，写错即 42201——报错时用 `metadata_object_neighborhood` 核对实名，不靠猜。
- 分页：`nextPageToken` 续查；`totalCount` 需显式传 include_total_count。
- 大表（如 HistorySalesByDay 十万级）必须过滤+分页；**过滤后抽查返回与条件一致**（历史上出现过静默忽略过滤返回全量的行为版本）。
- 历史防回退：裸 where / `field` 键 / base 节点内嵌 where 的旧写法均报 42200/422——这不是「平台 where 不可用」，是语法错误。曾有四天「where 一律不可用、结果侧筛选」的误判铁律，已废止，勿再引用旧结论。

## 工具行为

- `objects_links`：计划对象（NewDishLaunchPlan）返回完整关系图；ReadinessUnit 等返空（部分关系实例未灌）——**先试 links，空则退回关联冗余字段 query**（readiness_unit_code / dish_id 等）。
- `actions_list`：404（路由未实现）；动作清单以 `metadata_list_actions` 为准。
- `actions_run`：服务已上线；**要求本体项目已发布——修订未发布时返回 409**；跨 workspace 调用 404（动作按 workspace 隔离）。旁路调用必须带 `mcp-session-id` 头（从 initialize 响应头抓取），否则 400。
- branch 族：list / create / delete / compare 实测可用；沙箱写操作（objects_save/edit 带 branch 参数）支持，**actions_run 不支持 branch**。
- `metadata_workspace_model` 全量数百 KB 会被工具结果预算截断——用 `metadata_list_object_types`（轻量）+ `metadata_object_neighborhood(ref_code, depth=0)`（单对象属性级）组合替代。

## 服务端状态与能力边界

- **检查程序可执行性**：ruleaction-service 已上线，只差本体项目发布当前修订（409 → 可执行）；执行前确认卡五要素。
- **首批采购链路无执行承载**：算法清单空（metadata_list_algorithms=[]）、无方案生成/成本测算/下单动作——被要求执行时如实说明无承载，不虚构接口、不用在途采购单冒充新生成结果。

## 元数据缺陷（服务端待修，回答时绕开）

- `InitialPurchaseSolution` 的 description 与 `InitialPurchaseObjective` 复制错位——不采信该 description，以实体名+属性为准。
- `NewDishLaunchPlan`、`ReferenceDishBinding` 的 description 为空。
- 规则清单中标注【待处理】的规则（价格系数/营销费用系数/齐套与子齐套状态触发/计划起止日期等）：引用时必须注明「待处理」；实例可能已有回写值——双标注「规则待定稿、实例已回写」，以 `metadata_list_rules` 实时标记为准。
- 业务文档中的规则名与实测规则名不一一对应——以 metadata_list_rules 为准，文档名仅作业务背景。

## 数据侧行为与脏数据模式（模式级；具体值现查，工单修复后删条目）

- **数值序列日期**：plan_start_date / plan_end_date 存在数值序列病（如 20230387）——引用原值并注明格式异常，不换算成假日期。
- **1970 零值时间戳与空串负责人**：时间与 operator 字段引用前先判空。
- **自指/矛盾依赖边**：齐套依赖存在自指、与业务文档上游约束不符的情况——依赖溯源以实例 `upstream/downstream_readiness_unit_list` 为准，差异列「待业务确认」。
- **口径矛盾**：单元级回写判定与行级明细数值可能不一致（如子项回写已齐套 vs MaterialDemand 行级毛>齐）——如实并列列待业务确认，不裁决哪边正确。
- **枚举中文化且会变**：plan_status 已从 COMPLETED →「已完成」、空串 →「执行中」——枚举值现查现引，不硬编码过滤词。
- **模拟时间轴**：ReadinessUnit 自带 current_date 字段——超期/倒计时以数据内 current_date 为准（不是真实系统日期），计划表无此字段；引用倒计时口径必须明示基准。
- **隐藏实体模式**：历史上存在元数据清单之外的实体（上市风险 entity_f44ddbf6 曾隐藏后转正）——links/query 遇未知实体属正常，以实时元数据为准。

## 已知数据问题工单（修复即删）

- ForecastSalesDemand 周拆分不全（业务口径应 4 条周粒度）——引用时注明数据不完整，待业务方补数。
