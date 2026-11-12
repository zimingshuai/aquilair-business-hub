<title>极米POC-需求描述及本体模型</title>

# 需求

## 整体需求概述

本轮极米 POC 的核心需求，是围绕"BOM 变化触发全链路供需平衡测算"这一条链路展开的，整体分为四个阶段：

四阶段逻辑说明：

1. **变化感知**（需求1–4）：比对两版 BOM，识别物料新增/删除、属性变更、替代关系变化，输出点检清单。以点检结果为输入反向查 BOM，列出被影响到的成品和已下单的销售订单，并按承诺强度分级——影响已下单订单为高，只影响未来生产计划为中，仅 BOM 结构变化为低。
2. **现状计算**（需求5–7）：以销售订单为输入，多层展开 BOM 计算毛需求；把该物料的供给池（质检合格批次 + 在途）按供需分配逐笔分给各条需求行，按本行实际分到的量扣减后，主料不够的先用常规替代料按优先级补缺口，算出每个物料最终还需要采购的净缺口。
3. **问题识别与分级**（需求8）：把库存多出来的（呆滞）和库存不够的（缺口）两边一起盘出来——呆滞侧含 BOM删除、用量调低、在途冗余、替代料多余供给，缺口侧含 BOM新增、用量调高——按金额分级，形成基线风险清单，作为后续方案对比的基线。
4. **策略测算与方案选优**（需求9–10）：从策略库中选取启用的策略，逐个测算每个策略的改善效果——补缺口类解决库存不够的问题，降库存类解决库存太多的问题，都要算出能改善多少、剩余风险还有多少、会不会带来新的问题和附带成本；最后把策略组合成不同方案，多维度并列对比（总改善、剩余风险、附带成本、执行周期、涉及供应商数），由决策人结合排产、客户关系和供应商谈判选定。系统只提供事实和辅助标记，不自动加权打分、不替业务拍板。策略是可扩展的，不限于具体几种。

下方逐项拆解需求清单：

## 需求1：BOM物料新增/删除点检

业务背景：当项目BOM从旧版本升级到新版本时，首先需要识别哪些物料被新增进来、哪些物料被移除出去，这是后续所有需求计算和呆滞评估的基础。本需求负责完成两版BOM之间物料清单的差集比对。

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">输入</th><th vertical-align="top">业务流程及规则</th><th vertical-align="top">输出</th></tr></thead><tbody><tr><td vertical-align="top"><b>【BOMHeader 表】</b><br/>· BOM_code（BOM编码）<br/>· output_code（产出品编码）<br/>· bom_version（版本号）<br/>· effective_date / expire_date（生效/失效日期）</td><td rowspan="4" vertical-align="top"><b>业务流程：</b><br/>① 用户选定某产品的基准BOM版本和目标BOM版本，触发点检<br/>② 系统按 output_code 定位同一产出物料的两版BOM表头<br/>③ 分别拉取两版BOM的全部明细行，按material_code做集合差运算<br/>④ 输出新增物料清单和删除物料清单，写入BOMCheckList（点检清单）<br/><b>规则明细：</b><br/>1. 比对范围锁定：两版BOM必须属于同一 output_code，bom_type均为正式计划版（不拿研发版和正式版比）；基准版为当前生效版本（effective_date ≤ 当前日期 ≤ expire_date），目标版为待上线的新版本（可尚未生效）<br/>2. 物料新增识别：目标BOMItem中存在、基准BOMItem中不存在的material_code → diff_type=新增<br/>3. 物料删除识别：基准BOMItem中存在、目标BOMItem中不存在的material_code → diff_type=删除<br/>4. 多层递归：按bom_level逐层展开比对，每一层物料的增删独立记录，不跨层合并<br/>5. 层级归属：记录每条新增/删除物料在对应BOM中的bom_level层级</td><td rowspan="4" vertical-align="top"><b>【BOMCheckList（点检清单）】</b><br/>新增和删除类差异记录：<br/>· compare_item_id：主键<br/>· base_bom_code / target_bom_code<br/>· material_code<br/>· diff_type：新增 / 删除<br/>· base_bom_level / target_bom_level：对应层级<br/>· base_base_qty / target_base_qty：对应用量<br/>· compare_time：比对时间</td></tr><tr><td vertical-align="top"><b>【BOMItem 表】</b><br/>· bom_code（BOM编码）<br/>· material_code（子件物料编码）<br/>· 物料名称不落库，展示时按 material_code 取主数据<br/>· bom_level（BOM层级）<br/>· base_qty（基准用量）<br/>· loss_rate（损耗率）<br/>· unit（单位）</td></tr><tr><td vertical-align="top"><b>【Material 表（成品）】</b><br/>· material_code（物料编码，material_type=成品）<br/>· 产品名称不落库，展示时按 material_code 取主数据</td></tr><tr><td vertical-align="top"><b>外部触发参数</b><br/>· base_bom_code（基准BOM）<br/>· target_bom_code（目标BOM）</td></tr></tbody></table>

## 需求2：BOM物料属性变更点检

业务背景：两版BOM中都存在的物料，可能在用量、损耗率、层级等属性上发生了变化。本需求负责识别这些属性级别的变更，量化变更幅度，为后续需求增量计算提供依据。

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">输入</th><th vertical-align="top">业务流程及规则</th><th vertical-align="top">输出</th></tr></thead><tbody><tr><td vertical-align="top"><b>【BOMItem 表】</b><br/>· bom_code（BOM编码）<br/>· material_code（物料编码）<br/>· bom_level（BOM层级）<br/>· base_qty（基准用量）<br/>· loss_rate（损耗率）<br/>· unit（单位）</td><td rowspan="3" vertical-align="top"><b>业务流程：</b><br/>① 取两版BOM的交集物料（material_code同时存在于基准版和目标版）<br/>② 逐字段比对每个物料的属性值<br/>③ 对存在差异的物料，生成属性变更记录，描述具体变更内容和前后值<br/>④ 按变更类型分类（用量调高/调低、损耗率变化、层级变化等）<br/><b>规则明细：</b><br/>1. 比对字段：bom_level（层级）、base_qty（基准用量）、loss_rate（损耗率）、unit（单位）<br/>2. 变更判定：任一字段前后值不一致 → diff_type=属性变更<br/>3. diff_content生成：自动拼接变更描述，如"用量：1.0→1.5；损耗率：5%→3%"<br/>4. 变更方向标注：base_qty变化时区分"用量调高"（target &gt; base）和"用量调低"（target &lt; base），为呆滞评估提供方向<br/>5. 多层独立：同一物料在不同层级出现时，按(bom_level, material_code)分别记录变更</td><td rowspan="3" vertical-align="top"><b>【BOMCheckList（点检清单）】</b><br/>属性变更类差异记录：<br/>· compare_item_id：主键<br/>· material_code<br/>· diff_type：属性变更<br/>· base_bom_level / base_base_qty / base_loss_rate / base_unit<br/>· target_bom_level / target_base_qty / target_loss_rate / target_unit<br/>· diff_content：具体变更描述<br/>· change_direction：调高/调低/其他</td></tr><tr><td vertical-align="top"><b>【BOMHeader 表】</b><br/>· BOM_code（BOM编码）<br/>· output_code（产出品编码）</td></tr><tr><td vertical-align="top"><b>外部触发参数</b><br/>· base_bom_code（基准BOM）<br/>· target_bom_code（目标BOM）</td></tr></tbody></table>

## 需求3：BOM替代关系变更点检

**业务背景**：BOM中的替代料规则直接影响物料缺口的填补方式。替代料的新增、删除、优先级调整都会改变物料供给策略。本需求负责识别两版BOM之间替代关系的所有变化。

| 输入 | 业务流程及规则 | 输出 |
|-|-|-|
| **【BOMAlter 表】**  <br/>· bom_code（BOM编码）  <br/>· material_code（主料编码）  <br/>· alt_material_code（替代料编码）  <br/>· replace_ratio（替代换算比例）  <br/>· priority（替代优先级）  <br/>  <br/>**【BOMHeader 表】**  <br/>· BOM_code（BOM编码）  <br/>· output_code（产出品编码）  <br/>  <br/>**外部触发参数**  <br/>· base_bom_code（基准BOM）  <br/>· target_bom_code（目标BOM） | **业务流程：**  <br/>① 分别拉取两版BOM的替代关系清单  <br/>② 按(material_code, alt_material_code)做集合差和比对  <br/>③ 识别替代关系的新增、删除、以及属性变化（优先级、换算比例）  <br/>④ 输出替代关系变更记录，写入BOMCheckList（点检清单）  <br/>  <br/>**规则明细：**  <br/>1. 替代新增识别：目标版有、基准版没有的(material_code, alt_material_code)对 → diff_type=替代新增  <br/>2. 替代删除识别：基准版有、目标版没有的 → diff_type=替代删除  <br/>3. 替代属性变更：两版都存在的替代对，priority或replace_ratio变化 → diff_type=替代属性变更  <br/>4. 变更方向标注：优先级调高/调低、换算比例增大/减小 | **【BOMCheckList（点检清单）】**  <br/>替代关系变更类记录：  <br/>· compare_item_id：主键  <br/>· material_code / alt_material_code  <br/>· diff_type：替代新增 / 替代删除 / 替代属性变更  <br/>· base_priority / target_priority：前后优先级  <br/>· base_replace_ratio / target_replace_ratio：前后换算比例  <br/>· diff_content：具体变更描述 |

## 需求4：受影响成品联动评估（防杂）

**业务背景**：BOM点检发现了变化后，需要知道这些变化会影响哪些成品、哪些销售订单，评估影响范围有多大；同时识别BOM变更是否导致物料种类变繁杂（防杂），为后续计算和呆滞评估提供基础。

| 输入 | 业务流程及规则 | 输出 |
|-|-|-|
| **【BOMCheckList（点检清单）】**  <br/>· material_code（物料编码）    <br/>· diff_type（差异类型）    <br/>· base_bom_code / target_bom_code    <br/>  <br/>**【BOMItem + BOMHeader】**  <br/>· 完整BOM结构    <br/>  <br/>**【SalesOrder（销售订单）】**  <br/>· product_code / undelivery_qty    <br/>  <br/>**【InventoryRisk（库存风险）】**  <br/>· material_code（仅用于展示，不参与本次分级） | **业务流程：**  <br/>① 物料→成品反查：从点检清单取出所有变化物料，反向查询BOM，找出用到该物料的所有成品    <br/>② 成品→销售订单关联：对受影响成品，关联未交付销售订单，判断是否影响已下单订单    <br/>③ 影响等级判定：按承诺强度分级——是否影响已下单订单、是否影响未来生产计划。此处不读风险金额，风险金额要到需求8 才产生    <br/>④ 繁杂度判定：统计BOM变更后物料种类数的净变化，识别"金额不变但物料变多"的情况    <br/>⑤ 输出受影响范围明细和汇总看板    <br/>  <br/>**规则明细：**  <br/>1. 反向展开路径：BOMItem.material_code → BOMItem.bom_code → BOMHeader.output_code → Material.material_code    <br/>2. 影响等级判定（按承诺强度判定，不按金额——风险金额要到需求8 才产生，此处引用会造成循环依赖）：    <br/>   · 高影响：影响已确认未交付的销售订单    <br/>   · 中影响：不影响已下单订单，但影响未来生产计划    <br/>   · 低影响：仅 BOM 结构变化，不影响任何订单与计划    <br/>3. 繁杂度判定（防杂）：    <br/>   · 统计本次点检的净新增物料种类数 = 新增物料种类数 - 删除物料种类数    <br/>   · 净新增 > 0 即标记为“繁杂度上升”，不看金额——金额对冲为零恰恰是最容易漏判的情况（一换一）    <br/>   · 繁杂度上升提示：物料种类增多将增加采购、备料、盘点复杂度    <br/>4. 双向视图：    <br/>   · 物料→成品视图：一个物料影响了哪些成品    <br/>   · 成品→物料视图：一个成品受哪些物料变化影响 | **【受影响范围明细（界面展示，不落地为实体表）】**  <br/>  <br/>① 物料→成品视图：    <br/>   · material_code    <br/>   · affected_products：受影响成品列表    <br/>   · product_count：受影响成品数量    <br/>   · affected_order_count：受影响未交付订单数    <br/>   · total_risk_amount：合计风险金额（呆滞+缺口）    <br/>   · impact_level：影响等级（高/中/低）    <br/>   · complexity_flag：繁杂度上升标记（Y/N）    <br/>  <br/>② 成品→物料视图：    <br/>   · product_code    <br/>   · affected_materials：受影响物料列表    <br/>   · material_count：受影响物料数量    <br/>   · total_risk_amount：合计风险金额    <br/>   · impact_level：影响等级 |

## 需求5：多层BOM展开与毛需求计算

业务背景：BOM是多层级结构（成品→半成品→原材料），要算某成品需要多少物料，必须从顶层成品开始逐层向下展开，每层用量相乘累加。本需求负责完成BOM递归展开和各物料毛需求计算，需求台数来源于销售订单的未交付量。

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">输入</th><th vertical-align="top">业务流程及规则</th><th vertical-align="top">输出</th></tr></thead><tbody><tr><td vertical-align="top"><b>【SalesOrder（销售订单）】</b><br/>· order_nr（订单编号）<br/>· product_code（成品编码）<br/>· undelivery_qty（未交付量）<br/>· status（订单状态，仅取已确认）<br/><b>【BOMHeader + BOMItem】</b><br/>· 完整BOM结构<br/>· bom_code / material_code / upper_material_code / bom_level（由 upper_material_code 逐级串联，层级由它推导）<br/>· base_qty / loss_rate / unit<br/><b>【BOMCheckList（点检清单）】</b><br/>· material_code / diff_type<br/>· base_base_qty / target_base_qty<br/><b>外部输入参数</b><br/>· target_bom_code（目标BOM编码）<br/>· product_code（待计算的成品）</td><td rowspan="3" vertical-align="top"><b>业务流程：</b><br/>① 取该成品的所有已确认未交付销售订单，汇总得到成品总需求量（根需求量）<br/>② 从顶层成品（bom_level=1）开始，按成品需求量计算第一层物料毛需求<br/>③ 若第一层物料本身是半成品（下挂子BOM），继续向下展开到第二层<br/>④ 逐层递归，直到全部展开到原材料层（无下级BOM）<br/>⑤ 汇总各层各物料的毛需求量，写入物料需求清单<br/><b>规则明细：</b><br/>1. 根需求量定义：第1层物料的"上层父件需求量" = 该成品所有已确认未交付销售订单的undelivery_qty合计值；根需求来源为销售订单，不手工录入<br/>2. 毛需求计算公式（通用）：某物料毛需求 = 上层父件毛需求量 × base_qty × (1 + loss_rate)；第1层的父件需求量即根需求量（销售订单未交付量合计）<br/>3. 新增物料（diff_type=新增）：按target_base_qty全额参与毛需求计算，纳入BOM展开链<br/>4. 用量调整物料：增量毛需求 = 根需求量 × 各层父件 base_qty 之积 × (target_base_qty − base_base_qty) × (1 + loss_rate)；注意：层数越深，父件用量乘积越大，不能只乘根需求量。“上层父件需求量”是已含台数的绝对量，不可相乘，此处乘的是各层父件“用量”<br/>5. 删除物料（diff_type=删除）：目标版毛需求=0，转入呆滞风险评估；基准版历史用量用于呆滞量推算<br/>6. 多层累加：同一物料在不同层级出现时，毛需求逐层累加，不合并<br/>7. 损耗率传递：每层损耗率独立计算，不向上传递</td><td rowspan="3" vertical-align="top"><b>【MaterialRequirement（物料需求清单）】</b><br/>每个物料每层一行毛需求记录：<br/>· req_id：需求行ID<br/>· material_code<br/>· bom_level：所在层级<br/>· parent_material_code：父件物料编码（第1层取产出物料编码）<br/>· root_demand_qty：根需求量（成品台数，来自销售订单）<br/>· gross_demand_qty：毛需求量<br/>· base_qty / loss_rate：BOM用量参数<br/>· diff_type：关联点检差异类型<br/>· bom_code / bom_version：计算依据的BOM<br/>· sales_order_nr：关联销售订单</td></tr><tr><td vertical-align="top"><b>【BOMHeader 表】</b><br/>· bom_code / output_code<br/>· bom_version / output_type / base_output_qty</td></tr><tr><td vertical-align="top"><b>【Material 表（成品）】</b><br/>· material_code（成品即 material_type=成品 的物料）</td></tr></tbody></table>

## 需求6：可用供给汇总（库存+在途）

业务背景：算出物料毛需求后，需要先盘清楚现有库存和在途采购订单能覆盖多少，剩余部分才是真正需要采购的缺口。本需求负责汇总两类可用供给：现有库存和在途订单。

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">输入</th><th vertical-align="top">业务流程及规则</th><th vertical-align="top">输出</th></tr></thead><tbody><tr><td vertical-align="top"><b>【BatchInventory 表】</b><br/>· material_code（物料编码）<br/>· wh_code（仓库）<br/>· available_qty（可用库存量）<br/>· qc_status（质检状态）<br/>· unit_cost（单位成本）</td><td rowspan="4" vertical-align="top"><b>业务流程：</b><br/>① 按物料归集需求行——同一物料常有多行（跨层、跨订单、跨 BOM 位置），这些行是竞争者，不是各自独立的需求<br/>② 收集该物料的全部供给源：质检合格批次（按入库日期升序）+ 未取消未关闭的在途（按预计到货日期升序）<br/>③ 供需分配：需求按需求日期升序、同日期按层级升序（父件先分），逐笔取「供给源剩余可分配量」与「需求行剩余未满足量」的较小值，一笔一条记录写入 SupplyDemandAllocation<br/>④ 按需求行汇总分配结果，回填该行的可用库存量、在途采购量与总可用供给<br/><b>规则明细：</b><br/>1. 库存只能用一次：同一物料的多行需求必须各自从分配账本取数，不得各自拿「该物料总库存」去减——否则同一批库存被用 N 次，缺口被系统性低估（镜片 2 行、库存 5000 的算例少算 61.2%）<br/>2. 可用库存口径：仅统计 qc_status=质检合格的批次；available_qty 已是扣除已分配/已锁定后的净可用量<br/>3. 在途供给口径：仅统计 cancel_flag=false 且 close_flag=false 且 status=已确认/已下达的订单<br/>4. 分配优先：需求按需求日期升序；供给先现货批次、后在途；批次内按入库日期升序（FEFO 先到期先出）<br/>5. 单笔上限：分配量 ≤ MIN(供给源剩余可分配量, 需求行剩余未满足量)，且必须大于 0<br/>6. 累计不超卖：同一供给源的全部分配量之和 ≤ 其可供总量<br/>7. 仓库维度：本轮 POC 默认全仓汇总，不拆仓库；后续可按需求仓库过滤<br/>8. 在途到货日：本轮 POC 不按预计到货日筛选，全部计入分配池；后续可按需求日期窗口过滤<br/>9. 单位一致性：库存和在途量单位需统一（均为采购单位），不一致时需换算</td><td rowspan="4" vertical-align="top"><b>【SupplyDemandAllocation（供需分配）】</b> 每笔一行：<br/>· supply_type / supply_ref_id：供给源（批次号或采购单号）<br/>· demand_line_id：分给了哪条需求行<br/>· allocated_qty：分配量<br/>· supply_remaining_qty / demand_remaining_qty：分配后两侧余量<br/><b>【MaterialRequirement（物料需求清单）】</b> 按需求行回填：<br/>· available_stock_qty：本行分到的现货量<br/>· in_transit_qty：本行分到的在途量<br/>· total_available_qty：两者之和<br/>· unit_cost：单位成本（用于金额计算）</td></tr><tr><td vertical-align="top"><b>【PurchaseOrder 表】</b><br/>· material_code（物料编码）<br/>· undelivery_qty（未交货量）<br/>· estimated_arrival_date（预计到货日）<br/>· cancel_flag / close_flag（取消/关闭标记）<br/>· status（订单状态）</td></tr><tr><td vertical-align="top"><b>【MaterialRequirement（物料需求清单）】</b><br/>· material_code（物料编码）<br/>· gross_demand_qty（毛需求量）</td></tr><tr><td vertical-align="top"><b>外部输入参数</b><br/>· wh_code（目标仓库，可选）<br/>· demand_date（需求日期，可选）</td></tr></tbody></table>

## 需求7：净缺口测算（含常规替代料分配）

**业务背景**：毛需求减去可用供给后得到净缺口。但有些物料有替代料，可以用替代料的库存来填补主料缺口，从而减少主料的采购量。本需求负责完成净缺口计算，并按优先级消耗替代料来填补缺口。

<callout emoji="💡">
**概念区分：两种"替代"场景**
本需求是**常规生产补缺口场景**的替代：主料库存不够，用替代料的库存来补生产缺口，目的是让生产不缺料。
需求9中的"替代消耗策略"是**呆滞处置场景**的替代：手里有呆滞料，想办法用到其他BOM的缺口上，目的是消耗呆滞库存。
两者方向相反、输入输出不同，不可混淆。
</callout>

| 输入 | 业务流程及规则 | 输出 |
|-|-|-|
| **【MaterialRequirement（物料需求清单）】**  <br/>· material_code（主料编码）  <br/>· gross_demand_qty（毛需求量）  <br/>· total_available_qty（总可用供给）  <br/>  <br/>**【BOMAlter（替代关系）】**  <br/>· alt_material_code（替代料编码）  <br/>· replace_ratio（替代换算比例）  <br/>· priority（替代优先级）  <br/>  <br/>**【BatchInventory（批次库存）】**  <br/>· 替代料可用库存量 | **业务流程：**  <br/>① 主料净缺口 = 毛需求 - 本行已分到的供给（来自供需分配账本，不是该物料总库存）  <br/>② 如净缺口 > 0，查 BOMAlter 表按优先级找替代料  <br/>③ 按替代优先级升序，依次用替代料的可用供给填补主料缺口——替代料库存同样只能扣一次，因此也走供需分配（需求行仍指向本条主料需求行）  <br/>④ 记录替代消耗的两个口径数量，以及替代比例快照  <br/>⑤ 计算填补后剩余的净缺口，以及替代料多余供给  <br/>**规则明细：**  <br/>1. 主料净缺口 = MAX(0, gross_demand_qty - total_available_qty)，其中 total_available_qty 是本行从分配账本分到的量之和  <br/>2. 替代料消耗顺序：按 priority 升序，优先级数字越小越先消耗  <br/>3. 替代比例换算：1 单位主料 = replace_ratio 单位替代料；消耗替代料实物量 = 主料缺口量 × replace_ratio  <br/>4. 替代料不能超额消耗：替代料实物消耗量 ≤ 该替代料「未被其他需求行占用」的可分配量；不足时按可用量消耗，剩余缺口保留  <br/>5. 替代比例快照：计算时记录当前 replace_ratio 值，后续即使 BOM 替代关系调整，本次测算结果不变  <br/>6. 替代料多余供给：替代料可用总量 - 已分配（含替代消耗）= 多余供给，纳入呆滞风险评估 | **【MaterialRequirement（物料需求清单）】**  <br/>更新每个主料物料的：  <br/>· net_shortage_qty：主料净缺口量（扣库存前）  <br/>· alt_consume_qty_alt_unit：替代料实物消耗量（替代料自己的单位，用于下采购单）  <br/>· alt_consume_qty_main_unit：替代消耗折算主料量（折回主料单位，用于扣减主料缺口）  <br/>· applied_replace_ratio：本次测算使用的替代比例快照  <br/>· remaining_shortage_qty：最终剩余净缺口（主料单位，需采购量）  <br/>· alt_surplus_qty：替代料多余供给（替代料单位，可用于后续呆滞处置） |

## 需求8：供需不平衡问题识别与分级

**业务背景**：算完毛需求、可用供给、净缺口之后，就可以准确识别所有供需不平衡问题了——包括呆滞风险（库存多了）和缺口风险（库存不够），并按金额大小分级，为后续策略测算提供输入。

| 输入 | 业务流程及规则 | 输出 |
|-|-|-|
| **【BOMCheckList（点检清单）】**  <br/>· material_code（物料编码）    <br/>· diff_type（差异类型）    <br/>  <br/>**【MaterialRequirement（物料需求清单）】**  <br/>· 毛需求量    <br/>· 净缺口量    <br/>· 替代料多余供给    <br/>  <br/>**【BatchInventory（批次库存）】**  <br/>· 现有库存量    <br/>· 单位成本    <br/>  <br/>**【PurchaseOrder（采购订单）】**  <br/>· 在途量 | **业务流程：**  <br/>① 从点检清单中结合库存和在途数据，计算每个物料的潜在呆滞量    <br/>② 结合净缺口，计算每个物料的潜在缺口量    <br/>③ 按金额大小分级（高/中/低风险）    <br/>④ 输出供需不平衡风险清单，供后续策略测算使用    <br/>  <br/>**规则明细：**  <br/>1. **呆滞风险识别**：    <br/>   - BOM删除物料：现有可用库存全部为潜在呆滞    <br/>   - 用量调低物料：呆滞量 = 新旧用量差 × 该物料上层父件的毛需求量（不能乘台数，深层物料会少算）    <br/>   - 在途冗余：对应物料已被BOM删除或用量缩减的在途PO，未到货量计入呆滞    <br/>   - 替代料多余供给：需求7中识别的替代料多余供给，也纳入呆滞风险    <br/>  <br/>2. **缺口风险识别**：    <br/>   - BOM新增物料：净缺口量就是潜在缺口风险    <br/>   - 用量调高物料：增量需求就是潜在缺口风险    <br/>  <br/>3. 风险金额计算：    <br/>   - 呆滞金额 = 呆滞量 × unit_cost    <br/>   - 缺口金额 = 缺口量 × unit_cost    <br/>  <br/>4. 风险分级：高风险=金额>10万；中风险=1万\~10万；低风险=<1万（阈值可配置）    <br/>5. 呆滞判定阈值：库龄超过90天算呆滞（可配置），本轮POC默认按BOM变化直接计算 | **【InventoryRisk（库存风险）】**  <br/>每个风险物料一行：    <br/>· material_code    <br/>· risk_type：风险类型（呆滞/缺口）    <br/>· risk_source：风险来源（BOM删除/用量减少/在途冗余/替代料多余/新增需求等）    <br/>· onhand_qty：现有库存量    <br/>· in_transit_qty：在途量    <br/>· risk_qty：风险量（呆滞量或缺口量）    <br/>· risk_amount：风险金额（元）    <br/>· risk_level：高/中/低风险等级    <br/>· 按风险金额降序排列 |



## 需求9：供需平衡策略测算

**业务背景**：识别出供需不平衡问题后，需要从策略库中选取对应的策略，逐个测算每个策略能改善多少风险、剩余还有多少风险。策略分为两类：补缺口类（解决库存不够的问题）和降库存类（解决库存太多的问题）。

| 输入 | 业务流程及规则 | 输出 |
|-|-|-|
| **【InventoryRisk（库存风险）】**  <br/>· 供需不平衡风险清单    <br/>· 呆滞风险/缺口风险    <br/>  <br/>**【MaterialRequirement（物料需求清单）】**  <br/>· 净缺口量    <br/>· 毛需求    <br/>  <br/>**【SupplyDemandStrategy（供需平衡策略）】**  <br/>· 策略库配置    <br/>· 启用的策略列表 | **业务流程：**  <br/>① 对每个风险物料，匹配适用的策略    <br/>② 逐个测算每个策略的效果：能改善多少、剩余多少、有没有附带成本    <br/>③ 记录每个策略的独立测算结果，供后续组合方案使用    <br/>  <br/>**规则明细：**  <br/>**一、补缺口类策略（解决库存不够的问题）**  <br/>1. **采购建议策略**：    <br/>   - 筛选净缺口>0的物料，计算建议采购量    <br/>   - 关联供应商表，按优先级推荐最优供应商    <br/>   - 建议采购量 = 净缺口量（本轮POC暂不考虑MOQ、订货倍数）    <br/>   - 缺口金额 = 净缺口量 × 单位成本    <br/>  <br/>**二、降库存类策略（解决库存太多的问题）**  <br/>2. **取消采购策略**：    <br/>   - 对未来到货的PO，计算取消后能减少的呆滞量    <br/>   - 注意：取消PO有违约金（默认按PO金额10%计算，可配置）    <br/>   - 净收益 = 减少的呆滞金额 - 取消违约金    <br/>  <br/>3. **延期到货策略**：    <br/>   - 对在途PO，计算延期到货后能减少的呆滞量    <br/>   - 延期时间越长，减少的呆滞越多，但要考虑供应商配合度    <br/>  <br/>4. **替代消耗策略**：    <br/>   - 计算呆滞物料能替代多少其他物料的缺口    <br/>   - 即：用呆滞物料去填其他需求的缺口，目的是消耗呆滞    <br/>  <br/>**三、扩展策略**  <br/>5. 后续可新增其他策略（如降价促销、返工改制、报废处置等），只需在策略库中配置即可 | **【StrategyResult（单策略测算结果）】**  <br/>每个策略对应一条测算记录：    <br/>· strategy_code：策略编码（关联 SupplyDemandStrategy）    <br/>· material_code：物料编码    <br/>· improve_amount：改善金额（元）    <br/>· remaining_risk_qty：剩余风险量    <br/>· remaining_risk_amount：剩余风险金额（元）    <br/>· extra_cost：附带成本（如违约金）    <br/>· |

## 需求10：供需平衡方案对比与辅助决策

**业务背景**：单个策略各有优劣，需要把不同策略组合成方案，放在一起对比各维度指标，供决策人员选择。系统不替人做最终决定，而是提供充分的量化对比信息和推荐参考。

| 输入 | 业务流程及规则 | 输出 |
|-|-|-|
| **【StrategyResult（单策略测算结果）】**  <br/>· 各策略单独的测算结果  <br/>· 每个策略的改善金额、剩余风险、附带成本  <br/>  <br/>**【InventoryRisk（库存风险）】**  <br/>· 基线风险总金额（呆滞侧+缺口侧） | **业务流程：**  <br/>① 汇总所有单策略测算结果的核心指标  <br/>② 枚举可行的策略组合，生成候选方案集  <br/>③ 对每个组合方案叠加计算总效果：总改善金额、总剩余风险、总附带成本、预计周期  <br/>④ 按剩余风险金额排序，输出TOP N候选方案对比表  <br/>⑤ 给出辅助推荐：标注剩余风险最低的方案为"风险优先推荐"，标注净收益最高的为"成本优先推荐"，由决策人最终选择  <br/>  <br/>**规则明细：**  <br/>1. 单策略测算：每个策略独立测算，结果写入StrategyResult实体  <br/>2. 组合方案生成：支持将多个单策略叠加为一个方案，叠加时注意策略间的互斥关系（如取消PO和延期PO不能同时用于同一PO行）  <br/>3. 方案对比维度（多维度并列展示，不自动加权求和）：  <br/>   · 剩余呆滞金额（元）  <br/>   · 剩余缺口金额（元）  <br/>   · 附带成本合计（违约金、额外采购成本等，元）  <br/>   · 预计执行周期（天）  <br/>   · 涉及供应商数量  <br/>4. 辅助推荐逻辑：  <br/>   · 系统标注"剩余风险最低"方案和"净收益最高"方案，作为两个参考方向  <br/>   · 不自动加权打分，不替业务拍板；最终方案由采购/计划人员综合排产、客户关系、供应商谈判等因素选定  <br/>5. 方案选定后，下发生成采购计划和处置任务 | **【Scheme（组合方案）】**  <br/>每个候选方案一条记录：  <br/>· scheme_id：方案ID  <br/>· scheme_name：方案名称  <br/>· included_strategies：包含的策略列表（StrategyResult ID集合）  <br/>· total_reduce_amount：总改善金额  <br/>· total_remaining_risk：总剩余风险金额  <br/>· total_extra_cost：总附带成本  <br/>· expected_duration_days：预计执行周期  <br/>· supplier_count：涉及供应商数  <br/>· recommendation_tag：辅助推荐标记（风险优先/成本优先/无）  <br/>  <br/>**【多方案对比看板（界面展示）】**  <br/>① 方案对比表：各组合方案的核心指标并列对比  <br/>② 辅助推荐：标注两个参考方向的最优方案及理由  <br/>③ 方案明细：所选方案包含的具体策略和执行内容 |

## 完整业务链路示例

整个系统从BOM变化触发，到最终输出推荐方案，完整经过以下四个阶段：

```Plain Text
【阶段1：变化感知】
BOM版本切换（V1→V2）
    ↓
① BOM点检（需求1–3）：找出所有变化点
    → 哪些物料新增了？删除了？用量变了？替代关系变了？
    ↓
② 影响范围评估（需求4）：反向查BOM
    → 这些变化会影响哪些成品？哪些已下单的销售订单？
    → 按承诺强度分级：高=影响已下单的销售订单；中=仅影响未来生产计划；低=仅BOM结构变化
```

```Plain Text
【阶段2：现状计算】
③ 毛需求计算（需求5）：多层展开BOM
    → 以销售订单为输入，逐层展开，算出每个物料总共需要多少
    ↓
④ 可用供给汇总（需求6）
    → 汇总每个物料现在有多少库存、多少在途PO，总共有多少可用
    ↓
⑤ 净缺口测算（需求7）
    → 毛需求 - 可用供给 = 主料缺口
    → 主料不够的，按替代优先级先用常规替代料补上，得到最终还需要采购的净缺口
```

```Plain Text
【阶段3：问题识别与分级】
⑥ 供需不平衡问题识别与分级（需求8）
    → 基于净缺口，结合库存和在途，把两类问题一起盘出来：
      · 呆滞风险：库存多了的物料
        （BOM删除、用量调低、在途冗余、替代料多余供给）
      · 缺口风险：库存不够的物料
        （BOM新增、用量调高）
    → 按金额分级（高/中/低），形成基线风险清单
```

```Plain Text
【阶段4：策略测算及方案优选】
⑦ 供需平衡策略测算（需求9）
    → 从策略库里取启用的策略，逐个算效果：
      · 补缺口类：不够的怎么办？→ 采购建议（含供应商推荐）
      · 降库存类：多出来的怎么办？→ 取消采购？延期到货？替代消耗？
      · 扩展策略：后续可新增（降价促销、返工改制、报废处置等），只需在策略库中配置
    → 每个策略单独算：能改善多少？剩多少风险？有没有附带成本？
⑧ 供需平衡方案对比与辅助决策（需求10）
    → 把不同策略组合成几个方案，多维度并列对比
      （剩余呆滞、剩余缺口、附带成本、执行周期、涉及供应商数）
    → 系统只标注"剩余风险最低""净收益最高"两个参考方向，不自动加权打分
    → 由决策人选定方案并填写理由，供采购和计划部门执行
```



---

# 实体

## Material（物料，含成品）

### 属性表｜实体描述：物料主数据，一张表覆盖成品、半成品与原材料，按 material_type 区分

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | material_code | 物料编码 | 物料编码，如 IC-MT9771-QFN128 | STRING | True | True |  |
| 2 | material_name | 物料名称 | 物料自身名称，如联发科 MT9771 主控芯片。这是物料主数据自身属性，不是引用他人名称 | STRING | False | True |  |
| 3 | material_type | 物料类型 | 成品、半成品、电子料、结构件、包材；成品即对外销售的整机，是销售订单与 BOM 产出品的挂载点 | STRING | False | True |  |
| 4 | product_series | 产品系列 | 产品所属系列（X / Z / H 等）；仅 material_type=成品 时有值，原材料留空 | STRING | False | False |  |
| 5 | stage | 生命周期阶段 | 研发 / 试产 / 量产 / 退市；仅成品有值 | STRING | False | False |  |
| 6 | specification | 规格型号 | 物料规格描述，如 QFN-128 封装/主频 2.0GHz | STRING | False | True |  |
| 7 | base_uom | 基础计量单位 | 基础计量单位，如 pcs、kg、m | STRING | False | True |  |
| 8 | purchase_uom | 采购计量单位 | 采购计量单位，如 盘（一盘 2500pcs） | STRING | False | False |  |
| 9 | stock_uom | 库存计量单位 | 库存计量单位，如 米。与采购单位不一致时通过 UnitConversion 换算 | STRING | False | False |  |
| 10 | unit_cost | 标准单位成本 | 物料标准单位成本（元），如 12.50 元/pcs | DECIMAL | False | False |  |
| 11 | abc_type | ABC分类 | 按库存金额累计贡献划分 A/B/C 等级，A 类 = 高价值物料 | STRING | False | False |  |
| 12 | status | 物料状态 | 物料当前状态：正常、停用、冻结 | STRING | False | True |  |
| 13 | create_time | 创建时间 | 数据行创建时间 | TIMESTAMP | False | False |  |
| 14 | update_time | 更新时间 | 数据行更新时间 | TIMESTAMP | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | bom_item | BOM明细 | 该物料作为子件出现在哪些BOM中 | BOMItem | ONE_TO_MANY | False |
| 2 | batch_inventory | 批次库存 | 该物料的批次库存 | BatchInventory | ONE_TO_MANY | False |

## Factory（工厂）

### 属性表｜实体描述：制造工厂，生产活动的组织单元

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | factory_code | 工厂编码 | 工厂编码，如F001 | STRING | True | True |  |
| 2 | factory_name | 工厂名称 | 工厂名称，如深圳光明工厂 | STRING | False | True |  |
| 3 | region | 所属区域 | 工厂所属区域，如华南、华东 | STRING | False | False |  |
| 4 | city | 所在城市 | 工厂所在城市，如深圳 | STRING | False | False |  |
| 5 | address | 详细地址 | 工厂详细地址，如深圳市光明区XX路XX号 | STRING | False | False |  |
| 6 | status | 工厂状态 | 工厂当前运营状态：启用、停用、维护中 | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | warehouse | 关联仓库 | 该工厂下的仓库 | Warehouse | ONE_TO_MANY | False |

## Warehouse（仓库）

### 属性表｜实体描述：物流存储网络中的物理库房与仓储节点

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | wh_code | 仓库编码 | 仓库编码，如WH-SZ-RAW-01 | STRING | True | True |  |
| 2 | wh_name | 仓库名称 | 仓库名称，如深圳原材料一号仓 | STRING | False | True |  |
| 3 | factory_code | 工厂编码 | 仓库所属工厂编码，如F001 | STRING | False | True |  |
| 4 | warehouse_type | 仓库类型 | 仓库业务类型：原材料仓、半成品仓、成品仓、不良品仓 | STRING | False | False |  |
| 5 | region | 所属区域 | 仓库所属区域，如华南 | STRING | False | False |  |
| 6 | city | 所在城市 | 仓库所属城市，如深圳 | STRING | False | False |  |
| 7 | address | 详细地址 | 仓库详细地址 | STRING | False | False |  |
| 8 | status | 仓库状态 | 仓库当前运营状态：启用、停用、维护中 | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | factory | 所属工厂 | 仓库所属工厂 | Factory | MANY_TO_ONE | False |
| 2 | batch_inventory | 批次库存 | 该仓库下的批次库存 | BatchInventory | ONE_TO_MANY | False |

## Supplier（供应商）

### 属性表｜实体描述：供应商

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | supplier_code | 供应商编码 | 供应商编码，如 SUP-001 | STRING | True | True |  |
| 2 | supplier_name | 供应商名称 | 供应商名称，如深圳华强电子有限公司 | STRING | False | False |  |
| 3 | city | 城市 | 供应商所在城市，如深圳 | STRING | False | True |  |
| 4 | address | 地址 | 供应商详细地址 | STRING | False | False |  |
| 5 | allow_supply | 是否允许供应 | 是否允许该供应商供应，Y/N | STRING | False | True |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | purchase_order | 采购订单 | 该供应商的采购订单 | PurchaseOrder | ONE_TO_MANY | False |

## SalesOrder（销售订单）

### 属性表｜实体描述：实时销售订单，成品需求的来源

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | order_nr | 订单编号 | 销售订单唯一编号，如 SO-20240501-001 | STRING | True | True |  |
| 2 | product_code | 产品编码 | 销售订单对应的成品产品编码，如 X98-PRO-2024 | STRING | False | True |  |
| 3 | wh_code | 仓库编码 | 需求对应的发货仓库编码，如 WH-SZ-FG-01 | STRING | False | True |  |
| 4 | due_date | 要货日期 | 客户要求交货日期，如 2024-06-30 | DATE | False | True |  |
| 5 | order_qty | 订单总量 | 销售订单成品总数量，如 1000 台 | DOUBLE | False | True |  |
| 6 | unit_code | 销售单位 | 销售计量单位，如 台 | STRING | False | False |  |
| 7 | unit_cost | 单位成本（元） | 成品单位成本，如 3500 元/台 | DECIMAL | False | False |  |
| 8 | delivery_qty | 已交付量 | 已交付成品数量 | DOUBLE | False | False |  |
| 9 | undelivery_qty | 未交付量 | 尚未交付的成品数量。毛需求计算的唯一规模输入，取此字段 | DOUBLE | False | True | order_qty - delivery_qty |
| 10 | status | 订单状态 | 订单状态：草稿、已确认、执行中、已完成、已取消 | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | product | 关联成品物料 | 订单对应的成品（Material 中 material_type=成品 的物料） | Material | MANY_TO_ONE | False |
| 2 | warehouse | 发货仓库 | 订单对应的发货仓库 | Warehouse | MANY_TO_ONE | False |

## BOMHeader

### 属性表｜实体描述：物料清单表头（产出物料 + 版本）。多层结构不靠行指针：表头 output_code 即第 1 层各行的 upper_material_code，逐级串联

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | bom_code | BOM编码 | BOM编码，如BOM-X98-V2 | STRING | True | True |  |
| 2 | output_code | 产出品编码 | 该BOM对应的产出品物料编码，统一指向 Material.material_code——成品与半成品都是物料，不能一个字段指两张表 | STRING | False | True |  |
| 3 | output_type | 产出品类型 | 产出品类型：成品 / 半成品；仅用于展示分类，外键统一指向 Material | STRING | False | True |  |
| 4 | base_output_qty | 基准产出数量 | 该版 BOM 的配比基数，缺省 1（按“产出 1 个父件”录入）。源表按批量录入时填实际基数（注塑一炉 24 个填 24、PCBA 一拼 8 片填 8），导入时据此折算成每个父件的用量写入 base_qty；本字段不参与毛需求公式 | DECIMAL | False | False |  |
| 5 | bom_version | BOM版本号 | BOM版本号，如V2.1 | STRING | False | True |  |
| 6 | bom_type | BOM类型 | 研发版、正式计划版 | STRING | False | True |  |
| 7 | status | BOM状态 | BOM状态：草稿、冻结、生效 | STRING | False | True |  |
| 8 | effective_date | 生效日期 | 生效日期，如2024-05-01 | DATE | False | True |  |
| 9 | expire_date | 失效日期 | 失效日期，如2025-12-31 | DATE | False | True |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | output_material | 产出品物料 | 该BOM对应的产出品物料（成品或半成品），外键 output_code 在本表 | Material | MANY_TO_ONE | False |
| 2 | bom_item | 物料清单明细 | 该BOM下的所有明细行 | BOMItem | ONE_TO_MANY | False |
| 3 | bom_alter | 替代关系 | 该BOM下的替代料规则 | BOMAlter | ONE_TO_MANY | False |

## BOMItem

### 属性表｜实体描述：物料清单明细（一行 = 一个产出物料 + 一个投入物料 + 用量）

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | line_id | 明细行ID | BOM 明细行唯一标识，如 L001。同一物料在一张 BOM 中出现多行（装在不同位置、或一行正料一行替代）时靠它区分，故作为主键 | STRING | True | True |  |
| 2 | bom_code | BOM编码 | 关联 BOM 表头的全局 BOM 编号，如 BOM-X98-V2 | STRING | False | True |  |
| 3 | material_code | 子件物料编码 | BOM 构成主料物料编码，如 IC-MT9771-QFN128 | STRING | False | True |  |
| 4 | upper_material_code | 直接父件物料编码 | 该行子件直接装在哪个物料上（投入的上一级）。这是多层 BOM 父子关系的唯一依据：等于 BOMHeader.output_code 即第 1 层；本身等于另一行的 material_code 时即接上了下一层。用物料码而不是行指针——同一物料可出现在多行，指针指“哪一行”会有歧义，而“这个件装在谁身上”只有一个答案 | STRING | False | True |  |
| 5 | bom_level | BOM层级 | BOM 展开层级，1 为顶层（直接装在成品上的）。不是录入字段，由计算动作从 BOMHeader.output_code 沿 upper_material_code 链数跳数推导后写入；参与计算：决定这一行乘谁的数 | INTEGER | False | True |  |
| 6 | base_qty | 基准用量 | 每个父件生产 1 单位所需该子件的标准用量。注意是相对父件的用量，不是单台成品累计用量 | DECIMAL | False | True |  |
| 7 | loss_rate | 损耗率 | 生产损耗率，0.05 = 5%，即每 100 颗多备 5 颗。本字段本身不带公式 | DECIMAL | False | False |  |
| 8 | required_qty | 含损耗用量 | 每父件实际需领用量 = 基准用量 ×（1 + 损耗率） | DECIMAL | False | False | base_qty × (1 + loss_rate) |
| 9 | unit | 单位 | 物料单位 pcs/kg/m，如 pcs | STRING | False | True |  |
| 10 | sort_no | 行序号 | BOM 明细前端展示排序号，如 1、2、3 | INTEGER | False | False |  |
| 11 | remark | 备注 | 主料备注信息，如“需提前备货” | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | bom_header | 所属BOM表头 | 该明细行所属的BOM表头 | BOMHeader | MANY_TO_ONE | False |
| 2 | material | 子件物料 | 子件物料对应的物料主数据 | Material | MANY_TO_ONE | False |
| 3 | upper_material | 直接父件物料 | 该行子件的直接父件主数据；展开时以「本行 material_code = 下一行 upper_material_code」串联 | Material | MANY_TO_ONE | False |

## BOMAlter（替代关系）

### 属性表｜实体描述：物料替代关系（按 bom_code + 主料编码 定位，不挂明细行）

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | bom_code | BOM编码 | 关联BOM表头全局BOM编号，如BOM-X98-V2 | STRING | True | True |  |
| 2 | material_code | 主料编码 | 被替代的主料物料编码，如IC-MT9771；与 bom_code 一起唯一定位一条替代规则（替代是对物料的，不挂明细行） | STRING | True | True |  |
| 3 | alt_material_code | 替代料编码 | 可替换主料的物料编码，如IC-MT9770 | STRING | True | True |  |
| 4 | replace_ratio | 替代换算比例 | 主料1单位对应替代料用量；如1.2代表主料1pcs = 替代料1.2pcs | DECIMAL | False | True | 替代料净用量 = 主料需求量 × replace_ratio（由需求展开动作按 bom_code + 主料编码 匹配后计算） |
| 5 | priority | 替代优先级 | 优先级数字，数值越小优先级越高，0 为最高优先级 | INTEGER | False | True |  |
| 6 | alt_effective_date | 替代生效日期 | 该替代料启用生效日期，如2024-05-01 | DATE | False | False |  |
| 7 | alt_expire_date | 替代失效日期 | 该替代料停用失效日期，如2024-12-31 | DATE | False | False |  |
| 8 | remark | 替代备注 | 替代说明、限制条件，如"需重新验证兼容性" | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | bom_header | 所属BOM | 该替代规则所属的BOM | BOMHeader | MANY_TO_ONE | False |
| 2 | main_material | 主料物料 | 主料对应的物料主数据 | Material | MANY_TO_ONE | False |
| 3 | alt_material | 替代料物料 | 替代料对应的物料主数据 | Material | MANY_TO_ONE | False |

## BatchInventory（批次库存）

### 属性表｜实体描述：仓库批次库存，按批次记录每批入库物料的库存明细

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | batch_nr | 库存批次号 | 库存批次号，如 LOT-20240501-001 | STRING | True | True |  |
| 2 | wh_code | 仓库编码 | 仓库编码，如 WH-SZ-RAW-01 | STRING | False | True |  |
| 3 | material_code | 物料编码 | 物料编码，如 IC-MT9771-QFN128 | STRING | False | True |  |
| 4 | batch_qty | 批次库存量 | 该批次入库总库存量，如 5000pcs | DOUBLE | False | True |  |
| 5 | available_qty | 可用库存量 | 该批次当前可用库存量（已扣分配/锁定），如 3200pcs。需求6 只统计此字段 | DOUBLE | False | True |  |
| 6 | frozen_qty | 冻结量 | 该批次冻结库存量，如待检冻结 500pcs | DOUBLE | False | False |  |
| 7 | qc_status | 质检状态 | 质检状态：合格、不合格、待检。需求6 只取合格 | STRING | False | False |  |
| 8 | inbound_date | 入库日期 | 该批次入库仓库日期，如 2024-05-10 | DATE | False | True |  |
| 9 | supplier_code | 供应商编码 | 该批次物料的供应商编码，如 SUP-001 | STRING | False | False |  |
| 10 | unit_code | 单位 | 库存计量单位，如 pcs | STRING | False | True |  |
| 11 | unit_cost | 单位成本 | 该批次单位成本（元），如 12.50 元/pcs | DECIMAL | False | True |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | warehouse | 所属仓库 | 该批次库存所在仓库 | Warehouse | MANY_TO_ONE | False |
| 2 | material | 关联物料 | 该批次库存对应的物料 | Material | MANY_TO_ONE | False |
| 3 | supplier | 供应商 | 该批次物料的供应商 | Supplier | MANY_TO_ONE | False |

## PurchaseOrder（采购订单）

### 属性表｜实体描述：已确认未收货的采购订单，在途采购量

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | purchase_order_nr | 采购订单编号 | 采购订单唯一编号，如 PO-20240420-001 | STRING | True | True |  |
| 2 | material_code | 物料编码 | 采购物料编码，如 IC-MT9771-QFN128 | STRING | False | True |  |
| 3 | wh_code | 仓库编码 | 采购订单所属仓库，如 WH-SZ-RAW-01 | STRING | False | True |  |
| 4 | order_date | 采购订单日期 | 由采购部门发起采购订单日期，如 2024-04-20 | DATE | False | True |  |
| 5 | required_delivery_date | 要求交货日期 | 要求供应商交货日期，如 2024-05-15 | DATE | False | True |  |
| 6 | estimated_arrival_date | 预计到达日期 | 采购订单预计到达日期，如 2024-05-12 | DATE | False | True |  |
| 7 | ship_date | 发货日期 | 供应商发货日期 | DATE | False | False |  |
| 8 | total_order_qty | 订单总量 | 订单总数量，如 10000pcs | DOUBLE | False | True |  |
| 9 | delivered_qty | 已交货量 | 已收货数量，如 5000pcs | DOUBLE | False | False |  |
| 10 | undelivery_qty | 未交货量 | 尚未交货的数量，如 5000pcs | DOUBLE | False | False |  |
| 11 | status | 采购订单状态 | 订单状态：待发货、已发货、部分收货、已完成 | STRING | False | False |  |
| 12 | unit_code | 采购单位 | 采购计量单位，如 pcs | STRING | False | False |  |
| 13 | unit_cost | 单位成本（元） | 单位采购成本，如 12.00 元/pcs | DECIMAL | False | False |  |
| 14 | cancel_flag | 是否取消标记 | 是否已取消，true/false | BOOLEAN | False | True |  |
| 15 | close_flag | 是否关闭标记 | 是否已关闭，true/false | BOOLEAN | False | True |  |
| 16 | supplier_code | 供应商编码 | 供应商编码，如 SUP-001 | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | supplier | 供应商 | 该采购订单对应的供应商 | Supplier | MANY_TO_ONE | False |
| 2 | warehouse | 收货仓库 | 该采购订单的收货仓库 | Warehouse | MANY_TO_ONE | False |
| 3 | material | 采购物料 | 该采购订单对应的物料 | Material | MANY_TO_ONE | False |

## PurchasePlan（采购计划）

### 属性表｜实体描述：由物料需求计算生成的采购计划，用于指导采购部门发起采购订单

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | plan_id | 采购计划ID | 采购计划行唯一标识，如 PLAN-20240501-001 | STRING | True | True |  |
| 2 | material_code | 物料编码 | 建议采购的物料编码，如 IC-MT9771-QFN128 | STRING | False | True |  |
| 3 | suggested_qty | 建议采购量 | 计算得出的建议采购数量，如 2000pcs | DOUBLE | False | True |  |
| 4 | unit_cost | 单位成本 | 该物料单位成本，如 12.50 元/pcs | DECIMAL | False | False |  |
| 5 | shortage_amount | 缺口金额 | 建议采购量对应的金额，如 25000 元 | DECIMAL | False | False | suggested_qty × unit_cost |
| 6 | recommended_supplier_code | 推荐供应商编码 | 按 SupplierMaterial 的供货优先级推荐的首选供应商编码，如 SUP-001 | STRING | False | False |  |
| 7 | scheme_id | 来源方案ID | 本计划由哪个组合方案生成，实现方案到执行的追溯；一个方案只生成一次 | STRING | False | False |  |
| 8 | plan_date | 计划日期 | 采购计划生成日期，如 2024-05-01 | DATE | False | True |  |
| 9 | status | 计划状态 | 状态：待审批、已下达、已关闭 | STRING | False | False |  |
| 10 | remark | 备注 | 采购计划备注说明，如“紧急采购” | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | material | 采购物料 | 计划采购的物料 | Material | MANY_TO_ONE | False |
| 2 | supplier | 推荐供应商 | 推荐的首选供应商 | Supplier | MANY_TO_ONE | False |

## BOMCheckList（点检清单）

### 属性表｜实体描述：BOM的前后变化点检清单

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | compare_item_id | 比对结果行ID | 比对结果单行唯一主键，如 CHK-20240501-001 | STRING | True | True |  |
| 2 | check_batch_id | 点检批次ID | 归属的点检批次，关联 CheckBatch。一次点检产生的全部差异行共用同一个批次号，支持复算与作废 | STRING | False | True |  |
| 3 | base_bom_code | 基准BOM编码 | 作为参照的基准BOM编码，如 BOM-X98-V1 | STRING | False | True |  |
| 4 | target_bom_code | 对比BOM编码 | 待和基准做比较的目标BOM编码，如 BOM-X98-V2 | STRING | False | True |  |
| 5 | product_code | 产品编码 | 本次点检的产成品编码，如 X98-PRO-2024 | STRING | False | True |  |
| 6 | material_code | 点检的物料编码 | 参与比对的子物料编码，如 IC-MT9771 | STRING | False | True |  |
| 7 | base_line_id | 基准-明细行ID | 差异发生在基准版 BOMItem 的哪一行（指向 line_id）。同料多行时必须靠它定位具体行 | STRING | False | False |  |
| 8 | target_line_id | 目标-明细行ID | 差异发生在目标版 BOMItem 的哪一行（指向 line_id）。新增行只填这个 | STRING | False | False |  |
| 9 | alt_material_code | 替代料编码 | 替代关系变更时的替代料编码，如 IC-MT9770 | STRING | False | False | 仅替代关系变更时有值 |
| 10 | diff_type | 差异类型 | 新增 / 删除 / 属性变更 / 替代新增 / 替代删除 / 替代属性变更 | STRING | False | True |  |
| 11 | base_bom_level | 基准BOM层级 | 基准BOM中该物料层级，如 1 | INTEGER | False | False |  |
| 12 | base_base_qty | 基准-基准用量 | 基准BOM内物料基准用量，如 1.0 | DECIMAL | False | False |  |
| 13 | base_loss_rate | 基准-损耗率 | 基准BOM内物料损耗率，如 0.05 | DECIMAL | False | False |  |
| 14 | base_unit | 基准-单位 | 基准BOM物料单位，如 pcs | STRING | False | False |  |
| 15 | target_bom_level | 目标BOM层级 | 目标BOM中该物料层级，如 1 | INTEGER | False | False |  |
| 16 | target_base_qty | 目标-基准用量 | 目标BOM内物料基准用量，如 1.2 | DECIMAL | False | False |  |
| 17 | target_loss_rate | 目标-损耗率 | 目标BOM内物料损耗率，如 0.03 | DECIMAL | False | False |  |
| 18 | target_unit | 目标-单位 | 目标BOM物料单位，如 pcs | STRING | False | False |  |
| 19 | base_priority | 基准-替代优先级 | 基准版替代料优先级，如 1 | INTEGER | False | False | 仅替代关系变更时有值 |
| 20 | target_priority | 目标-替代优先级 | 目标版替代料优先级，如 2 | INTEGER | False | False | 仅替代关系变更时有值 |
| 21 | base_replace_ratio | 基准-替代换算比例 | 基准版替代换算比例，如 1.0 | DECIMAL | False | False | 仅替代关系变更时有值 |
| 22 | target_replace_ratio | 目标-替代换算比例 | 目标版替代换算比例，如 1.2 | DECIMAL | False | False | 仅替代关系变更时有值 |
| 23 | diff_content | 差异内容 | 描述哪些字段不一致，如：用量由 1.0 改为 1.2 | STRING | False | False |  |
| 24 | change_direction | 变更方向 | 用量调高/调低/其他 | STRING | False | False |  |
| 25 | compare_time | 比对时间 | 本次比对执行时间，如 2024-05-01 10:30 | TIMESTAMP | False | True |  |
| 26 | remark | 备注 | 比对备注说明 | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | base_bom | 基准BOM | 基准版本的BOM表头 | BOMHeader | MANY_TO_ONE | False |
| 2 | target_bom | 目标BOM | 目标版本的BOM表头 | BOMHeader | MANY_TO_ONE | False |
| 3 | product | 关联成品物料 | 点检对应的成品物料（Material 中 material_type=成品 的物料） | Material | MANY_TO_ONE | False |
| 4 | material | 点检物料 | 点检涉及的物料 | Material | MANY_TO_ONE | False |

## MaterialRequirement（物料需求）

### 属性表｜实体描述：物料需求计算结果，记录每个物料的毛需求、可用供给和净缺口

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | req_id | 物料需求编号 | 物料需求行唯一标识，如 REQ-20240501-001 | STRING | True | True |  |
| 2 | check_batch_id | 点检批次ID | 本行由哪一次点检触发计算，关联 CheckBatch | STRING | False | True |  |
| 3 | wh_code | 仓库编码 | 需求对应的仓库编码，如 WH-SZ-RAW-01 | STRING | False | True |  |
| 4 | root_product_code | 根需求产品编码 | 顶层成品产品编码，如 X98-PRO-2024 | STRING | False | True |  |
| 5 | parent_material_code | 父件物料编码 | 上一层父件物料编码，如 主板半成品 MB-001；第 1 层取 BOMHeader.output_code（产出物料本身），不再留空 | STRING | False | False |  |
| 6 | material_code | 物料编码 | 需求物料编码，如 IC-MT9771-QFN128 | STRING | False | True |  |
| 7 | bom_level | BOM层级 | 该物料在BOM中的层级，如 1 | INTEGER | False | False |  |
| 8 | sales_order_nr | 销售订单号 | 关联的销售订单编号，如 SO-20240501-001 | STRING | False | True |  |
| 9 | require_date | 需求日期 | 物料需求日期，如 2024-05-15 | DATE | False | True |  |
| 10 | root_demand_qty | 根需求量 | 该成品所有已确认未交付销售订单的未交付量合计。全行同值，仅用于溯源核对，不参与本层计算 | DOUBLE | False | False |  |
| 11 | gross_demand_qty | 毛需求量 | 本行毛需求 = 上层父件毛需求 × 本层用量 ×（1 + 损耗率）；第 1 层的上层父件即根需求量 | DOUBLE | False | True |  |
| 12 | available_stock_qty | 可用库存量 | 本行实际分到的现货供给量，来自供需分配账本（仅质检合格批次），如 800pcs。不是该物料的总库存——按物料码回填会让同一批库存被多行各用一次 | DOUBLE | False | False |  |
| 13 | in_transit_qty | 在途采购量 | 本行实际分到的在途供给量，来自供需分配账本（仅已确认、未取消、未关闭的订单），如 500pcs | DOUBLE | False | False |  |
| 14 | total_available_qty | 总可用供给 | 本行已分到的现货 + 在途，如 1300pcs；两项都是分配结果，故天然不会重复占用同一份供给 | DOUBLE | False | False | available_stock_qty + in_transit_qty |
| 15 | net_shortage_qty | 净缺口量 | 扣减本行分到的可用供给后的缺口，如 0（供给大于需求） | DOUBLE | False | False | MAX(0.0, gross_demand_qty - total_available_qty) |
| 16 | alt_consume_qty_alt_unit | 替代料实物消耗量 | 替代料按自己单位算的消耗量，用于下采购单，如 500 个 B | DOUBLE | False | False |  |
| 17 | alt_consume_qty_main_unit | 替代消耗折算主料量 | 替代料折回主料单位后的数量，用于从净缺口里扣减，如相当于 250 个 A | DOUBLE | False | False |  |
| 18 | applied_replace_ratio | 替代比例快照 | 本次测算实际使用的换算比例（1 个替代料抵几个主料）。算的时候是多少就存多少，不事后重算 | DECIMAL | False | False |  |
| 19 | remaining_shortage_qty | 最终剩余缺口 | 扣掉替代料填补量之后仍需采购的主料数量 | DOUBLE | False | False | MAX(0.0, net_shortage_qty - alt_consume_qty_main_unit) |
| 20 | alt_surplus_qty | 替代料多余供给 | 替代料供给超过可消耗量的部分，可能呆滞 | DOUBLE | False | False |  |
| 21 | diff_type | 关联差异类型 | 关联点检清单的差异类型，如 新增 | STRING | False | False |  |
| 22 | unit_cost | 单位成本 | 物料单位成本，如 12.50 元/pcs | DECIMAL | False | False |  |
| 23 | bom_code | BOM编码 | 计算依据的BOM编码，如 BOM-X98-V2 | STRING | False | True |  |
| 24 | bom_version | BOM版本 | 计算依据的BOM版本，如 V2.1 | STRING | False | False |  |
| 25 | create_time | 创建时间 | 需求计算创建时间，如 2024-05-01 10:30 | TIMESTAMP | False | True |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | warehouse | 需求仓库 | 需求对应的仓库 | Warehouse | MANY_TO_ONE | False |
| 2 | material | 需求物料 | 需求对应的物料 | Material | MANY_TO_ONE | False |
| 3 | bom | 关联BOM | 计算依据的BOM | BOMHeader | MANY_TO_ONE | False |
| 4 | sales_order | 关联销售订单 | 需求来源的销售订单 | SalesOrder | MANY_TO_ONE | False |

## SupplyDemandAllocation（供需分配）

### 属性表｜实体描述：一行 = 某条需求行从某个供给源取用了多少量。它是「够不够」的账本，不是处置手段——处置由供需平衡策略承担。必须存在的理由是库存只能用一次：同一物料常有多条需求行（跨层、跨订单、跨 BOM 位置），若每行都拿该物料总库存去减，同一批库存会被重复扣减，缺口被系统性低估

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | allocation_id | 分配记录ID | 分配记录唯一标识（代理主键）；真实唯一性为「需求行 × 供给源」，同一需求行可有多笔（多个供给源凑一批） | STRING | True | True |  |
| 2 | material_code | 物料编码 | 被分配的物料编码；冗余一份便于按物料核对「分出去的量是否等于供给总量」，也供动作按物料分组循环 | STRING | False | True |  |
| 3 | demand_line_id | 需求行ID | 承接该笔供给的需求行，指向物料需求清单的 req_id；汇总该行全部分配量才是它的「已满足量」 | STRING | False | True |  |
| 4 | supply_type | 供给类型 | 现货批次库存 / 在途采购；决定 supply_ref_id 指向哪张表，也是两条供给连线各自的生效条件 | STRING | False | True |  |
| 5 | supply_ref_id | 供给源单据号 | 供给源标识：stock_batch 时填 BatchInventory.batch_nr，in_transit 时填 PurchaseOrder.purchase_order_nr。多态外键，由 supply_type 消歧——须建两条各带条件的连线，不能建一条多态连线 | STRING | False | True |  |
| 6 | supply_available_qty | 供给源可供量 | 分配前该供给源的可供总量快照：现货批次取 available_qty 且质检合格，在途取未交货量且未取消未关闭。落快照是为了供给源数据变动后账本仍可复算 | DOUBLE | False | True |  |
| 7 | allocated_qty | 分配量 | 本次从该供给源分给该需求行的量（主料单位）；必须同时不超过供给源剩余可分配量与需求行剩余未满足量 | DOUBLE | False | True |  |
| 8 | allocation_seq | 分配序号 | 同一物料内第几笔分配（从 1 起）。排序即优先级：需求按需求日期升序，供给先现货后在途、批次内按入库日期升序。落库是为了出问题能原样重演 | INTEGER | False | True |  |
| 9 | supply_remaining_qty | 供给源剩余可分配量 | 本笔分配后该供给源还剩多少可分配。落库用于审计：最后一条记录的剩余量应等于未被任何需求占用的余量 | DOUBLE | False | False | supply_available_qty - SUM(allocated_qty) |
| 10 | demand_remaining_qty | 需求行剩余未满足量 | 本笔分配后该需求行还差多少；为 0 即已满足，大于 0 的部分才进入替代料填补与净缺口 | DOUBLE | False | False | gross_demand_qty - SUM(allocated_qty) |
| 11 | allocate_rule | 分配依据 | 本次分配遵循的规则：FEFO 先到期先出 / 需求日期优先 / 人工指定。人工指定必须留痕，否则事后无法解释为什么某批料分给了后到期的订单 | STRING | False | True |  |
| 12 | allocated_by | 分配执行方 | 执行分配的系统或人员标识；自动分配填动作名，人工调整填工号 | STRING | False | False |  |
| 13 | allocate_time | 分配时间 | 本笔分配发生的时间，同一轮分配内各笔相同，用于按轮次回溯 | TIMESTAMP | False | True |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | demand_line | 承接需求行 | 该笔供给分给哪条需求行 | MaterialRequirement | MANY_TO_ONE | False |
| 2 | material | 分配物料 | 被分配的物料主数据 | Material | MANY_TO_ONE | False |
| 3 | supply_batch | 供给批次 | 供给来源批次；仅在 supply_type=stock_batch 时成立，此时 supply_ref_id 即批次号。同字段建两条连线是有意的——一条连线表达不了「按类型分指两张表」 | BatchInventory | MANY_TO_ONE | False |
| 4 | supply_in_transit | 供给在途订单 | 供给来源采购订单；仅在 supply_type=in_transit 时成立，此时 supply_ref_id 即采购订单号 | PurchaseOrder | MANY_TO_ONE | False |

## InventoryRisk（库存风险）

### 属性表｜实体描述：供需不平衡风险清单，记录识别出的呆滞风险（库存过剩）和缺口风险（库存不足）及风险等级

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | risk_id | 风险ID | 库存风险行唯一标识，如 RISK-20240501-001 | STRING | True | True |  |
| 2 | check_batch_id | 点检批次ID | 本次风险识别所属的点检批次，关联 CheckBatch | STRING | False | True |  |
| 3 | material_code | 物料编码 | 风险物料编码 | STRING | False | True |  |
| 4 | risk_type | 风险类型 | 风险类型：呆滞（库存过剩）/ 缺口（库存不足） | STRING | False | True |  |
| 5 | risk_source | 风险来源 | 呆滞侧：BOM删除/用量减少/在途冗余/替代料多余；缺口侧：BOM新增/用量调高 | STRING | False | True |  |
| 6 | onhand_qty | 现有库存量 | 该物料当前可用库存量 | DOUBLE | False | False |  |
| 7 | in_transit_qty | 在途量 | 该物料在途采购量 | DOUBLE | False | False |  |
| 8 | risk_qty | 风险量 | 呆滞量或缺口量（根据 risk_type 区分方向） | DOUBLE | False | True |  |
| 9 | risk_amount | 风险金额（元） | 呆滞金额或缺口金额，取绝对值。呆滞按批次实际成本算，缺口按标准成本算 | DECIMAL | False | True | risk_qty × unit_cost |
| 10 | risk_level | 风险等级 | 高（大于 10 万）/ 中（1 万到 10 万）/ 低（小于 1 万），阈值走策略参数表 | STRING | False | True |  |
| 11 | identify_date | 识别日期 | 风险识别日期 | DATE | False | True |  |
| 12 | status | 处置状态 | 待处置 / 处置中 / 已消化 | STRING | False | False |  |
| 13 | remark | 备注 | 风险说明及处置记录 | STRING | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | material | 风险物料 | 风险对应的物料 | Material | MANY_TO_ONE | False |

## SupplyDemandStrategy（供需平衡策略）

### 属性表｜实体描述：供需平衡处置策略配置库，可扩展，支持自定义策略

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | strategy_code | 策略编码 | 策略唯一编码，如STRATEGY-CANCEL-PO | STRING | True | True |  |
| 2 | strategy_name | 策略名称 | 策略名称，如取消采购订单 | STRING | False | True |  |
| 3 | strategy_description | 策略描述 | 策略的业务含义和适用场景 | STRING | False | False |  |
| 4 | strategy_direction | 策略方向 | 策略作用方向：补缺口 / 降库存 / 双向 | STRING | False | True |  |
| 5 | applicable_scenario | 适用场景 | 适用的场景类型，如BOM变更呆滞、预测偏差呆滞 | STRING | False | False |  |
| 6 | priority_level | 优先级 | 策略优先级，数值越小越优先，如1=最高 | INTEGER | False | True |  |
| 7 | is_active | 是否启用 | 该策略是否启用，Y/N | STRING | False | True |  |
| 8 | create_time | 创建时间 | 策略创建时间 | TIMESTAMP | False | False |  |
| 9 | update_time | 更新时间 | 策略最后更新时间 | TIMESTAMP | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | scheme_result | 关联方案 | 使用该策略的方案 | SchemeResult | ONE_TO_MANY | False |

## SchemeResult（方案测算结果）

<callout emoji="💡">
**本表已被拆分，不要按此建实体。**单策略测算结果见 StrategyResult，组合方案见 Scheme。本表的 scheme_id 与 Scheme.scheme_id 同名但不是同一个对象，两者并存会导致导入平台时主键冲突。
</callout>

### 属性表｜实体描述：每个处置方案的测算结果，记录每个方案能减少多少呆滞、剩余呆滞还有多少

| 序号 | 属性字段 | name | description | data_type | is_primary | is_required | derived_calculation |
|-|-|-|-|-|-|-|-|
| 1 | scheme_id | 方案ID | 【已废弃】旧版方案测算行标识。拆分后单策略见 StrategyResult，组合方案见 Scheme | STRING | True | True |  |
| 2 | scheme_type | 方案类型 | 方案类型：取消采购/延期到货/替代消耗/组合方案 | STRING | False | True |  |
| 3 | material_code | 物料编码 | 该方案针对的物料编码，如 IC-MT9771 | STRING | False | True |  |
| 4 | base_deadstock_amount | 基线呆滞金额 | 不做任何处置时的基线呆滞金额，如 50000 元 | DECIMAL | False | True |  |
| 5 | reduce_amount | 可减少呆滞金额 | 本方案能减少的呆滞金额，如 30000 元 | DECIMAL | False | True |  |
| 6 | remaining_deadstock_amount | 剩余呆滞金额 | 本方案执行后剩余的呆滞金额，如 20000 元 | DECIMAL | False | True | base_deadstock_amount - reduce_amount |
| 7 | new_shortage_amount | 新增缺口风险金额 | 本方案执行后可能新产生的缺口金额，如 5000 元 | DECIMAL | False | False |  |
| 8 | detail | 方案明细 | 方案具体内容描述，如“取消 PO-20240420-001 的 5000pcs” | STRING | False | False |  |
| 9 | risk_flag | 风险标记 | 是否有风险：低/中/高 | STRING | False | False |  |
| 10 | calc_time | 测算时间 | 方案测算生成时间 | TIMESTAMP | False | True |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | is_required |
|-|-|-|-|-|-|-|
| 1 | material | 目标物料 | 方案针对的物料 | Material | MANY_TO_ONE | False |
| 2 | inventory_risk | 关联风险 | 方案对应的库存风险项 | InventoryRisk | MANY_TO_ONE | False |

## SupplierMaterial（供应商-物料供货关系）

**实体描述**：供应商与物料的多对多供货关系，优先级、价格、起订量、交期均记录在此表，而非供应商主表上。

| 序号 | 属性字段 | name | description | data_type | 主键 | 必填 |
|-|-|-|-|-|-|-|
| 1 | supplier_material_id | 供货关系ID | 供应商-物料关系唯一标识 | STRING | True | True |
| 2 | supplier_code | 供应商编码 | 关联Supplier表 | STRING | False | True |
| 3 | material_code | 物料编码 | 关联Material表 | STRING | False | True |
| 4 | supply_priority | 供货优先级 | 该供应商供此物料的优先级，越小越优先 | INTEGER | False | True |
| 5 | unit_price | 单价 | 该供应商供此物料的单价 | DECIMAL | False | False |
| 6 | min_order_qty | 最小起订量 | 该物料在该供应商处的最小起订量 | DOUBLE | False | False |
| 7 | lead_time_days | 交期（天） | 该供应商供此物料的标准交货周期 | INTEGER | False | False |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | 外键位置 | is_required |
|-|-|-|-|-|-|-|-|
| 1 | supplier | 供应商 | 该供货条件属于哪个供应商 | Supplier | MANY_TO_ONE | 本表 supplier_code | True |
| 2 | material | 物料 | 该供货条件对应哪个物料 | Material | MANY_TO_ONE | 本表 material_code | True |

## UnitConversion（单位换算）

**实体描述**：物料不同计量单位之间的换算关系，如采购按"卷"、库存按"米"。

| 序号 | 属性字段 | name | description | data_type | 主键 | 必填 |
|-|-|-|-|-|-|-|
| 1 | conversion_id | 换算ID | 换算关系唯一标识 | STRING | True | True |
| 2 | material_code | 物料编码 | 关联Material表 | STRING | False | True |
| 3 | from_uom | 源单位 | 换算前单位，如"卷" | STRING | False | True |
| 4 | to_uom | 目标单位 | 换算后单位，如"米" | STRING | False | True |
| 5 | conversion_factor | 换算系数 | 1源单位 = conversion_factor 目标单位 | DECIMAL | False | True |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | 外键位置 | is_required |
|-|-|-|-|-|-|-|-|
| 1 | material | 物料 | 该换算关系属于哪个物料 | Material | MANY_TO_ONE | 本表 material_code | True |

## CheckBatch（点检批次）

**实体描述**：每次BOM点检的批次记录，将所有差异行、后续测算结果归组到同一批次，支持历史追溯和复算。

| 序号 | 属性字段 | name | description | data_type | 主键 | 必填 |
|-|-|-|-|-|-|-|
| 1 | check_batch_id | 点检批次ID | 本次点检唯一批次号，如CHK-BATCH-20240501-001 | STRING | True | True |
| 2 | product_code | 产品编码 | 本次点检的产品 | STRING | False | True |
| 3 | base_bom_code | 基准BOM编码 | 基准版本BOM | STRING | False | True |
| 4 | target_bom_code | 目标BOM编码 | 目标版本BOM | STRING | False | True |
| 5 | check_time | 点检时间 | 本次点检执行时间 | TIMESTAMP | False | True |
| 6 | status | 批次状态 | 有效 / 已作废 / 已复算 | STRING | False | True |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | 外键位置 | is_required |
|-|-|-|-|-|-|-|-|
| 1 | base_bom | 基准BOM | 本次点检的基准版BOM表头 | BOMHeader | MANY_TO_ONE | 本表 base_bom_code | True |
| 2 | target_bom | 目标BOM | 本次点检的目标版BOM表头 | BOMHeader | MANY_TO_ONE | 本表 target_bom_code | True |
| 3 | product | 成品物料 | 本次点检的成品（Material 中 material_type=成品 的物料） | Material | MANY_TO_ONE | 本表 product_code | True |
| 4 | check_list | 差异明细 | 本批次产生的全部点检差异行 | BOMCheckList | ONE_TO_MANY | 对方 check_batch_id | False |

## StrategyResult（单策略测算结果）

**实体描述**：每个策略单独测算的结果记录，与组合方案(Scheme)分离。

| 序号 | 属性字段 | name | description | data_type | 主键 | 必填 |
|-|-|-|-|-|-|-|
| 1 | strategy_result_id | 策略测算ID | 单策略测算结果唯一标识 | STRING | True | True |
| 2 | scheme_id | 所属方案ID | 本策略结果被归入哪个组合方案。方案与策略的关系靠这个字段表达，不再用字符串列表 | STRING | False | False |
| 3 | strategy_code | 策略编码 | 关联 SupplyDemandStrategy | STRING | False | True |
| 4 | material_code | 物料编码 | 该策略作用的物料 | STRING | False | True |
| 5 | risk_id | 关联风险ID | 关联 InventoryRisk 中的风险项 | STRING | False | False |
| 6 | improve_amount | 改善金额 | 执行该策略后减少的风险金额（元） | DECIMAL | False | True |
| 7 | remaining_risk_amount | 剩余风险金额 | 执行该策略后剩余的风险金额（元） | DECIMAL | False | True |
| 8 | extra_cost | 附带成本 | 执行该策略产生的额外成本（如违约金） | DECIMAL | False | False |
| 9 | detail | 测算明细 | 策略执行的具体内容描述 | STRING | False | False |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | 外键位置 | is_required |
|-|-|-|-|-|-|-|-|
| 1 | scheme | 所属方案 | 本策略测算结果被归入哪个组合方案 | Scheme | MANY_TO_ONE | 本表 scheme_id | False |
| 2 | strategy | 策略 | 关联策略库中的定义 | SupplyDemandStrategy | MANY_TO_ONE | 本表 strategy_code | True |
| 3 | material | 物料 | 该策略作用的物料 | Material | MANY_TO_ONE | 本表 material_code | True |
| 4 | risk | 关联风险 | 该策略针对的风险项 | InventoryRisk | MANY_TO_ONE | 本表 risk_id | False |

## Scheme（组合方案）

**实体描述**：由多个单策略组合而成的完整处置方案，支持方案间对比和选定后下发生成采购计划。

| 序号 | 属性字段 | name | description | data_type | 主键 | 必填 |  |
|-|-|-|-|-|-|-|-|
| 1 | scheme_id | 方案ID | 组合方案唯一标识 | STRING | True | True |  |
| 2 | scheme_name | 方案名称 | 方案名称，如“部分取消+部分延期” | STRING | False | True |  |
| 3 | total_improve_amount | 总改善金额 | 本方案包含的全部策略改善金额之和 | DECIMAL | False | True |  |
| 4 | total_remaining_deadstock | 剩余呆滞金额 | 执行本方案后仍存在的呆滞金额 | DECIMAL | False | True |  |
| 5 | total_remaining_shortage | 剩余缺口金额 | 执行本方案后仍存在的缺口金额 | DECIMAL | False | True |  |
| 6 | total_extra_cost | 总附带成本 | 所有策略附带成本合计（违约金、额外采购成本等） | DECIMAL | False | False |  |
| 7 | net_benefit | 净收益 | 总改善金额 − 总附带成本 | DECIMAL | False | False | total_improve_amount - total_extra_cost |
| 8 | cost_performance | 性价比倍数 | 总改善金额 ÷ 总附带成本，衡量每花一块钱附带成本能换回多少改善 | DECIMAL | False | False | total_improve_amount / MAX(1.0, total_extra_cost) |
| 9 | expected_duration_days | 预计执行周期 | 本方案执行预计需要多少天 | INTEGER | False | False |  |
| 10 | supplier_count | 涉及供应商数 | 本方案执行需要协调的供应商数量 | INTEGER | False | False |  |
| 11 | recommendation_tag | 推荐标记 | 风险优先 / 成本优先 / 无（系统辅助标记，不替人决策） | STRING | False | False |  |
| 12 | selected_flag | 是否选定 | 决策人是否选定此方案执行 | BOOLEAN | False | False |  |

### Link 表

| 序号 | Link 字段 | name | description | target | cardinality | 外键位置 | is_required |
|-|-|-|-|-|-|-|-|
| 1 | strategy_result | 包含的策略测算 | 本方案由哪些单策略测算结果组合而成。加入方案时回写 StrategyResult.scheme_id | StrategyResult | ONE_TO_MANY | 对方 scheme_id | False |
| 2 | purchase_plan | 生成的采购计划 | 方案选定后据此生成采购计划 | PurchasePlan | ONE_TO_MANY | 对方 scheme_id | False |

# 业务规则

规则范式：每条规则包含规则编码、规则描述、作用实体、触发方式、规则逻辑（输入→处理→输出）。

## BOM点检模块

### BOM版本比对规则

**规则编码**：RULE-BOM-CHECK-001

**规则描述**：对同一产品的两版BOM进行全量差异比对，识别物料新增、删除、属性变更、替代关系变化，输出点检清单。

**作用实体对象**：BOMCheckList、CheckBatch

**触发方式**：手动触发（用户选定基准BOM和目标BOM）

**规则逻辑**：

- **输入数据**：基准BOM编码、目标BOM编码（须属于同一output_code，且bom_type=正式计划版）
- **处理逻辑**：  
step1：创建CheckBatch记录，生成check_batch_id  
step2：拉取两版BOM的全部BOMItem明细行，按line_id逐行比对  
step3：集合差运算识别新增物料（目标有、基准无）和删除物料（基准有、目标无）  
step4：交集物料逐字段比对（base_qty、loss_rate、bom_level、unit），生成属性变更记录  
step5：比对BOMAlter替代关系表，识别替代新增、替代删除、替代属性变更  
step6：所有差异行写入BOMCheckList，关联同一check_batch_id
- **输出结果**：生成CheckBatch记录 + BOMCheckList差异记录集

## 影响评估模块

### 受影响范围反查规则

**规则编码**：RULE-IMPACT-001

**规则描述**：根据点检清单中的变化物料，反向查询BOM结构，找出所有受影响的成品和对应销售订单，计算影响等级和繁杂度。

**作用实体对象**：BOMItem、BOMHeader、Material、SalesOrder、InventoryRisk

**触发方式**：自动触发（点检完成后自动执行）

**规则逻辑**：

- **输入数据**：CheckBatch关联的所有BOMCheckList记录
- **处理逻辑**：  
step1：从点检清单取所有去重后的material_code列表  
step2：对每个物料，反查BOMItem中哪些bom_code包含该物料，再通过BOMHeader找到对应output_code（成品）  
step3：对每个受影响成品，关联SalesOrder表，统计已确认未交付订单数和数量  
step4：结合后续算出的风险金额，按规则判定影响等级（高/中/低）  
step5：计算繁杂度变化 = 新增物料种类数 - 删除物料种类数，若净新增>0且金额对冲≈0，标记繁杂度上升
- **输出结果**：受影响范围明细（界面展示），不落地为独立实体表

## 需求计算模块

### 多层BOM毛需求展开规则

**规则编码**：RULE-DEMAND-001

**规则描述**：从顶层成品销售订单需求出发，多层递归展开BOM，逐层计算各物料的毛需求量。

**作用实体对象**：MaterialRequirement

**触发方式**：手动触发 / 点检批次确认后自动触发

**规则逻辑**：

- **输入数据**：  
· 根需求：筛选该成品所有status=已确认的销售订单，undelivery_qty求和得到根需求量  
· 目标BOM：该成品的目标版本BOMHeader及其全部BOMItem  
· 点检清单：check_batch_id对应的差异记录
- **处理逻辑**：  
step1：第1层物料毛需求 = 根需求量 × base_qty × (1 + loss_rate)  
step2：若该物料是半成品（存在对应BOMHeader且output_type=半成品），将其毛需求量作为下一层的父件需求量，继续向下展开  
step3：递归直到所有叶子节点（无下级BOM的原材料）  
step4：同一物料在不同层级出现时，毛需求逐层累加，不合并  
step5：删除物料目标版毛需求=0，转入呆滞评估
- **输出结果**：生成MaterialRequirement记录集，每个物料每层一行

### 用量调整增量需求计算规则

**规则编码**：RULE-DEMAND-002

**规则描述**：对于BOM中用量发生变化的物料，计算其增量毛需求，用于缺口/呆滞的增量分析。

**作用实体对象**：MaterialRequirement

**触发方式**：随毛需求展开规则自动执行

**规则逻辑**：

- **输入数据**：点检清单中diff_type=属性变更且change_direction为调高/调低的物料记录
- **处理逻辑**：  
step1：找到该物料在BOM中的所有上层父件路径，计算从根到该物料的全路径父件用量乘积（累计系数）  
step2：增量毛需求 = 根需求量 × 累计系数 × (target_base_qty - base_base_qty) × (1 + loss_rate)  
step3：注意：层数越深，累计系数越大，增量公式必须乘全路径父件乘积，不能只乘根需求量
- **输出结果**：增量需求标记写入MaterialRequirement.diff_type和增量字段

## 供给与缺口模块

### 可用供给汇总规则

**规则编码**：RULE-SUPPLY-001

**规则描述**：汇总每个物料的质检合格库存和有效在途采购订单量，得到总可用供给。

**作用实体对象**：MaterialRequirement、BatchInventory、PurchaseOrder

**触发方式**：自动触发（毛需求计算完成后）

**规则逻辑**：

- **输入数据**：  
· 库存：BatchInventory中qc_status=合格且available_qty>0的批次  
· 在途：PurchaseOrder中cancel_flag=false、close_flag=false、status=已确认/已下达的未交货量
- **处理逻辑**：  
step1：按material_code汇总所有合格批次的available_qty合计 → available_stock_qty  
step2：按material_code汇总所有有效在途订单的undelivery_qty合计 → in_transit_qty  
step3：total_available_qty = available_stock_qty + in_transit_qty  
step4：单位不一致时通过UnitConversion换算为统一单位
- **输出结果**：回填MaterialRequirement的供给类字段

### 常规替代料补缺口规则

**规则编码**：RULE-NETSHORT-001

**规则描述**：主料存在净缺口时，按替代优先级从替代料的供给池逐笔分配（同样走供需分配，替代料库存同样只能用一次，不得被多条需求行各扣一次），计算剩余缺口和替代料多余供给。

**作用实体对象**：MaterialRequirement、BOMAlter、BatchInventory、SupplyDemandAllocation

**触发方式**：自动触发（可用供给汇总完成后）

**规则逻辑**：

- **输入数据**：  
· 主料净缺口 = MAX(0, gross_demand_qty - total_available_qty)  
· BOMAlter中该主料的所有替代料关系（按priority升序）  
· 各替代料的可用库存量
- **处理逻辑**：  
step1：按替代优先级从高到低遍历替代料列表  
step2：计算当前替代料可填补量 = MIN(替代料可用库存, 剩余主料缺口 × replace_ratio)  
step3：记录两个口径：替代料实物消耗量（替代料单位）和折算主料填补量（主料单位）  
step4：记录本次使用的replace_ratio快照  
step5：更新剩余主料缺口，继续处理下一个替代料  
step6：替代料库存减去已消耗量，多余部分记录为alt_surplus_qty
- **输出结果**：更新MaterialRequirement的alt_consume_qty_alt_unit、alt_consume_qty_main_unit、remaining_shortage_qty、alt_surplus_qty等字段

## 风险识别模块

### 供需不平衡风险识别规则

**规则编码**：RULE-RISK-001

**规则描述**：结合点检结果、库存、在途和净缺口数据，识别所有呆滞风险和缺口风险，按金额分级。

**作用实体对象**：InventoryRisk

**触发方式**：自动触发（净缺口测算完成后）

**规则逻辑**：

- **输入数据**：CheckBatch关联的BOMCheckList、MaterialRequirement计算结果、BatchInventory、PurchaseOrder
- **处理逻辑**：  
step1：呆滞风险识别（risk_type=呆滞）：  
  · BOM删除物料：现有合格库存全部计入呆滞量  
  · 用量调低物料：呆滞量 = (base_base_qty - target_base_qty) × 上层父件累计需求量  
  · 在途冗余：BOM已删/已减料的对应在途PO未到货量计入呆滞  
  · 替代料多余供给：alt_surplus_qty计入呆滞  
step2：缺口风险识别（risk_type=缺口）：  
  · BOM新增物料：remaining_shortage_qty计入缺口风险  
  · 用量调高物料：增量需求对应的净缺口计入缺口风险  
step3：风险金额 = risk_qty × unit_cost（取绝对值）  
step4：按金额分级：高>10万，中1\~10万，低<1万（阈值可配置）
- **输出结果**：生成InventoryRisk记录集，每条带risk_type区分呆滞/缺口

## 策略与方案模块

### 单策略效果测算规则

**规则编码**：RULE-STRATEGY-001

**规则描述**：对每个启用的策略，独立测算其对每条风险的改善效果、剩余风险和附带成本。

**作用实体对象**：StrategyResult、SupplyDemandStrategy、InventoryRisk

**触发方式**：自动触发（风险识别完成后）

**规则逻辑**：

- **输入数据**：InventoryRisk风险清单、SupplyDemandStrategy启用策略列表
- **处理逻辑**：  
step1：对每条风险，匹配适用的策略（补缺口类策略匹配缺口风险，降库存类策略匹配呆滞风险）  
step2：逐个策略独立测算：  
  · 采购建议策略：改善金额 = 净缺口×单价，剩余风险=0，附带成本=0  
  · 取消采购策略：改善金额 = 可取消在途量×单价，附带成本 = 取消金额×10%违约金，剩余风险=对应呆滞量减少后的剩余  
  · 延期到货策略：改善金额 = 延期期间可消耗的呆滞量×单价，附带成本=供应商沟通成本（人工评估）  
  · 替代消耗策略：改善金额 = 呆滞料可用于填补的缺口量×呆滞单价，附带成本=替代验证成本  
step3：每个策略×每个风险物料生成一条StrategyResult记录
- **输出结果**：生成StrategyResult记录集

### 组合方案生成与对比规则

**规则编码**：RULE-SCHEME-001

**规则描述**：基于单策略测算结果，生成可行的策略组合方案，多维度并列对比，辅助决策人选择。

**作用实体对象**：Scheme、StrategyResult

**触发方式**：手动触发 / 单策略测算完成后自动生成候选集

**规则逻辑**：

- **输入数据**：StrategyResult记录集、基线风险总金额
- **处理逻辑**：  
step1：枚举可行的策略组合（注意互斥约束：同一PO不能同时取消和延期）  
step2：对每个组合，叠加计算：总改善金额、总剩余风险、总附带成本、涉及供应商数  
step3：按剩余风险金额升序排序，取TOP N作为候选方案  
step4：系统辅助标记：剩余风险最低的标记为"风险优先"，净收益最高的标记为"成本优先"  
step5：系统不自动选最优，由决策人综合排产、客户关系、供应商谈判等因素最终选定
- **输出结果**：生成Scheme候选方案集；决策人选定后，触发采购计划生成规则

### 采购计划生成规则

**规则编码**：RULE-PURCHASE-PLAN-001

**规则描述**：决策人选定组合方案后，根据方案中的采购建议策略，生成正式采购计划。

**作用实体对象**：PurchasePlan、Scheme、SupplierMaterial

**触发方式**：手动触发（决策人选定方案后点击"生成采购计划"）

**规则逻辑**：

- **输入数据**：已选定的Scheme（selected_flag=true）、对应的StrategyResult中采购建议策略明细
- **处理逻辑**：  
step1：从方案中提取所有采购建议类策略的物料和建议采购量  
step2：关联SupplierMaterial表，按供货优先级推荐首选供应商  
step3：检查MOQ、订货倍数约束（本轮POC暂不强制，仅提示）  
step4：生成PurchasePlan记录，关联scheme_id实现方案到执行的追溯  
step5：采购计划状态初始为"待审批"，审批后下达
- **输出结果**：生成PurchasePlan记录集

## 配置参数说明

以下阈值参数均应支持配置化管理，建议使用独立的ConfigParam实体存储，而非硬编码：

| 参数名称 | 默认值 | 说明 |
|-|-|-|
| risk_level_high_threshold | 100000元 | 高风险金额阈值，超过此值判定为高风险 |
| risk_level_low_threshold | 10000元 | 低风险金额阈值，低于此值判定为低风险；中间为中风险 |
| cancel_penalty_rate | 10% | 取消采购订单的违约金比例 |
| dead_stock_age_days | 90天 | 呆滞判定库龄阈值（本轮POC默认按BOM变化直接计算，不按库龄） |