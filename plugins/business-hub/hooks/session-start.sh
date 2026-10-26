#!/bin/sh
# ============================================================
# Aquilair 技能路由 - 会话启动引导脚本（SessionStart hook 载体）
# 作用：输出 hooks/bootstrap.md 全文；SessionStart 事件的纯文本
#       stdout 会被宿主注入为会话上下文，使路由门控从第一条
#       消息即生效、compaction 压缩后不丢失。
# 定位：优先宿主导出的 CLAUDE_PLUGIN_ROOT（插件安装目录）；
#       未设置或为空时，回落到本脚本所在目录的上两级（即插件根）。
# ============================================================

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

# cat 成功即以退出码 0 结束；bootstrap.md 缺失时按真实失败退出，
# 不做任何兜底静默（不降级纪律）。
cat "${PLUGIN_ROOT}/hooks/bootstrap.md"
