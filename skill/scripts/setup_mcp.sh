#!/usr/bin/env bash
set -e

REPO="https://github.com/DKnight927/flowchart"
SKILL_DIR="$HOME/.comate/skills/flowchart"
SERVER_URL="${FLOWCHART_URL:-https://unrecuperative-rochell-mawkishly.ngrok-free.dev/mcp}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  flowchart skill 安装器"
echo "  ─────────────────────────────────"
echo ""

# ─── 1. 安装 skill 文件 ────────────────────────────────────────────────────
command -v git >/dev/null 2>&1 || error "需要 git，请先安装"

if [ -d "$SKILL_DIR/.git" ]; then
  warn "已有旧版，更新中..."
  git -C "$SKILL_DIR" pull --quiet
  info "skill 已更新"
elif [ -d "$SKILL_DIR" ]; then
  # 通过 sparse-checkout 只下载 skill/ 子目录
  rm -rf "$SKILL_DIR"
  git clone --quiet --no-checkout --depth=1 "$REPO" /tmp/flowchart_tmp
  git -C /tmp/flowchart_tmp sparse-checkout set skill 2>/dev/null || true
  git -C /tmp/flowchart_tmp checkout --quiet
  cp -R /tmp/flowchart_tmp/skill "$SKILL_DIR"
  rm -rf /tmp/flowchart_tmp
  info "skill 已安装 → $SKILL_DIR"
else
  git clone --quiet --no-checkout --depth=1 "$REPO" /tmp/flowchart_tmp
  git -C /tmp/flowchart_tmp sparse-checkout set skill 2>/dev/null || true
  git -C /tmp/flowchart_tmp checkout --quiet
  mkdir -p "$(dirname "$SKILL_DIR")"
  cp -R /tmp/flowchart_tmp/skill "$SKILL_DIR"
  rm -rf /tmp/flowchart_tmp
  info "skill 已安装 → $SKILL_DIR"
fi

# ─── 2. 检查服务器 ────────────────────────────────────────────────────────
HEALTH_URL="${SERVER_URL%/mcp}/health"
if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
  info "远程服务器可用"
else
  error "远程服务器不可用（$HEALTH_URL），请联系管理员确认服务是否开启"
fi

# ─── 3. 配置 mcp.json ────────────────────────────────────────────────────
MCP_JSON=""
for candidate in "$PWD/.cursor/mcp.json" "$HOME/.cursor/mcp.json"; do
  if [ -f "$candidate" ]; then
    MCP_JSON="$candidate"
    break
  fi
done

if [ -z "$MCP_JSON" ]; then
  MCP_JSON="$HOME/.cursor/mcp.json"
  mkdir -p "$(dirname "$MCP_JSON")"
  echo '{"mcpServers":{}}' > "$MCP_JSON"
  info "创建 $MCP_JSON"
fi

if grep -q '"flowchart"' "$MCP_JSON" 2>/dev/null; then
  warn "mcp.json 已有 flowchart 配置，正在更新..."
fi

python3 - "$MCP_JSON" "$SERVER_URL" <<'PYEOF'
import json, sys
path, url = sys.argv[1], sys.argv[2]
with open(path) as f: config = json.load(f)
if 'mcpServers' not in config: config['mcpServers'] = {}
config['mcpServers']['flowchart'] = {'transport': 'http', 'url': url}
with open(path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write('\n')
PYEOF

info "已写入 $MCP_JSON"

# ─── Done ─────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────"
echo "  安装完成！"
echo "  请重启 Cursor，然后直接对 AI 说"画个流程图"即可。"
echo "  ────────────────────────────────────────────────"
echo ""
