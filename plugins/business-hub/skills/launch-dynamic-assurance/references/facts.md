# 接口行为手册（launch-dynamic-assurance）

> 配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f（新品上市POC-最新版）；MCP 服务=aquilair-mcp-servers。
> 本手册只记**服务端与数据侧行为**：DSL 正确语法、工具行为、能力边界、元数据缺陷（模式级+建议工单）。
> 不快照任何数据实态——数值、条数、状态、规模以 `objects_query` 实时结果为准；实体/属性/关系/规则清单以
> `metadata_list_*` / `metadata_workspace_model` 实时返回为唯一权威，本手册不维护副本。
> 铁律修改必须先有实测证据；条目挂工单，服务端修复后即删。原始实测记录见 hub 仓 `evals/runs/2026-11-03-launch-poc-probe.md`。

## 工作区接入

- workspace_id **逐字核对**（本项目=新品上市POC-最新版）；网关下存在相近名项目（「新品上市POC—V2.0」
  「新品上市保障（废弃）」等），**禁止按名称模糊匹配**——同名不同物，数据互不相通。
- 本项目状态以 `list_workspaces` 实时返回为准（2026-11-09 观测=published v1.100.0）；发布后又修改未重发布会回退 draft（届时 actions_run 409，判据见下文）。

## objects_query 的 ObjectSet DSL（本项目方言，2026-11-03 实测定稿）

- **裸 base 可查全量**：`object_set={"type":"base","objectType":"<实体 code>"}`——本项目接受。
- **filter 必须带 where**（无 where 的 filter 报 42200）：
  `object_set={"type":"filter","objectSet":{"type":"base","objectType":"<实体 code>"},"where":{...}}`
- **where 算子放 `type` 键**（不是 operator 键，传 operator 报 42200）：
  `{"type":"eq|neq|lt|lte|gt|gte|in|containsAnyTerm","property":"<属性 code>","value":<标量或数组>}`
- 组合条件：`{"type":"and|or","children":[...]}`；**`{"type":"not","child":{...}}` 用单数 child**
  （传 children 报 42201「not 条件缺少 child」——本项目特有）。
- `property` **只认属性 code**：传 PROP_ refCode 报 42201 未知属性。
- `select` 传属性 code 数组；臆造字段名报 42201——报错时用 `metadata_object_neighborhood` 核对实名，不靠猜。
- 分页只认 `page_token`（`page` 参数被 pydantic 拒绝）；`totalCount` 需显式 `include_total_count=true`，
  返回值是**字符串**（如 "0"），比较时先转型。
- **排序当前不可用**：order_by 四种合理形态（对象值式/单对象 property-direction/fields-orders/数组式）全部
  42200 或被 pydantic 拒——排序在客户端做（工单 TK-排序）。
- 大表必须过滤+分页；过滤后抽查返回与条件一致。
- `objectType` 可传实体 code；正式实体传 OBJ_ refCode 亦被接受。**entity_ 前缀的未命名实体两种 ID 都报
  40401 未知对象类型**——见「元数据缺陷」节，历史销量/采购计划/采购方案查询无承载。

## 工具行为

- `objects_get`：object_type 传实体 code + 主键值；实例不存在报 40402「对象在本体模型不存在」。
  **注意**：对 entity_ 未命名实体同样报 40402 而非类型错误——判断「类型是否可查」必须用
  objects_query（报 40401 才是类型问题）。
- `objects_links`：实例不存在报 40402；link_codes 省略展开全部出边。关系 code 均为 rel_ 生成名——
  拿关系实名用 `metadata_workspace_model` 的 relations（name/refCode/两端属性）。
- `objects_relation_counts`：**2026-11-03 傍晚已打通**（服务端更新后参数校验放行）。正确语法（三必填参数）：
  `{"workspace_id":..., "source_object_type":"<code>", "source_object_set":{<ObjectSet>},
    "relations":[{"relationCode":"rel_<生成名>"}]}`——工具描述所写 relationRefCode/REF_ 形态不认（42200）；
  relations 须传对象数组（字符串数组被拒）；关系须与源对象类型匹配（不匹配 42201）；relatedCount 是**字符串**。
  工具描述待服务端同步（工单 TK-relcnt 保留至描述修正）。2026-11-09 复验通过
  （rel_5d6bf6d5→"13"、rel_3712b263→"1"，与实例一致）。
- **枚举字段数据侧写值风格**（2026-11-09 实测，证据=hub 仓 evals/runs/2026-11-09-launch-subgraph-0.1.14.md）：
  SupplyDemandAllocation.supply_type 实际写值为小写连写 apiCode——purchaseorder（↔业务口径 PURCHASE_IN_TRANSIT）
  / batchinventory（↔INVENTORY）；allocation_status 实测另见 ALLOCATED（业务文档三值 PLANNED/CONFIRMED/CANCELLED
  之外）。**过滤查询传实测值，语义解释沿用业务口径**；按文档大写值 filter 会查空。枚举权威仍以元数据+业务文档
  出处为准，实测差异如实报告（domain-model「三、决策枚举」已同步映射）。
- `metadata_workspace_model`：全量模型完整返回（2026-11-03 观测约 560KB 未截断；实体/关系/规则数当日持续
  变化——规模以实时返回为准，不快照）；载荷大需警惕截断，截断时退回 metadata_list_object_types（轻量）+
  metadata_object_neighborhood(ref_code, depth=0)。
- `metadata_list_actions`：返回 refCode+name+description，**不含 apiName**；apiName（ACT_ 前缀）须从
  `metadata_workspace_model.actions[].apiName` 取——**2026-11-03 晚已全部填充（15/15）**，动作定义完整
  （含 steps/function/OSS 包路径）。取 apiName 走 workspace_model，勿从 list_actions 找。
- `actions_task_status`：task_id 必须 UUID；服务在线（非 UUID 报 400 即为连通证据）。
- `metadata_object_neighborhood`：depth 参数上限 10（服务端约束）。
- **`System` 实体 = 演示检查日（重要）**：objectType 传 `System`（code 已正式化，勿用 entity_ 名），
  主键 `launch_plan_id`，字段 `system_date` / `system_time`——POC 演示的「当前检查日」以它为准
  （2026-11-03 实测 system_date=2026-10-28，即演示时间轴与真实时间不同）。所有「超期/剩余天数」
  必须基于检查日计算并注明来源：用户指定日 > System.system_date > 真实查询时间。
- **物料需求单位口径（易错）**：`MaterialDemand.material_demand_qty` 的单位是物料
  `Material.base_uom`（如「筐」），**不是** `bom_uom`（如「g」）；换算须乘 `bom_uom_factor`
  （如 5000 g/筐）。展示时必须标对单位，禁止把「筐」标成「g」或反之——实测出现过 10200 筐
  被标为 10200 g（错 5000 倍）。
- `metadata_list_algorithms`：算法定位为外部优化 webhook 摘要；本项目清单为空（content:[] 形态，
  存档脚本按空清单写占位）。
- `actions_run` 执行语义：实际为**异步**（2026-11-03 实测：直接返回 `{taskId, executionMode: "ASYNC",
  status}`——工具描述所写「同步等 10 秒」与实际不符）；任务快时结果一并带回，慢时用 taskId 经
  `actions_task_status` 轮询至 `completed_at`；支持 `branch`（沙箱分支）与 `trigger_key`（幂等键，
  重试同一 key 返回原任务 duplicate=true 不重复执行）。
- **动作执行三类失败形态（2026-11-03 晚双向实测，务必按错误码分流）**：
  | 现象 | 判据 | 处置 |
  | --- | --- | --- |
  | `409` business code `20301`「本体项目尚未发布」 | `list_workspaces` 的 status=draft（发布后又有修订即回退） | 请平台方重新发布；**与 apiName/branch/参数无关**（实测假动作名也报同一错） |
  | `400` business code `10000`「更新或删除动作必须提供目标实例」 | data 类动作未传 `instances` | 传 `instances:[{"entity_ref_code":"OBJ_...","instance_ids":[...]}]`（**注意此处的 entity 用 refCode**，与 objects_* 工具的 code 不同）；通道可达 |
  | 任务 `FAILED` + `response:"404 page not found"` | 函数包未部署（algoScheduler 找不到该函数路由，`executionTimeMs` 个位数即返回） | 函数包**逐个部署中**（2026-11-03 晚实测分化：生成物料需求已 SUCCEEDED 但其余多数仍 404）；如实报该函数不可用，**不要重试刷屏、不要把 FAILED 说成成功**；SUCCEEDED 也要核对实际效果（见下） |
| 任务 `SUCCEEDED` 但数据未变 | 函数执行了但动作 `parameters:[]`（无参数定义）→ 空参空跑 | **SUCCEEDED ≠ 生效**——执行后必须在同分支复查实例数/字段，无变化则如实报「执行成功但无效果（动作未定义输入参数）」 |
| 任务 `FAILED` + `response:{"type":"TypeError","error":"missing a required argument: 'xxx'"}` | **函数已真执行**（executionTimeMs 百毫秒级）但入参没送到 | **首查 `caller_params` 的键名**（见下方铁律，最常见原因就是键名带 `$`）；若动作 `parameters:[]` 且 inputMappings 是常量占位，则属动作配置缺陷（工单 TK-inputmapping），如实报「函数已执行但入参未配置」 |
- **动作执行路径建议**：先在**沙箱分支**试跑，核对无误再考虑 main；写完用 `objects_delete_branch`（参数是 **name 不是 branch_id**）清理。
- **`caller_params` 键名铁律（实测踩坑）**：传参时键名**不带 `$` 前缀**——动作定义里写 `$dish_id`，
  caller_params 要写 `{"dish_id": "926001"}`。带 `$` 会报 TypeError missing required argument（函数收到空参）。
  三种形态实测：无前缀 SUCCEEDED / 带 `$` FAILED / 嵌 `params` 层 FAILED。
- **`SUCCEEDED` 但零效果的第二类原因（假成功）**：函数体空实现或查询条件不匹配。实测「冻结BOM版本」：
  参数正确、SUCCEEDED、28~74ms 快速返回空 `response:[]`，但把沙箱 BOM 从「草稿态」跑动作后**仍是草稿态**
  → 动作不生效。**判定方法**：改动前后同一分支对比目标字段（本次用 objects_edit 造前置态再跑动作）；
  无变化即报「动作执行成功但未产生预期变更」，不得声称冻结成功。
- **data 类动作已实测全链路可用（2026-11-03 晚）**：`创建新品上市计划`（ACT_2DFA547172154786）带
  `caller_params`（29 个 `$` 前缀必填参数，从 workspace_model.actions[].parameters 取清单）沙箱执行
  SUCCEEDED 且真实落库（NP010 创建成功，字段全对）。data 类动作通用姿势：参数查动作定义 →
  caller_params 按 `$name` 传值 → 更新/删除类还须传 `instances`（entity 用 refCode）。
- **branch 参数口径**：`actions_run` 的 branch 接受分支 id 或 name（实测均通）；`objects_query/get`
  的 branch **只认 name**（传 id 报 40403 分支不存在）——统一用 name 最稳。
- **动作执行 409「本体项目尚未发布」根因判据**：`list_workspaces` 的 `status=draft` 且有
  `publishedAt < updatedAt`（发布后又有修订）→ ruleaction-service 一律拒绝执行，**与 apiName、
  branch、参数无关**（实测：假动作名、真实动作+假分支均返回同一 409 20301）。处置：先由平台方
  重新发布；**不要重试刷屏**，也不要用「执行成功」措辞掩盖。
- `objects_list_branches`：仅 main（branchId=0）；沙箱推演前须先 objects_create_branch（写操作，走确认卡）。

## 服务端状态与能力边界

- **数据状态以实时为准**：2026-11-03 傍晚观测到 NP009 演示数据灌入 main（上市计划/菜品/门店/物料需求/
  采购订单等已有实例，数值随时变化不快照）——回答前先探实例规模；仅大范围 0 实例才报「数据未灌入」，
  禁止用文档演示值（NP009/300000 杯等）冒充查询结果。
- **无「检查上市齐套」类动作**：15 动作/8 函数中不存在检查上市齐套/重排齐套时间/采购成本测算承载；
  六类齐套进展以 DishLaunchItem（上市事项）数据 + 已注册规则（metadata_list_rules 实时清单）说明。
- **算法清单空**（metadata_list_algorithms=[]）：首批采购方案生成/成本测算无算法承载，被要求执行时
  如实说明，不虚构接口。
- 规则清单中【待处理】规则（价格系数/营销费用系数/计划起止日期/当前交货逾期天数/上市事项执行状态）：
  引用时必须注明「待处理」；以 metadata_list_rules 实时标记为准。

## 元数据缺陷（服务端待修；工单后删）

| 缺陷 | 现象与复现 | 处置 | 工单 |
| --- | --- | --- | --- |
| 4 实体无正式 code | HistorySalesByDay/采购计划/采购方案/「系统」为 entity_ 生成名——元数据层存在（enabled=true，属性 15/16/5/3），实例查询通道**不稳定**：2026-11-03 复验 40401/500/data-service unreachable 交错，期间采购计划 code 曾查通返回空态（服务端修复进行中） | 每次实时尝试：成功用返回结果；失败按错误码如实报告（40401=类型未注册/500=服务端错误/unreachable=服务不可达），不编造不重试刷屏；开工单补正式 code 并稳定通道（参考品历史销量链路受影响最大） | TK-code |
| MaterialSupplier 主键口径 | 文档主键 strategy_code，系统主键 material_supplier_code（另有 material_in_wh_code，无 strategy_code） | 一律以实时元数据 isKey 为准，get 用 material_supplier_code | TK-主键 |
| 供应按时判定字段缺失 | SupplyDemandAllocation 无 expected_supply_qty_ontime / expected_gap_qty（文档有公式） | 到货可行性判定改由 supply_available_date vs demand 日期现算展示口径，并注明字段缺失 | TK-sda字段 |
| 库存指标字段缺失 | MaterialInWarehouse 缺 available_inventory_qty/dii/idd/inventory_holding_cost/remain_forecast_sales_qty | 相关指标不承诺，字段清单以实时元数据为准 | TK-miw字段 |
| 划线属性未同步清除 | DishLaunchPlan（plan_start_date 等 4 个）、ReferenceDishBinding（系数 9 个）、ForecastSalesDemand（3 个）、MaterialDemand（net_demand_qty 等 3 个）、SupplyDemandAllocation（material_demand_date）——文档删除线但系统仍在 | 引用前双核对（元数据为实、文档为背景）；不因文档划线断言字段不存在 | TK-划线 |
| 关系缺口 | Dish.history_sales_by_day、DishLaunchPlan.ref_launch_plan 自关联、MaterialInWarehouse→purchase_orders/purchase_plan/forecast_sales_demand 3 条缺失 | 参考品历史销量经 Dish→HistorySalesByDay 无关系可走（且该实体查询通道不稳定）；参考计划链经 ReferenceDishBinding.ref_launch_plan_id 属性中转；在途采购经 SupplyDemandAllocation.supply_nr 中转 | TK-关系 |
| MCP 工具 description 为空 | objects_query 等 description 空串，DSL 用法无内嵌文档 | 技能侧自备方言表（本手册）；平台侧补文档属增强项 | 低优先 |
