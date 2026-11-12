# 更新日志（CHANGELOG）

> 维护规则：**每发版一节、倒序排列**；版本号 / 日期 / 要点三要素，日期取版本锚点 commit 的提交时间。
> 每版本内容以 git tag `v<版本>` 为不可变锚点（`git show v<版本>` 可回看全量内容）；
> 发版三条规则（版本号不可变 / 只进不退 / 找回旧做法）见 [README.md 发版规则](README.md#发版规则本仓默认纪律)。
> 自 v0.4.6 起版本漂移由 `tools/check_principles.py` P3 闸门自动拦截（内容变更必 bump，两处清单同步）。
> 本文件变更不触发 P3（检测范围仅 `plugins/`）。

## v0.5.1（2026-11-12）｜tag `v0.5.1` → 出图策略对比期回切

- **出图策略回退一个版本供对比**（用户指令）：data-delivery 横切规范 + 三 agent 配图口径行 + skill-router 三处 + launch SKILL 交付段 + principles.yaml delivery-shape 锚点，整体自 V8 基线（形态服从问题/图比文字更清楚才配图）回切至 v0.4.6 基线（**交付随子图伸缩：单对象/单边查看纯文本合法，跨对象子图分析类必配图表看板**，两档形态与脚本渲染通道不变）
- **V8 基线备份**：文件 `~/Downloads/data-delivery_SKILL_V8基线_v0.4.8_备份.md` + tag `v0.4.8`（不可变锚点）；对比期 V8 措辞不入 principles 禁词（保护切换自由）
- 对比方法：`git diff v0.4.8 v0.5.1 -- plugins/business-hub/skills/aquilair-data-delivery/` 看规范差异；宿主实测装 0.5.1 体验子图伸缩基线，切回 V8 = revert 本节回切 + bump
- xgimi 域配图口径豁免不受影响（不在 delivery-shape 影响面，挂账待统一）

## v0.5.0（2026-11-12）｜极米供需平衡域并入（新业务域）

- **新技能 `xgimi-sdb`**：极米（XGIMI）BOM 升级供需平衡操作台（受控执行型）——点检→影响→展开→分配→替代→风险→策略→方案→采购计划全链测算＋2×2 多沙箱推演对比；含 knowledge（FACT-CARDS/STATUS/sources）、references 六件、scripts 五件（fire_action/run_plan 等）。**以 xgimi-sdb 0.3.9 全量 zip 包为基底并入**（用户裁决 2026-11-12：以 zip 为准，0.3.10~0.3.12 瘦身线不采，独立插件 `xgimi-supply-demand-balance` 形态终结、本机缓存删除）
- **第四域专家（同日）**：origin 人设 `agents/xgimi-supply-demand-balancer.md`（极米供需平衡师，受控执行型样板重铸）＋ WorkBuddy 独立专家包 `workbuddy/experts-src/xgimi-supply-demand-balancer/` v1.0.0（龚衡平，四件套齐，头像暂占位复用 mfg 待设计替换）；装配脚本 `install_aquilair_team.py` 加第四包＋xgimi 口径闸门豁免（PRINCIPLES_GATED_PKGS 分离，与 hub 仓 surfaces 不登记对称）；本机真装配全绿（四包校验通过、AGENT_SYNC 逐字一致、旧团队包 marketplace 残留登记顺手摘净）；hub README/agents README/workbuddy README 同步四域四专家
- **接线适配仅 4 处**（其余内容零改动）：SKILL.md 两处 MCP 服务名 `aquilair-mcp` → `aquilair-mcp-servers`（旧名 2026-11-05 停用）；knowledge 位置说明「插件根目录」→「技能目录内」；FC-25 备用通道卡改记并入后新事实（与各域共用同一网关连接，独立备用通道不复存在）
- **evals 资产抢救入库**：`evals/xgimi-sdb/cases.yaml`（16 条草稿 mature: false，锚定 0.3.9 形态）＋ 11 份实测 runs（2026-10-26~11-02，自旧独立插件 0.3.12 缓存迁出）＋ demo-case/demo-script 两知识源（xgimi-006 勘误对照用例的判定背景）；技能内 evals 双件（evals.json 16 条 + trigger-queries.json 正 6 负 5）按 agentskills.io 出厂标准补齐；evals/README 目录树与套件状态同步
- **接线五处**：README 技能表＋workspace 表加行；skill-router 路由表加行（特征词「极米/XGIMI/X20/X30 BOM 升级」与 launch 域「供需分配」区分）；plugin.json＋marketplace.json description 加域、version bump 0.5.0（两处同步）
- **已知口径差异挂账**：xgimi 0.3.9 交付口径为「凡呈现查询数据必可视化」（域内 delivery.md 五段式），与 V8 横切基线「图比文字更清楚才配图」不同——路由表已声明 xgimi 行「不恒叠加 aquilair-data-delivery」如实隔离，统一裁决留待后续
- 后续项：技能内 evals 双件（evals.json + trigger-queries.json）待补齐；16 条用例本仓 pass^3 回归转正前不视为 mature

## v0.4.8（2026-11-10）｜tag `v0.4.8` → facts 实测补录收口

- **facts.md 补三条 2026-11-10 WorkBuddy 实测发现**（99aa5b3）：Warehouse 无 wh_type（42201）、max_purchase_date 第 4 周非法日期（RULE_F8D3E28432C04B4B 计算异常）、relation_counts 首调偶发超时重试即通
- 流程备注：该补充在 v0.4.7 打 tag 后追加，触发 P3 闸门拦截（内容变更未 bump）——按「只进不退」规则 bump 0.4.8 收口而非重打 tag；v0.4.7 的 facts.md 不含上述三条

## v0.4.7（2026-11-10）｜tag `v0.4.7` → feat/v8-merge（MR：launch 域 V8 大吸收）

- **launch 域大吸收**：同事包 `aquilair-launch-poc-v2`（V8 rev248 文档基线的 fork 重写版）融合进仓，经用户四项裁决：① 网页兜底（MCP 不可用读已登录网页）**不吸收**——保持「不可达如实报告」纪律，该条款删除；② data-delivery 横切层换其基线（不强制配图 / 图比文字更清楚才配图 / 强制结论可信·口径清楚·数值一致·来源可追）并融合我方子图判据（跨对象/多实体联动分析图更清楚）；③ launch-assurance-actions 吸收后 WorkBuddy 启航专家挂载（WorkBuddy 侧另行处理）；④ 一步到位一个 MR
- **读写分离**：`launch-dynamic-assurance` 0.4.0（问答，以同事 0.3.0 为基线重写）+ `launch-assurance-actions` 0.2.2（新技能，动作受控执行：创建/修改计划、生成预测与物料需求、重算齐套、确认下发采购计划、模拟下发、新建模拟根计划；确认卡融合为「环境/实例/动作链/参数/影响/不可逆性 + 执行前快照」）
- **references 改名重写**：storyline-playbook / business-semantics / mrp-playbook / launch-assurance 四件以同事版为基线替换并回灌我方实测（supply_type 写值映射 purchaseorder/batchinventory 与 ALLOCATED 进 business-semantics「决策枚举」表与 mrp「有效供应与状态处理」节）；facts.md 我方版为基线增量吸收（类型坑表行 / 事项与齐套两清单口径）；旧三件（domain-model / material-purchase / readiness-playbook）移 `retired-skills/launch-dynamic-assurance-refs/` 备查
- **治理资产保留**（语义在场）：子图锚定探查循环（深度=元数据关系与基数驱动，禁动词枚举）融入其「回答流程」；principles 四条口径锚点更新（delivery-shape 换「图比文字更清楚 / 形态服从问题」新短语，stale_variants 保留全部历史禁词并追加本次变体，surfaces 加 launch SKILL 与 actions SKILL）；facts.md 实测资产零丢失（写值映射 / relation_counts 语法 / System 检查日 / entity_ 通道不稳 / DSL 方言）；save_meta.py 缓存机制保留；lda-014~017 伸缩行为断言不弱化
- **人设与路由**：launch-poc-advisor 吸收「取证者与解释者」定位与核心能力五条（首轮采购方案三态表述），挂载技能表 +launch-assurance-actions，新增触发词（上市事项进度/采购计划三态/模拟根计划）；fnb/mfg 配图条款对齐新横切基线；skill-router 路由表加 actions 行 + 复合裁决补「问答与动作分离」
- **evals**：`evals/launch-dynamic-assurance/cases.yaml` 扩至 35 条（lda-001~013 按 V8 基线口径跟随并逐条注明；lda-014~017 断言不动；lda-018~035 为同事 21 条用例中问答类 18 条转入，mature: false 草稿待复核）；新建 `evals/launch-assurance-actions/cases.yaml`（lax-001~003 动作类，草稿）；技能内 evals 三件同步（actions 补齐 evals.json + trigger-queries.json 出厂双件）
- WorkBuddy 侧（workbuddy/ 目录）本版本不动——三人设镜像与新技能挂载由总监工后续工作令处理

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
