# 物料齐套与首批采购剧本

> 适用问题：物料齐套情况、毛需求/齐套量/净需求缺口、首批采购方案与成本对比、采购订单到货跟踪。
> 上游输入：ForecastSalesDemand（4 条周粒度预测需求）为根需求；全部计算由检查程序/规则完成，本技能只读取与解释。

## 物料链路（需求 → 缺口）

```
ForecastSalesDemand（根需求）
   ↓ 有效 BOM 展开
MaterialDemand：gross_demand_qty 毛需求 / total_kit_qty 总齐套量 / net_demand_qty 净需求
   ↓ 供需匹配（MaterialKitting + SupplyDemandAllocation）
供应来源：BatchInventory 实时库存（按优先级）＋ PurchaseOrder 采购在途（PURCHASE_IN_TRANSIT）
```

- 优先级规则（预测需求/实时库存/采购在途）由本体定义，解释时引用规则名与版本，**不自行重算优先级或净需求**。
- 回答缺口时同时给出：适用物料数、有缺口物料数、缺口量合计（注明「由 N 行明细加总」并复核）。

## 首批采购链路（缺口 → 方案 → 订单）

```
net_demand_qty > 0 的物料
   ↓ InitialPurchaseStrategy（首批比例、供应商、提前期、最小/最大订货量、订货倍数）
   ↓ 首批采购规则
InitialPurchaseSolution（方案）+ PurchasePlan（采购计划明细）
   ↓ 采购方案成本测算规则（结合 InitialPurchaseObjective）
成本测算对比 → 用户选定方案并确认 → 生成采购订单（PurchaseOrder）
```

- 方案对比口径：**优先保障上市日和首月需求，再考虑同等保障水平下的采购成本**（业务设计原则，引用它解释排序逻辑）。
- 「选定方案 → 生成采购订单」是写操作：确认卡（环境/动作链/关键参数/影响/不可逆性）用户同意后才执行。

## 到货跟踪口径

| 视角 | 字段（业务语义） | 判断 |
| --- | --- | --- |
| 能否按期到仓 | estimated_arrival_date vs required_delivery_date | 预计晚于要求交期 → 风险项列出 |
| 交付进展 | total_order_qty / delivered_qty / undelivery_qty | 剩余未交货量 + 状态 |
| 订单状态 | status、cancel_flag、close_flag | 已取消/已关闭订单不再计入在途保障 |
| 供应关联 | SupplyDemandAllocation 供应类型 PURCHASE_IN_TRANSIT | 哪些物料需求获得了在途分配 |

注意：到货保障聚焦**供应商到仓库**，仓库到门店配送不在范围内（本体边界，见 domain-model.md）。

## 物料备货建议口径（POC 演示期望）

POC 期望答案采用「**独用物料按需锁量、共用物料增量补足**」策略组织建议：

- **独用物料**（新品专用）：按研发 BOM 单耗 × 首月目标测算需求，含损耗；关注采购提前期与效期——效期短的不囤货、分批滚动到货、按提前期倒排下单节奏；鲜果类建议双供应锁定。
- **共用物料**（与存量菜品共用）：读当前库存与历史采购频率，在原采购节奏上做增量预留缓冲，设安全库存。

> ✅ 已实测结案（2026-10-26）：Product 实体 22 个属性中**无「独用/共用」标识属性**。本节作为组织建议的叙事框架使用；物料引用面（只被新品 BOM 引用 vs 同时被存量菜品引用）可按 BOM 关系事实陈述，但损耗率、安全库存等数值一律引用工具返回，不自行估算。效期相关字段有承载（shelf_life_days / min_receive_shelf_life / sled_days）。

## 交付形态

- 物料齐套情况 → 齐套看板（六类齐套状态矩阵 + 物料缺口明细），见 delivery.md。
- 采购方案对比 → 方案对比表 + 成本/交付条件对比图。
- 到货跟踪 → 订单执行进度表 + 风险订单清单。
