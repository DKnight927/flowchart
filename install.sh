#!/usr/bin/env bash
set -e

# ─── Config ───────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/DKnight927/flowchart.git"
INSTALL_DIR="$HOME/.flowchart"
MCP_JSON="$HOME/.cursor/mcp.json"
PORT="${FLOWCHART_PORT:-3000}"

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  flowchart MCP server installer"
echo "  ─────────────────────────────────"
echo ""

# ─── Check dependencies ───────────────────────────────────────────────────────
command -v git  >/dev/null 2>&1 || error "需要 git，请先安装：https://git-scm.com"
command -v node >/dev/null 2>&1 || error "需要 Node.js，请先安装：https://nodejs.org"
command -v npm  >/dev/null 2>&1 || error "需要 npm，通常随 Node.js 一起安装"

info "环境检查通过（git / node / npm）"

# ─── Clone or update ──────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  warning "已检测到旧版本，正在更新..."
  git -C "$INSTALL_DIR" pull --quiet
  info "代码已更新"
else
  info "正在克隆仓库到 $INSTALL_DIR ..."
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  info "克隆完成"
fi

# ─── Install & build ──────────────────────────────────────────────────────────
info "正在安装依赖..."
npm --prefix "$INSTALL_DIR" install --quiet

info "正在编译..."
npm --prefix "$INSTALL_DIR" run build --quiet

info "编译完成 → $INSTALL_DIR/dist/index.js"

# ─── Auto-update mcp.json ─────────────────────────────────────────────────────
if [ -f "$MCP_JSON" ]; then
  if grep -q '"flowchart"' "$MCP_JSON"; then
    warning "mcp.json 中已存在 flowchart 配置，跳过自动写入"
  else
    python3 - "$MCP_JSON" "$PORT" <<'PYEOF'
import json, sys
path, port = sys.argv[1], sys.argv[2]
with open(path) as f: config = json.load(f)
if 'mcpServers' not in config: config['mcpServers'] = {}
config['mcpServers']['flowchart'] = {
    'transport': 'http',
    'url': f'http://localhost:{port}/mcp'
}
with open(path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write('\n')
print("mcp.json 已自动更新")
PYEOF
    info "已自动写入 $MCP_JSON"
  fi
else
  warning "未找到 $MCP_JSON，请手动添加以下配置"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────────"
echo "  安装完成！"
echo ""
echo "  启动服务器（每次开机后运行一次）："
echo "    node $INSTALL_DIR/dist/index.js"
echo ""
echo "  或者设置端口："
echo "    PORT=3001 node $INSTALL_DIR/dist/index.js"
echo ""
echo "  mcp.json 配置："
echo "    \"flowchart\": {"
echo "      \"transport\": \"http\","
echo "      \"url\": \"http://localhost:${PORT}/mcp\""
echo "    }"
echo ""
echo "  启动后重启 Cursor 即可使用 liuchengtu 工具。"
echo "  ────────────────────────────────────────────────────"
echo ""
