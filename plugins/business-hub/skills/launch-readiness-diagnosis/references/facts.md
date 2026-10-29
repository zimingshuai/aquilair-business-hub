# 实测事实卡片（2026-10-23 首轮实测）

> 记录真实调用 MCP（连接器 `aquilai-mcp-servers`，workspace「新品上市保障」）踩到的事实。
> **铁律修改必须先有本页证据**；拍脑袋写的铁律在评估中必然暴露为空条款。

## 数据环境（截至 2026-10-23）

- **本域 workspace**：新品上市保障，id `01a15c77-4e87-7000-880f-1d637582e3b1`，status=draft，37 实体 / 49 关系（2026-10-28 复核；facts.md 首版记录的 36/44 已随业务演进），创建人曾桧。
- **同名陷阱**：列表中另有「新品上市保障（废弃）」`01a139d5-6ce5-7000-acd2-720484f280c1`（43 实体）与「新品上市保障（测试Ontology Forge）」`01a15379-b94e-7000-b9b6-c1e1154bb5e8`（40 实体）——**传 workspace_id 必须逐字核对 uuid，不得按名称模糊匹配**。
- **三库均未建表**：objects_query 返回 `40404: project … 未建表，请先调用 create_workspace`。对照已发布的 demo workspace（餐饮库存 `019fd9ed-…`）返回 `40401 未知对象类型`（已建表、校验走到类型层），证明「未建表」是新品域现状而非平台通病。**当前无任何实例数据可查**；被问数据时如实报告「数据尚未装载」，不编造。

## 工具面（20 个工具，与 fnb/mfg data-service 完全不同）

| 族 | 工具 | 实测 |
| --- | --- | --- |
| workspace | `list_workspaces` | ✅ 返回 17 个项目，按 id 精确锁定 |
| metadata | `metadata_list_object_types` / `_actions` / `_rules` / `_algorithms` / `metadata_workspace_model` / `metadata_object_neighborhood` | ✅ 前四个实测通过（36 实体/3 动作/18 规则/0 算法） |
| objects 读 | `objects_query` / `objects_get` / `objects_links` / `objects_relation_counts` | query DSL 实测见下；其余待建表后验 |
| objects 写 | `objects_save` / `objects_delete` / `objects_edit` | 未执行（底层写接口，业务变更禁用，见铁律） |
| branch | `objects_list_branches` / `create_branch` / `delete_branch` / `compare_branch` | 未执行（沙箱推演用，待数据就绪后验） |
| actions | `actions_list` / `actions_run` | **`actions_list` 404**（action-service 路由未实现，2026-10-23）；动作清单以 `metadata_list_actions` 为准 |

## objects_query 的 ObjectSet DSL

- ✅ 通过的结构（2026-10-26 建表后复测）：`object_set = {"type": "base", "objectType": "<实体 code，如 NewDishLaunchPlan>"}`——**objectType 传实体 code**；传 refCode（OBJ_…）报 `40401 未知对象类型`。
- ⚠️ 行为曾反转：2026-10-23 建表前 refCode 通过类型校验（走到 40404）、code 也通过（同样 40404）；**建表灌数后（10-26）只认 code**。漏传 `type:"base"` 字段会被 422 拒绝（422 的真正原因是缺 type，与 code/refCode 无关——首日曾误归因为 refCode 限定，已纠正）。
- 分页：返回 `nextPageToken`，以 `page_token` 续查；`totalCount` 默认 null（要总数需传 include_total_count）。
- **select 实测（2026-10-28 复核）**：`select` 传属性 **code** 数组生效（如 `["plan_id","plan_name"]`）；传 refCode（PROP_…）报 `42201 未知属性`，传臆造名同样报 42201——SKILL.md 曾写「refCode 数组」为误导，已纠正。

## 动作面（检查程序）

- `ACT_105E8C9A57F249E9` **检查上市齐套**：对指定上市计划执行六类齐套检查，更新结果并汇总状态——即 SKILL.md 所述「检查程序」。
- `ACT_0177575B2C544EA3` 更改子齐套状态；`ACT_6757509DDD284C24` 更改齐套单元的齐套状态——状态回写入口（run 前确认卡）。
- **首批采购链路无执行承载**：算法清单为空（metadata_list_algorithms 返回 []），无「物料齐套计算/首批采购方案生成/成本测算」动作——业务文档 3.4 描述为目标态，当前实态只能读实体数据，被问时如实说明。

## 规则面（18 条，名称以 metadata_list_rules 为准）

- 生效规则族：参考品系数读取/计算（季节系数、销售均价、销售定价、营销预算、营销费用、上市实际均店销量、预测新品首月均店销量）、首月需求预测基准值、齐套时间汇总（计划/实际齐套开始/结束时间=子齐套最早/最晚值）。
- **【待处理】规则 6 条**（价格系数、营销费用系数、齐套状态触发规则、子齐套状态触发规则、计划开始日期、计划结束日期）：本体标记未完成，**引用时必须注明「待处理」，不得当作已生效口径**。
- 业务文档中的规则名（齐套单元最大计划齐套时间计算规则、新品上市前计划通过状态判断规则、物料齐套计算规则、首批采购规则、采购方案成本测算规则、新品参考品推荐规则、预测需求拆分规则等）**与实测规则名不一一对应**——回答以实测规则名为准，文档名仅作业务背景。

## 元数据缺陷（服务端待修，回答时绕开）

- `InitialPurchaseSolution`（首批采购方案）的 description 与 `InitialPurchaseObjective` 完全相同（复制错位）——描述「定义…优化目标…目标函数」实为 Objective 的释义；引用时以实体名+属性为准，不采信其 description。
- `NewDishLaunchPlan`、`ReferenceDishBinding` 的 description 为空。

## 认证与接入（宿主接排障用）

- 服务：`https://aquilair.idcs.elitescloud.com/mcp-service/mcp`（多项目网关，所有工具显式传 workspace_id）。
- OAuth2：protected resource 发现 `/.well-known/oauth-protected-resource/mcp-service/mcp` → authorization server `…/system`；DCR 仅开放公开应用（redirect_uris 必填，client_credentials 拒绝，错误信息原文「机器应用请走人工注册」）；token 端点必须 `application/x-www-form-urlencoded`（发 JSON 返回 401 空 body——踩坑实录）。
- ZCode 宿主内通过连接器（http 类型 + URL）完成 OAuth 授权后，会话直接可用 `mcp__aquilai-mcp-servers__*` 工具，无需手工 token。
- **Doubao Work 宿主适配（2026-10-28 实测核对）**：连接器 `aquilai-mcp-servers` 已在本机挂载（同名同址 `https://aquilair.idcs.elitescloud.com/mcp-service/mcp`），工具前缀为 `mcp__aquilai_mcp_servers__`（连字符转下划线）；已确认可调用：`list_workspaces` / `metadata_list_object_types` / `metadata_list_actions` / `metadata_list_rules` / `metadata_list_algorithms` / `metadata_workspace_model` / `metadata_object_neighborhood` / `objects_query` / `objects_get` / `objects_links` / `objects_relation_counts` / `objects_save` / `objects_edit` / `objects_delete` / `objects_create_branch` / `objects_list_branches` / `objects_delete_branch` / `actions_run`；`actions_list`、`compare_branch` 未挂载（SKILL.md 工具表未依赖，按需再核）。

## 二轮实测（2026-10-26，建表灌数后）

**数据已就位**：业务方已完成建表灌数。NewDishLaunchPlan 共 9 条（NP001~NP009），**NP009 即 POC 主角「青提冰茶」**（dish 926001，2026-11-15 上市，参考品=蓝莓冰茶 923001/NP001，forecast_first_month_sales_qty=646454.121 已算出，plan_status 为空串=上市前状态，actual_* 全 0）。NP001~NP008 为历史参考品计划（COMPLETED）。

**where 条件过滤（实测通过）**：`object_set = {"type":"base","objectType":"<code>","where":{"type":"eq","field":"plan_status","value":"COMPLETED"}}`。

**六类齐套实例（ReadinessUnit 全 6 条，Q0001~Q0006）**：

| 编码 | 名称 | 状态 | 上游（数据实际值） | 计划窗口 |
| --- | --- | --- | --- | --- |
| Q0001 | 商品齐套 | 已齐套 | Q0002（⚠️ 与文档「无上游」不符） | 10-18~10-22 |
| Q0002 | 配方齐套 | 已齐套 | null（⚠️ downstream 自指 Q0002） | 10-23~10-27 |
| Q0003 | 物料齐套 | 已齐套 | Q0001、Q0005、Q0006（⚠️ 文档说还应含配方 Q0002） | 10-28~11-01 |
| Q0004 | 供应齐套 | **未齐套** | Q0003 | 11-02~11-06（actual 全 null，已超窗） |
| Q0005 | 仓配齐套 | 已齐套 | null | 10-23~10-27 |
| Q0006 | 门店与营销齐套 | **未齐套** | Q0001 | 11-04~11-06（actual 全 null，已超窗） |

- `readiness_status` 枚举为**中文**：「已齐套」/「未齐套」（暂未见第三态）。
- **模拟时间轴**：ReadinessUnit 自带 `current_date`（实测值 2026-11-10）——判断「是否超期/距上市几天」**以数据内 current_date 为准，不用真实系统日期**；NewDishLaunchPlan 无 current_date 字段，倒计时基准取数据口径需明示。
- 依赖追溯时以上表「数据实际值」为准，文档上游约束表仅作背景（差异本身就是待业务确认的数据问题，可列「待确认影响」）。

**Product 属性（22 个全量核验）**：
- **无「独用/共用物料」属性**——material-purchase.md 的该口径结案：本体未定义，只能作叙事框架或按 BOM 引用面说明（引用面宽窄是事实陈述不是业务重算），数值一律引用工具返回。
- 效期字段有承载：`shelf_life_days` 总货架寿命、`min_receive_shelf_life` 收货最小剩余货架期、`sled_days` 最佳赏味期——POC 语境「青提鲜果效期 5 天」对应 shelf_life_days 类字段。
- `product_type` 枚举：成品/物料/半成品；另有 abc_type ABC 分类、storage_condition 存储条件。

**脏数据清单（回答时绕开/注明）**：
- `plan_start_date` / `plan_end_date` 为数值序列（如 20230387），非日期字符串——展示须换算说明或引用原值并注明格式异常。
- NP005~NP009 的 create_time/update_time 为 1970-01-01 00:00:00（零值时间戳）、operator 空串——引用时间/负责人字段前先判空。
- Q0002 自指依赖、Q0001 上游与文档矛盾（见上表）。

**where 过滤算子（行为变化史——2026-10-27 下午三测更新）**：
- 10-26（建表后首测）：eq 有效过滤 ✅；like/contains 被静默忽略返回全量。
- 10-27 上午（平台发版后）：**全部算子静默忽略、返回全量**（不报错）；无 session 头时另一表现：返回 0 条（恒空）。
- **10-27 下午（当前状态）：全部算子一律显式 `42200 请求参数校验失败`**（无字段级详情），任何结构/值都过不了——显式报错优于静默，但 where 仍不可用。已提缺陷报告（`xinpin/docs/缺陷报告-where过滤静默失效-2026-10-27.md`）。
- **现行铁律不变：objects_query 的 where 一律视为不可用**。筛选：拉全量（分页）→ 结果侧筛选 → 抽查一致性；或按主键 `objects_get`。平台修复后按报告 §5 回归用例复测（注意 plan_status 枚举已改为中文「已完成」）。
- 数据侧同步变更：plan_status 存量值 COMPLETED→「已完成」（ReadinessUnit 的已齐套/未齐套未变）。

**objects_links 部分可用（10-29 修正——此前"一律返空"结论以偏概全）**：
- ✅ NewDishLaunchPlan NP009 返回完整关系图 4 条链：→Dish（上市新品）、→ReferenceDishBinding（参考品绑定，**系数已回写**：price_coef 1.88 / marketing_amount_coef 1.47 / ref_seasonal_coef 0.867 / forecast_average_sales_qty 2154.85——价格系数规则虽标【待处理】，绑定实例已有值）、→自关联（参考品上市计划，返回 NP009 自身而非 NP001，实现略怪）、→entity_f44ddbf6 上市风险（4 条台账）。
- ❌ ReadinessUnit Q0003 仍返空（SubReadinessUnit↔ReadinessUnit 关系实例未灌）。
- **导航策略：先试 objects_links，返回空再退回关联冗余字段 query**（readiness_unit_code / dish_id / ref_launch_plan_id 等）。

**上市风险台账（entity_f44ddbf6，经 NP009 links 获取，元数据清单未列）**：字段结构=risk_id / risk_category（按期上市风险）/ risk_type（商品·BOM·物料·供应，对应齐套单元）/ readiness_unit_code + sub_readiness_code（精确指向子项）/ risk_level（次要）/ risk_status（已关闭·评估）/ risk_description + impact_description + mitigation_plan / risk_owner / discovered_date + resolve_date。**这是六类齐套诊断的现成问题台账**：处理顺序表可直接引用（负责人/期限/缓解措施有数据承载），LR-NP009-01~03 已关闭、04（供应 SQ0004_02 到货偏晚）评估中。

**SubReadinessUnit 子齐套（全量 28 条）**：
- 编码体系 `SQ{单元4位}_{序号2位}`：商品 5 项（SQ0001_01~05）、配方 9 项（SQ0002_01~09）、物料 5 项（SQ0003_01~05）、供应/仓配/门店营销其余。
- **`sub_readiness_desc` 就是每条子项的判定口径原文**（如「Dish.dish_status 为正常；草稿、停用、空值或未知均不通过」「有效且分配给该需求的采购量 ≥ 待采购缺口」）——回答「为什么没齐套/判定依据」直接引用该字段，这是判定依据的第一来源。
- SQ0004_01「采购缺口数量已落实」未齐套（actual 全 null）→ 供应齐套 Q0004 未齐套的直接原因。
- 子项级 upstream/downstream_subreadiness_list 全为 null（子项依赖数据未灌）。

**action-service 未上线（10-27 带 session 复测确认仍 404）**：`actions_list` 与 `actions_run`（含「检查上市齐套」ACT_105E8C9A57F249E9）均返回 404「资源不存在」——与 10-26 结论一致；注意网关对无 `mcp-session-id` 头的请求返回 400 Missing session ID（旁路调用时必须从 initialize 响应头抓取 session）。当前只能读已回写的状态数据，不能触发重算。

**branch 沙箱（实测可用）**：`objects_list_branches`（main=branchId 0）→ `objects_create_branch`（实测创建 branchId 557）→ `objects_compare_branch`（返回逐实体 added/removed/modified/unchanged）→ `objects_delete_branch`（清理成功）。沙箱写操作（objects_save/edit 带 branch 参数）支持，actions_run 不支持 branch。

**全库数据规模（compare_branch 盘点，2026-10-26）**：HistorySalesByDay 18.24 万条（大表，查询必须过滤+分页）、ProductListing 6504、NewDishLaunchStore 1000、DishInStore 1900、Store 688、SupplyNetwork 520、SubReadinessUnit 28、PurchasePlan 28、MaterialDemand 24、BOM 34、Dish 5、NewDishLaunchPlan 9、ReadinessUnit 6、ForecastSalesDemand **仅 1 条**（文档口径应 4 条周粒度——数据不完整，回答时注明）、PurchaseOrder 8、Warehouse 2、Supplier 12。InventoryBusinessStrategy / SalesOrder 0 条。
- **隐藏实体**：compare_branch 出现元数据清单（36 实体）之外的第 37 个实体 `entity_f44ddbf6`「上市风险」4 条——metadata_list_object_types 未列出，引用时注意元数据缺失。

## 首轮评估记录（2026-10-26，独立子代理应答 + 人工判分）

- **方法**：4 个 general-purpose 子代理（只加载 SKILL.md + references，不带开发会话上下文）真实应答 11 条用例，主代理按 expected 独立判分。
- **结果**：11/11 行为层 PASS。亮点：npi-004 子代理主动纠正用户错误前提（物料齐套实际已通过，转向真正未过的两单元）；npi-005 拒绝替未定义规则下「能否上市」判定；npi-007 陷阱三步口径完整；npi-008/010 拒自算/确认卡不跳；npi-011 开发边界正确且提醒凭证不硬编码。
- **用例修正（D 类·断言口径）**：npi-004 原 expected 假设物料齐套未通过，与数据实态不符——已改为「纠偏前提」考核点。
- **评估环境限制（C 类·环境）**：**子代理上下文中 aquilai-mcp-servers MCP 工具不可用**（4 个子代理中 3 个一致报告仅有 fnb/mfg 服务；主会话正常）——子代理基于 facts.md 快照应答并如实标注「待核查/非实时」。行为纪律评估有效；数据实时性路径（触发查询、分页、过滤）待在 MCP 可用的评估环境复测。真实使用场景（主对话直接装技能应答）不受此影响。
- 副产物：评估在 `deliverables/` 下生成了 2 份子代理看板（齐套/物料齐套，2026-10-26）。

## 交付路由更新（2026-10-28：输出强制可视化）

**变更动因**：用户要求输出必须根据查询所得数据做可视化——简单数据用 echarts 模式生成多个图；复杂数据用 html_svg 交互看板并落档 + echarts 图。原「三级渲染链」仅要求数据类交付配图，未区分复杂度、未强制全部数据输出出图、复杂场景未强制落档，本次补齐。

**宿主渲染能力实测（2026-10-28）**：
- `doubao-visualization` 技能本机已挂载（.skills 目录），echarts 模式输出协议为独立 ```echarts option 块（自包含、不硬编码颜色），html_svg 模式为 ```html type="renderer" 块（静态首屏可读 + 交互）。
- 渲染前必须 Read `doubao-visualization/SKILL.md`；echarts 分支追加读 `references/mode-echarts.md`（电脑端再读 `references/echarts-web-pc-spec.md`），html_svg 分支读 `references/mode-html-svg.md`。

**路由规则（已写入 SKILL.md 输出规范与 references/delivery.md）**：
- **简单数据**（分类 ≤6、单/双指标、一次性对比、无需筛选/下钻）→ **echarts 模式生成多个图**：2~4 个独立 echarts option（状态总览条形/占比、时间轴倒排甘特、缺口/对比条形）。
- **复杂数据**（多指标多维度：跨仓/跨 SKU 缺口矩阵、多订单到货跟踪、采购方案多维度对比；需筛选/下钻/联动）→ **html_svg 交互看板并落档 + echarts 图**：对话内 renderer 交互看板 + 自包含 HTML 落档 `deliverables/`（文件名含场景与数据口径日期，页脚注数据来源与生成日）+ echarts 图承载精确数值。
- 豁免：仅元数据解释/确认卡/无数据明细的纯结论与待核查说明。
- 铁律：只回纯 Markdown 文本表格=违规；图与正文数值一致；数据来源（含 current_date 基准）必须标注。

**联动改动（2026-10-28 增量改，同仓一致）**：
- `evals/cases.yaml`：npi-002 期望对齐新路由；新增 npi-012（简单→echarts 多图）、npi-013（复杂→html_svg 落档+echarts）**草稿用例（mature: false，待人工复核转正）**。
- `_plugin/agents/new-arrival-advisor.md`、`_plugin/README.md`、`_plugin/README-doubao-adaptation.md` 可视化表述同步。

**验收**：工厂 `tools/lint_skills.py` / `tools/pack_skill.py` 未随分发挂载（四处技能根目录均无）——文件级核对替代：SKILL.md 80 行（预算 50~120）、frontmatter name=目录名、5 个 references 链接有效、cases.yaml 可解析（13 条）。正式出包前需在工厂仓库跑 lint+pack。

## 10-29 复测（MCP 恢复，workspace 已发布 v1.0.0 + 修订中）

- **workspace**：published v1.0.0（10-23 发布，冯雅），37 实体/49 关系，10-29 仍修订更新中；平台新增「测试函数执行用」等 workspace（总数 21）。
- **plan_status 枚举中文化**：历史计划 "COMPLETED"→「已完成」；NP009 青提冰茶从空串→「**执行中**」——「plan_status 空串=上市前」的旧口径作废。
- **where 行为第三态**：带 where 节点（type/field/value 与 field/operator/value 两种写法）显式报 42200 参数校验失败（不再静默返回全量）——fail-fast 优于静默，但结论不变：where 不可用，一律结果侧筛选。
- **action-service（ruleaction-service）已上线**：`actions_run` 不再 404——本 workspace 返回 409「本体项目尚未发布」（执行要求发布态，当前修订未发布）；跨 workspace 调用返回 404「未找到动作」（动作按 workspace 隔离，正常）。**检查程序可执行性只差业务方发布当前修订**。
- **新规则出现**：「计算物料需求的物料净需求」（MaterialDemand 净需求为派生属性；10-29 实测实例查询未回写该字段值——引用时注明「派生未回写」，缺口用毛需求−总齐套量展示层口径）。
- **新口径矛盾（待业务确认）**：子项 SQ0003_04「全部必需物料可用数量覆盖需求」回写「已齐套」，但 MaterialDemand 多行明细总齐套量 < 毛需求（如青提酱 0/14285.7）——单元级判定与行级数值不一致。
- **子代理环境 MCP 已恢复**：npi-001/002 实时复测双 PASS（28 次实时工具调用；计划总览含门店范围/目标/执行中状态全要素；物料看板含 6 物料×4 周矩阵、展示层口径注明、SQ0003_04 矛盾未掩盖）——数据实时性路径验证完成，11 条首轮用例全部闭环。

## 10-29 元数据大版本刷新（workspace 修订，published v1.0.0 后修订中）

- **规则 18→37**（新增 19 条生效）：齐套/子齐套←计划读取族 7 条（计划日/就绪日/开始时间/计划编码）；物料需求族 3 条（需求日期/优先级/**净需求=毛−齐套**）；**首批采购成本族 4 条**（优化后缺货量/缺货成本×2/采购计划采购成本=总量×单位成本）；子项检查展开 1 条（更新子齐套-上市计划已明确新品的检查情况）；门店供应仓库编码、补货频次、预测需求交期、参考品编码读取 2 条。待处理仍 6 条。
- **实体 36→37**：上市风险 entity_f44ddbf6 转正入元数据（18 属性，描述给出**上市决策枚举：通过/有条件通过/延期**——SKILL「能否上市」口径据此更新）；属性数多处增长（Store 14、ForecastSalesDemand 13、NewDishLaunchPlan 36、MaterialDemand 21、PurchasePlan 21、ReadinessUnit 20、SubReadinessUnit 23 等）。
- **关系 44→49**：ReadinessUnit→NewDishLaunchPlan（所属新品上市计划，齐套正式挂计划）；NewDishLaunchPlan→上市风险（1:n）；上市风险→ReadinessUnit/SubReadinessUnit（触发单元/子项）；SupplyRouting→SupplyNetwork；SalesOrder→Dish。
- **首批采购链路口径更新**：规则层已建（缺货/成本可读），执行动作与算法仍无——SKILL 铁律已同步为「读得到成本规则、跑不了方案生成」。
- 数据层稳定复核：六类齐套（4 已齐套/2 未齐套超窗）、风险台账 4 条（3 关闭/1 评估 LR-NP009-04 供应到货偏晚）无变化；ruleaction-service 已上线（409=需发布态）。

## 10-29 彻底迭代回归（7 条重点用例，2 子代理实时应答）

- **7/7 PASS**（npi-001/002/003/004/005/007/008）：新口径全部正确落地——上市决策枚举（通过/有条件通过/延期）用于「能否上市」表述；【待处理】系数标注「实例已回写、规则待定稿」；风险台账 LR-NP009-04 接入处理顺序表（负责人刘洋）。护栏 5 条（009~013）不受本次口径影响未重跑（10-26/28 已验）。
- **新发现① 就绪日双口径**：NewDishLaunchPlan.planned_ready_date=2026-11-15 vs ReadinessUnit/SubReadinessUnit.planned_ready_date=2026-11-12——两处并存，回答时如实列出、待业务确认统一。
- **新发现② ForecastSalesDemand 定位**：仅有的 1 条是 FD20261115926001（60,108 杯、预测日期 2026-12-05，即第 4 周）——4 条周拆分仍缺 3 条。
- 回归副产物：deliverables/ 新增《新品上市齐套总览》《物料齐套看板》《首月销量预测》三份 2026-11-10 口径看板（含预测因子链可视化）。

## 10-29 晚间重大更正：where 正确语法确立（四天误判终结）

- **根因**：此前所有 where 测试用裸 where（base 节点内嵌 where）+ 键名 `field`——均为错误结构。参考 hub 仓库 fnb 技能（已上线跑通）的 ObjectSet 语法，**正确写法是 filter 包裹 + `property` 键**：
  - `object_set={"type":"filter","objectSet":{"type":"base","objectType":"<实体code>"},"where":{"type":"eq","property":"<属性code>","value":...}}`
  - 组合：`{"type":"and","children":[<where>,<where>]}`（children 不是 nodes）
- **10-29 实测三项全通**（workspace 新品上市保障）：eq property=dish_id value=926001 → 仅 NP009 ✓；containsAnyTerm property=dish_name value=青提 → 仅 NP009 ✓（**中文模糊可用**）；and children=[Q0006+未齐套] → SQ0006_01~06 六条 ✓。property 直接用属性 code 即可（fnb 文档建议 PROP_ refCode，本 workspace 实测 code 兼容——两者皆可，以 code 更省一步）。
- 历史三轮结论（eq 有效→静默忽略→显式 422）全部作废为「语法错误的下游表现」；「where 一律不可用、结果侧筛选」的铁律**废止**，替换为「filter 包裹语法 + 过滤后抽查」。SKILL.md 已同步。

## 10-29 修订（豆包侧会话同步）：简单档新增 HTML 静态看板落档

- **来源**：用户在豆包会话对技能做的同日优化，核心变更一处——**简单档交付从「只出多图」升级为「多图 + HTML 静态看板落档」**，复杂档不变（交互看板 + 落档 + 数值图）。至此两档交付均须落档。
- **落档要求**：自包含单文件 HTML（内联 CSS/脚本、无外部依赖、静态首屏完整可读）→ `deliverables/`；看板/图表与落档 HTML 同一份数据、同一口径；语义色约定（绿=已齐套 红=不通过 黄=待核查）覆盖静态看板。
- **验收口径**：全仓「简单→（echarts）多图」表述均须含 HTML 静态看板落档（残留 0 处）；母仓与 hub 同步触点：SKILL.md / delivery.md / facts.md / cases.yaml npi-002·npi-012 / agent 人设三处（另修人设 where 旧口径残留）。
- 豆包侧另建议（未执行）：青提冰茶数据样板交付验证新路由；npi-012/013 类草稿用例转正后跑全量回归（本仓 13 条已全 mature 且经实答验证，不受影响）。

## 待实测清单（剩余项）

- [x] ~~objects_get / objects_links / objects_relation_counts~~（links 已测返空；objects_get 与 query 返回结构等价、get 未单独跑；relation_counts 未测——links 既空，计数意义有限）
- [x] ~~actions_run「检查上市齐套」~~（404 未上线，结论已记录；上线后需复测参数与返回）
- [x] ~~中文模糊匹配~~（like/contains 静默忽略，结论已记录）
- [x] ~~branch 沙箱~~（create/compare/delete 已测）
- [x] ~~where 的其他算子~~（10-27 复测：全算子失效返回全量，见上方行为变化史；平台修复后按对照测试集复测）
- [ ] ForecastSalesDemand 仅 1 条 vs 文档 4 条周粒度——待业务方补数或确认口径
- [ ] MCP 可用评估环境下的数据实时性路径复测（子代理环境工具不可用，见评估记录）

