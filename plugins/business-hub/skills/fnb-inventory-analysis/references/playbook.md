# 餐饮库存诊断 · 查询剧本与输出模板

> 本文件由 SKILL.md 按需引入：处理仓群总览、溯源追问、明细下钻或口径收窄时读取。
> 剧本描述「缺数据时查什么」，不是每轮全量执行；阈值与动作链以业务元数据为准。
> 示例中的仓库名/SKU 名为**格式示意**，真实名称以查询返回的 `wh_name` / `sku_name` 为准。
>
> **出处说明**：本域开发于溯源区设立（2026-09-28）之前，源文档未留档，以下口径出处均为实测元数据（`get_meta_objects` / `get_meta_rules` / 实例回放验证；2026-10-22 接口迁移至统一网关，工具映射见 SKILL.md），标注格式见仓库 `aquilair-knowledge/sources/README.md`（知识库源文档区随技能 zip 一并分发）。业务方补充口径文档后，落位 `aquilair-knowledge/sources/fnb/` 并替换为文档出处。

## 场景 A：仓群风险总览

### L0（默认）——「各仓有没有风险？」

- 缺数据时：`Warehouse` + `InventoryRisk`（可并行，含 `wh_name`）。
- 输出：1 段总结 + 汇总表（全量仓库，按 P0→P1→P2→P3→无风险排序；仓库列用「名称（编码）」）+ 无风险仓列表。

```markdown
## 结论先行
（总结一句 + 汇总表）

| 📦 仓库 | 风险等级 | 风险类型 | 状态 |
| --- | --- | --- | --- |
| 苏州区域仓（WH002） | P0 | 库存缺货风险 | 专项管控 |

## 无风险仓库
- ✅ 杭州区域仓（WH003）：当前无风险记录。
```

### L1（追问依据）——「为什么 / 怎么判定的？」

- 缺数据时：`InventoryInWarehouse`。
- 溯源链（📎 编号列表）：规则原文（元数据）→ 指标数值（工具）→ 风险/Problem/Cause 记录（工具）。（来源：实测 2026-09-16，get_meta_rules 触发规则 + InventoryRisk 记录结构）
- 无风险仓只陈述指标原值，**不做区间判定**。（来源：实测 2026-09-16，InventoryInWarehouse 指标释义未提供判定区间）

```markdown
## 一、苏州区域仓（WH002）— P0 库存缺货风险
以下是对系统既有判定结果的解释，非重新计算。
- 触发规则「{规则名}」：`{logic}` → `{action_name}`
- 判定指标：{字段} = {数值}
- 风险记录：**{risk_code}**（{create_date}，{control_measures}）
- 业务问题：**{problem_code}**（若有）
```

### L2（追问明细）——「根因 / SKU 明细 / 升级链路？」

- 按需补查：`InventoryInWHProblem` → `InventoryInWHCause`；`SKUInWarehouse`（含 `sku_name`）。
- `risk_source` 仅有编码时：用已查到的 SKU 清单补全名称，禁止编造。

## 场景 B：单仓 / 单 SKU / 口径收窄

| 问法 | 缺数据时补查 |
| --- | --- |
| 某仓周转/库存 | `objects_query`（实体 `InventoryInWarehouse`，where=`eq`（wh_code，'…'）） |
| 某 SKU 详情 | `objects_get`（object_type=SKU，object_id=SKU 编码） |
| 某仓 SKU 列表 | `objects_query`（实体 `SKUInWarehouse`，where=`eq`（wh_code，'…'）） |
| 某类 SKU（如 A 类）视角 | `SKU`（取 `abc_type` + `sku_name`）+ 相关 `SKUInWarehouse` / `InventoryRisk` |

### 口径收窄输出示例（A 类 SKU 视角）

```markdown
| 📦 仓库 | 原风险 | 涉及 SKU（A 类视角） | 结论 |
| --- | --- | --- | --- |
| 上海中心仓（WH001） | P3 超储 | 全脂牛奶1L（SKU003）、生抽酱油1.9L（SKU005） | 不变 |
| 苏州区域仓（WH002） | P0 缺货 | 冷冻鸡胸肉2kg（SKU001）、冷鲜鸡腿肉1kg（SKU002）；剔除 B 类淡奶油1L（SKU004） | 不变 |
```

## 名称与编码细则

- 枚举多个对象时每个都带名称：**不得**写「SKU001、SKU002、SKU003」。（来源：实测 2026-09-16，查询返回含 `wh_name` / `sku_name` 中文名称字段）
- 同段第二次出现可只写中文名称，不得用编码作简称。
- 输出前自检：正文中是否还有单独的 `WH\d+` / `SKU\d+` / `PC\d+`？非单据号一律改为「名称（编码）」。
