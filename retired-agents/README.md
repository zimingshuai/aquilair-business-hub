# retired-agents/ —— 退役 agent 人设备查

本目录存放已退役的 agent 人设源文件，仅备查（保留拆分前的完整原文），不再随插件分发、不纳入任何宿主编成。目录先例参照仓根 `retired-skills/`（c5730b6）。

## aquilair-supply-chain-advisor.md（2026-11-10 退役）

原「餐饮供应链库存与多工厂调拨顾问 - 天鹰」，身兼 fnb（餐饮库存）与 mfg（制造调拨）两域，子代理内部需先判域再挂技能，违反「子代理 = 域内全权、单一职责」原则。

按 2026-11-10 定则——三个业务技能（fnb-inventory-analysis / mfg-transfer-allocation / launch-dynamic-assurance）是三个互不关联的独立本体项目，ZCode 与 WorkBuddy 两侧编成同构「一域一 agent」——拆分为两个独立域 agent：

- 餐饮库存域 → `plugins/business-hub/agents/fnb-inventory-analyst.md`
- 制造调拨域 → `plugins/business-hub/agents/mfg-transfer-planner.md`

launch 域 `launch-poc-advisor.md` 不受影响；拆分后三 agent 三足鼎立。注意：本备查文件中的「沙箱 `sandbox` 顶层参数」口径已随 mfg 技能 2026-10-29 改版废除（现为 `branch` 显式参数制），以新 agent 与技能 SKILL.md 为准。
