---
name: video-to-text
version: "1.0.0"
description: "视频转逐字稿（嘉润版，独立于原作者）。抖音/小红书 URL → ~/Downloads/douyin-transcripts/<id>.txt（desc + 可读中文逐字稿）。纯云端 ASR（SiliconFlow SenseVoiceSmall）为默认：云端失败直接报告、绝不降级本地 whisper、本地模型已删。支持单条和批量（transcribe.sh 按行均分多 worker + 自动跳过已有）。触发：抖音转文字 / 转写这条 / 批量转写 / transcribe。"
agent_created: true
---

# video-to-text（嘉润版）

> 版本：1.0.0 ｜ 首次发布：2026-08-15（从 douyin-video-to-text 思路重构，非原作者分支）
> 更新记录见 [CHANGELOG.md](CHANGELOG.md)

把抖音/小红书视频 URL 变成可读中文逐字稿。**设计目标：可靠 + 批量 + 不发热**——纯云端 ASR，不跑本地模型。

## 0. 与旧 skill 的关系（为什么新建）

原 `douyin-video-to-text` 是第三方 skill，本地 whisper 为主、又慢又发热、失败静默降级。嘉润按自己的流程大改后（2026-08-14）：纯云端 ASR、云端失败直接报、本地模型删除，已与原作是两个 skill，故新建本 skill 独立迭代，不再作为原作者的衍生分支。

## 1. 能力

- **单条转写**：`scripts/run.sh "<url>"`
- **批量转写**：`scripts/transcribe.sh urls.txt [JOBS=5]`——按行均分多 worker 并行、自动跳过已有、日志可续看
- **支持**：抖音（主用）+ 小红书（同流程）
- **产出**：`~/Downloads/douyin-transcripts/<id>.txt`

## 2. 铁律（2026-08-14 用户确认）

- **纯云端 ASR 为默认。** `V2T_TRANSCRIBER=api` 强制云端；云端失败 → **直接报错**（`fail_step asr` + 提示检查云端设置），**绝不降级本地 whisper**。
- **本地 whisper 模型已删**（`~/.local/share/whisper-models/` 已清空）。`local` 模式会直接报「no whisper model found」——这是预期，不要尝试恢复。
- **真 key 只读 `~/.workbuddy/secrets/siliconflow`**。不要用 `~/.zshrc` 里的旧占位符（曾写 `sk-你的真实key` 导致 401 一小时；已改为 `$(cat ~/.workbuddy/secrets/siliconflow)` 动态读取）。
- **验收看文件**：`~/Downloads/douyin-transcripts/<id>.txt` 是否存在，不要只信后台 task_id。
- **源视频被删/限区（f2-download）**：重试一次仍失败即放弃，如实报告，不反复耗。

## 3. 用法

### 3.1 单条

```bash
export SILICONFLOW_API_KEY="$(cat ~/.workbuddy/secrets/siliconflow)"
V2T_TRANSCRIBER=api bash ~/.workbuddy/skills/video-to-text/scripts/run.sh "https://www.douyin.com/video/<id>"
```

### 3.2 批量（推荐）

```bash
# urls.txt 每行一个视频 URL；JOBS 默认 5
bash ~/.workbuddy/skills/video-to-text/scripts/transcribe.sh /path/to/urls.txt
JOBS=8 bash ~/.workbuddy/skills/video-to-text/scripts/transcribe.sh /path/to/urls.txt
```

自动跳过已有稿（同 id 已转则跳过），断点续跑安全。日志：`<urls 同目录>/transcribe_<时间戳>.log`。

## 4. 云端 ASR（SiliconFlow）

- **Key**：`$SILICONFLOW_API_KEY` → `~/.workbuddy/secrets/siliconflow`（chmod 600，outside git）
- **模型**：`V2T_ASR_MODEL`（默认 `FunAudioLLM/SenseVoiceSmall`，免费、中文优化；`whisper-large-v3-turbo` 更高保真）
- **费用**：~¥0.003/分钟 或 SenseVoice/TeleSpeech 免费档（500 分钟/月）
- **限流**：50MB/1h 上传上限，WAV>40MB 自动压 64kbps MP3；JSON 响应自动包成单段 SRT
- **实测**：每条约 6-20 秒（下载占大头），5 并行 130+ 条约 15-20 分钟

## 5. 产物格式

```text
## desc/hashtags
<标题 + 话题标签>

## transcript
<可读中文段落>
```

## 6. 失败模式速查

| category | 含义 | 处理 |
|---|---|---|
| `parse` | URL 不支持 | 检查链接格式 |
| `douyin-network` | 网络 | 检查网络/VPN，重试一次 |
| `f2-download` | 视频被删/限区/需登录 | 跳过继续（重试一次仍失败即弃） |
| `asr` | 云端 ASR 失败 | **直接报告用户检查云端设置**（key/模型/余额），不 fallback |
| `ffmpeg` | 音频提取失败 | 重试 |
| `srt-format` | 空逐字稿 | 重转或标记无效 |
| `output-write` | 输出目录不可写 | 检查磁盘 |

## 7. 触发词

- 抖音转文字 / 转写这条 / 批量转写 / transcribe / 把 N 条转成逐字稿
