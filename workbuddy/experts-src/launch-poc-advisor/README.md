# 新品上市POC动态保障专家（launch-poc-advisor）v1.0.0

源自 [aquilair-business-hub](https://github.com/zimingshuai/aquilair-business-hub) 的 WorkBuddy **独立单专家**包：
正文取上游宿主无关 origin（`plugins/business-hub/agents/launch-poc-advisor.md`），本包仅补 WorkBuddy 适配层
（displayName / profession / maxTurns / skills）。独立专家直接服务用户，无主理人中转。

## 职责

围绕一个新品上市计划（POC 项目）的全链问答与诊断（MCP 网关 `aquilair-mcp-servers` 的新品上市POC-最新版本体项目）：
上市计划与预测口径 → 事项与齐套 → 物料缺口 → 供需分配 → 采购订单跟踪 → 上市风险；交付随子图伸缩。

| 技能 | 职责 |
| --- | --- |
| `launch-dynamic-assurance` | POC 上市动态保障主技能：计划与口径 / 齐套诊断 / 物料缺口 / 供需分配 / 采购跟踪 / 风险交付 |
| `aquilair-data-delivery` | 数据交付可视化规范：配图铁律 / 复杂度两档落档 |

## 数据服务

MCP 数据网关连接见包根 `.mcp.json`（统一网关 `aquilair-mcp-servers`，OAuth Bearer 鉴权）。
服务部署在公司内网，首次使用需批准 MCP 连接并完成 OAuth 登录。

## 改造背景（v1.0.0 / 2026-11-10）

供应链专家团（aquilair-supply-chain-team）退役：三域（餐饮库存 / 制造调拨 / 新品上市）为互不关联的独立本体项目，
按「一域一独立专家」拆为三个包，砍掉主理人四段中转。本包即其中新品上市域专家；旧团队包文件与历史缓存保留备查。
