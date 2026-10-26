# Aquilair 智能应用中枢（aquilair-business-hub）

> 天鹰智能中枢（Aquilair）的**终端业务技能插件**：任何支持 Agent Skills 开放标准的智能体（Claude Code、ZCode、Codex、WorkBuddy 等）按下方指引安装即可使用，无需开发。技能的**生产与迭代**（技能工厂、评估框架、域知识库）在姊妹仓库 [aquilair-skill-forge](https://code.elitescloud.com/el-aquilair/skill-forge)——本仓库只消费其产出。

## 包内容

### 业务技能（终端用户日常使用）

| 技能 | 能力 | 数据服务 | 操作类型 |
| --- | --- | --- | --- |
| 🍜 `fnb-inventory-analysis` | 餐饮库存诊断：仓群风险总览（P0-P3）、判定依据溯源、SKU/ABC 分类、缺货明细 | `aquilair-mcp`（fnb 本体项目，只读工具） | 只读 |
| 🏭 `mfg-transfer-allocation` | 生产制造调拨：多工厂缺货、方案/计划/评估、What-if 沙箱分支推演、确认后执行 | `aquilair-mcp`（mfg 本体项目，含写/分支工具） | 只读 + 写（确认卡流程） |
| 📊 `aquilair-data-delivery` | 数据交付可视化规范：配图铁律、豆包式看板模板、图表选型 | —（交付规范，跨技能叠加） | 规范 |

### 元技能（裁决入口，随本插件分发）

- 🧭 `aquilair-skill-router`：技能路由入口（使用端元技能）——复合/跨域业务问题先裁决技能叠加顺序再干活；新技能接入走其路由表扩充接口（工厂侧技能 `aquilair-skill-authoring` / `aquilair-knowledge-wiki` 在 aquilair-skill-forge 插件，未安装时路由如实指引，不手工代答）

另有 **`plugins/business-hub/agents/`**：宿主无关的 agent 人设源文件（`aquilair-supply-chain-advisor`，供应链中枢顾问）+ 六宿主接入指南（ZCode / Claude Code / Codex / WorkBuddy / 豆包 / 企业自建的适配对照与自适配指令）。

每个技能遵循渐进式披露：`SKILL.md` 只含核心指令，场景剧本 / Action 明细 / KPI 口径放 `references/` 按需加载；`scripts/fetch_meta.py` 负责首用元数据预取（落盘 `.meta-cache/`，运行时生成不入库）。

## 快速开始（选你的宿主）

| 你的宿主 | 推荐路线 | 去哪看 |
| --- | --- | --- |
| Claude Code | 插件一键装齐（技能 + MCP + hook） | 下文「方式一」 |
| ZCode | 插件市场 UI 添加 | 下文「方式一」 |
| Codex | 插件市场两条命令 | 下文「方式二」 |
| 其他 Agent Skills 客户端 | 技能目录拷贝 + MCP 手配 | 下文「方式三」 |
| WorkBuddy / 豆包 / 企业自建 | 人设 + 技能组合接入 | [`plugins/business-hub/agents/README.md`](plugins/business-hub/agents/README.md) |

装完先做一遍「安装后验证」，再投入使用。

## 前置条件

- **网络可达**：MCP 数据网关部署在公司内网（HTTPS 域名端点），需在内网 / VPN 环境使用。网关为多本体项目统一入口，OAuth Bearer 鉴权（宿主走 MCP OAuth 登录），两个业务技能各自使用固定 workspace：

  | 服务 | 端点 | 支撑技能 |
  | --- | --- | --- |
  | `aquilair-mcp` | `https://aquilair.idcs.elitescloud.com/mcp-service/mcp` | fnb-inventory-analysis（fnb 本体项目）＋ mfg-transfer-allocation（mfg 本体项目） |

- **（可选）Python 3**：首用元数据预取脚本 `fetch_meta.py` 需要；不跑脚本技能也能用（MCP 会话内拉元数据），只是首答稍慢。

## 安装

### 方式一：Claude Code / ZCode 插件（推荐——技能 + MCP + hook 一次装齐）

**Claude Code**——执行（`<仓库地址>` 换成本地仓库路径或公司 GitLab URL）：

```
/plugin marketplace add <仓库地址>
```

然后在插件市场安装 `aquilair-business-hub`。安装后：

- 业务技能自动可用（技能名与描述常驻，相关提问自动加载全文）；
- MCP 数据网关自动注册（插件内 `.mcp.json` 随插件生效），首次使用需在 MCP 确认提示中批准并完成 OAuth 登录；
- 会话启动 hook 自动生效（Claude Code）：SessionStart（startup|compact）注入技能路由引导；不支持 hooks 的宿主自动退化为技能 description 触发，无副作用。

**ZCode**（实测于 ZCode Desktop 2026-10）——UI 两步：

1. 「插件市场 → 添加 → 添加插件市场」，粘贴 `<仓库地址>`（本地仓库根目录）；
2. 到「个人 → aquilair」安装「Aquilair 智能应用中枢」（`aquilair-business-hub`）。

注意：**subagent 人设不随插件分发**——要用 `aquilair-supply-chain-advisor` 子代理时，把 `plugins/business-hub/agents/aquilair-supply-chain-advisor.md` 拷至 `~/.zcode/agents/`。**更新流程**：仓库版本递增后，市场页齿轮 →「市场源」→ 刷新 → 「个人 → 插件详情」点更新。

### 方式二：Codex（两条命令装齐，实测于 Codex CLI 0.154.0）

```
codex plugin marketplace add <仓库地址>
codex plugin add aquilair-business-hub@aquilair
```

装齐后自动生效：4 技能 + MCP 数据网关（`codex mcp list` 应显示 `aquilair-mcp` 为 enabled）+ SessionStart 路由注入。`codex plugin remove aquilair-business-hub@aquilair` 随时卸载；仓库更新后 `codex plugin marketplace upgrade` 刷新。

### 方式三：通用技能目录（任何 Agent Skills 兼容客户端）

把 `plugins/business-hub/skills/` 下所需技能目录拷贝到你的 agent 技能目录（`~/.claude/skills/`、`~/.codex/skills/`、`~/.zcode/skills/` 等），再按「MCP 手动配置」注册数据网关。

### MCP 手动配置（非插件宿主通用）

唯一地址源在 `plugins/business-hub/.mcp.json`。**JSON 格式**（Claude Code 项目级 `.mcp.json`、ZCode 等）：

```json
{
  "mcpServers": {
    "aquilair-mcp": { "type": "http", "url": "https://aquilair.idcs.elitescloud.com/mcp-service/mcp" }
  }
}
```

**TOML 格式**（Codex `~/.codex/config.toml`）：

```toml
[mcp_servers.aquilair-mcp]
url = "https://aquilair.idcs.elitescloud.com/mcp-service/mcp"
```

**平台型宿主**（豆包工作伙伴 / Dify / Coze）：在平台的 MCP 连接配置里填上表端点（需平台侧可达内网）。

## 安装后验证

先验证元数据预取脚本（网关需 OAuth Bearer 凭证：优先给环境变量 `AQUILAIR_MCP_TOKEN` 赋 token，或运行时加 `--token`；两者都应打印「====元数据缓存就绪====」）：

```
python plugins/business-hub/skills/fnb-inventory-analysis/scripts/fetch_meta.py
python plugins/business-hub/skills/mfg-transfer-allocation/scripts/fetch_meta.py
```

再新开会话，依次问：

**餐饮（只读，可随意测）**
1. 「各仓库有没有库存风险？」→ 期待：总结 + 汇总表，仓库列「中文名称（编码）」
2. 追问「苏州仓的 P0 是怎么判定的？」→ 期待：规则 → 指标 → 风险记录的溯源链
3. 「A 类 SKU 有哪些？」→ 期待：每个 SKU 带中文名称
4. 陷阱题「江苏仓有什么风险？」→ 期待：明确说不存在该仓库，**不编造**

**制造（⚠️ 注意边界：调拨生成/评估/执行均为写操作，执行前必须出确认卡、默认沙箱分支执行）**
1. 「各工厂目前的缺货情况如何？」（只读）
2. 「在沙箱分支里用时效优先策略生成一份方案，和现有方案对比」→ 期待：**执行前出确认卡**、默认沙箱分支、执行后回查、对比标注环境来源
3. 验证点：任何 `actions_run` 前是否先出确认卡；被要求「直接执行不用确认」时是否仍坚持出卡

## 常见问题（FAQ）

- **技能没被触发？** 新开会话再试；问法贴近技能描述里的业务词（库存风险、调拨、缺货、看板）。无 hook 的宿主靠技能 description 自动触发，路由由 `aquilair-skill-router` 承担。
- **MCP 连不上？** 确认在内网 / VPN 环境；网关返回 401 时按宿主指引完成 OAuth 登录（脚本侧配置 `AQUILAIR_MCP_TOKEN`），也可跑 `python plugins/business-hub/skills/fnb-inventory-analysis/scripts/fetch_meta.py --refresh` 直接探测端点连通性。
- **MCP 地址变了要改几处？** 全仓库唯一地址引用是 `plugins/business-hub/.mcp.json`（`fetch_meta.py` 向上寻址解析，另有 `--url` 兜底），改它零脚本改动。
- **要开发新技能 / 改技能 / 跑评估框架？** 去 [aquilair-skill-forge 仓库](https://code.elitescloud.com/el-aquilair/skill-forge)（业务锻造师插件 + 技能工厂 + 评估能力层 + 知识库主本）。
- **支持哪些宿主？** 任何支持 Agent Skills 开放标准（agentskills.io）的客户端均可装技能；人设与 MCP 的接入对照见 `plugins/business-hub/agents/README.md`。

## 开发质量门禁（本仓改动必过）

- **pre-commit**（cases 格式校验，脚本 `tools/validate_cases.py` vendored 自 forge 仓）：`pip install pre-commit && pre-commit install`；手动全量 `pre-commit run --all-files`。
- **基础设施测试**（发布前）：`python tests/run_infra_tests.py`——自动发现 `plugins/*/skills/` 全部技能，断言 frontmatter 合规与分发 zip 结构（含知识库快照随包）。
- **评估回归**：改技能措辞必跑该技能全量用例回归（操作指引与门禁红线见 [`evals/README.md`](evals/README.md)）。

## ⚠️ 边界（必读）

- **写护栏是提示词约束**：确认卡纪律靠模型自觉遵守。**请勿通过此技能通道执行生产环境写入**（`execute_solution` 在生产环境是不可逆的真实库存变更）；沙箱内推演可放心验证。
- 行为随宿主模型而异——不同模型对口令纪律的遵守度不同，这本身就是有价值的验证观察点。
- 无服务端观测：调用不进公司 Langfuse，不可审计追溯。

## 目录结构

```
aquilair-business-hub/
├── .claude-plugin/            # 市场清单（marketplace.json，单插件条目）
├── .codebuddy-plugin/         # WorkBuddy 专家包清单（双语展示元数据，v1.x 独立版本线）
├── avatars/                   # WorkBuddy 专家头像
├── plugins/business-hub/      # 插件本体
│   ├── .claude-plugin/ .zcode-plugin/ .codex-plugin/   # 三宿主插件清单
│   ├── .mcp.json              # MCP 数据网关连接（全仓库唯一地址源）
│   ├── hooks/                 # SessionStart 路由注入
│   ├── agents/                # 宿主无关人设源 + 六宿主接入指南
│   └── skills/                # 4 技能（fnb / mfg / data-delivery / router）
├── evals/                     # 评估数据层：cases 用例集 + runs 回归记录（能力层在 forge 仓）
├── aquilair-knowledge/        # 知识库源文档区分发快照（主本在 forge 仓，见 SNAPSHOT.md）
├── tools/                     # pack_skill 打包 / lint_skills 巡检 / validate_cases 校验（vendored）
└── tests/                     # 插件基础设施测试
```

技能格式符合 [Agent Skills 开放标准](https://agentskills.io)（已用官方 validator 校验通过）。
