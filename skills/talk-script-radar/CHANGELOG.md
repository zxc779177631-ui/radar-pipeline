# CHANGELOG · talk-script-radar

> 每次修改必须：更新本文件 + 提升 SKILL.md 的 version。

## [1.7.2] 2026-09-22 · 分叉合并 + GitHub 备份补齐

三份副本此前**双向分叉**，本版合并为单线，并把 GitHub 备份从 8-15 的 1.6.0 快照补到当前：

- 合入 1.7.1：§0 商业热点分流、`transcribe_robust.sh`（自动重试 + 指数退避）
- 合入 9-03 排除词：`default-tags.yaml` 新增 P1 数字人话术 / P2 同行卖课引流 / P4 贷款理财 / P6 剧情整蛊搞笑
- 合入 8-25 修复：`merge_inbox.py` 归一化 U+2028/U+2029，修抖音标题换行导致整条漏解析
- 保留 repo 侧更新的小红书链路：`build_list.py` / `radar_ai_filter.py` / `radar_ai_ingest.py` 平台感知（抖音 5000 / 小红书 1000）+ `crawl_xhs.sh` / `transcribe_xhs_*.sh|py`
- 教训：同一 skill 存在 `radar-pipeline/skills`、Obsidian 库 `skills/`、`~/.workbuddy/skills` 三份副本，改完必须同步，否则分叉

## [1.7.1] 2026-08-20 · 商业热点分流

- §0 标明：牛来/钟睒睒/企业家争议走 `business-hotspot-radar`（只出链接），等人说「收集」再回本 skill collect。本 skill 仍不是热点监控。

## [1.7.0] 2026-08-15 · 第一性收口：先杀再转 + 入库回写账本

- `build_list.py --min-likes` 默认改为 **5000**（传 0 才关闭），低赞不再靠人记得加参数
- 标题排除词前移到清单层：跳舞/访谈/数字人等进 `assets/default-tags.yaml`，转写只跑幸存者
- `radar_ai_ingest.py` 一次做完：搬 md + 账本 `ingested` + reject 标 `excluded` + 写出 `待出RS卡_{主题}_{日期}.md`
- collect 默认关评论（`GET_COMMENT=false`）；daily 仍默认可开
- 诚实边界：所谓 AI 预筛只看标题+字数；`reference-copy-ingester` 没有批量脚本，入库后必须按队列由 agent 出 RS 卡
- 真源只留账本 + 库里的稿。只搬文件不算入库完成

## [1.6.0] 2026-08-15 · 复盘迭代：工作台同步脚本 + 铁律落地到 SKILL.md

- §2 铁律新增「不入低赞数据」条目（赞数门槛从 CHANGELOG 提升为 SKILL.md 正文铁律）
- §3.4 补 `radar_sync_workbench.py` 工作台状态同步脚本（状态映射、覆盖导入坑、用户「全入」回写流程）
- §6 命令补 `--min-likes 5000` 用法（源头拦截）
- 用户确认流程：review「全入」→ Obsidian 补搬 + 备份 JSON 回写 ingested，工作台只保留待人工确认项

## [1.5.0] 2026-08-14 · 赞数门槛（复盘后铁律）

- **用户复盘痛点**：AI 预筛把几百赞/几十赞的低赞数据也入库了（331 条里 50 条 <1000 赞、最低 4 赞）
- **新铁律**：抖音 ≥5000 赞才入库，小红书 ≥1000。未达门槛 = 未被市场验证 = 不入库不交确认
- 双层拦截：`build_list.py` 加 `--min-likes`（源头，collect/daily 都用）+ `radar_ai_filter.py` 加 `MIN_LIKES`（预筛层）
- 已入库低赞 139 条从 Obsidian 撤出（移 `/tmp/radar_lowlikes_removed/` 可恢复），三批保留 192 条
- 重新生成工作台备份：192 ingested + 36 review + 157 rejected + 10 pending
- 待人工确认清单按新门槛重出（安徽同城 16 / 长鑫 13 / 企业AI 7）

## [1.4.0] 2026-08-14 · AI 预筛入库（大批量默认流程）

- 新增 `scripts/radar_ai_filter.py`（分类 ingest/review/reject/missing）+ `scripts/radar_ai_ingest.py`（生成入库 md 搬 Obsidian）
- 用户确认：人工一个个过眼 → AI 预筛，大部分直接入库，只把拿不准的（超长>4000字/超短<150字）列清单交用户
- 剔除规则（标题特征词）：无口播（跳舞/变装/BGM/翻唱/街拍/舞蹈/特效/快闪/广场舞/手势舞/魔术/穿搭展示/健身操/舞蹈教学）+ 重策划访谈（访谈/专访/对谈/对话/做客/夜话/面对面/圆桌/论坛）
- 调优教训：①vlog≠无口播靠字数兜底；②「卡点」「跟练」误伤口播干货已删；③问答密度检测误伤人间观察/探店，放弃；④财经深度口播普遍长，阈值 4000
- 入库 frontmatter 标 `curation_status: ai_reviewed_valid`；review 清单归档工作区 `待人工确认_{主题}.md`

## [1.3.3] 2026-08-14 · 反面排除 + 职场主题 + 云端 ASR

- 排除词补：访谈节目 / 程前朋友圈 / 对谈访谈 / 数字分身（数字人原有）
- 实习生/找工作可入库，主题进「职场」，不算商业，不要进 exclude
- 人改口后 `reviewed_bad` 可升 `ingested`（只升不降）
- 用户点名云端 ASR：`V2T_TRANSCRIBER=api` + `~/.workbuddy/secrets/siliconflow`，失败直接报，禁止 fallback 本地、禁止用 zshrc 占位 key
- 工作台 `suggestFolder` 按标题语义，职场优先于商业/AI工具

## [1.3.2] 2026-08-14 · 过完了以工作台为准

- 「过完了」真源是工作台 `wb_radar_v1`，禁止误读 Downloads 同日旧导出
- Chrome `file://` 状态在 LevelDB（UTF-16LE）；读不到 JS 就按 vid 窗口抽最后一次 status
- 主题分拣按标题语义，全文关键词会把财税/执行力误丢进 AI 工具
- 近重复分卡；工作台 ingested 标机写不进 Chrome 时，让用户刷新或点「批量标已入库」

## [1.3.1] 2026-08-14 · 账本不降级 + 清单不互盖

- `ledger.upsert` 按 status 只升不降，避免 `merge_inbox` 把已入库片打回 transcribed
- `build_list.py`：collect 默认写 `爆款口播候选清单_全量_YYYY-MM-DD.md`，不再覆盖当日 daily 清单

## [1.3.0] 2026-08-14 · 送到能审稿

- daily 契约改成：账本去重 → 只转新片 → inbox 带稿过眼；不再把「只有链接的清单」当交付
- 新增 `seen-ledger.json`（跨天/跨机 vid 账本）+ `bootstrap_ledger.py` / `merge_inbox.py`
- `build_list.py` 增加账本已见剔除、排除词剔除
- 用户说「过完了/入库」：搬 `【03】` + 立刻 `reference-copy-ingester`，不再先导出 JSON 再确认
- 人审只过 ≥150 字稿；短稿标黄不入库；不做全文校对
- 一台生产机跑前半段；不拆成「那台只推链接、这台再转写」
- 工作台补「导入清单.md」（按 vid 合并）；备份 JSON 才覆盖

## [1.2.0] 2026-08-13 · 工作台闭环与对稿铁律

- 补 §3.4：转写 → 过眼看稿 → 标有效/类型 → 入库；单文件工作台 + `ingest_radar.py`，用户说入库就搬、不确认
- 铁律：抖音 id 当字符串从 URL 抽取；SEED 稿底保不被脏 localStorage 冲掉；<150 字短稿不得当范文入库
- 修正转写耗时（本地 1–2 分钟/条，不是 10 秒）；SiliconFlow 401 回退本地；用产物文件验收进度
- 明确清单链接是抖音不是视频号；不做常驻 localhost

## [1.1.0] 2026-08-13 · 入库闸门改到转写之后

- collect **允许老片进清单**，daily 仍只收近 90 天
- 入不入库不在清单层判：先转逐字稿，发现纯 BGM / 无口播 / 混剪（如美妆卡点）视为无效，不进 `【03.参考资料】/文案参考/`
- 有效口播才走 `reference-copy-ingester`

## [1.0.0] 2026-08-13 · 首发

- 定位：只找被市场验证过的口播视频，输出候选清单；不转写、不入库、不做客户关联度
- 双场景：daily（发现层 + 近 90 天过滤 + 小量）/ collect（给定标签大量攒、不过时间）
- 提取层默认抖音 MediaCrawler；小红书默认关闭
- 发现层默认 WebSearch，不强制依赖 agent-reach
- 诚实边界：搜索结果无粉丝数，禁止宣称「已验证低粉」；口播只做标题启发式
- 附 `scripts/build_list.py`：去重、时间窗、分档、评论信号、写 Markdown
