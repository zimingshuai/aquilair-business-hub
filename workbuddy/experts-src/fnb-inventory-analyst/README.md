# 餐饮库存诊断专家（fnb-inventory-analyst）v1.0.0

源自 [aquilair-business-hub](https://github.com/zimingshuai/aquilair-business-hub) 的 WorkBuddy **独立单专家**包：
正文取上游宿主无关 origin（`plugins/business-hub/agents/fnb-inventory-analyst.md`），本包仅补 WorkBuddy 适配层
（displayName / profession / maxTurns / skills）。独立专家直接服务用户，无主理人中转。

## 职责

只读诊断餐饮库存域（MCP 网关 `aquilair-mcp-servers` 的 fnb 本体项目）：仓库风险 P0-P3、
判定依据溯源（规则 → 指标 → 风险记录）、SKU 周转与 ABC 分类、缺货 / 超储 / 呆滞明细；交付随子图伸缩。

| 技能 | 职责 |
| --- | --- |
| `fnb-inventory-analysis` | 餐饮库存域诊断（只读）：风险总览 / 溯源 / SKU / ABC |
| `aquilair-data-delivery` | 数据交付可视化规范：配图铁律 / 复杂度两档落档 |

## 数据服务

MCP 数据网关连接见包根 `.mcp.json`（统一网关 `aquilair-mcp-servers`，OAuth Bearer 鉴权）。
服务部署在公司内网，首次使用需批准 MCP 连接并完成 OAuth 登录；技能首用可跑技能目录下 `scripts/fetch_meta.py` 预取元数据（非必需）。

## 改造背景（v1.0.0 / 2026-11-10）

供应链专家团（aquilair-supply-chain-team）退役：三域（餐饮库存 / 制造调拨 / 新品上市）为互不关联的独立本体项目，
按「一域一独立专家」拆为三个包，砍掉主理人四段中转。本包即其中餐饮库存域专家；旧团队包文件与历史缓存保留备查。
