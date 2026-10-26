# agents/ —— Aquilair 顾问人设与跨宿主接入指南

> 本目录存放**宿主无关的 agent 人设源文件**。`aquilair-supply-chain-advisor.md` 的正文
> 是各宿主通用的系统提示词；frontmatter 遵循 Claude Code / ZCode subagent 规范。
> 把整个仓库交给任何智能体（或其使用者）后，按本文件第三节宿主对照表与第四节字段映射即可自行适配接入。

## 一、资产总览（整个仓库的可移植分层）

| 层 | 位置 | 可移植性 |
| --- | --- | --- |
| 技能本体 | `plugins/*/skills/`（SKILL.md + references + scripts；业务技能在 business-hub、元技能在 skill-forge） | **零适配**——Agent Skills 开放标准（agentskills.io），任何兼容客户端直接用 |
| MCP 连接 | `plugins/business-hub/.mcp.json`（全仓库唯一地址引用） | 半通用——MCP 是行业标准协议，但挂载位置随宿主而定（见下表） |
| Agent 人设 | `agents/*.md`（本目录） | 正文通用，frontmatter 元数据按宿主补齐 |
| 工程资产 | `evals/`、`tools/`、`tests/`、`aquilair-knowledge/`（仓库根） | 供人类开发者与评估流程使用，宿主无需加载 |

## 二、人设与技能的分工（为什么人设这么薄）

- **人设（本目录）**：身份、职责边界、核心原则、输出风格——宿主无关，改一处全局生效。
- **技能（`plugins/*/skills/`）**：各业务域的行为细则（工具用法、铁律、确认卡模板、剧本）——
  人设不重复技能内容，一律按技能名引用。**修改行为细则请改技能，不要在多宿主的人设副本里各改一份**（那是漂移的根源）。

## 三、已验证宿主的接入方式

| 宿主 | 接入方法 | 已验证 |
| --- | --- | --- |
| **ZCode** | **推荐插件**（2026-09-24 实测，拆分后双插件）：「插件市场 → 添加 → 添加插件市场」粘贴本仓库根目录 → 「个人 → aquilair」按需安装 `aquilair-business-hub`（业务 4 技能 + MCP + SessionStart hook 一次装齐）与 `aquilair-skill-forge`（技能工厂元技能，开发者装）；更新走「市场源刷新 → 插件详情更新」。人设拷至 `~/.zcode/agents/`（插件清单不含 agents，subagent 人设需单独拷）。备选：技能拷 `~/.zcode/skills/` + `plugins/business-hub/.mcp.json` 抄 `~/.agents/mcp.json`（新会话生效） | ✅ 2026-09-24 插件闭环（双插件结构待实测） |
| **Claude Code** | 人设拷至 `~/.claude/agents/`（或项目 `.claude/agents/`）；插件方式 `/plugin marketplace add <本仓库>`；技能目录拷 `~/.claude/skills/`；MCP 加进 `claude mcp add` 或项目 `.mcp.json` | ✅ 插件格式即为此设计 |
| **Codex** | 插件市场两条命令（Codex CLI 0.154.0 实测，拆分后双插件）：`codex plugin marketplace add <仓库地址>` → `codex plugin add aquilair-business-hub@aquilair`（业务技能 + MCP + SessionStart hook 全自动装齐；开发者再加装 `aquilair-skill-forge@aquilair`）——0.15x 兼容 Claude Code 市场清单。备选：技能目录拷 `~/.codex/skills/` + MCP 手写 `~/.codex/config.toml`（片段见主 README「MCP 手动配置」节） | ✅ 2026-09-24 验证（双插件结构待实测） |
| **WorkBuddy / CodeBuddy** | 已有适配版（`my-experts` 市场里的 `aquilair-supply-chain-advisor` 专家包）：`.codebuddy-plugin/plugin.json` + `plugins/business-hub/agents/*.md`（frontmatter 加 displayName/profession/maxTurns/skills）+ 业务技能 + avatars。**适配资产已入库本仓库**（`.codebuddy-plugin/` 清单与包内 README、`avatars/` 头像，v1.x 独立版本线；只随 business-hub 业务技能，不含 forge 元技能），WorkBuddy 侧目录是分发副本 | ✅ 运行中（v1.3.0 对齐 hub 0.3.0） |
| **豆包工作伙伴 / 豆包智能体** | 平台无文件导入：新建智能体 → 把 `aquilair-supply-chain-advisor.md` **正文**（frontmatter 以下）粘贴为系统提示词 → 技能按平台「沉淀为技能」机制录入（`aquilair-data-delivery` 源自豆包侧，天然兼容） | 🟡 平台操作（[功能手册](https://aily.feishu.cn)） |
| **企业自建 agent**（Dify / Coze / 自研） | 同上：正文作系统提示词；MCP 端点见 `.mcp.json`（需内网可达）；技能文件可作为知识库/工作流提示词挂载 | 🟡 按平台能力 |

## 四、frontmatter 字段对照（新宿主适配只需补元数据）

人设正文不动，frontmatter 按宿主习惯映射：

| 语义 | Claude Code / ZCode | WorkBuddy / CodeBuddy | 豆包 / 平台表单 |
| --- | --- | --- | --- |
| 标识 | `name` | `name` | 智能体名称 |
| 触发条件 | `description` | `description` | （由平台入口决定，无需触发词） |
| 展示名 | —（标题区自带双语） | `displayName.en/zh` | 名称/头像配置 |
| 职务头衔 | —（正文 Profession 行） | `profession.en/zh` | 简介栏 |
| 工具白名单 | `tools`（**建议省略**=继承全部，可移植） | 平台配置 | 平台插件/工具勾选 |
| 挂载技能 | 技能系统自动发现（靠 description） | `skills: [列表]` | 平台技能挂载 |
| 轮数上限 | — | `maxTurns` | 平台配置 |

## 五、给接收方智能体的自适配指令（可直接粘贴）

> 你收到了 aquilair-skills 仓库。请为本环境接入 Aquilair 供应链顾问：
> 1. 读 `plugins/business-hub/agents/aquilair-supply-chain-advisor.md`，正文即系统提示词；
> 2. 按本环境的 agent 定义机制创建智能体，frontmatter/配置字段按 `agents/README.md` 第四节映射；
> 3. 把 `plugins/business-hub/skills/` 下 4 个业务技能安装到本环境的技能位置（终端用户必装；`plugins/skill-forge/skills/` 3 个元技能供开发者按需；无技能机制则作为系统提示词附件/知识库挂载）；
> 4. 在本环境的 MCP 配置中注册 `plugins/business-hub/.mcp.json` 里的统一数据网关 `aquilair-mcp`（需内网可达）；
> 5. 验证：问「各仓库有没有库存风险？」应触发 fnb 技能；问「工厂缺货情况」应触发 mfg 技能；验证清单见仓库 `evals/`（37 条评估用例全部 mature，其中护栏/红队用例零容忍）。

## 六、可视化交付通道（桌面端形态）

> 数据类交付的可视化通道按宿主**实际使用形态**（桌面 app）选择；规范与模板见
> [skills/aquilair-data-delivery/SKILL.md](../skills/aquilair-data-delivery/SKILL.md) 第五节与
> [skills/aquilair-data-delivery/references/viz-templates.md](../skills/aquilair-data-delivery/references/viz-templates.md)。

| 宿主 | 单图直呈 | 多图/交互看板 | 依据 |
| --- | --- | --- | --- |
| **WorkBuddy/豆包** | `show_widget` 内联图表 | 生成 HTML 看板 + `present_files` 预览 | 宿主原生 |
| **ZCode（桌面）** | SVG/PNG 文件 + 图片内联直呈（2026-09-24 实测 ✅） | 单文件 HTML 看板 + browser-use 新建标签页 | 本仓实测 |
| **Claude 桌面/Cowork** | live artifacts（HTML 写盘即运行） | 同左（多图/交互均宜 artifacts） | 官方文档 |
| **ChatGPT app（Codex）** | 图片内联/图像查看（app 内） | 单文件 HTML 看板（文件引用/附件；canvas 开放度待实测） | 2026-07 起 Codex 并入统一 app |
| **文档宿主（GitLab/GitHub）** | — | Mermaid 代码块（pie 成熟、xychart 已支持） | 平台渲染 |

> PNG 仅留档/嵌入 docx-pptx 场景；对话内交付不默认生成 PNG。

## 七、变更纪律（防多宿主漂移）

1. **单一事实源**：技能与人设只在**本仓库**修改；各宿主的副本是分发产物。
2. 修改 `plugins/*/skills/` 或 `agents/` 后：重打包/同步各宿主（WorkBuddy 目录、GitLab、zip），并按 `evals/README.md` 回归纪律评估。
3. 宿主特有适配（如 WorkBuddy 的 fetch_meta 路径补丁）尽量收敛回源文件（向上搜索等通用写法），实在无法收敛的记录在宿主适配层内，并在此文件登记。
