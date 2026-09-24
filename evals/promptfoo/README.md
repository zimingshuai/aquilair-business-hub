# promptfoo（L3 自动化评估）

> 用 promptfoo 把 `cases.yaml` 用例转成机器判定：确定性断言 + 轨迹顺序断言 + llm-rubric，失败退出码非零，可直接作发布门禁。技术路线 2026-09-21 POC 验证通过，2026-09-22 真实样本回放与 rubric 校准达标，CI 接线已改道 pre-commit 本地门禁落地（见文末落地清单）。

## 快速上手

**环境准备**（本目录内，首次）：

```bash
npm ci          # 安装本地 promptfoo 0.123.1（node_modules 不入库）
```

rubric 评审（`promptfooconfig.rubric.yaml` / `replay-rubric` / `gate` / calibration 相关）还需火山方舟 key，从环境变量读，仓库不落密钥：`ARK_API_KEY`（Windows CMD：`setx ARK_API_KEY "<你的key>"`，新开终端生效）。

**按场景选命令**（本目录内，均已实测）：

| 场景 | 命令 |
| --- | --- |
| 冒烟：断言引擎与退出码是否正常 | `npx promptfoo eval -c promptfooconfig.smoke.yaml --no-cache` |
| 用例集变更后重新转出 | `python convert_cases.py` |
| 回放校准·餐饮 | `npx promptfoo eval -c promptfooconfig.replay.yaml -c tests_fnb-inventory-analysis.yaml --no-cache` |
| 回放校准·制造 | `npx promptfoo eval -c promptfooconfig.replay.yaml -c tests_mfg-transfer-allocation.yaml --no-cache` |
| 回放校准·含 rubric 评审（用例集含 llm-rubric 时用这个） | `npx promptfoo eval -c promptfooconfig.replay-rubric.yaml -c tests_mfg-transfer-allocation.yaml --no-cache`（tests 文件可换 fnb / ddl） |
| 轨迹断言自检（预期 1 PASS + 1 FAIL、退出码 100） | `npx promptfoo eval -c promptfooconfig.trajectory.yaml --no-cache` |

其余配置（`replay-real` 真实样本回放 / `rubric` 评审 / `gate` 门禁 / `calibration` 校准对拍）同模式运行：`npx promptfoo eval -c <配置名>.yaml --no-cache`；用途见下表与「已验证结论」。

## 已验证的三项结论

| # | 验证项 | 结果 | 证据 |
| --- | --- | --- | --- |
| 1 | 安装与断言引擎、CI 门禁前提 | ✅ | promptfoo 0.123.1（本地 node_modules，未装全局）；echo provider 冒烟：contains-any 命中 PASS、未命中 FAIL，**失败退出码 100** |
| 2 | cases.yaml 断言可转换且与合规输出形态匹配 | ✅ | 转换器转出 24 条（fnb 14 + mfg 10，trigger-negative 5 条人工判定不适用机器断言，正确跳过）；样本回放：fnb 28/28、mfg 20/20 全 PASS |
| 3 | 「确认卡在写操作前」可机器判定并作门禁 | ✅ | python 自定义断言（`asserts/confirm_card_before_write.py`）：合规样本 PASS、违规样本 FAIL 且 reason 精确定位（「未见确认卡；run_supply_demand_allocation 发生在确认前」），端到端退出码 100 |
| 4 | llm-rubric 与人审校准对拍（judge 可信度） | ✅ | **30/30（100%）**：正样本（ddl 成熟轮真实 transcript）24/24 零误杀、负样本（历史失败现象复刻）6/6 零漏判、零解析失败（`gen_calibration.py` + `promptfooconfig.calibration.yaml`，2026-09-22） |
| 5 | 断言补全（37 条全机器判定） | ✅ | 7 条 `assert: []` 用例补齐（4 轨迹断言 `asserts/no_forbidden_tools.py` + 3 条 rubric）；gate 验证 7 PASS + 负样本拦截 FAIL、退出码 100（`promptfooconfig.gate.yaml`） |
| 6 | 含 rubric 的全量回放回归（replay-rubric 组合） | ✅ | 2026-09-24 可视化泛化改造回归：fnb 32/32、mfg 26/26（含 mfg-007 rubric 方舟评审）、ddl-005/007 rubric 评审 PASS；纯 `replay.yaml` 无评审模型，含 llm-rubric 的回放一律用 `replay-rubric` |

评审模型（llm-rubric）：**已验证（2026-09-22，火山方舟 OpenAI 兼容端点）**——`promptfooconfig.rubric.yaml` 内联双向冒烟用例（合规判 PASS / 代查代答判 FAIL，评审理由精确到违规点），评审模型 `doubao-seed-2-1-pro-260915`。key 从环境变量 `ARK_API_KEY` 读（`apiKeyEnvar`，仓库不落密钥）。**0.123.x 配置字段踩坑**：`apiKeyEnvar` 与 `apiBaseUrl` 都是 provider `config` 的**顶层字段**（写成 `config.api.baseURL` 嵌套会静默回落到 api.openai.com 超时）；方舟模型名用连字符（`doubao-seed-1-6`，点号 404），可用模型以 `GET /api/v3/models` 为准。**门禁资格**：2026-09-22 已完成 30/30 校准对拍（见落地清单 2），rubric 可当门禁；**换评审模型后资格作废**，须按下节重跑对拍。

### 换评审模型（发版交接必读）

评审模型名**单一事实源**：`set_rubric_model.py` 的 `DEFAULT_MODEL`（全仓唯一硬编码点）。覆盖优先级：命令行参数 > 环境变量 `ARK_RUBRIC_MODEL` > `DEFAULT_MODEL`。

> 为什么不用配置内环境变量引用：promptfoo 0.123 不解析 provider id 中的 `${VAR}`（2026-09-24 实测：字面量被原样发给 API，方舟返回 404），故由脚本同步各配置文件中的模型名。

```bash
python set_rubric_model.py <新模型名>     # 或 export ARK_RUBRIC_MODEL=<新模型名> 后无参运行
```

脚本自动完成：① 同步 3 个手维护配置（`rubric` / `replay-rubric` / `gate`）的 provider id（幂等，与现值一致不写文件）；② 经 `gen_calibration.py` 重新生成 `promptfooconfig.calibration.yaml`（**生成物不手改**，命令行模型名经 `ARK_RUBRIC_MODEL` 传导给生成器）；③ 打印后续必做步骤。模型名规范：方舟模型名用连字符（点号 404），可用模型以 `GET /api/v3/models`（带 `ARK_API_KEY`）为准；若换其他 OpenAI 兼容服务商，各配置 `defaultTest.options.provider.config` 段的 `apiBaseUrl` / `apiKeyEnvar` 需一并手改。

换模型后两步必做（脚本运行结束也会提示）：

1. **冒烟**：`npx promptfoo eval -c promptfooconfig.rubric.yaml --no-cache`——预期 2 条内嵌用例方向正确（合规 PASS / 违规 FAIL）且退出码 0；404 model not found 即模型名/端点没改对。
2. **重新校准对拍**：30/30 对拍结论**只对当前模型有效**——换模型 = 换 judge，须重跑 `npx promptfoo eval -c promptfooconfig.calibration.yaml --no-cache` 与人审结论对齐（正负样本一致率达标）后，rubric 才能继续当门禁。

## 组件与用法

```
evals/promptfoo/
├── convert_cases.py             # cases.yaml -> promptfoo config 转换器（id/description 保留原编号）
├── replay_provider.py           # 文件回放 provider：按 case_id 回放样本（不调 LLM/MCP）
├── asserts/
│   └── confirm_card_before_write.py   # 轨迹断言：确认卡在写操作前（create_sandbox 按技能规定豁免）
├── samples/replay-samples.json  # 回放样本（POC 为形态代表；L3 落地后由真实 transcript 落盘）
├── promptfooconfig.smoke.yaml       # 冒烟：echo provider 验断言引擎与退出码
├── promptfooconfig.replay.yaml      # 回放校准：确定性断言 × 合规样本（形态代表）
├── promptfooconfig.replay-real.yaml # 真实样本回放校准：B 侧 transcript（2026-09-22 ddl 首批 7/7）
├── promptfooconfig.replay-rubric.yaml # 回放 + 方舟 rubric 评审组合（用例集含 llm-rubric 的回放回归用这个）
├── promptfooconfig.rubric.yaml      # llm-rubric 评审（火山方舟 doubao-seed，见上节；换评审模型的冒烟入口）
├── set_rubric_model.py              # 一键切换评审模型（DEFAULT_MODEL 单一事实源，见「换评审模型」节）
├── promptfooconfig.trajectory.yaml  # 轨迹断言：含故意违规样本，验证门禁捕获
├── tests_<技能名>.yaml           # 转换器产物（独立 config 形态，经 -c 合并使用）
└── package.json / node_modules  # promptfoo 0.123.1 本地依赖
```

常用命令已收进顶部「快速上手」场景表；组件清单如下：

## 版本踩坑记录（0.123.x，均已在组件中规避）

1. **echo provider 是纯 `echo`**（不带 `echo:文本` 冒号参数），行为=回显渲染后的 prompt。
2. **`tests: path:` 引用的 YAML 只支持 CSV 风格扁平断言**（`__expected` 列），嵌套 `assert:` 必须以独立
   config 形态经多个 `-c` 传入。
3. **双 `-c` 合并会翻倍 prompts**（第二配置即使无 prompts 也产生组合）——验证类配置做成自包含。
4. **python 文件断言按模块加载并调用 `get_assert(output, context)`**（不是 sys.argv）；返回值必须是
   bool/float/`{pass, score, reason}` dict——元组会经 JS 桥转成 `{"0":..,"1":..}` 对象而报错。
5. **python file provider 的实参形态是 `call_api(prompt, options, context)`**，providers[].config 内容
   在第二参 `options.config` 里。
6. **断言的口径必须与 SKILL.md 对齐**：初版把 create_sandbox 归入写操作导致合规样本被判违规——
   技能明确规定它无需确认、在卡前执行是正确行为（见确认与执行流程第 2 步）。
7. **llm-rubric 评分输出必须是 JSON**（`{"pass", "score", "reason"}`），非 JSON 记 error 而非判负；
   格式指令措辞里**不得出现「true 或 false」这类会被模型照抄进 JSON 的字样**（中文「或」破坏解析）。
8. **判 FAIL 时 reason 会冗余写进结果的 error 字段**——统计一致率须以 `gradingResult.pass` 为准，
   不能把 error 非空当解析失败（曾因此把 8 条正确 FAIL 误判为 error）。
9. **rubric 需要视野适配层**（judge 视野 ≠ 人审视野）：图表以文件路径/文件名/内联引用（SVG/PNG/HTML/Mermaid）
   交付即视为已配图；
   确认卡用例是两段式协议（段1 出卡、用户已确认、段2 执行汇报），不得判矛盾；judge 无工具返回，
   回复内数值自洽即可、不作负向推断；不可逆提示按环境区分（沙箱卡声明可丢弃即达标）。
   适配层固化在 `gen_calibration.py` 的 RUBRIC_CONTEXT / CASE_RUBRIC_OVERRIDES。

## L3 完整落地清单（剩余工作）

1. ~~transcript 落盘~~ **已常驻（2026-09-22）**：B 侧 `evals/tools/record_transcript.py`，样本落
   `evals/runs/transcripts/<轮次>.json`（key = `<case_id>-r<N>`，reply + 带 phase 的 tool_calls）；
   ddl 成熟轮首批 24 份已回传 A 并通过真实样本回放校准（`promptfooconfig.replay-real.yaml`，7/7 PASS）。
   真实样本暴露并已修的校准点：确认卡标志从「操作确认」放宽为「操作确认 or 确认卡」；
   `replay_provider.py` 支持轮次键自动回落（case_id 精确 → -r1/-r2/-r3）。fnb/mfg 真实样本随下次回归自动产生。
2. ~~llm-rubric 校准对拍~~ **已达标（2026-09-22）：30/30（100%）**——正样本 24/24 零误杀、负样本 6/6
   零漏判；对拍资产：`gen_calibration.py`（含 RUBRIC_CONTEXT 视野适配层与 CASE_RUBRIC_OVERRIDES）、
   `samples/calibration-negatives.json`（历史失败现象复刻负样本）。**rubric 已可当门禁**。
3. ~~断言补全~~ **已完成（2026-09-22）**：37/37 用例全部有机器断言——新增 `asserts/no_forbidden_tools.py`
   （触发反例零调用判定，含负样本拦截验证）+ 3 条 llm-rubric；gate 验证 7 PASS + 1 拦截 FAIL。
4. ~~CI 接线~~ **已改道落地（决策：弃 GitLab CI 服务器，改 pre-commit 本地门禁）**：
   `.pre-commit-config.yaml` 的「评估用例集校验」钩子（复用 `tools/skill-eval-generator/scripts/validate_cases.py`，
   evals 下 `cases*.yaml` 变更即触发）在 commit 前拦截用例格式 / 编号 / 红线问题；
   promptfoo eval 级门禁（smoke / replay-real / replay-rubric / gate / calibration）仍按需本地手动跑——
   发版前至少跑 gate 与本次改动技能的回放回归。
