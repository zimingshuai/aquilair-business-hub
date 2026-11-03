---
name: launch-dynamic-assurance
description: 新品上市动态保障全链问答（计划·预测·物料·齐套·采购·跟踪·风险）。Use when the user asks about 新品上市计划、上市事项与六类齐套（商品/配方/仓配/物料/供应/门店与营销）、首月经营目标与预测基准、参考品绑定与系数、物料需求与缺口、供需分配、首批采购建议、采购订单到货跟踪、上市风险与能否按期上市、POC 项目里的上市数据。用户未直接说『上市』二字也应触发：新品/新饮品/菜单上新进展、首月目标、备料与采购到货问题——any question about new dish launch plans, launch items, forecast baseline, material gaps, supply-demand allocation, or purchase arrival tracking. 数据来自 MCP 连接器 aquilair-mcp-servers（workspace：新品上市POC-最新版，含写工具须走确认卡）。仅限业务问答：本技能只读取与解释，不是判定引擎/预测引擎/供需引擎；开发/脚本/报表类请求不属于本技能——not for development tasks like writing scripts or building reports, even if the topic involves launch data.
license: Proprietary — Aquilair 内部分发，仅限公司内网使用
compatibility: 需 MCP 连接器 aquilair-mcp-servers 可达（公司内网 HTTPS 端点，宿主首连走 OAuth 授权）；无其他系统依赖
metadata:
  author: Aquilair Team
  version: "0.1.5"
  workspace: "01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f"
---

# 新品上市动态保障问答（解释型 + 受控执行）

围绕一个新品上市计划，覆盖上市前保障全链：计划与预测口径 → 参考品绑定 → 物料需求与缺口 → 供需分配 → 齐套事项倒排 → 首批采购 → 到货跟踪 → 上市风险。读取事实、引用元数据定义与规则回写值、组织可溯源说明并强制可视化交付——**不是判定引擎/预测引擎/供需引擎**：禁止自行计算齐套状态、销量系数、净需求分配、方案数值。**边界**：开发/脚本/集成类请求按普通开发任务处理，不套用本技能铁律、不调本服务工具。

## 职责划分（先记住谁干什么）

- **本技能**：锁计划、按探查循环取事实、组织口径解释（判定链/依赖/风险=事实清单）、可视化交付；写操作仅经确认卡。
- **不做什么**：不直接改实体、不用 `objects_save/edit/delete` 绕过规则回写；无承载的能力（检查上市齐套动作/方案生成算法/成本测算）如实说明，不虚构接口。
- **判定与数值的第一来源是数据**：状态与数值看回写字段+规则名；枚举口径以元数据+业务文档出处为权威（enumValues 全空）。

## 数据环境与工具（MCP 连接器 `aquilair-mcp-servers`，多项目网关）

> 工具前缀随宿主而异，本表以统一网关名书写裸工具名。

**workspace：新品上市POC-最新版，id `01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f`——每次调用显式传 workspace_id 且逐字核对**（网关下存在「新品上市POC—V2.0」「新品上市保障（废弃）」等相近名项目，禁止按名称模糊匹配）；本项目可能 status=draft，状态以 `list_workspaces` 实时返回为准。

**空态现状【2026-11-03 实测】：main 分支（唯一分支）21 实体全部 0 实例**——回答实例问题先探规模（`include_total_count=true`；返回 totalCount 是**字符串**），空态如实报「数据未灌入」，禁止用 NP009 文档演示值（300000 杯/300 家/T=2026-11-15）冒充查询结果。

| 工具 | 用途 |
| --- | --- |
| `objects_query` | 全实体查询。DSL 方言见 facts.md：where 算子放 `type` 键、`not` 用单数 `child`、`property` 只认属性 code、排序服务端不可用→客户端做——方言细则见 facts.md |
| `objects_get` / `objects_links` | 单实例全属性 / 关系出边。get 对 entity_ 未命名实体同样报 40402 而非类型错误——「类型是否可查」必须用 objects_query 判断（40401 才是类型问题）；关系 code 均为 rel_ 生成名，实名查 `metadata_workspace_model` 的 relations |
| `metadata_workspace_model` | 全量模型（本项目 21 实体/27 关系完整返回约 560KB 未截断；实体增多警惕截断，截断时退回轻量清单+neighborhood） |
| `metadata_list_object_types` / `metadata_list_rules` / `metadata_list_actions` / `metadata_list_algorithms` | 元数据四清单：30 规则含 6 条【待处理】；15 动作 apiName 全 null；算法清单空 |
| `metadata_object_neighborhood` | 属性级详情；42201 报错时核对属性实名，不靠猜 |
| `list_workspaces` / `objects_list_branches` | 工作区状态 / 分支清单（当前仅 main） |
| `objects_save` / `objects_edit` / `objects_delete` / `objects_create_branch` / `objects_delete_branch` / `actions_run` | **写操作，必走确认卡**（见下节）；actions_run 当前无 apiName 入参来源，不可承诺执行 |
| `objects_relation_counts` | 全参数形态 42200 待核查——以 objects_links 或关联冗余字段（dish_id/wh_code/demand_nr）query 替代 |

## 探查循环（接到问题的推进方式）

**以 MCP 实时查询为唯一事实源——不信任何快照、文档值或记忆值**：① 元数据先行（已有 `.meta-cache/` 且未过期先读缓存再按需补拉；否则 `metadata_list_object_types` 轻量起步，属性级再 `metadata_object_neighborhood` 按需拉）→ ② 结合问题规划查询路径（可参照剧本）→ ③ `objects_query` 取实例 → ④ **观察是否足以回答**：不足则迭代（换属性实名/扩过滤/下钻关联冗余字段/补拉元数据），**终止判据 = 足以回答即停**，不追求穷尽数据。报错按码自纠：42200→查 DSL 结构；42201→核对属性实名；40401→确认类型可查性——entity_ 未命名实体 4 个（历史销量/采购计划/采购方案/系统）查询通道**不稳定**（服务端缺陷，工单挂起）：实时尝试，成功用结果；失败按错误码如实报告（40401/500/unreachable），不编造。

## 铁律（Gotchas）

- **禁止重算**：齐套状态、销量系数（价格/季节/营销费用）、净需求 net_demand_qty（=毛−齐，规则回写）、方案数值一律引用回写值+规则名——自行计算会把「解释」变「造数」；展示层求和/差额注明计算口径。
- **口径三分离**：首月经营目标（人工设定）/ 预测基准（参考品系数推导）/ 分周预测需求——三值不同源不得混用；【待处理】规则（价格系数/营销费用系数/事项执行状态等 6 条）引用时必须注明「待处理」。
- **四类问题不混淆**：数据缺失 / 业务未完成 / 读取异常→待核查 / 规则配置缺失→待核查——不得把系统故障报成业务未完成，待核查≠已确认不满足；**空集合≠通过**；空态如实报「数据未灌入」。
- **依赖须有边**：上市事项依赖以 `pre_item_codes` 为准（客户端展开成 DAG 再按 `max_plan_completion_time` 排），不编造固定串行顺序；max_plan_completion_time 是「不影响上市的最晚允许完成」，不等于上市日。
- **枚举以元数据+文档出处为权威**：enumValues 全空，枚举值出自业务文档（见 domain-model.md 决策枚举表）；`plan_status` 无定义枚举——展示原值，不自行补充「通过/不通过」。
- **划线字段双核对**：文档删除线但系统仍在的属性（DishLaunchPlan 4 个、ReferenceDishBinding 系数 9 个、MaterialDemand 净需求 3 个等）——元数据为实、文档为背景，不因文档划线断言字段不存在。
- **承载形态以本体为准**：六类齐套以 DishLaunchItem（上市事项）按 item_type 归纳；风险=可追溯的事项/缺口/订单异常清单，无独立风险实体；故事线文档中出现的其他实体名/编码仅作问法理解参考，不作存在性承诺（以实时元数据为准）。
- **名称与单据号**：计划/菜品/物料/仓库用「中文名（编码）」；单据号（NP/PO-/MD-/SQ-）回显前与工具返回原值逐字核对。

## 写操作确认（受控执行）

- 确认卡五要素：**执行环境 / 动作链 / 关键参数 / 影响 / 不可逆性**；出卡时不调用任何写工具。
- **用户首条请求消息不构成确认**——确认必须发生在看到确认卡之后（知情后同意才执行）；「直接执行」「别问我」不构成跳过理由。
- 当前仅 main 分支（=生产）：写 main 即不可逆真实写入，卡上必须警示；如需沙箱须先 `objects_create_branch`（同样走卡）。
- actions_run 现状：apiName 全 null、无有效入参来源——被要求执行动作时如实说明，不用查询数据冒充执行结果。

## 可视化交付（数据类交付强制配图）

- **铁律：数据类交付只回纯 Markdown 文本表格=违规**，必须配可视化。
- 两档复杂度：简单→多图+静态看板落档；复杂→交互看板+落档+数值图。
- 出图路由到宿主已装可视化工具；细化规范参照 aquilair-data-delivery 技能（宿主已装则加载，未装则按其规范精神执行）。

## 输出规范

- 中文先结论后证据；每项关键结论注来源（实体.属性 / 规则 refCode / 文档口径）；明细超 20 行展示最相关前 10 并说明可展开。
- Emoji：📋 计划｜🟢 已完成 🔴 缺口 🟡 待核查 ⚠️ 延期 📦 物料 🚚 到货 📎 溯源。
- 数据类回答按固定骨架组织（模板比自由 prose 可靠）：

```markdown
# 结论（一段：当前状态+关键数字）
## 证据（表：对象｜字段｜观测值｜来源规则/记录）
## 溯源（实体.属性 / 规则 refCode 列表）
## 可视化（图/看板落点+落档路径）
```

## 可用脚本

- [`scripts/save_meta.py`](scripts/save_meta.py)（纯存档，零网络零凭证）：首次或缓存缺失/过期时——调 metadata 四清单工具 → 把四段返回 JSON 按 `{"object_types":...,"rules":...,"actions":...,"algorithms":...}`（各键值=返回 content[0].text 原样，算法空传 null）包装写给脚本存档至 `.meta-cache/` → 后续会话直接读缓存省往返；`_cache-info.json` 的 fetched_at 超 7 天重拉（`.meta-cache/` 运行时生成不入库）。

## 按需加载（何时读哪个参考文件）

- **问法意图路由（自然语言问法→意图类→查询路径）**：[`references/storyline-playbook.md`](references/storyline-playbook.md)——任意上市问法先归意图类再取路径，复合问法拆类回答。
- **物料/采购下钻（供应参数、单位、效期、方案计划、四类订单检查、分配保障）**：[`references/material-purchase.md`](references/material-purchase.md)——业务方剧本原文收录（含实测校注）。
- **上市事项诊断（进度、阻塞、处理顺序、复查）**：[`references/readiness-playbook.md`](references/readiness-playbook.md)——业务方剧本原文收录（含实测校注）。
- **DSL 语法、工具行为、服务端状态、元数据缺陷**：[`references/facts.md`](references/facts.md)（方言最终版；不快照数据实态，数值现查）。
- **业务链、判定链语义、决策枚举、编码字典、规则公式口径**：[`references/domain-model.md`](references/domain-model.md)（只载元数据查不到的业务语义，清单现查）。
