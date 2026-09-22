# 跨机清单（生产机）

不要拆成「A 只推链接、B 再转写」。B 会重复去重、重复等转写。

## 必须有

1. **WorkBuddy + 5 个链路 skill**
   - `talk-script-radar` 1.7+（主线：采集→去重→预筛→入库→排 RS 队列）
   - `video-to-text`（纯云端 ASR）
   - `reference-copy-ingester`（第 5 步出 RS 卡）
   - `media-crawler`（MediaCrawler 引擎 wrapper）
   - `xiaohongshu-video-to-text`（XHS 转写脚本硬引用其 `shared/scripts/xhs_extract.py` / `srt_to_readable.py`）
   - 一次性搬齐：`git clone <radar-pipeline>` → `bash setup.sh`（详见仓库 README）
2. **上游发现层（跑商业热点监控才需要）**：`business-hotspot-radar` + `trending-hub` / `trending-hub-top10` / `douyin-daily-hot`
3. `~/MediaCrawler`（`.venv` 就绪）。**抖音要在这台扫一次码**，cookie 在该目录、不跨机
4. `video-to-text`：纯云端 ASR（`V2T_TRANSCRIBER=api` + `~/.workbuddy/secrets/siliconflow`）。本地 whisper 已废弃（模型已删，别装回）。SiliconFlow key 失效就报错让用户检查云端
5. Obsidian 库。macOS 默认
   `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/git`
   **Windows 另改路径**，并同步改 `radar_ai_ingest.py` 顶部的 `OBSIDIAN` 常量
6. 账本 `【03.参考资料】/文案参考/雷达清单/seen-ledger.json`
   换机先跑 `bootstrap_ledger.py`

## Windows 额外注意

- 用 **Git Bash 或 WSL** 跑脚本，不要用 cmd/PowerShell
- `business-hotspot-radar` 里的 `date -v-1d` 是 BSD date（macOS）→ Git Bash 改 `date -d "1 day ago" +%F`
- `transcribe_xhs_playwright.py` 需 `pip install playwright && playwright install chromium`
- 依赖：`winget install --id Gyan.FFmpeg -e`、`winget install --id astral-sh.uv -e`
- 换行符保持 LF（`git config core.autocrlf input`）

## 同步什么

- **要同步**：账本、`雷达inbox_YYYY-MM-DD.json`（含逐字稿）、过眼后的入库 md / RS 卡（走 Obsidian）
- **不要只同步**：只有链接的清单 md、浏览器 localStorage、抖音 cookie

## 过眼机（可选）

只打开已带稿的工作台 / inbox。不再手贴清单，不再先看标题。
