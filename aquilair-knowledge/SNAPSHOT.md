# 知识库快照区（勿在此直接编辑）

本目录是 Aquilair 域知识库源文档区的**分发快照**（仅 `sources/`），主本在
[aquilair-skill-forge 仓库](https://code.elitescloud.com/el-aquilair/skill-forge)的
`aquilair-knowledge/`（摄取、编译、再摄取均在主本进行）。

- **用途**：`tools/pack_skill.py` 打技能 zip 时收录 `sources/`，包内保持同名坐标，
  技能 references 的出处标注得以在分发副本内解析溯源。
- **同步**：主本知识更新后，在 forge 仓跑 `python tools/sync_knowledge.py <本仓库路径>`
  推送快照并提交（commit message 标注来源 forge commit），本仓不接受对快照的直接编辑。
