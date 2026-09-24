# 天鹰·供应链中枢（Aquilair Supply Chain Advisor）v1.1.1

埃林哲 Aquilair（天鹰智能中枢）agent 中枢顾问——专注餐饮供应链库存与多工厂物料调拨，
交付库存诊断报告、缺货响应方案、调拨优化方案与沙盘推演结论，支撑供应链运营决策。

> v1.1.1 变更（2026-09-24）：同步上游仓库 `aquilair-skills` v0.1.2——data-delivery 泛化改版
> （交付场景三通道分流 + 宿主能力卡 + `viz-templates.md` 模板库，新增色盲友好/零基线/克制装饰三条图表规范）、
> `fetch_meta.py` 支持 `.mcp.json` 与无点 `mcp.json` 双文件名（`~/.workbuddy/mcp.json` 直接受益）。
>
> v1.1.0 变更：技能由 3 个补齐为**全量 6 个**（业务 3 + 元技能 3），
> 技能正文与顾问人设改用上游仓库 `aquilair-skills` 的宿主无关版正文（单一事实源），
> 仅保留 WorkBuddy 特有的展示层字段（displayName / profession / maxTurns / skills 挂载列表）。

## 类型

Agent 型（单个 AI 专家）｜行业分类：12-IndustryConsultant 行业顾问

## 功能

| 职责 | 说明 | 数据环境 |
| --- | --- | --- |
| 库存健康诊断 | 仓群风险总览（P0-P3）、SKU 周转、ABC 分类、缺货明细、判定依据溯源 | `data-service-fnb`（只读） |
| 缺货响应处理 | 接收工厂缺货反馈，联动库存数据匹配可调出物料，给出初步响应方案 | 跨域联动 |
| 调拨方案生成 | 多工厂物料调拨方案：调拨路径、数量、时效预期 + 方案评估 | `data-service-mfg-sandbox` |
| 沙箱推演验证 | What-if 模拟推演，评估执行风险与预期效果，确认后才在生产执行 | `data-service-mfg-sandbox` |

**核心原则**：数据真实（禁止重算/重判/估算）、不编造、不确定先确认、隐私不泄露、交付完整、不发半成品、多步骤同步进展。
数据类交付默认强制配可视化看板（详见技能 `aquilair-data-delivery`）。

## 绑定技能（6 个）

### 业务技能（终端用户日常使用）

| 技能 | 作用 |
| --- | --- |
| `fnb-inventory-analysis` | 餐饮库存诊断：工具清单、铁律、filter 语法、L0-L2 下钻剧本 |
| `mfg-transfer-allocation` | 制造调拨：双环境、8 个 Action、确认卡流程、KPI 口径 |
| `aquilair-data-delivery` | 数据交付可视化规范（Playbook）：强制配图、看板结构、图表选型、自检规则 |

### 元技能（开发侧，终端业务问答不经过它们）

| 技能 | 作用 |
| --- | --- |
| `aquilair-skill-router` | 路由入口：复合/跨域问题先裁决技能叠加顺序（诊断 → 行动 → 横切）再干活 |
| `aquilair-skill-authoring` | 工厂主技能：新业务域经六步流水线产出业务技能并评估迭代 |
| `aquilair-eval-diagnostics` | 评估失败自诊断：读报告与轨迹，按四类归因给带证据的反哺建议 |

## 使用示例

- 各仓库目前有哪些库存风险？给我一份带看板的诊断报告
- 上海工厂反馈缺货，帮我匹配可调出物料并生成调拨方案
- 在沙箱里用时效优先策略重新生成方案，和现有方案对比

## 宿主适配说明（WorkBuddy）

- 本环境**无 hooks 机制**，上游仓库的 SessionStart 路由注入不生效，
  路由退化为技能 description 自动触发；复合问题由 `aquilair-skill-router` 承担裁决。
- 配图通道按宿主能力等价映射：内联单图走 `show_widget`，多图/交互走 HTML 看板 + `present_files`，
  留档再出 PNG 文件（见 `aquilair-data-delivery` 第五章）。
- 元数据预取脚本改用上游通用版（向上搜索 `.mcp.json`），无需宿主特化路径补丁。

## 前置条件

两个数据服务部署在公司内网，需在能访问下列端点的环境（内网 / VPN）下使用：

```
data-service-fnb           https://aquilair-mcp0.idcs.elitescloud.com/mcp
data-service-mfg-sandbox   https://aquilair-mcp1.idcs.elitescloud.com/mcp
```

宿主环境需注册这两个 MCP 服务（本包的 `.mcp.json` 为标准格式，供 `fetch_meta.py` 解析服务地址）。

首次使用建议先验证元数据预取（两个都应打印「====元数据缓存就绪====」）：

```bash
python skills/fnb-inventory-analysis/scripts/fetch_meta.py
python skills/mfg-transfer-allocation/scripts/fetch_meta.py
```

## ⚠️ 边界

- **写护栏是提示词约束**：确认卡纪律靠模型自觉遵守。**请勿通过本通道执行生产环境写入**
  （`execute_solution` 在生产环境是不可逆的真实库存变更）；沙箱内推演可放心验证。
- 本专家处理的是业务问答；编写库存/调拨相关脚本、系统、报表等**开发类请求**按普通开发任务处理。

## 头像

头像位于 `avatars/expert.png`（512×512，PNG）。如需替换，要求：PNG/JPG、512×512 px、≤500KB。

## 安装位置

- 市场源：`C:\Users\zishuai\.workbuddy\plugins\marketplaces\my-experts\plugins\aquilair-supply-chain-advisor\`
- 安装缓存：`C:\Users\zishuai\.workbuddy\plugins\cache\my-experts\aquilair-supply-chain-advisor\1.1.0\`

上游仓库副本：`C:\Users\zishuai\WorkBuddy\2026-09-24-13-23-29\aquilair-skills\`
（更新技能正文时改上游仓库，再同步到上述两处，避免多份副本漂移。）
