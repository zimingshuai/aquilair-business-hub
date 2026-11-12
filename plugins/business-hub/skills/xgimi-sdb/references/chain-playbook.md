# 全链编排剧本（chain-playbook）

> 9 函数执行地图。参数契约与脚本用法见 platform.md；口径解释见 caliber.md；平台现状见 `knowledge/STATUS.md`。数字正确性靠 §4 勾稽自洽保证，不背任何基准数字——结果与历史/文档数字不同不是异常（SKILL.md 红线 8）。

## 1. 依赖图与串行铁律

```
bom_check_diff ──→ impact_scope（只读，可与 bom_explode 并行）
       │
       └──→ bom_explode ──→ supply_demand_allocation ──→ substitute_fill
                     │                                        │
                     └──────────────→ risk_identify ←─────────┘
                                        │
                                        └→ strategy_simulate ──→ scheme_compose ──[选定]→ purchase_plan_generate
```

- 全链以 check_batch_id 归组：① 创建 CheckBatch＋差异行，此后每步带 check_batch 定位同批数据；每步读上一步落库产出，严格按序。
- 可并行：影响反查×需求展开（都只依赖点检结果）；多个沙箱分支整链互相独立。

## 2. 九函数入口

| # | 函数 | 必填参 | 产出（落库实体） |
|---|---|---|---|
| ① | bom_check_diff | base_bom, target_bom | CheckBatch＋BOMCheckList 差异行（六类） |
| ② | impact_scope | check_batch | **只读不落库**：影响概览由技能层展示层拼装——差异行计数＋物料失效时间（expire_time ≤ V2 生效日）＋订单查询按需求 4 口径（变化物料→受影响成品→未交付订单→影响等级＋繁杂度「一进一出」：进入/退出/净额，退出 = BOM 删除 ∪ 失效物料，并集去重，见 caliber §10），交付注明「展示层口径」 |
| ③ | bom_explode | check_batch | MaterialRequirement 需求行（根需求=订单未交付合计）；**目标口径（函数待升级）**：按「产品×订单」展开，需求行带 sales_order_nr＋require_date=订单交期，已删除物料保留单行、订单留空（呆滞载体与订单无关，见 caliber §11） |
| ④ | supply_demand_allocation | check_batch | SupplyDemandAllocation 分配账本＋回填需求行供给字段（FEFO、现货先于在途）；**目标口径（函数待升级）**：按需求行交期升序分配（先保早交期订单），分配行 sales_order ← 需求行订单号（冗余追溯键，见 caliber §11） |
| ⑤ | substitute_fill | check_batch | 回填替代字段（消耗两口径＋比例快照＋多余供给）；是否填补由本世界 STRAT-SUB 开关决定；**替代料三重有效期校验（关系日期按需求行 require_date 判定＋物料本体 status/expire_time，过期库存不进④供给池）**，被拦截项日志留痕 |
| ⑥ | risk_identify | check_batch | InventoryRisk（呆滞＋缺口，金额由平台规则自动算）；**呆滞 = 账本余量口径（未被占用现货+在途，占用从分配账本扣减），与缺口互斥（同物料呆滞×缺口=0）；孤儿库存按「无需求库存」进呆滞**（2026-11-03 函数升级，见 caliber §4/§5） |
| ⑦ | strategy_simulate | check_batch | StrategyResult 测算行（参与策略由本世界 is_active 开关决定；全关=维持现状空跑） |
| ⑧ | scheme_compose | check_batch | Scheme（候选）＋ SchemeObjectiveValue（按目标目录逐维度） |
| ⑨ | purchase_plan_generate | scheme | PurchasePlan（待审批） |

- 执行 ① 前核对：两版 BOM 同 output_code、bom_type 均正式计划版（目标版可未生效）。
- ⑨ 前置：Scheme 状态候选→已选定（写操作，确认卡）；一个方案只生成一次；计划初始「待审批」，审批是 UI 直改，助手不代审批。

## 3. 沙箱推演剧本（2×2 决策矩阵，决策即数据）

两维均为分支内策略库开关：`STRAT-SUB` 替代 × `STRAT-PURCHASE` 采购。生产 main 恒全开（不变量），沙箱内只关不开。

1. **公共段（生产 main，跑一次）**：①→④。展开与分配跟决策无关，四世界共用同一份底账——分叉点在 ④ 后。
2. **建沙箱**：`objects_create_branch` × 4，命名 `sb-{批次尾号}-sub-buy / -sub-nobuy / -nosub-buy / -nosub-nobuy`（无需确认，一个 turn 并行建）。
3. **整链一卡**：确认卡覆盖 4 分支 ×（开关＋⑤⑥⑦⑧），一次确认整链执行。
4. **执行**：出推演卡时同步生成清单 plan.json（卡面动作链的机器可读版，platform.md §5），确认后 `python scripts/run_plan.py --plan plan.json` 整链执行（或逐分支手动 fire_action.py）。世界配置：**sub-buy 零开关调用**（继承全开）｜sub-nobuy 关 STRAT-PURCHASE｜nosub-buy 关 STRAT-SUB｜nosub-nobuy 两个都关。分支内严格按序，分支间在清单中依次排列。
5. **回查与勾稽**：按脚本输出的主键清单，一个 turn 并行回查各分支产出；勾稽按 §4（recheck.py 代算）。
6. **对比交付**：按 SupplyDemandObjective 目标目录 8 维并列四分支 SchemeObjectiveValue（方案级汇总＋物料明细下钻），可辅 objects_compare_branch。讲解要点（呈现事实，不推荐）：**替代能否救交期取决于瓶颈是否可替代**——瓶颈不可替代时台数贡献为 0（但仍有呆滞减少＋主料采购差额＋⑦ 替代记账），瓶颈可替代时替代可单独跨过整单齐套门槛；替代的价值按「交付解锁（当瓶颈可替代）/ 呆滞减少 / 采购差额 / 替代记账」分维度呈现，不硬凑台数。具体数字一律当轮实跑。
7. **选定与落地**：默认仍在沙箱置「已选定」＋生成采购计划核验；正式落地 main 属生产写入，单独确认卡＋加粗不可逆警示——main 保持全开、直接重跑 ⑤→⑨（生产可复现世界仅「替代开＋采购开」，其余三世界为对比支撑）。
8. **清理**：本会话创建的分支用完可 objects_delete_branch 丢弃（须确认）。

**判停条款（只看逻辑矛盾）**：跨沙箱分岔只允许出现在 ⑤ 及之后——此前出现沙箱间差异即判停；⑤ 后必须按开关分化——nosub 分支无替代消耗账本行、nobuy 分支 ⑦ 无采购测算行，未分化即判停上报，不得继续对比。**数字与历史/文档/其他批次不同不构成判停理由**（数据会变，SKILL.md 红线 8）。

## 4. 勾稽自洽（当轮明细机械核对，不背数字）

核对一律用当轮返回明细，`recheck.py` 代算（加总/守恒），模型只读结论；核对通过=静默继续，不符=停下说明。

- **守恒**：每物料 毛需求 = 已分配合计 ＋ 剩余缺口（分配后）；替代后剩余缺口 = 分配缺口 − 替代消耗折算（÷比例）。
- **互斥（2026-11-03 起）**：同一物料 呆滞量 × 缺口量 = 0；「呆滞」行物料确有未被占用的冗余现货/在途（占用按分配账本逐笔核）。
- **替代记账守恒（2026-11-03 起）**：同一物料 风险金额（可化解部分）= ⑦ 替代记账改善 ＋ 采购改善，逐物料对得上；⑦ 的 kind=substitute 行只读 ⑤ 账本（alt_consume_qty_main_unit），不得重复模拟或重复扣库存。
- **⑤ 账本合并坑（2026-11-03 实测）**：⑤ 的返回**只含本轮新增账本行**——本地离线串跑时若 `inputs.update(o5)` 整体覆盖 SupplyDemandAllocation，会丢掉 ④ 的分配记录，导致占用统计清零、有需求的物料被误报呆滞。必须 **合并 o4 分配行 + o5 新增行**。平台 fire 链路落库不受影响（写库是追加）。
- **集合一致**：风险「缺口」行物料集合 = 分配后缺口>0 的物料集合；「呆滞」行物料确有冗余库存/在途。
- **按单归属（函数升级后启用）**：各订单需求行合计 = 订单未交付量；分配行 sales_order 与承接需求行一致、无跨单串行；四世界总量不受按单拆行影响。
- **加总复核**：风险金额合计 = 明细加总；方案目标值 = 物料明细加总（双口径注记见 caliber）。
- **归组**：报告任何数字前核对批次一致，不混批。
- 异常/空返回按 SKILL.md 红线 6 处理（先回查、不自动重试）。

## 5. 会话状态与多轮复用

- 工作区 `.aquilair/run-state.json` 由脚本维护（最新批次、分支清单、最近动作与主键）；上下文被压缩或跨会话续跑时**先读它恢复现场**，不重复查询。
- 报告历史测算先查 CheckBatch 归组，引用带批次号＋分支名；旧查询随写失效，用户要「最新」或切分支/范围时重查。
