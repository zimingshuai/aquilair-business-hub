# 极米供需平衡专家（xgimi-supply-demand-balancer）v1.0.0

源自 [aquilair-business-hub](https://github.com/zimingshuai/aquilair-business-hub) 的 WorkBuddy **独立单专家**包：
正文取上游宿主无关 origin（`plugins/business-hub/agents/xgimi-supply-demand-balancer.md`），本包仅补 WorkBuddy 适配层
（displayName / profession / maxTurns / skills）。独立专家直接服务用户，无主理人中转。

## 职责

极米 BOM 升级供需平衡域（MCP 网关 `aquilair-mcp-servers` 的极米POC-NEW 本体项目，只读 + 确认卡受控执行）：
点检差异 → 影响反查 → 需求展开 → 供需分配 → 替代填补 → 风险 → 策略 → 方案 → 采购计划九环节全链，
④分配后默认分叉 2×2 四世界沙箱推演（替代 × 采购两开关），对比后受控落地。

| 技能 | 职责 |
| --- | --- |
| `xgimi-sdb` | 极米 BOM 升级供需平衡：全链测算 / 四世界推演 / 受控执行（交付按域内 `references/delivery.md` 五段式，自带出图模板，**不挂 `aquilair-data-delivery`**——域内配图口径与 hub 横切基线不同，已挂账待统一） |

## 数据服务

MCP 数据网关连接见包根 `.mcp.json`（统一网关 `aquilair-mcp-servers`，OAuth Bearer 鉴权）。
服务部署在公司内网，首次使用需批准 MCP 连接并完成 OAuth 登录。动作执行走 fire HTTP 直调
（技能目录 `scripts/fire_action.py`，执行账号一次配置；MCP `actions_run` 在本域不可用）。

## 建包背景（v1.0.0 / 2026-11-12）

极米供需平衡域随 xgimi-sdb 技能并入 aquilair-business-hub 0.5.0（以 0.3.9 全量 zip 为基底），
按「一域一独立专家」同日建本包成为第四位域专家；旧独立插件 `xgimi-supply-demand-balance`
（0.3.12 瘦身线）同日废弃删除。头像暂复用 mfg 头像占位，待设计专属头像后替换。
