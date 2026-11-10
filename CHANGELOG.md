# 更新日志（CHANGELOG）

> 维护规则：**每发版一节、倒序排列**；版本号 / 日期 / 要点三要素，日期取版本锚点 commit 的提交时间。
> 每版本内容以 git tag `v<版本>` 为不可变锚点（`git show v<版本>` 可回看全量内容）；
> 发版三条规则（版本号不可变 / 只进不退 / 找回旧做法）见 [README.md 发版规则](README.md#发版规则本仓默认纪律)。
> 自 v0.4.6 起版本漂移由 `tools/check_principles.py` P3 闸门自动拦截（内容变更必 bump，两处清单同步）。
> 本文件变更不触发 P3（检测范围仅 `plugins/`）。

## v0.4.6（2026-11-10）｜tag `v0.4.6` → cdb6112

- 供应链中枢顾问拆分为 `fnb-inventory-analyst`（餐饮库存诊断师）+ `mfg-transfer-planner`（多工厂调拨专员）两独立域 agent，与 `launch-poc-advisor` 三足鼎立（MR !3；配图口径经总监工验收返工对齐子图伸缩——767e6ba）
- 行为口径治理基建入库：`principles.yaml` 单一事实源 + `check_principles.py` 双端闸门 + lint/install 挂接（MR !4）
- **历史瑕疵，如实记录**：MR !4 携带的 data-delivery 冲突条款括号修复（e0fa0b5，经 cdb6112 合入）在本版本号下入库——0.4.6 于 0302c05 bump 后 plugins/ 内容仍有变更未再 bump，出现同版本号双快照窗口。**自 v0.4.6 起规则：内容变更必 bump（两处清单同步）**，由 P3 闸门自动拦截
- tag 锚点说明：按「同版本相关 commit 取后者」锚定 cdb6112（0.4.6 版本号下内容终态入库点），而非 bump commit 0302c05——保证 tag 内容与该版本号最终分发形态一致

## v0.4.5（2026-11-10）｜tag `v0.4.5` → ec4afbb

- skill-router 横切配图口径对齐子图伸缩：路由表 / 复合裁决 / 反合理化表三处补「分析类配图、单对象单边查看纯文本合法」，消除横切层旧「必须配图」残留（WorkBuddy team-lead 6 分钟事故溯源发现的漏网点）
- 两处清单同步 bump 0.4.5

## v0.4.4（2026-11-10）｜tag `v0.4.4` → 7959bc3（MR !2 相关）

- launch 域交付深度改本体子图锚定驱动伸缩：单对象/单边查看纯文本交付合法，跨对象子图诊断保持强制看板（两档不变）；探查循环增子图锚定规划步（元数据关系与基数驱动）
- lda-014~017 用例授权转正（17/17 mature）+ 三项口径实测同步（objects_relation_counts 打通复验 / workspace 实测 published v1.100.0 / supply_type、allocation_status 数据侧写实测值）
- MR !2 内容先合入 main（bdb0c9a），发版两处清单同步 bump 于 7959bc3

## v0.4.3（2026-11-09）｜tag `v0.4.3` → 1d44ff8

- data-delivery 出图通道改脚本渲染优先：模型只写规格 JSON，`render_dashboard.py` 确定性渲染（12 图型，实测毫秒级）；负值与未注册图型 fail-fast 拦截；新增成员回传与主理人不重复出图条款
- fnb/mfg/launch 探查循环补互不依赖查询同消息并发纪律；launch 出图口径同步 + fnb 补 Playbook 叠加引用
- ddl-009 口径修订 + ddl-010 新增并转正，夹具回放回归 19/19 全绿（渲染脚本 v1.1.1）
- 市场清单版本号补同步（1d44ff8）：上笔发版只 bump 插件清单漏了市场层，致 ZCode directory 市场侧仍显示 0.4.2 无更新入口——**tag 锚定两处清单齐备点 1d44ff8**（d1de058 bump 插件清单 + 1d44ff8 补市场清单，取后者）

## v0.4.2（2026-11-05）｜tag `v0.4.2` → c5730b6

- 旧上市保障技能 `launch-readiness-diagnosis` 与配套顾问 `new-arrival-advisor` 移出插件分发（`retired-skills/` 备查），联动路由表 / 评估配置 / 知识标注

## v0.4.1（2026-11-05）｜tag `v0.4.1` → f9c5ffb

- MCP 网关双名收敛为单名 `aquilair-mcp-servers`：`.mcp.json` 单条目、技能 / 文档 / 脚本 / 评估统一改名、lint 兼容旧名过渡

## v0.4.0（2026-11-03）｜tag `v0.4.0` → 03f5e85

- 收录 `launch-dynamic-assurance`（新品上市POC动态保障）：技能 + agent + MCP 条目 + 路由表；旧 `launch-readiness-diagnosis` 标记退役过渡
- 本版本号下陆续同步 launch 技能 poc 0.1.2~0.1.13 演进（storyline 瘦身、agentskills.io 规范对齐、fetch_meta 预取、实测判据同步等 20 余笔，含 P6 总验收修复 b0783aa）

## v0.3.3（2026-10-30）｜tag `v0.3.3` → b42b35f

- 实时为准探查循环改版 + data-delivery 减法改版，双轮回归全绿（72/72 + 18/18）

## v0.3.2（2026-10-29）｜tag `v0.3.2` → ee101ec

- `launch-readiness-diagnosis` 技能随包分发：简单档静态看板落档修订 + facts 平台行为更新（裸 base 查询 422、select 字段名严格校验）

## v0.3.1（2026-10-28）｜tag `v0.3.1` → 7f93365

- data-delivery 出图通道路由化：铁律不变、渲染外置，豆包 / ZCode / WorkBuddy 三宿主各装可视化工具，`viz-templates` 降兜底；`doubao-visualization` 技能包入 `vendors/` 按需分发
- evals 断言扩宿主方言 + 新增 ddl-009
- 版本号下后续入库：launch-readiness-diagnosis 五处接线接入（9387993）等，随 v0.3.2 分发

## v0.3.0（2026-10-26）｜tag `v0.3.0` → 5abe6f4

- 拆分为智能应用中枢（hub 0.3.0）与业务锻造师（forge 0.1.0）双插件：单仓双插件目录迁移，三宿主清单与 marketplace / WorkBuddy 分家，路由表与零件图跨插件引用同步，业务技能文件零内容改动
- 前身：本仓由原单插件仓经 filter-repo 双仓拆分而来（1bd4ffa，市场清单初建 0.3.0）

---

更早历史（v0.2.x 及以前，双仓拆分前）见 `git log` 原始提交记录，不在此展开。
