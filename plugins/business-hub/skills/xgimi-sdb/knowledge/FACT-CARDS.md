# xgimi-sdb 实测事实卡片（🟢 有效区——铁律唯一来源）

> 第 2 步「实测攒坑」产出。每条卡片 = 真实 MCP 实测的**当前有效结论**（附首次实测日期）；改技能措辞前先来这里找依据，新踩的坑先实测再追加，不许凭印象写铁律。卡片只记**规则与教训**，不记数字实例（2026-11-04 用户规范：技能包不放任何演示数据——案例、预期结果、批次/物料实例都在模型仓库 demo/）。
> 历史演进档案已迁出至模型仓库 `demo/skill-archive/FACT-CARDS-archive.md`（仅供追溯，不约束行为）。平台现状/挂账看 `STATUS.md`。

## FC-04 分支五件套全部可用（2026-10-23 实测）

- `objects_create_branch(name, parent="main")` / `objects_list_branches()` / `objects_query|get(…, branch=…)` / `objects_compare_branch(name)` / `objects_delete_branch(name)`（删除须确认）。
- **branch 缺省即 main**——操作沙箱必须显式传；对比生产与沙箱分别查询。

## FC-05 分支隔离成立；is_active 值域「是/否」（2026-10-23 实测）

- 分支内写 STRAT-* 的 is_active → 分支生效、main 分毫未动（隔离经 FC-18 迁移后复验仍成立）。
- is_active 值域为**中文字符串「是/否」**（非 Y/N）——以实时数据为准。

## FC-06 策略库与目标目录（模型基线）

- 策略库启用 2 行：STRAT-SUB 替代消耗（优先级 1）、STRAT-PURCHASE 采购建议（优先级 2）；处置类策略不在基线——「为什么没有」→ 策略库加行即参与下轮，不改代码。
- 目标目录 8 维（方案对比看板列以此为准，新增维度=加一行）：OBJ-ON-TIME-QTY 按期交付 / OBJ-DELAY-QTY 延迟交付 / OBJ-SHORTAGE-QTY 剩余缺口 / OBJ-DEADSTOCK-QTY 剩余呆滞 / OBJ-PURCHASE-QTY 采购数量 / OBJ-PURCHASE-AMT 采购金额 / OBJ-EXTRA-COST 附带成本 / OBJ-DURATION 预计周期；注意描述中的口径注记（按物料明细行 vs 方案级汇总）。
- 主键 strategy_code；属性含 strategy_direction（降库存/补缺口）、applicable_scenario、priority_level（数字型）。

## FC-08 直连端点不可用，元数据走宿主 MCP 工具（2026-10-23 实测＋用户裁决）

- 脚本直连 MCP 端点 401；凭证由宿主连接器 OAuth 注入、令牌约 2 小时轮换——静态 token/无人值守直连脚本方案已被用户裁决否决。
- **结论**：元数据一律会话内直调 MCP 工具（`metadata_list_object_types` 概览 → `metadata_object_neighborhood` 按需），无缓存层。fire 是例外：其鉴权为静态头 X-User-Account（非轮换密钥），HTTP 直调可行（scripts/fire_action.py）。

## FC-11 动作执行通道 = ruleaction HTTP fire（2026-10-26 打通）

- 端点/鉴权/payload 骨架/响应判读见 platform.md §1（唯一契约源）；执行为同步，写入主键在 `executionResult.items[].dataService`。
- triggerKey 为幂等键每次唯一；`duplicate:true` 回查不重发。

## FC-13 中文编码坑（2026-10-26 实测）

- 手写 curl 内联中文按本地编码发送 → 10000 请求体格式错误。fire_action.py 走 Python urllib＋UTF-8，已结构性规避。
- check_time 等时间参数用**毫秒时间戳**（ISO 串未验证通过）。

## FC-14 published 前置与发布语义（2026-10-26 实测）

- fire 对 draft 项目返回 20301；编辑已发布项目翻回 draft——遇 20301 等 2~5 分钟重试，持续则提醒用户去 studio 发布。
- 发布后瞬时窗口 data-service 可能 40401（缓存冷），稍候重试。

## FC-17 调用格式：instances 数组＋callerParams=函数入参名（2026-10-26 实测）

- `instances: []` 为标准骨架；新建类动作为空数组；更新类动作必须提供目标实例（`[{"entityRefCode": "<OBJ_>", "instanceIds": ["<主键>"]}]`）。
- callerParams 的 key = 函数签名入参名（非实体属性名）；批次号由 ① 响应自动生成（CHK-{product}-{时间戳}），调用方不传。
- 函数真实签名（本地源码 functions/<名>/main.py）：②~⑧ 主参 `check_batch`，⑨ `scheme`。

## FC-18 data-service 实体 code 直调，refCode 形态失效（2026-10-26 实测）

- objects_* 全部读写一律实体 code＋属性 code；`OBJ_`/`PROP_` refCode 报 40401/42201；返回 `records[].objectType`=实体 code、properties 键=属性 code。
- 不受迁移影响：元数据服务仍按 refCode（返回同时带 refCode 与 code——映射从这里拿）、规则引用仍 RULE_ refCode、fire 的 instances 仍用 entityRefCode。

## FC-20 callerParams 只传必填参（2026-10-27 用户规范）

- 只传函数签名中无默认值的参数（速查表见 platform.md §2，唯一来源）；可选参不传，默认值即业务基线；批次号不传（响应自动生成）。
- `use_substitute` 已随 FC-22 退役（替代决策改由 STRAT-SUB 开关表达）。

## FC-21 空参 fire 全面禁用（2026-10-27 复测）

- 占位符清理后任何动作空参 fire 都直通引擎：缺主参 500 崩、参数可空可能真执行。
- 参数清单一律按本地源码签名＋platform.md §2 速查表，不靠探针发现。
- 规则 11→9：RULE_A5A37E06（性价比）/AE62559F（净收益）已删除，不得引用。

## FC-22 沙箱推演机制：决策即数据＋④后分叉（2026-10-28 用户裁决）

- 替代决策不走函数参数——建沙箱时写本分支 STRAT-SUB 的 is_active（与 STRAT-PURCHASE 同机制）；⑤⑦ 签名收窄，推演链内零决策参数；「不替代」世界 ⑤ 按开关不填补；全关世界策略测算空跑、方案按维持现状口径照常产出。
- 分叉点 = ④ 后：公共段生产跑一次，四世界共用底账；每分支建箱即写开关，再跑 ⑤⑥⑦⑧。
- 函数按 strategy_code 精确匹配策略行（显示名变更不反转判定；自定义策略保留关键词回退）；策略库空 raise 报错（与全关合法空跑区分）。
- 技能层去基线化：核对一律用当轮明细做勾稽自洽（chain-playbook §4）；函数层测试基线数字归函数工程测试（`_demo_chain_test.py`，模型仓库），技能运行时不引用。

## FC-24 action_010 策略开关动作：沙箱专用＋生产恒全开（2026-10-28 用户定稿）

- 契约见 platform.md §2（branch 顶层必带＋instances 定位＋callerParams 空）；每轮最多 4 笔，sub-buy 零调用。
- **生产 main 恒为默认全开不变量**——「关」只存在于沙箱假设世界；推演执行前核对 main 双开关均「是」，非全开判停上报；生产若需关策略属生产配置变更，另行裁决。
- 兜底通道：`objects_save(SupplyDemandStrategy, is_active, branch=…)`（fire 不可用时）。

## FC-25 备用 MCP 通道（2026-10-28 实证；2026-11-12 并入 hub 后前提失效，改记新事实）

- 原机制（xgimi 独立插件时代）：借相邻插件的独立凭证连接做断连只读核验——并入 `aquilair-business-hub` 后与 fnb/mfg/launch 共用同一 `aquilair-mcp-servers` 连接，**独立备用通道不复存在**。
- 现行口径：网关断连时如实报告、不降级代答；只读核验随连接恢复后再做。
- fire 走 HTTP 不依赖 MCP 连接；不得用旧数据冒充新查询。

## FC-27 ②影响概览 = 展示层呈现（2026-10-28 用户定稿）

- impact_scope 只读不落库；概览由落库差异行计数＋销售订单查询按需求 4 口径拼装（变化物料→受影响成品→未交付订单→影响等级＋繁杂度），交付注明「展示层口径（需求 4）」。
- 教训：判断「输出缺失」先分清展示层能否给，再考虑通道/落库类架构改动。

## FC-28 ✅ 沙箱读透传修复收口（2026-10-29 用户确认）

- 此前「分支开关写入生效、但函数运行时读固定 main」的读侧问题（历史调查 FC-23/26，见 archive），已由平台引擎把 fire 的 branch 上下文透传到函数数据读取而修复，复测通过——**四世界对比结论可正常交付**。
- 沙箱推演相关判停条款自此只覆盖逻辑矛盾（分岔点错位、开关未分化）；数字与历史不同不构成判停理由（SKILL.md 红线 8）。

## FC-29 文档不预置 BOM 数值（2026-11-02 用户规范＋实测）

- **用户规范（权威）**：技能文档（参数速查表、脚本示例、剧本）**不得预置任何 BOM/成品数值**——执行前实时查 `BOMHeader` 发现同 output_code 的基准/目标两版（基准取生效版、目标取新版本），多对并存时先向用户确认。「找到什么就是什么」。数据基线随平台版本走（曾整体迁移），脚本/文档硬编码数据集专有名会静默空跑。
- **教训**：fire「成功」≠有写入——判完成只看回查到的落库主键（脚本 keys 为空即报警，回查批次表/差异表确认）。

## FC-30 ⚠️ action_010 契约变更：空参 fire 被拒，改走兜底通道（2026-11-03 实测）

- **实测**：action_010 按 FC-24 契约（callerParams 空＋instances 定位＋branch 顶层）fire 返回 `REJECTED`，`missingRequiredParams: ["enable"]`——引擎现已要求必填参数 `enable`，旧「空参」契约失效。**REJECTED 零写入**（回查证实）。
- **处置**：改走 FC-24 兜底通道 `objects_save(SupplyDemandStrategy, is_active="否", branch=…)` 完成三个沙箱开关写入，写后回查分化正确、main 恒全开不变量成立，推演链全部跑通。
- **未解**：`enable` 参数的值域与语义未验证（疑与 is_active「是/否」同域），在平台侧确认前**不得猜测传值重试 fire**；开关操作一律走 objects_save 兜底。挂账见 STATUS.md。
- 牵连修订：platform.md §2 开关行、§6 兼容条款同步改为条件式规则。

## FC-31 ⑥⑦⑧ 口径修订：呆滞账本余量＋缺口统一净额（2026-11-03 函数升级）

- ⑥ 呆滞改**账本余量口径**：未被任何需求行占用的现货 + 未被占用的有效在途（占用从 SupplyDemandAllocation 逐笔扣减）；与缺口**互斥**（同物料呆滞×缺口=0）；BOM 用量调低/删除只作 risk_source 归因标签，不再决定数量。
- ⑥ 缺口改**账本净额**（分配+替代后 remaining_shortage_qty），与 ⑦⑨ 同口径——旧「增量口径 vs 全量口径」双口径陷阱不复存在（caliber §1 已改写）。
- 孤儿库存**已识别**：有库存、无需求、不在 BOM 消耗链的物料按「无需求库存」进呆滞（含替代料孤儿）。

## FC-32 替代有效期三重校验（2026-11-03 函数升级＋实测）

- ⑤ 判有效期改用**需求行 require_date**（非当前日）——推演是对未来需求的假设；新增物料本体温控（status 非「正常」或 expire_time < require_date 拦截）；④ 同步把过期物料库存排除出可用供给池。
- 被拦截项写日志＋remark 留痕，形成证据链；过期物料按残值口径评估，不当可处置资产按账面成本计。
- 配套数据纪律：替代路线的有效性是**案例设计约束**（唯一交付瓶颈必须可替代）——主数据自相矛盾（物料卡失效日与替代关系并存）先修数据，不靠代码绕。

## FC-33 ⑤ 账本只返回新增行，本地串跑必须合并（2026-11-03 踩坑）

- substitute_fill.solve 返回的 SupplyDemandAllocation **只含本轮新增行**；本地离线串跑 `inputs.update(o5)` 会覆盖 ④ 的分配记录 → 占用统计清零 → 有需求物料被误报呆滞。
- 正确写法：`inputs["SupplyDemandAllocation"] = o4_allocs + o5["SupplyDemandAllocation"]`。平台 fire 链路写库为追加，不受影响。

## FC-34 ⑦ 替代记账＋替代对交付的价值维度（2026-11-03 实测＋用户裁决）

- strategy_simulate 对替代**只记账不模拟**：读 ⑤ 账本生成 kind=substitute 行（improve_amount = 替代补主料量 × 主料标准成本）；采购 need 取 remaining_shortage_qty（已扣替代），两口径不重叠。守恒自证：同物料「可化解风险金额 = 替代改善 + 采购改善」逐物料对得上。
- **用户裁决**：替代必须对演示有效果；案例设计约束固化为「唯一交付瓶颈必须是可替代物料，不可替代的长周期料交给在途覆盖」。
- 讲解口径：替代价值按「交付解锁（瓶颈可替代时）/ 呆滞减少 / 采购差额 / 替代记账」分维度呈现，不硬凑台数；双开比只采购少花的钱与替代记账的差额可能是**起订量取整**吃掉的，不是算错——被追问时先查 MOQ。

## FC-35 函数 SDK branch_context 门槛（2026-11-04 收口）

- 平台函数运行时升级后，旧 aquilair.py 注册的函数执行报 `RuntimeError: Function SDK lacks branch_context; re-register its ZIP with the updated aquilair.py`——**9 个函数全挂**，与业务代码无关。
- 9 个函数（含新版 SDK）已重打包为 `functions/upload-packages/*-20261104a.zip`，用户 2026-11-04 重注册后恢复（STATUS 已解除）。**教训**：平台升级运行时后所有函数需重注册；报此错即检查 SDK 版本，不排查业务代码。
