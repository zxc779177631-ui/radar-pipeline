# Changelog

## [1.4.2] 2026-09-15 · 首批后空搜即停

- 2026-09-15 日监控：首批 4 词（苹果破发/华为折叠屏/广汽停牌/宇树市值）正常；同会话后续关键词几乎全是 `page: 1 is empty`，28 秒间隔仍空，不是验证码。中间一次 `TargetClosedError`。
- 规则：空搜连续 2 次停止补爬；没片只留热搜词；日榜链可补但要标明。宇树高赞片>7 天标旧热点，只留回撤 56% 新片。

## [1.4.1] 2026-08-26 · crawl 每批最多 4 词

- 2026-08-26 日监控：`crawl_douyin.sh daily` 一次塞 8 词，跑到第 4 个（小熊电器）Playwright `TargetClosedError`，前 3 词数据还在。改成每批 4 词后连续 4 批都跑完。
- cookie 仍有效，不必扫码。今日 daily jsonl 爬前为空，抽出后还原为空文件。

## [1.4.0] 2026-08-21 · 飞书默认通道（猪妞私聊）

- 用户问「飞书怎么接入」：本机 lark-cli 已通，bot「猪妞」ready，user=曾嘉润。不需要 Webhook。
- 默认 `--as bot --user-id ou_b8d86bb065409519fa9412de3322b9b3` 发 markdown。2026-08-21 12:36 测通（message_id `om_x100b67491207f4a8b3e7011f6f08001`）。
- 改推群要先把猪妞拉进群；bot chat-list 当前为空。
- 企微仍要 Webhook，飞书不替代邮件（邮件继续发）。

## [1.3.0] 2026-08-21 · 约 30 话题（含中热度）+ 企微 Webhook 可选

- 用户：6 条不够；黑神话钟馗这种中热度也要。清单改为约 30 个话题。
- 软广淹没（飞鹤）不给广告链接；没口播的话题只留热搜词。
- crawl 可分批，每批抽出后还原 jsonl。
- 企微：本机无登录态，只能群机器人 Webhook（WECOM_WEBHOOK）。没有就不要假装推过。

## [1.2.1] 2026-08-21 · Key 在 zshrc；top10 聚类不可信；实测自己发现 6 簇

- `REDFOX_API_KEY` 写在 `~/.zshrc`，自动化/对话环境经常读不到。跑 redfox 前从 zshrc 注入，禁止把 Key 打进命令行。
- `trending-hub-top10` 的 source_keyword 会把商业事件归到「日本」「七夕」，只看 title。
- `douyin-daily-hot` 没有「商业」赛道，用 `--type 财富理财` / `个人成长`。
- 实测 2026-08-21：自己发现许家印无期 / 宇树大跌 / 董明珠技校 / 公积金新规 / 小熊吃灰 / 泡泡玛特不及预期。钟睒睒/牛来/AB货不再当发现。

## [1.2.0] 2026-08-20 · 接入 redfox 发现层（修复「自己发现 = 0」）

- 用户复盘：三个热点里 2 个是他给的（钟睒睒/牛来），第 3 个（AB货）是过期新闻——发现层失效。
- 修复：发现层改为 redfox 优先——`trending-hub`（7 平台热搜原榜）+ `trending-hub-top10`（跨平台聚合）+ `douyin-daily-hot`（抖音赛道日榜）；无 REDFOX_API_KEY 才降级 WebSearch。
- 安装：`~/.workbuddy/skills/trending-hub`、`~/.workbuddy/skills/trending-hub-top10`（来自 redfox-data/redfox-community，已审计 P2 安全，仅调 redfox.hk 官方 API）。`douyin-daily-hot` 此前已装。
- 仍缺：REDFOX_API_KEY（需用户去 https://redfox.hk 注册获取）。

## [1.1.0] 2026-08-20 · 加邮件推送 + 改 12:00

- 定时从 09:00 改 12:00（用户要求中午发邮件）。
- 新增 §2.5 发邮件步骤：用 `mcp__agent-mail__SendMessage` 发 MARKDOWN 简报到 `zxc779177631@gmail.com`，`skip_confirmation=true`。
- Agent 邮箱未开通时优雅降级，不阻断主流程。
- Automation prompt 同步更新。

## [1.0.0] 2026-08-20 · 首发

- 从「口播雷达入库」会话拆出独立链路：热点 → 可点链接 → 人审 → collect。
- 实测：MediaCrawler cookie 有效时可 30 秒搜完 5 词；必须备份/还原当日 jsonl，否则会污染 11:00 口播雷达。
- 红狐、零一本机无 Key，默认不调用。
