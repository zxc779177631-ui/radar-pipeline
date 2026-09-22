# 口播雷达流水线（radar-pipeline）

把「爆款口播视频」找出来 → 云端转逐字稿 → AI 预筛 → 自动入库 Obsidian → 出 RS 演绎卡 的完整流水线。
嘉润自建 + 联动 skill 全家桶，**macOS / Windows 通用**（本仓库即跨机搬运包）。

> 本仓库**不含任何密钥、cookie、客户数据**。部署后在目标机配置 SiliconFlow key（见下）。

## 组成

```
radar-pipeline/
├── setup.sh                       # 一键部署（依赖检查 + 复制全部 skills + 引导 key）
├── skills/
│   ├── talk-script-radar/         # ★ 主线：采集→去重→预筛→入库→排 RS 队列
│   ├── video-to-text/             # ★ 工具：抖音/小红书 → 纯云端 ASR 逐字稿
│   ├── reference-copy-ingester/   # ★ 出卡：逐字稿 → 单篇 RS 演绎卡（第 5 步）
│   ├── media-crawler/             # ★ 采集引擎 wrapper（MediaCrawler）
│   ├── xiaohongshu-video-to-text/ # ★ XHS 转写依赖（talk-script-radar 脚本硬引用其 shared 脚本）
│   ├── business-hotspot-radar/    # ○ 上游：商业热点链接日监控（分流入口）
│   ├── trending-hub/              # ○ 发现层：全网热搜 7 平台（redfox）
│   ├── trending-hub-top10/        # ○ 发现层：跨平台聚合 TOP10（redfox）
│   └── douyin-daily-hot/          # ○ 发现层：抖音日榜按赛道（redfox）
└── workbench/
    └── 口播雷达工作台.html          # 人工确认界面（localStorage 本机保存）
```

★ = 链路必需　○ = 上游发现层（跑商业热点监控才需要，缺 `REDFOX_API_KEY` 会降级 WebSearch）

## 联动关系

```
business-hotspot-radar  ←  trending-hub / trending-hub-top10 / douyin-daily-hot
        │  「收集」确认后回到主线
        ▼
talk-script-radar  ──crawl──▶  media-crawler（MediaCrawler 引擎）
        │
        ├── 抖音转写 ──▶ video-to-text（SiliconFlow 云端 ASR）
        └── 小红书转写 ─▶ transcribe_xhs_* ──▶ xiaohongshu-video-to-text/shared/scripts
        │
        ▼
  入库 Obsidian + 待出RS卡队列
        │
        ▼
reference-copy-ingester  ──▶ 逐篇 RS 演绎卡（【06.知识库】/skeletons/source-cards/）
        │
        ▼
  写作层：cross-source-writer（检索 RS）→ opening-copy-reviewer（检查开头）
```

## 快速部署（新电脑）

```bash
git clone git@github.com:zxc779177631-ui/radar-pipeline.git
cd radar-pipeline
bash setup.sh
```

脚本会：识别平台 → 检查/安装 ffmpeg + uv → 复制 **9 个 skill** 到 `~/.workbuddy/skills/` → 引导输入 SiliconFlow key → 提示装 MediaCrawler。

### 手动步骤

```bash
# 1) 复制全部 skills
mkdir -p ~/.workbuddy/skills
cp -r skills/* ~/.workbuddy/skills/
chmod +x ~/.workbuddy/skills/*/scripts/*.sh

# 2) SiliconFlow key
mkdir -p ~/.workbuddy/secrets
printf '%s' "你的key" > ~/.workbuddy/secrets/siliconflow
chmod 600 ~/.workbuddy/secrets/siliconflow
# 不要把 key 写进 shell 配置（曾踩占位符坑导致 401），skill 只读 secrets 文件

# 3) MediaCrawler（采集层，可选）
bash ~/.workbuddy/skills/media-crawler/scripts/setup.sh
# 或：git clone https://github.com/NanmiCoder/MediaCrawler ~/MediaCrawler
```

## Windows 部署要点

Windows 用 **Git Bash** 或 **WSL**（不要用 cmd/PowerShell 直接跑 `.sh`）。

| 事项 | 处理 |
|---|---|
| 依赖安装 | `winget install --id Gyan.FFmpeg -e` + `winget install --id astral-sh.uv -e`（或 scoop） |
| Obsidian 库路径 | macOS 是 `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/git`；Windows 要改成 iCloud/OneDrive 实际路径 |
| 库路径变量 | `talk-script-radar/scripts/radar_ai_ingest.py` 顶部的 `OBSIDIAN` 常量需按 Windows 路径改 |
| XHS 转写硬编码 | `transcribe_xhs_*.{sh,py}` 里的 `XHS_EXTRACT` / `SRT2TXT` 指向 `~/.workbuddy/skills/xiaohongshu-video-to-text/...`，Git Bash 下 `$HOME` 正常即可 |
| `date -v-1d` | `business-hotspot-radar` 里用的是 BSD date（macOS）。Git Bash 下改成 `date -d "1 day ago" +%F` |
| Playwright | `transcribe_xhs_playwright.py` 需要 `pip install playwright && playwright install chromium`（仅小红书登录态链路用） |
| 抖音 cookie | 采集要**在目标机自己扫一次码**，cookie 不跨机同步 |
| 账本 | 换机先跑 `python3 ~/.workbuddy/skills/talk-script-radar/scripts/bootstrap_ledger.py` |
| 换行符 | 提交时保持 LF（仓库 `.gitattributes` 未设，建议 `git config core.autocrlf input`） |

## 工作流（一条龙）

```bash
# 1. 采集（collect 默认关评论）
GET_COMMENT=false bash ~/.workbuddy/skills/talk-script-radar/scripts/crawl_douyin.sh collect "词1,词2,词3"

# 2. 生成候选清单（--min-likes 默认 5000，标题排除词已杀）
python ~/.workbuddy/skills/talk-script-radar/scripts/build_list.py \
  --mode collect --out "爆款口播候选清单_主题_$(date +%F).md"

# 3. 只转清单幸存者（自动重试 + 退避封装）
grep -oE 'https://www.douyin.com/video/[0-9]+' "爆款口播候选清单_主题_$(date +%F).md" | sort -u > urls.txt
bash ~/.workbuddy/skills/talk-script-radar/scripts/transcribe_robust.sh urls.txt 4 6

# 4. 规则预筛（ingest/review/reject）
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_ai_filter.py "爆款口播候选清单_主题_$(date +%F).md" filter.json

# 5. 入库（搬文件 + 回写账本 + 待出 RS 队列）
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_ai_ingest.py filter.json 同城

# 6. 按 待出RS卡_*.md 出卡（reference-copy-ingester）
# 7. 工作台同步
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_sync_workbench.py "爆款口播候选清单_主题_$(date +%F).md" filter.json 同城 wb_sync.json
```

工作台打开 `workbench/口播雷达工作台.html` → 「⬆ 导入备份.json」同步状态 → 只过「待人工确认」项。

## 铁律

- **赞数门槛**：抖音 <5000 赞、小红书 <1000 赞 = 未验证，不入库、不交确认（`--min-likes` + `radar_ai_filter.py` 双层拦截）。
- **纯云端 ASR**：云端失败直接报告，不降级本地 whisper（本地模型已废）。
- **key 只读 `~/.workbuddy/secrets/siliconflow`**，不进 shell 配置、不上传本仓库。
- **不入低赞、不上传 cookie/逐字稿/客户稿**。
- **不吃探店**：城市认知类优先，美食探店不进榜单。

## 跨机同步什么

- **要同步**：账本 `seen-ledger.json`、`雷达inbox_YYYY-MM-DD.json`（含逐字稿）、过眼后的入库 md / RS 卡（都走 Obsidian）。
- **不要同步**：只有链接的清单 md、浏览器 localStorage、抖音 cookie。

## 版本

| skill | 版本 | 来源 |
|---|---|---|
| `talk-script-radar` | **1.7.2**（2026-09-22 分叉合并） | 自建 |
| `video-to-text` | 1.0.0（2026-08-15） | 自建（非原作者分支） |
| `business-hotspot-radar` | 1.4.2（2026-09-15） | 自建 |
| `reference-copy-ingester` | 未标版本（2026-07-24） | 自建 |
| `media-crawler` | 0.1.4 | 第三方（ZhouGuang，包 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler.git)） |
| `xiaohongshu-video-to-text` | — | 自建/改造 |
| `trending-hub` / `trending-hub-top10` / `douyin-daily-hot` | — | 第三方（redfox 发现层） |

## 已知依赖

- macOS / Linux / Windows(Git Bash、WSL)
- ffmpeg、uv
- Python 3.10+（MediaCrawler 用）
- SiliconFlow API key（免费模型 `FunAudioLLM/SenseVoiceSmall`，500 分钟/月免费档）
- 可选：`REDFOX_API_KEY`（发现层 trending-hub / douyin-daily-hot）
- 抖音 / 小红书扫码 cookie（采集用，转写不需要）
