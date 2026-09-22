#!/bin/bash
# radar-pipeline 一键部署（新电脑安装用）
# 用法: bash setup.sh
# 作用: 检查依赖 → 复制全部 skills 到 ~/.workbuddy/skills/ → 引导 SiliconFlow key
#
# 支持 macOS / Linux / Windows(Git Bash 或 WSL)
set -uo pipefail

echo "=== radar-pipeline 部署 ==="
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DST="${WORKBUDDY_SKILLS_DIR:-$HOME/.workbuddy/skills}"

# 识别平台
case "$(uname -s)" in
  Darwin) PLAT="macos" ;;
  MINGW*|MSYS*|CYGWIN*) PLAT="windows" ;;
  Linux) PLAT="linux" ;;
  *) PLAT="unknown" ;;
esac
echo "→ 平台: $PLAT"

# 1) 系统依赖
need_ffmpeg=0; need_uv=0
command -v ffmpeg >/dev/null || need_ffmpeg=1
command -v uv     >/dev/null || need_uv=1

if [ "$need_ffmpeg" = 1 ] || [ "$need_uv" = 1 ]; then
  echo "→ 缺少依赖 (ffmpeg=$need_ffmpeg uv=$need_uv)，尝试安装 ..."
  case "$PLAT" in
    macos)
      if command -v brew >/dev/null; then
        [ "$need_ffmpeg" = 1 ] && brew install ffmpeg
        [ "$need_uv" = 1 ] && brew install uv
      else
        echo "⚠ 未装 Homebrew，请手动安装 ffmpeg / uv：https://brew.sh"
      fi ;;
    windows)
      if command -v winget >/dev/null; then
        [ "$need_ffmpeg" = 1 ] && winget install --id Gyan.FFmpeg -e
        [ "$need_uv" = 1 ] && winget install --id astral-sh.uv -e
      elif command -v scoop >/dev/null; then
        [ "$need_ffmpeg" = 1 ] && scoop install ffmpeg
        [ "$need_uv" = 1 ] && scoop install uv
      else
        echo "⚠ 未装 winget/scoop，请手动安装 ffmpeg 与 uv"
      fi ;;
    linux)
      echo "  请手动装：sudo apt install ffmpeg ; curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
  esac
else
  echo "✓ ffmpeg / uv 已就绪"
fi

# 2) 复制全部 skills
echo "→ 复制 skills → $SKILLS_DST/"
mkdir -p "$SKILLS_DST"
installed=0
for d in "$REPO_DIR"/skills/*/; do
  name="$(basename "$d")"
  rm -rf "$SKILLS_DST/$name"
  cp -r "$d" "$SKILLS_DST/$name"
  chmod +x "$SKILLS_DST/$name"/scripts/*.sh 2>/dev/null || true
  chmod +x "$SKILLS_DST/$name"/shared/scripts/*.sh 2>/dev/null || true
  echo "  ✓ $name"
  installed=$((installed+1))
done
echo "✓ 已安装 $installed 个 skill"

# 修一处硬编码：XHS 脚本假定 xiaohongshu-video-to-text 在 ~/.workbuddy/skills/ 下。
# 若自定义了 WORKBUDDY_SKILLS_DIR，这里给个提示（脚本内路径仍是默认位置）。
if [ "$SKILLS_DST" != "$HOME/.workbuddy/skills" ]; then
  echo "⚠ 你用了自定义安装目录，XHS 转写脚本内的硬编码路径仍指向 ~/.workbuddy/skills/"
  echo "  如需改，见 skills/talk-script-radar/scripts/transcribe_xhs_*.{sh,py} 里的 XHS_EXTRACT / SRT2TXT"
fi

# 3) SiliconFlow key
KEY_FILE="$HOME/.workbuddy/secrets/siliconflow"
if [ -f "$KEY_FILE" ]; then
  echo "✓ 已检测到 SiliconFlow key: $KEY_FILE"
else
  echo "→ 请粘贴你的 SiliconFlow API key（sk- 开头，粘贴后回车）:"
  mkdir -p "$HOME/.workbuddy/secrets"
  read -r KEY
  printf '%s' "$KEY" > "$KEY_FILE"
  chmod 600 "$KEY_FILE" 2>/dev/null || true
  echo "✓ key 已保存到 $KEY_FILE"
  echo "  注意：不要写进 shell 配置（曾踩占位符坑导致 401），skill 只读这个文件"
fi

# 4) MediaCrawler 采集引擎（可选，采集层需要）
if [ -d "$HOME/MediaCrawler" ]; then
  echo "✓ MediaCrawler 已存在: $HOME/MediaCrawler"
else
  echo "→ MediaCrawler 未安装（采集层需要）。建议用 media-crawler skill 自动装："
  echo "     bash $SKILLS_DST/media-crawler/scripts/setup.sh"
  echo "  手动安装："
  echo "     git clone https://github.com/NanmiCoder/MediaCrawler ~/MediaCrawler"
  echo "     cd ~/MediaCrawler && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  echo "  首次运行需在本机扫码登录抖音 / 小红书"
fi

# 5) 可选发现层（redfox API）
if [ -n "${REDFOX_API_KEY:-}" ]; then
  echo "✓ 检测到 REDFOX_API_KEY（trending-hub / douyin-daily-hot 发现层可用）"
else
  echo "· 未设 REDFOX_API_KEY：business-hotspot-radar 的发现层会降级到 WebSearch"
fi

# 6) 工作台
echo "→ 工作台: $REPO_DIR/workbench/口播雷达工作台.html（浏览器直接打开，localStorage 本机保存）"

echo
echo "=== 部署完成 ==="
echo "自测: V2T_TRANSCRIBER=api bash $SKILLS_DST/video-to-text/scripts/run.sh \"<抖音URL>\""
