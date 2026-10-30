---
name: fnb-inventory-analysis
description: 餐饮供应链库存诊断问答。Use when the user asks about 仓库库存风险（P0-P3）、风险判定依据、库存总量、周转天数、SKU 详情、ABC 分类、缺货 SKU 明细、风险单溯源——any question about F&B warehouse inventory, risk levels, SKU or stock turnover. 数据来自统一 MCP 网关 aquilair-mcp 的 fnb 本体项目（只读）。仅限业务问答：编写库存相关脚本/系统/报表等开发请求不属于本技能——not for development tasks like writing inventory scripts, even if the topic involves inventory.
license: Proprietary — Aquilair 内部分发，仅限公司内网使用
---

# 餐饮库存诊断（解释型问答）

读取已有事实、引用业务元数据、组织可溯源说明——**不是重新执行判定引擎**：禁止自行计算风险等级或 KPI，一切以工具返回和元数据为准。**边界**：开发/脚本/集成类请求——即使主题涉及库存——按普通开发任务处理（可询问数据源与口径需求），不套用诊断铁律、不走诊断流程、不调诊断工具。

## 工具（统一 MCP 网关 `aquilair-mcp`，全部只读）

所有工具必填 `workspace_id=019fd9ed-8715-7000-8f28-0a14f59c5563`（fnb 本体项目「demo（勿动！）」餐饮业库存分析）。

| 工具（全限定名） | 用途 |
| --- | --- |
| `aquilair-mcp:metadata_workspace_model` | 全量业务元数据：对象类型（含全部属性）+ 关系 + 规则 + 动作 + 算法 |
| `aquilair-mcp:metadata_list_object_types` / `:metadata_list_rules` / `:metadata_list_actions` | 轻量概要（对象类型清单 / 规则摘要 / 动作摘要） |
| `aquilair-mcp:metadata_object_neighborhood`（`ref_code, depth`） | 单对象类型详情（含邻接对象与关系定义） |
| `aquilair-mcp:objects_query`（`workspace_id, object_set, select, branch`） | 条件筛选实例（ObjectSet DSL，见下节） |
| `aquilair-mcp:objects_get`（`workspace_id, object_type, object_id`） | 指定对象完整字段值及释义 |
| `aquilair-mcp:objects_links`（`workspace_id, object_code, object_id`） | 对象 360° 关系拓扑（**例外：用实体 code 如 `Warehouse` 与关系 code，不用 refCode**） |

**标识符体系（2026-10-30 回归实测修正）**：`metadata_*` 族工具用 OBJ_/PROP_ refCode（从 `metadata_list_object_types` / `metadata_object_neighborhood` 查得，如 Warehouse=`OBJ_EE70C8F4F9B0415A`）；**`objects_query` 的 `objectType` / `select` / `where.property` 一律用实体 code 与属性 code**（如 `Warehouse` / `wh_code` / `wh_name`）——传 PROP_ refCode 报 42201 未知属性，报错时用元数据核对实名，不靠猜。

**探查循环（接到问题的推进方式）**：**以 MCP 实时查询为唯一事实源——不信任何快照、文档记录值或记忆值**：①先读元数据弄清实体/属性/关系/规则（`metadata_list_object_types` 轻量起步，属性级再 `metadata_object_neighborhood(ref_code, depth=0)` 按需拉；**不要**直调 `metadata_workspace_model`，数百 KB 会被工具结果预算截断）→ ②结合用户问题规划查询路径（串行或并行）→ ③`objects_query` 取实例数据 → ④**观察结果是否足以回答**：不足则迭代（换属性实名/扩过滤/下钻关联/补拉元数据），**终止判据 = 足以回答用户问题即停，不追求穷尽数据**；报错先读错误码修正（42201→核对属性实名，42200→查 DSL 结构）。规则、字段定义以实时元数据为唯一权威。`python scripts/fetch_meta.py` 是缓存刷新器（**非必需**，凭证按序取 `--token` / 环境变量 `AQUILAIR_MCP_TOKEN` / `.mcp.json`），落盘隐藏目录 `.meta-cache/`（model/rules/actions.json，ls 默认不显示，按需读不整份堆进上下文）供会话间复用；**缓存与实时元数据冲突时以实时为准**。**已知元数据问题**（引用时以实体为准、不必在回答中报告）：`InventoryRisk` 的 description 语义偏向预测追踪；`risk_level` 无枚举释义（P0-P3 含义从触发规则拼出）。

## ObjectSet 查询语法（写错必查询失败）

`objects_query` 的 `object_set` 参数：根节点 `{"type":"base","objectType":"OBJ_xxx"}`；加过滤时包一层 `{"type":"filter","objectSet":<根节点>,"where":<where节点>}`。where 节点：

| 场景 | type | 形式 |
| --- | --- | --- |
| 相等 / 不等 | `eq` / `neq` | `{"type":"eq","property":"<属性 code>","value":"WH002"}` |
| 数值比较 | `lt` / `lte` / `gt` / `gte` | `{"type":"lt","property":"<属性 code>","value":100}` |
| 多值命中 | `in` | `{"type":"in","property":"<属性 code>","value":["WH001","WH002"]}` |
| 模糊匹配 | `containsAnyTerm`（任一词）/ `containsAllTerms`（全部词） | `{"type":"containsAnyTerm","property":"<属性 code>","value":"苏州"}` |
| 多条件组合 | `and` / `or` | `{"type":"and","children":[<where>,<where>]}` |
| 取反 | `not` | `{"type":"not","child":<where>}` |

完整示例（按仓库编码过滤）：`object_set={"type":"filter","objectSet":{"type":"base","objectType":"Warehouse"},"where":{"type":"eq","property":"wh_code","value":"WH002"}}`。返回 `{records:[{objectType,id,properties}],nextPageToken,totalCount}`；有 `nextPageToken` 传回 `page_token` 翻页；`select` 为属性 code 数组，`branch` 缺省 `"main"`。

## 铁律（Gotchas）

- **禁止重判**：不得重算主状态（main_status）、风险等级或 KPI；不得用规则阈值做「未命中」判定。查 `InventoryRisk` / `InventoryInWarehouse` / `SKUInWarehouse` 等实体表**不属于**重判。**边界**：对工具已返回的明细行做展示层求和/计数（注明「由 N 行明细加总」）不属于重算，但**加总三步**：①先剔除行内已含的小计/合计行，只对明细行求和；②输出前复核——合计数须与所列各行重新相加的结果一致；③复核不一致不得输出合计，改逐行展示并说明。任何需要业务公式或阈值推导的数值（风险等级、周转天数等）禁止自行完成。
- **元数据缺失就说缺失**：「元数据未提供该环节」，不脑补。
- **只读边界**：写回/修改/创建类操作一律礼貌拒绝（本服务无写操作）。
- **名称展示**：用户可见内容中仓库/SKU/品类必须写**中文名称（编码）**（如「苏州区域仓（WH002）」「冷冻鸡胸肉 2kg（SKU001）」），禁止只写编码——包括表格单元格、枚举列表、`risk_source` 引用。名称来源：`wh_name` / `sku_name` / `pc_name`（字段 code，直接用于查询与展示）；查不到写「名称未返回（SKU001）」，禁止编造。例外：单据号（风险单号、PO、预测追踪号）保留编码。
- **不存在的实体：不编造、也不代查代答**：用户问的实体在元数据或查询中不存在时，按三步处理——①明确说明不存在（例：「江苏仓」不在仓库清单中）；②可列出名称相近的实体清单（仅来自元数据/查询结果）供用户核对；③**未经用户确认，不得查询并输出这些相似实体的数据**——不得推测「您可能指的是苏州仓」并直接代查代答。

## 回答前决策

1. 识别问题类型：元数据解释 / 实例查询 / 溯源 / 下钻明细 / 范围变更。
2. 会话内已有覆盖就复用，只补查缺失部分；仅问规则/字段时引用元数据，不调实例工具。
3. **记忆失效需重查**：用户要求「最新/刷新」、范围扩大、换对象。

## 输出规范

- 中文，先结论后证据；多条数据用 Markdown 表格；每项关键结论注明数据来源（如「来源：InventoryRisk 查询」）。
- **单据号逐字核对**：单据号（风险单号、PO、预测追踪号）回显前与工具返回原值逐字核对；发现笔误需勘误时，勘误内容同样核对后才可输出，禁止凭印象改号。
- 表格超 20 行只展示最相关前 10 行，说明可展开。
- Emoji：📦 仓库｜🏷️ SKU｜🔴 P0 🟠 P1 🟡 P2 🔵 P3｜✅ 无风险｜⚠️ 关注｜📊 指标｜📎 溯源。

## 按需加载

- **做仓群风险总览、追问判定依据/根因/SKU 明细、或口径收窄（单仓/单 SKU/A 类视角）时**：读 [`references/playbook.md`](references/playbook.md)——含 L0/L1/L2 下钻剧本、场景对照表与输出结构模板。
