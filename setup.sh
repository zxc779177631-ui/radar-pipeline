#!/bin/bash
# radar-pipeline 一键部署（新电脑安装用）
# 用法: bash setup.sh
# 作用: 安装依赖 → 复制 skills 到 ~/.workbuddy/skills/ → 引导 SiliconFlow key
set -euo pipefail

echo "=== radar-pipeline 部署 ==="
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1) 系统依赖（macOS）
if [ "$(uname)" = "Darwin" ]; then
  if ! command -v brew >/dev/null; then
    echo "❌ 需要 Homebrew，先装: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
  fi
  echo "→ 检查 ffmpeg / uv ..."
  command -v ffmpeg >/dev/null || brew install ffmpeg
  command -v uv >/dev/null || brew install uv
fi

# 2) 复制 skills 到用户目录
echo "→ 复制 skills → ~/.workbuddy/skills/"
mkdir -p ~/.workbuddy/skills/
cp -r "$REPO_DIR/skills/talk-script-radar" ~/.workbuddy/skills/
cp -r "$REPO_DIR/skills/video-to-text" ~/.workbuddy/skills/
echo "✓ talk-script-radar + video-to-text 已安装"

# 3) SiliconFlow key 引导
KEY_FILE=~/.workbuddy/secrets/siliconflow
if [ -f "$KEY_FILE" ]; then
  echo "✓ 已检测到 SiliconFlow key: $KEY_FILE"
else
  echo "→ 请粘贴你的 SiliconFlow API key（sk- 开头，粘贴后回车）:"
  mkdir -p ~/.workbuddy/secrets
  read -r KEY
  printf '%s' "$KEY" > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
  echo "✓ key 已保存到 $KEY_FILE (chmod 600)"
fi

# 4) MediaCrawler（抖音采集，可选）
if [ ! -d ~/MediaCrawler ]; then
  echo "→ MediaCrawler 未安装。可选安装:"
  echo "  git clone https://github.com/NanmiCoder/MediaCrawler ~/MediaCrawler"
  echo "  cd ~/MediaCrawler && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  echo "  首次运行需扫码登录抖音"
else
  echo "✓ MediaCrawler 已存在"
fi

# 5) 工作台
echo "→ 工作台: $REPO_DIR/workbench/口播雷达工作台.html（浏览器打开即可，localStorage 本机保存）"

echo
echo "=== 部署完成 ==="
echo "验证: V2T_TRANSCRIBER=api bash ~/.workbuddy/skills/video-to-text/scripts/run.sh \"<抖音URL>\""
