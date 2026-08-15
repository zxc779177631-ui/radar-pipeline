# 跨机清单（生产机）

不要拆成「A 只推链接、B 再转写」。B 会重复去重、重复等转写。

## 必须有

1. WorkBuddy + `talk-script-radar` 1.6 + `video-to-text`（纯云端 ASR）+ `reference-copy-ingester`
2. `~/MediaCrawler`（`.venv` 就绪）。抖音要在这台扫一次码，cookie 在该目录
3. `video-to-text`：纯云端 ASR（`V2T_TRANSCRIBER=api` + `~/.workbuddy/secrets/siliconflow`）。本地 whisper 已废弃（模型已删，别装回）。SiliconFlow key 失效就报错让用户检查云端
4. Obsidian 库。macOS 默认  
   `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/git`  
   Windows 另改路径
5. 账本 `【03.参考资料】/文案参考/雷达清单/seen-ledger.json`  
   换机先跑 `bootstrap_ledger.py`

## 同步什么

- **要同步**：账本、`雷达inbox_YYYY-MM-DD.json`（含逐字稿）、过眼后的入库 md / RS 卡（走 Obsidian）
- **不要只同步**：只有链接的清单 md、浏览器 localStorage、抖音 cookie

## 过眼机（可选）

只打开已带稿的工作台 / inbox。不再手贴清单，不再先看标题。
