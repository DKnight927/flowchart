#!/usr/bin/env bash
set -e

REPO="https://github.com/DKnight927/flowchart"
SKILL_DIR="$HOME/.comate/skills/flowchart"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  flowchart skill 安装器（本地版）"
echo "  ─────────────────────────────────"
echo ""

# ─── 1. 检查 Python3 ──────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || error "需要 python3，请先安装"
info "Python3 已就绪"

# ─── 2. 检查 git ──────────────────────────────────────────────────────────
command -v git >/dev/null 2>&1 || error "需要 git，请先安装"

# ─── 3. 下载 skill 文件 ────────────────────────────────────────────────────
if [ -d "$SKILL_DIR" ]; then
  warn "已有旧版，备份后重新安装..."
  rm -rf "${SKILL_DIR}.bak"
  mv "$SKILL_DIR" "${SKILL_DIR}.bak"
fi

mkdir -p "$(dirname "$SKILL_DIR")"

git clone --quiet --no-checkout --depth=1 "$REPO" /tmp/flowchart_tmp 2>/dev/null
cd /tmp/flowchart_tmp
git sparse-checkout set flowchart-local/skill 2>/dev/null || true
git checkout --quiet
cd -

if [ -d "/tmp/flowchart_tmp/flowchart-local/skill" ]; then
  cp -R /tmp/flowchart_tmp/flowchart-local/skill "$SKILL_DIR"
  info "skill 已安装 → $SKILL_DIR"
else
  error "下载失败：找不到 flowchart-local/skill 目录"
fi

rm -rf /tmp/flowchart_tmp

# ─── 4. 验证 generate.py ──────────────────────────────────────────────────
SCRIPT="$SKILL_DIR/scripts/generate.py"
if [ -f "$SCRIPT" ]; then
  # Quick smoke test
  echo '{"format":"mermaid","diagramType":"flowchart","elements":[{"id":"a","type":"node","label":"Test"}]}' \
    | python3 "$SCRIPT" >/dev/null 2>&1 \
    && info "generate.py 验证通过" \
    || warn "generate.py 运行异常，请检查 Python3 环境"
else
  error "generate.py 未找到"
fi

# ─── Done ──────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────"
echo "  安装完成！"
echo ""
echo "  本地版无需配置 MCP 服务器。"
echo "  直接对 Comate/OpenClaw 说"画个流程图"即可。"
echo ""
echo "  脚本位置：$SCRIPT"
echo "  ────────────────────────────────────────────────"
echo ""
