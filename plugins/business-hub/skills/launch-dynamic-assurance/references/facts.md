# 接口行为手册（launch-dynamic-assurance）

> 配置项：workspace_id=01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f（新品上市POC-最新版）；MCP 服务=aquilair-mcp-servers。
> 本手册只记**服务端与数据侧行为**：DSL 正确语法、工具行为、能力边界、元数据缺陷（模式级+建议工单）。
> 不快照任何数据实态——数值、条数、状态、规模以 `objects_query` 实时结果为准；实体/属性/关系/规则清单以
> `metadata_list_*` / `metadata_workspace_model` 实时返回为唯一权威，本手册不维护副本。
> 铁律修改必须先有实测证据；条目挂工单，服务端修复后即删。原始实测记录见 hub 仓 `evals/runs/2026-11-03-launch-poc-probe.md`。

## 工作区接入

- workspace_id **逐字核对**（本项目=新品上市POC-最新版）；网关下存在相近名项目（「新品上市POC—V2.0」
  「新品上市保障（废弃）」等），**禁止按名称模糊匹配**——同名不同物，数据互不相通。
- 本项目可能处于 status=draft（发布后又修改未重发布）；引用工作区状态时以 `list_workspaces` 实时返回为准。

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
- `objects_relation_counts`：**全部参数形态 42200（含 inputSchema 自述形态），待核查**（工单 TK-relcnt）——
  当前以 objects_links 或关联冗余字段（dish_id/wh_code/demand_nr 等）query 替代。
- `metadata_workspace_model`：本项目规模（21 实体/27 关系）完整返回约 560KB 未被截断；实体增多需警惕
  截断风险，截断时退回 metadata_list_object_types（轻量）+ metadata_object_neighborhood(ref_code, depth=0)。
- `metadata_list_actions`：仅返回 refCode+name+description，**不返回 apiName**；workspace_model 中
  15 动作 apiName 全为 null——**actions_run 当前无有效入参来源，不可承诺动作执行**（工单 TK-apiname）。
- `actions_task_status`：task_id 必须 UUID；服务在线（非 UUID 报 400 即为连通证据）。
- `metadata_object_neighborhood`：depth 参数上限 10（服务端约束）。
- `metadata_list_algorithms`：算法定位为外部优化 webhook 摘要；本项目清单为空（content:[] 形态，
  存档脚本按空清单写占位）。
- `actions_run` 超时语义：提交后同步等待约 10 秒，未完成返回 `{task_id, status: RUNNING}`——
  需用 `actions_task_status` 轮询直至 `completed_at` 有值；本项目 apiName 全 null，当前无有效入参。
- `objects_list_branches`：仅 main（branchId=0）；沙箱推演前须先 objects_create_branch（写操作，走确认卡）。

## 服务端状态与能力边界

- **数据层当前空**：main 分支 21 实体实测全为 0 实例（2026-11-03）——回答业务实例问题前先探实例规模，
  空态如实报告「数据未灌入」，禁止用文档演示值（NP009/300000 杯等）冒充查询结果。
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
