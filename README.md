# 口播雷达流水线（radar-pipeline）

把「爆款口播视频」找出来 → 云端转逐字稿 → AI 预筛 → 自动入库 Obsidian 的完整流水线。
嘉润自建版：`talk-script-radar`（采集/筛选/入库）+ `video-to-text`（纯云端转写）+ 口播雷达工作台。

> 本仓库**不含任何密钥、cookie、客户数据**。部署后需在目标机配置 SiliconFlow key（见下）。

## 组成

```
radar-pipeline/
├── setup.sh                 # 一键部署（装依赖 + 复制 skills + 引导 key）
├── skills/
│   ├── talk-script-radar/   # 采集→去重→预筛→入库（含 build_list / radar_ai_filter / radar_ai_ingest / radar_sync_workbench）
│   └── video-to-text/       # 纯云端 ASR 转写（单条 + 批量 transcribe.sh）
├── workbench/
│   └── 口播雷达工作台.html   # 人工确认界面（localStorage 本机保存）
└── README.md
```

## 快速部署（新电脑）

```bash
bash setup.sh
```

脚本会：检查 ffmpeg/uv → 复制两个 skill 到 `~/.workbuddy/skills/` → 引导输入 SiliconFlow key → 提示安装 MediaCrawler。

### 手动步骤

1. **复制 skills**（setup.sh 已自动做）：
   ```bash
   cp -r skills/talk-script-radar ~/.workbuddy/skills/
   cp -r skills/video-to-text ~/.workbuddy/skills/
   ```
2. **配置 SiliconFlow key**：
   ```bash
   mkdir -p ~/.workbuddy/secrets
   printf '%s' "你的key" > ~/.workbuddy/secrets/siliconflow
   chmod 600 ~/.workbuddy/secrets/siliconflow
   # 注意：不要把 key 写进 ~/.zshrc（曾踩占位符坑导致 401），skill 只读 secrets 文件
   ```
3. **（可选）MediaCrawler 采集引擎**：
   ```bash
   git clone https://github.com/NanmiCoder/MediaCrawler ~/MediaCrawler
   cd ~/MediaCrawler && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
   首次运行需扫码登录抖音（`python main.py --platform dy --lt qrcode --type search --keywords "..."`）。

## 工作流（一条龙）

```bash
# 1. 采集（collect 场景，不过时间）
cd ~/MediaCrawler && .venv/bin/python main.py --platform dy --lt qrcode --type search \
  --keywords "词1,词2,词3" --crawler_max_notes_count 30 --get_comment true \
  --headless false --save_data_option jsonl

# 2. 生成候选清单（赞数门槛：抖音 5000）
python ~/.workbuddy/skills/talk-script-radar/scripts/build_list.py \
  --mode collect --min-likes 5000 --out "爆款口播候选清单_主题_$(date +%F).md"

# 3. 批量云端转写
grep -o 'https://www.douyin.com/video/[0-9]*' "爆款口播候选清单_主题_$(date +%F).md" | sort -u > urls.txt
bash ~/.workbuddy/skills/video-to-text/scripts/transcribe.sh urls.txt 5

# 4. AI 预筛（ingest/review/reject）
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_ai_filter.py "爆款口播候选清单_主题_$(date +%F).md" filter.json

# 5. 入库 + 工作台同步
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_ai_ingest.py filter.json 同城
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_sync_workbench.py "爆款口播候选清单_主题_$(date +%F).md" filter.json 同城 wb_sync.json
```

工作台打开 `workbench/口播雷达工作台.html` → 「⬆ 导入备份.json」同步状态 → 只过「待人工确认」项。

## 铁律

- **赞数门槛**：抖音 <5000 赞、小红书 <1000 赞 = 未验证，不入库、不交确认（`--min-likes` + `radar_ai_filter.py MIN_LIKES` 双层拦截）。
- **纯云端 ASR**：云端失败直接报告，不降级本地 whisper（本地模型已废）。
- **key 只读 `~/.workbuddy/secrets/siliconflow`**，不进 zshrc、不上传本仓库。
- **不入低赞、不上传 cookie/逐字稿/客户稿**。

## 版本

- `talk-script-radar` 1.6.0（2026-08-15）
- `video-to-text` 1.0.0（2026-08-15，独立于原作者 douyin-video-to-text）

## 已知依赖

- macOS + Homebrew（ffmpeg、uv）
- Python 3.10+（MediaCrawler 用）
- SiliconFlow API key（免费模型 FunAudioLLM/SenseVoiceSmall，500 分钟/月免费档）
- 抖音扫码 cookie（采集用，转写不需要）
