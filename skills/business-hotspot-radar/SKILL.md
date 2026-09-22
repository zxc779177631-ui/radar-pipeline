---
name: business-hotspot-radar
version: 1.4.2
description: 商业热点口播链接日监控。发现近7日企业家/电商/平台争议 → 抖音搜索 → 可点爆款链接清单。不转写、不入库。触发：商业热点、牛来、钟睒睒、刘润、日监控。
agent_created: true
---

# 商业热点口播雷达

> 版本：1.4.2 ｜ 2026-09-15
> 与 talk-script-radar 分工：那条是「被验证的口播 → 转写入库」；这条是「正在吵的热点 → 人先点开」。

## 0. 第一性

**输入**：无（定时）或用户点名的热点名（牛来 / 钟睒睒 / 某企业家言论）  
**机器输出**：当日约 30 个话题（超级热 + 中热度）+ 能搜到的可点抖音链接（≥1000 赞，90 天内）  
**人输出**：点开看，说「这几条收集」  
**之后**：才交给 talk-script-radar collect 转写入库

不是口播雷达 daily。不要 ASR。不要当选题匹配器。

用户原话口径（2026-08-18/20）：**热点 → 相关爆款口播链接 → 自己点开看 → 再定向收集**。

## 1. 不要做的事

- **不转写、不入库、不跑 reference-copy-ingester。**
- **不跑 lingyi-daily-hot-topic**（扣点，且本机常无 `LY_API_KEY`）。用户没明确同意扣点不准发。
- **不把 redfox 当口播主粮。** 有 `REDFOX_API_KEY` 时，trending-hub / trending-hub-top10 / douyin-daily-hot 只做发现层（找「现在在吵什么」）。抖音可点链接仍走 MediaCrawler。无 Key 才降级 WebSearch，禁止用用户给过的旧热点顶替新发现。
- **不污染当天口播雷达 jsonl。** 爬之前备份 `search_contents_YYYY-MM-DD.jsonl`，抽完热点行后还原。
- **不把访谈原片当仿拍范文。** 标题含 访谈/对话/专访/做客 → 标「原片切片」。
- **不编链接。** jsonl 为空或 cookie 失效就停。
- 抖音 id 当字符串，禁止 `Number(id)`。

## 2. 工作流（daily 默认定时 12:00）

```text
redfox 三件套（有 Key）/ WebSearch（无 Key）
    → 约 20–30 个话题（超级热 + 中热度；人名+事件，必须来自当日热搜/日榜）
    → 备份当日 MediaCrawler jsonl
    → crawl_douyin.sh daily "词1,词2,..."（GET_COMMENT=false）
    → 抽出本轮 keyword 新片到 radar_jsonl_商业热点_YYYY-MM-DD/
    → 还原 daily jsonl
    → ≥1000赞 + ≤90天 + 去重；>7天无新片标「旧热点」不算数
    → 写 Obsidian 雷达清单/商业热点口播链接_YYYY-MM-DD.md
    → 发邮件到 zxc779177631@gmail.com
    → 飞书：猪妞 bot 私聊曾嘉润
```

### 2.1 发现层（redfox 优先，WebSearch 降级）

**Key 加载（2026-08-21 实测）**：当前对话的环境变量经常没有 `REDFOX_API_KEY`，但本机 `~/.zshrc` 里有 `export REDFOX_API_KEY=...`。跑 redfox 前用 Python 从 zshrc 读入 `os.environ`，**禁止把 Key 写进命令行/日志**。可用工作区 `run_redfox_discover.py`。读不到才算「无 Key」并降级。

有 Key 时，**先跑 redfox 三件套**（这才是真正的「现在全网在热什么」）：

```bash
PY=/Users/a1-6/.workbuddy/binaries/python/versions/3.13.12/bin/python3
# 1) 7 平台热搜原榜，筛商业相关（平台可组合：wb微博 dy抖音 bz B站 zh知乎 tt头条 bd百度 ks快手）
$PY ~/.workbuddy/skills/trending-hub/scripts/fetch_hotspot.py \
  --platforms wb,dy,zh,tt --output markdown --start-date "$(date -v-7d +%Y-%m-%d) 00:00:00" --end-date "$(date +%Y-%m-%d) 23:59:59"
# 2) 跨平台聚合 TOP10（一眼看穿真热点；仅支持近 7 天回溯）
$PY ~/.workbuddy/skills/trending-hub-top10/scripts/fetch_hotspot.py --start-date "$(date -v-1d +%Y-%m-%d)" --end-date "$(date +%Y-%m-%d)"
# 3) 抖音日榜 TOP50 按赛道（T-1；赛道名必须用 --type，没有「商业」这个类）
$PY ~/.workbuddy/skills/douyin-daily-hot/scripts/douyin_daily_hot.py --type 财富理财 --start "$(date -v-1d +%Y-%m-%d)" --full
$PY ~/.workbuddy/skills/douyin-daily-hot/scripts/douyin_daily_hot.py --type 个人成长 --start "$(date -v-1d +%Y-%m-%d)" --full
```

从输出里挑「商业/电商/企业家/上市/净利/创始人/公积金/平台」相关热搜词当搜索关键词（人名+事件）。  
- `trending-hub-top10` 的 `source_keyword` 聚类很噪（会把一切归到「日本」「七夕」），**只看 title，不看聚类名**。  
- `douyin-daily-hot` 赛道没有「商业」，用 `--type 财富理财` + `--type 个人成长`。  
- 排除体育「加盟」、情感、纯八卦、软广（搜出来全是种草就标「广告淹没」不给链接）。过期话题（>7 天无新片）标「旧热点」。  
- **超级热不够。** 中热度也收：游戏实机/IP 续作（如黑神话钟馗）、开机率、驾校、称重秤、招工——热搜有名、日榜有片，哪怕不如许家印高。清单目标 **约 30 个话题**，不是 6 条头条。没搜到口播的话题保留热搜词，**不编链接**。  
- crawl 词可以 8–16 个，**每批最多 4 词**（2026-08-26 实测：一次 8 词到第 4 个会 `TargetClosedError` 浏览器被关）。每批抽出热点行再还原 jsonl。  
- **2026-09-15：首批 4 词成功后，同会话后续搜索常返回空 `[]`（不是验证码、cookie 仍能开页）。** 空搜 2 次就停，不要词词空跑。未拿到片的话题只留热搜词；日榜 T-1 已有对应新片时可用日榜链补，但必须标注来源是日榜不是本次搜索。  
- **禁止把用户给过的旧热点（钟睒睒/牛来/AB货）当新发现。**

**没有 Key 时降级**：WebSearch 2–4 组「近一周中国商业热点 企业家 电商 平台」，子话题必须能直接塞进 `--keywords`；再降级固定词 `许家印,宇树科技,电商平台,实体店,创始人`，清单头部写「发现层降级」。

### 2.2 提取层

```bash
MC="$HOME/MediaCrawler/data/douyin/jsonl"
DAY=$(date +%Y-%m-%d)
WS="$PWD/radar_jsonl_商业热点_$DAY"
mkdir -p "$WS"
cp -f "$MC/search_contents_$DAY.jsonl" "$WS/before_contents.jsonl" 2>/dev/null || true

GET_COMMENT=false bash ~/.workbuddy/skills/talk-script-radar/scripts/crawl_douyin.sh daily "词1,词2,词3"

# 按 source_keyword 抽出本轮，写 $WS/search_contents_hotspot.jsonl
# 再把 $MC/search_contents_$DAY.jsonl 还原成 before_contents.jsonl
```

cookie 失效 / 验证码：停下说「需要你扫一次抖音码」，不要假装有链接。

### 2.3 过滤

| 档 | 条件 |
|---|---|
| 进清单 | liked ≥1000 且 create_time 在 90 天内 |
| 可拍口播 | 单人评述/拆账/反驳，非原片 |
| 原片切片 | 标题含访谈/对话/专访/做客/央视《对话》 |
| 新闻切片 | 人民日报/新华社/半月谈/媒体原创 |
| 猎奇/二创 | 电影切片、抽象玩梗、无拆解 |
| 丢掉 | 跳舞/变装/BGM；<1000 赞；>90 天（可在附录提一句「旧片被搜索捞回」） |

5000 赞只当分档（中等热度），不当淘汰线。

### 2.4 落盘

路径（铁律，进 Obsidian，不进工作区当交付）：

`【03.参考资料】/文案参考/雷达清单/商业热点口播链接_YYYY-MM-DD.md`

必须有：

1. 今日约 30 个话题（叶明 / 邓毅轨A / 轨B 分表），中热度单独标
2. 有片的话题必须可点击 `[标题](https://www.douyin.com/video/{id})`；没有片只写热搜词
3. 叶明 / 邓毅轨A / 邓毅轨B 各能拍什么
4. 「点开后说收集，再走 talk-script-radar」

给用户的对话：30 话题表 + 另列 8 条「若只点这些」。不要只交 6 条头条。

### 2.5 发邮件

落盘后把简报发到 `zxc779177631@gmail.com`：

1. `ToolSearch` 加载 `["mcp__agent-mail__SendMessage"]`
2. `DeferExecuteTool` 调用 `mcp__agent-mail__SendMessage`：
   - `to`: `[{"email":"zxc779177631@gmail.com"}]`
   - `subject`: `商业热点口播链接 YYYY-MM-DD`
   - `body`: 第 2.4 步的简报（MARKDOWN）
   - `body_format`: `"MARKDOWN"`
   - `skip_confirmation`: `true`
3. 如果返回 `not_bound`（Agent 邮箱未开通），跳过发邮件，在回复里提醒用户开通。

### 2.6 飞书（默认，2026-08-21 接上）

本机飞书已通，**不需要 Webhook**。用 `lark-cli`（`/Users/a1-6/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli`，也可用 `~/.hermes/node/bin/lark-cli`）。

- 身份：**`--as bot`**（应用名「猪妞」）。user token 会过期；bot 不需要 `auth login`。
- 默认收件人：曾嘉润 `ou_b8d86bb065409519fa9412de3322b9b3`（私聊）。8/14 发视频、8/21 发热点简报都通了。
- 命令（路径必须相对 cwd；先把正文写成工作区临时 md）：

```bash
export LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1 LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1 LARK_CLI_NO_PROXY_WARN=1
LARK=/Users/a1-6/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli
cd "$工作区"
$LARK im +messages-send --as bot --user-id ou_b8d86bb065409519fa9412de3322b9b3 --markdown "$(cat feishu_hotspot.md)" --format json
```

- 成功看 JSON `ok == true`（不要看顶层 `code`）。失败不要假装推过。
- 若改推群：先把「猪妞」拉进目标群，再用 `--chat-id oc_xxx`。bot 的 `+chat-list` 为空=没进任何群。
- 用户身份缺 `im:resource:upload`，发文件/视频一律 `--as bot`。

### 2.7 企微（可选）

本机没有企业微信 App 登录态。能推的方式只有 **群机器人 Webhook**（`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...`）。

- Webhook 存在环境变量 `WECOM_WEBHOOK` 或工作区文件（用户提供后写入，禁止把 key 打进日志）时：把 30 话题简报 POST 成 markdown 文本（企微机器人 `msgtype=markdown`，内容截到约 4000 字）。
- **没有 Webhook 就不要假装推过。** 提醒用户：企微群 → 群设置 → 群机器人 → 复制 Webhook 发过来。
- 不要走 Hermes wecom adapter（本机未配置）。

## 3. 客户分流

- **叶明**：大品牌老板（年营收 3000万–1亿）。渠道价盘、平台权力 vs 效率、企业决策。不吃小老板账、知识付费教程。
- **邓毅轨 A**：实体/开店/抽成/AB货。
- **邓毅轨 B**：IP / 传播机制 / 0 宣发出圈。
- 内容标准优先于账号归属。账号匹配只影响优先级。

## 4. 现有 skill 拼法

| 能力 | 用谁 | 何时 |
|---|---|---|
| 全网热搜原榜（7 平台） | `trending-hub`（redfox） | 有 REDFOX_API_KEY，每次（发现层首选） |
| 跨平台聚合 TOP10 | `trending-hub-top10`（redfox） | 有 REDFOX_API_KEY，每次 |
| 抖音日榜按赛道 | `douyin-daily-hot`（redfox） | 有 REDFOX_API_KEY，每次（数据 T-1） |
| 近一周在吵什么 | WebSearch | 无 REDFOX_API_KEY 时降级 |
| 抖音链接+赞数 | talk-script-radar `crawl_douyin.sh` | 每次（主粮） |
| AI 圈背景 | aihot `items?mode=selected` | 可选一行 |
| 转写入库 | talk-script-radar collect | 人点完说收集之后 |

> 2026-08-20 教训：只靠 WebSearch 发现 = 0（用户给 2 个热点，第 3 个还是过期新闻）。发现层必须用结构化热榜，不能靠泛搜索猜。

talk-script-radar 自己写了「不是热点监控」。商业热点走本 skill，不要改它的 §3.1 转写闭环。

## 5. 定时

Automation：`商业热点口播日监控`，`FREQ=DAILY;BYHOUR=12;BYMINUTE=0`，cwd 为口播雷达工作区。  
已有「口播雷达每日推送」11:00 转写 daily，不要合并、不要改那条的 prompt。

## 6. 失败怎么说

| 情况 | 说法 |
|---|---|
| 未登录 / 验证码 | 需要你扫一次抖音码，扫完告诉我 |
| 发现层全是新闻标题 | 仍要抽成搜索词去爬；爬完再判有没有口播 |
| jsonl 当天该词 0 条 | 不编清单 |
| ≥1000 赞过滤后 0 | 「今日无新热点片」——正常交付 |

## 7. 触发词

商业热点 / 牛来 / 钟睒睒 / 刘润评 / 监控类似热点 / 今日商业在吵什么
