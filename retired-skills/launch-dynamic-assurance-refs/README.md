# launch-dynamic-assurance 旧 references 退役区（2026-11-10 V8 大吸收）

本目录存放 `launch-dynamic-assurance` 技能在 **2026-11-10 V8 大吸收**（hub v0.4.7，MR feat/v8-merge）中被替换退役的三个旧参考文件，git 历史可回看全文：

| 旧文件 | 去向（被吸收进现行 references） |
| --- | --- |
| `domain-model.md` | 业务语义/判定链/决策枚举 → `references/business-semantics.md`（同事 V8 版为基线重写；supply_type 写值映射与 ALLOCATED 实测校注已回灌其「决策枚举」表） |
| `material-purchase.md` | 物料/采购下钻剧本 → `references/mrp-playbook.md` + `references/launch-assurance.md`（按 MRP 链路 / 保障跟踪两条线重组） |
| `readiness-playbook.md` | 上市事项诊断剧本 → `references/launch-assurance.md`「上市事项跟踪」节 |

- **吸收来源**：同事包 `aquilair-launch-poc-v2`（V8 rev248 文档基线的 fork 重写版，zip 解压于 2026-11-10）；四项用户裁决与治理资产保留清单见仓库 `CHANGELOG.md` v0.4.7 节。
- **保留说明**：旧文件中的 hub 实测发现（写值映射、relation_counts 语法、System 检查日、entity_ 通道不稳、DSL 方言等）零丢失——已分别沉淀在现行 `references/facts.md`（服务端行为）与 `business-semantics.md` / `mrp-playbook.md`（业务口径校注）；本目录仅作历史备查，不再随插件分发。
