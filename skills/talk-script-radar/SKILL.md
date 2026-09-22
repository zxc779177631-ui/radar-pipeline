---
name: talk-script-radar
version: "1.7.0"
description: "爆款口播雷达 1.7：先杀再转。build_list 默认 ≥5000 赞 + 标题排除词 + 账本去重，只转幸存者。入库回写账本 ingested/excluded，并排出待出 RS 队列。触发：雷达、每日口播、定向收集、过完了。"
agent_created: true
---

# 爆款口播雷达

> 版本：1.7.0 ｜ 更新记录见 [CHANGELOG.md](CHANGELOG.md)
> 首次发布：2026-08-13

把「被市场验证过的口播视频」找出来，**变成写稿能抽的料**。贵步骤（下载+ASR）必须排在便宜判断之后。

## 0. 第一性

**输入**：场景（daily / collect）+ 领域种子或关键词  
**机器输出**：清单层已杀过的新片 + 幸存者逐字稿  
**人输出**：只过超长/超短拿不准的稿  
**机器收尾**：搬进 `【03.参考资料】/文案参考/{主题}/` + 回写账本 + 排出待出 RS 队列，再跑 `reference-copy-ingester`

真源只留两份：**账本（见过没有）+ 库里的稿（能不能抽）**。工作台 / 备份 JSON 不是脊柱。

不是热点监控，不是选题匹配器，不是自动成稿。

人审闸门：**只过已转写、且字数出界的稿。** 标题排除词在转写前就杀掉。

## 1. 两种场景

| 场景 | 触发词 | 发现层 | 时间过滤 | 抓取量 | 用途 |
|---|---|---|---|---|---|
| **daily** | 每日雷达 / 今天有什么值得看 / 定时任务 | **开** | **开**：默认 ≤90 天 | 小（每词 8–12，清单保留 15–25） | 近期能拍的样本 |
| **collect** | 定向收集 / 给我攒一批 X | **关** | **关**（老片也收） | 大（每词 20–40） | 建档案库；入不入库等转完再判 |

用户没说场景时先问一句。定时任务默认 daily。

## 2. 不要做的事（铁律）

- **不做关联度排序 / 客户 IP 匹配。**
- **不替人判「好不好写」。** 标题废片/低赞可自动杀；字数出界必须交人。大批量默认走规则预筛入库，不要再让人逐条过眼。
- **不宣称低粉爆款。** 无粉丝字段；只写「中小热度」。
- **不依赖 agent-reach** 才能跑发现层。
- **不碰配音、字幕、剪辑、分发、视频号。**
- **不把「口播」当硬过滤。** 标题启发式只作提示。
- **不做全文错别字校对。** 入库前只允许轻量可读修补（分段/明显同音错）；专有名词不瞎改。
- **不拆两台各干一半。** 生产机必须能爬、能转、能写账本。另一台只打开已带稿的 inbox/工作台过眼。
- **不上传 cookie、逐字稿、客户稿到 GitHub。**
- **不入低赞数据（赞数门槛铁律）。** 抖音 <5000 赞、小红书 <1000 赞 = 未被市场验证，**不进清单、不转写、不入库**。`build_list.py --min-likes` 默认 5000（源头）；`radar_ai_filter.py MIN_LIKES` 是漏网补刀。
- **不先转后杀。** 跳舞/访谈/数字人等标题排除词必须在 `build_list` 杀掉，转写只跑清单幸存者。

## 3. 工作流

### 3.1 daily（定时默认走完整闭环前半段）

```text
发现层 WebSearch
    → MediaCrawler 抖音
    → build_list.py --mode daily   # 默认 ≥5000 赞 + 标题排除 + 账本已见 + ≤90 天
    → 只转清单幸存者（禁止对排除词/低赞片花钱下载）
    → 规则预筛：正常稿入库+回写账本；超长超短交人
```

清单可以写，但**不得把「只有链接、还没转写」当交付。** cookie 失效要扫码：先停，不要假装转写成功。

### 3.2 collect

给定关键词（或默认种子）→ 大量抓、不过时间 → `build_list`（默认 5000 赞 + 排除词 + 账本）→ **只转幸存者** → 规则预筛入库。  
collect 默认关评论（`GET_COMMENT=false`）；daily 默认可开。老片可以进清单；入不入库仍看逐字稿。

### 3.3 过眼（人）

工作台「已转写·候选」看稿：

- **有效**：连续口播，能当仿写底子
- **无效**：纯 BGM / 卡点混剪 / 几乎无口播 / 转完不知所云（例：2019「60秒各行套路」）
- **短稿（<150 字）**：标黄，不进过眼队列，不当范文

不要让用户先看标题审。

### 3.4 过完了（机器一次做完）

用户说「过完了 / 入库 / ingest」，或 collect 大批量时**用户授权 AI 预筛**：

**A. 规则预筛入库（大批量默认；名称仍叫 radar_ai_*，实际只看标题+字数，不读正文）**
- 脚本：`python scripts/radar_ai_filter.py <清单md> <out.json>` → 分类 `ingest / review / reject / missing`
- 规则（调优后）：
  - `reject`：标题漏网的无口播/访谈词（正路应已在 `build_list` 杀掉）
  - `review`：字数 <150 或 >4000，列清单交用户
  - `ingest`：其余直接入库
- **调优教训**：①vlog ≠ 无口播，靠字数兜底；②「卡点」「跟练」会误伤口播干货，已删；③问答密度检测误伤人间观察/探店，放弃改靠标题；④财经深度口播普遍 2500-8000 字，阈值用 4000
- 入库：`python scripts/radar_ai_ingest.py <filter.json> <主题目录>` **一次做完**：搬 Obsidian + 账本标 `ingested` + reject 标 `excluded` + 写出 `【03】/文案参考/雷达清单/待出RS卡_{主题}_{日期}.md`
- **必须接着跑 `reference-copy-ingester`**（该 skill 没有批量脚本，agent 按队列逐篇出 RS 卡）。只搬 md 不算入库完成。
- review 清单归档工作区 `待人工确认_{主题}.md` 交用户扫一遍
- **工作台状态同步（2026-08-14 新增）：** `python scripts/radar_sync_workbench.py <清单md> <filter.json> <主题> <out.json>` → 合并三份为 `口播雷达_备份_AI筛选_YYYY-MM-DD.json`（candidates + transcripts 双字段，内嵌逐字稿）→ 用户在工作台「⬆ 导入备份.json」覆盖导入即同步状态。
  - 状态映射：ingest→`ingested` / review→`reviewed_ok`(note 写原因) / reject→`reviewed_bad` / missing→`pending`
  - 用户确认后（如「全入」）：review→ingested 回写备份 JSON，Obsidian 补搬文件
  - 坑：备份 JSON 必须有 `transcripts` 字段才走「覆盖导入」；inbox 形态（有 source/counts 无 transcripts）会走 merge 不覆盖——注意区分
  - 用户已确认「以后工作台只看需人工确认的，其余靠 AI 筛选」

**B. 工作台人工过眼（单条/少量，或用户明确要走工作台）**
1. **过眼真源是工作台** `localStorage.wb_radar_v1`，不是 Downloads 里任意一份「待入库」JSON。同日旧导出（例：早上已入库的 39 条）禁止当成这一批。
2. 读不到 Chrome JS 时：扫 `~/Library/Application Support/Google/Chrome/Default/Local Storage/leveldb`，值是 UTF-16LE；按 vid 窗口抽**最后一次** `status`。AppleScript 执行 JS 可能被关，不要卡死。
3. 只处理 `reviewed_ok` 且稿 ≥150 字；`reviewed_bad` 回写账本，不搬库、不跑 ingest。
4. 写入 `【03.参考资料】/文案参考/{主题}/`。主题按**标题语义**分拣，禁止只扫全文关键词（「智能/AI」会把财税自保误丢进 AI工具）。实习生/找工作进 **职场**，不要进商业。
5. **马上**跑 `radar_ai_ingest.py`（或等价搬库）回写账本，并按待出 RS 队列跑 `reference-copy-ingester`（RS 续现有最大号，近重复也分卡，校验 PASS）
6. 账本 `status=ingested`；人改口后 `reviewed_bad` 可升 `ingested`。工作台需用户刷新或点「批量标已入库」（机器通常写不进 Chrome JS）
7. 不再让用户先导出 JSON 再确认
8. 过眼备注要当反面类型的：写入 `assets/default-tags.yaml` 的 `exclude`（访谈/程前朋友圈、数字人教程）。下次 `build_list` 标题命中即跳过。实习生不是反面。

工作台「下载 md」只作人眼备份，不是主路径。不要起常驻 localhost。

### 3.5 工作台

- 单文件：工作区 `口播雷达工作台.html`，归档 `【05.我的上下文】/办公工作台/`。**只开这一份。**
- **抖音 id 是 19 位字符串。** 从 URL 抽 `video/(\d{15,})`，禁止 `Number(id)`。
- 顶栏「导入清单.md」按 vid 合并，已有状态不动。「导入备份.json」才会覆盖。
- daily 正路：`merge_inbox.py` 写 `雷达inbox_YYYY-MM-DD.json`，再并进工作台；不要手改 SEED 当日常。
- localStorage 短残稿不得盖更长新稿（取最长）。跨机不要只靠 localStorage，以账本 + inbox 为准。

## 4. 账本

真源：`【03.参考资料】/文案参考/雷达清单/seen-ledger.json`  
回退：本 skill `data/seen-ledger.json`（不进 git）

```bash
# 首次 / 换机：从已入库 + 历史清单回填
python ~/.workbuddy/skills/talk-script-radar/scripts/bootstrap_ledger.py \
  --workbench "./口播雷达工作台.html"
```

字段：`items[vid] = {status, title, first_seen, updated}`。  
`status`：`seen` / `transcribed` / `reviewed_ok` / `reviewed_bad` / `ingested` / `excluded`。  
**只升不降**：`merge_inbox` / `bootstrap` 不得把 `ingested` 打回 `transcribed`/`seen`。  
`build_list.py` 默认丢掉账本里已有的 vid（今天 5 条重复就是没这笔账）。

## 5. 数据标准

MediaCrawler 搜索 jsonl **有**：`aweme_id` / `aweme_url` / `title` / `desc` / `liked_count` / `comment_count` / `share_count` / `collected_count` / `create_time` / `nickname` / `source_keyword` / `cover_url`  
**没有**：粉丝数、播放量、完播率。

| 档 | 条件 | 含义 |
|---|---|---|
| 绝对爆款 | ≥5 万赞 | 选题天花板 |
| 中等热度 | 5 千–5 万赞 | 可二创 |
| 中小热度 | <5 千赞 | 可能小号，未验粉丝 |

daily：`create_time >= now - 90天`。collect 不过时间。

## 6. 命令

引擎：`$HOME/MediaCrawler`。关键词走 `--keywords`，不要改 `config/base_config.py`。

```bash
# daily 默认可开评论；collect 默认关。要开评论：GET_COMMENT=true
bash ~/.workbuddy/skills/talk-script-radar/scripts/crawl_douyin.sh daily "词1,词2,词3"
GET_COMMENT=false bash ~/.workbuddy/skills/talk-script-radar/scripts/crawl_douyin.sh collect "词1,词2,词3"

python ~/.workbuddy/skills/talk-script-radar/scripts/build_list.py \
  --mode daily --max-age-days 90
  # --min-likes 默认 5000，不用再手写；小红书传 1000；调试才传 0
  # 默认写出 爆款口播候选清单_YYYY-MM-DD.md
  # collect 默认写出 爆款口播候选清单_全量_YYYY-MM-DD.md

# 只转清单幸存者（清单已不含低赞/排除词/账本已见）
export SILICONFLOW_API_KEY="$(cat ~/.workbuddy/secrets/siliconflow)"
grep -oE 'https://www.douyin.com/video/[0-9]+' 爆款口播候选清单_YYYY-MM-DD.md | sort -u > urls.txt
bash ~/.workbuddy/skills/video-to-text/scripts/transcribe.sh urls.txt 5

python ~/.workbuddy/skills/talk-script-radar/scripts/radar_ai_filter.py 爆款口播候选清单_YYYY-MM-DD.md filter.json
python ~/.workbuddy/skills/talk-script-radar/scripts/radar_ai_ingest.py filter.json 同城
# ingest 后必须按「待出RS卡_*.md」跑 reference-copy-ingester
```

同日多次跑会追加同一 jsonl，`build_list.py` 必须按 `aweme_id` 去重。  
CDP 默认关。小红书默认不做。

转写：纯云端 SiliconFlow SenseVoice（`V2T_TRANSCRIBER=api`）。真 key 只读 `~/.workbuddy/secrets/siliconflow`，不要用 zshrc 占位符（会 401）。云端失败**直接报**，禁止降级本地 whisper。云端大约 6–15 秒/条（下载更久）。验收看 `~/Downloads/douyin-transcripts/<id>.txt` 是否存在。

## 7. 发现层（daily）

WebSearch 2–4 组，问「近一个月在聊什么」，不要问今日新闻。子话题必须能当搜索词。失败则降级到耐久种子，清单头部写「发现层降级」。

## 8. 文件落点

| 产物 | 位置 |
|---|---|
| 当日 daily 清单 | `{workspace}/爆款口播候选清单_YYYY-MM-DD.md` |
| 当日 collect 清单 | `{workspace}/爆款口播候选清单_全量_YYYY-MM-DD.md` |
| 当日 inbox | `{workspace}/雷达inbox_YYYY-MM-DD.json` |
| 账本 | `【03.参考资料】/文案参考/雷达清单/seen-ledger.json` |
| 有效稿 | `【03.参考资料】/文案参考/{主题}/` |
| 待出 RS 队列 | `【03.参考资料】/文案参考/雷达清单/待出RS卡_{主题}_{日期}.md` |
| RS 卡 | `【06.知识库】/skeletons/source-cards/` |
| 工作台 | 工作区 + `【05.我的上下文】/办公工作台/` |

清单不是参考文案，不要丢进主题子目录和 RS 卡混在一起。

## 9. 触发词

- 雷达 / 口播雷达 / 每日口播 / 今天有什么值得拍
- 定向收集 / 给我攒一批 XX 素材
- 过完了 / 入库 / ingest 这批
- 导入清单 / 灌进工作台

## 10. 失败怎么说

| 情况 | 说法 |
|---|---|
| 未登录 / 验证码 | 「需要你扫一次抖音码，扫完告诉我」 |
| 发现层全是新闻 | 降级到耐久种子，头部标明 |
| jsonl 当天为空 | 不编清单，报告爬虫失败 |
| 时间过滤后 0 条 | 放宽到 180 天，或改 collect |
| 账本过滤后 0 条新片 | 「今日无新片（已见/已入库已剔除）」——这是正常交付 |
| 转写目录没有 txt | 不要把链接当过眼队列 |
| 小红书失败 | 记下，继续只用抖音 |

## 11. 跨机

生产机必备：`~/MediaCrawler`（扫码 cookie）、`video-to-text`（纯云端 ASR）、本 skill、`reference-copy-ingester`、Obsidian 库路径。  
Windows 库路径不是 macOS iCloud 那条，换机先改账本/入库路径。  
同步的是 **账本 + inbox json（含逐字稿）**，不是「一份只有链接的 md」。  
台式机迁移 / 双向同步 Obsidian：用户没点名就不做。

## 12. 已知边界

- 抖音无登录会被验证码拦住；扫码后可抓搜索+评论。
- 搜索结果大量超一年老片，daily 必须过滤。
- macOS Chromium：`~/Library/Caches/ms-playwright/`。
- 清单链接是抖音，不是视频号。
- ASR 会繁简混、同音错；过眼看结构能不能仿。
- 定时任务必须按 §3.1 跑完转写+inbox，禁止停在「只出链接」。
