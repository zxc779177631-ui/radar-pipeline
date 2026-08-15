# CHANGELOG · video-to-text（嘉润版）

> 每次修改必须：更新本文件 + 提升 SKILL.md 的 version。

## [1.0.0] 2026-08-15 · 首发（独立于 douyin-video-to-text）

- 从第三方 douyin-video-to-text 的思路重构，按嘉润流程独立成 skill，**非原作者分支**。
- 核心差异：纯云端 ASR（SiliconFlow SenseVoiceSmall）为默认；云端失败直接报、不降级本地 whisper；本地模型已删。
- 新增 `scripts/transcribe.sh` 批量转写（按行均分 N worker 并行、自动跳过已有、日志可续看）——从实战 transcribe_ah/ai.sh 提炼通用化。
- 铁律沉淀：key 只读 `~/.workbuddy/secrets/siliconflow`（勿用 zshrc 占位符）；验收看 `<id>.txt` 文件存在；f2-download 重试一次即弃。
