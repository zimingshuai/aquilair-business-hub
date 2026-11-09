# 评估记录：2026-11-09（scope：launch-dynamic-assurance 0.1.14 子图锚定伸缩改版）

## 改版背景

用户问「查看新品上市计划」（单对象查看意图），launch-poc-advisor 旧版（0.1.13）跑了 21 次工具调用、
7 类实体全扫、强制出 4 图看板、总耗时 6.8 分钟。根因：agents 行为约束表「交付必配图」无条件强制 +
SKILL.md「可视化交付」节无条件强制 + 探查循环缺子图锚定规划。改版为「本体子图锚定驱动的伸缩交付」
（单对象/单边查看纯文本合法；跨对象子图诊断必配图，两档形态不变）。

## 本次完成项

### 1. 工具链验证（全绿）

- `python tools/validate_cases.py`：5 个文件 69 条用例校验通过
  （drill 9 | guardrail 18 | normal 27 | redteam 2 | trap 9 | trigger-negative 4）
- `python tools/lint_skills.py`：launch-dynamic-assurance PASS；ERROR 0（10 个 WARN 为其他技能存量 C13 渐进补齐项）
- `python tools/pack_skill.py launch-dynamic-assurance`：打包成功

### 2. 新用例数据前提实测（真实 MCP 调用，2026-11-09）

环境事实：workspace 新品上市POC-最新版（01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f）已转 **published**
（v1.100.0，2026-11-09 17:50 发布，22 对象 27 关系）——actions_run 的 draft 409 约束已随发布解除。

| 探查 | 结果 | 支撑 |
| --- | --- | --- |
| DishLaunchPlan 裸 base | totalCount="9"（NP001~NP005 历史计划 + NP009 等；此前仅 NP009） | lda-014/015；**注意：无锚点查看问法的合理回答=计划清单表，lda-014 断言已按此措辞** |
| DishLaunchPlan filter plan_id=NP009 | 1 条：青提冰茶/926001/plan_launch_date=2026-11-15/300000 杯/300 家/plan_status=执行中 | lda-015 单对象直查路径可行：**1 次查询即答，无需看板** |
| DishLaunchItem | totalCount="13"（launch_plan_id=NP009） | lda-016 路径一 |
| MaterialDemand | totalCount="20"（net_demand_qty 有回写值） | lda-016 路径二 / lda-017 链路 |
| PurchaseOrder | totalCount="3"（PO-2026-1010-01 在途） | lda-016 路径三 |
| SupplyDemandAllocation | totalCount="9" | lda-017 链路；实测 supply_type 值为 "purchaseorder"（小写连写，与业务文档口径 PURCHASE_IN_TRANSIT 不同——按「如实报告差异」处理，枚举权威口径以元数据+文档出处为准） |
| filter 算子误用 operator 键 | HTTP 42200（与 facts.md 记载吻合：算子必须放 type 键） | 再次验证 facts.md DSL 方言手册准确 |

### 3. pass^3 正式跑批：待人工执行（未跑，不伪造）

按 evals/README.md 协议，正式跑批需「新会话 × 每条 3 次 × 17 条」且被测技能 0.1.14 需先进入宿主技能
加载路径（发版或本地安装）。本轮子代理会话无法开新宿主会话，如实记为待办：

- [ ] lda-014~017（新增 4 条）跑批 3 次/条
- [ ] lda-001~013（既有 13 条）全量回归（改措辞必回归纪律）
- 判定要点：查看类断言「纯 Markdown 表格交付 + 无 deliverables/ 落档 + 不越关系邻居」；
  诊断类断言「跨对象链路 + 看板落档」强度不降。

## 结论与跟进

- 新条款（子图锚定 → 单对象直查 → 纯文本交付）在本域数据上实测可执行（1 次 filter 查询即答 NP009 计划卡）。
- lda-014~017 为草稿（mature: false），待人工逐条复核转正 + pass^3 跑批后转正。
- 规格外发现（未擅动，待立项）：① facts.md 记载 objects_relation_counts 已打通（2026-11-03 傍晚），
  SKILL.md L40 工具表仍写「42200 待核查」——存量不同步；② workspace 已转 published，SKILL.md 数据环境节
  「可能 status=draft」表述可留（实时为准条款覆盖）但 actions_run 409 前提已变化；
  ③ supply_type 实测值与业务文档枚举口径不一致（服务端数据问题，建议挂工单核对）。
