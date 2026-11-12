# workbuddy/ —— WorkBuddy 侧资产权威源

本目录是 Aquilair 业务资产在 **WorkBuddy 宿主侧的权威源**（2026-11-10 收编入库，此前散在本机
`C:\Users\zishuai\.workbuddy\aquilair-tools\` 下、git 之外无版本管理）。收编理由：WorkBuddy 专家包与
hub 仓技能 / 人设 origin / 口径闸门是共生资产，同仓后一处克隆即可全恢复，且 principles 闸门的
`--extra-surface` 人设镜像路径与本仓路径统一。

- **experts-src/**：四个业务域独立专家包（fnb-inventory-analyst / mfg-transfer-planner /
  launch-poc-advisor / xgimi-supply-demand-balancer，各含 plugin.json + agents/ + avatars/ + README.md；
  xgimi 包 2026-11-12 随技能并入建包，头像暂占位待设计替换，且不进 delivery-shape 口径闸门——
  域内配图口径挂账待统一，见包 README）。本机装配脚本
  `C:\Users\zishuai\.workbuddy\aquilair-tools\install_aquilair_team.py` 从本目录读取骨架源装配
  （技能 / .mcp.json / 域知识库快照仍取本仓 plugins/ 与 aquilair-knowledge/），
  改包内容请直接改本目录后重跑该脚本。
- **已退役资产去向**：早期团队包骨架 `team-src/`（aquilair-supply-chain-team，被独立专家包
  取代）仍在本地 `aquilair-tools\team-src\` 备查不删除；本地旧源目录已改名
  `aquilair-tools\experts-src.retired-20261110\` 留档，一切以本目录为准。
