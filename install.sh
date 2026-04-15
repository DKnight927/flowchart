#!/usr/bin/env bash
set -e

# ─── Config ───────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/DKnight927/flowchart.git"
INSTALL_DIR="$HOME/.flowchart"
MCP_JSON="$HOME/.cursor/mcp.json"

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  flowchart installer"
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
ENTRY_POINT="$INSTALL_DIR/dist/index.js"
MCP_BLOCK=$(cat <<EOF
    "flowchart": {
      "transport": "stdio",
      "command": "node",
      "args": ["$ENTRY_POINT"]
    }
EOF
)

if [ -f "$MCP_JSON" ]; then
  # Check if already configured
  if grep -q "flowchart" "$MCP_JSON"; then
    warning "mcp.json 中已存在 flowchart 配置，跳过自动写入"
  else
    # Use Python to safely insert into JSON (macOS has python3 built-in)
    python3 - "$MCP_JSON" "$ENTRY_POINT" <<'PYEOF'
import json, sys

mcp_json_path = sys.argv[1]
entry_point   = sys.argv[2]

with open(mcp_json_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['flowchart'] = {
    'transport': 'stdio',
    'command': 'node',
    'args': [entry_point]
}

with open(mcp_json_path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write('\n')

print("mcp.json 已自动更新")
PYEOF
    info "已自动写入 $MCP_JSON"
  fi
else
  warning "未找到 $MCP_JSON，请手动添加以下配置："
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────"
echo "  安装完成！"
echo ""
echo "  请将以下配置加入你的 .cursor/mcp.json："
echo ""
echo '  "flowchart": {'
echo '    "transport": "stdio",'
echo '    "command": "node",'
echo "    \"args\": [\"$ENTRY_POINT\"]"
echo '  }'
echo ""
echo "  然后重启 Cursor 即可使用 liuchengtu 工具。"
echo "  ────────────────────────────────────────────────"
echo ""
