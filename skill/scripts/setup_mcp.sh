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

# ─── 3. 配置 Comate config.yaml ──────────────────────────────────────────
COMATE_YAML=""
for candidate in "$HOME/.comate/config.yaml" "$HOME/.config/comate/config.yaml"; do
  if [ -f "$candidate" ]; then
    COMATE_YAML="$candidate"
    break
  fi
done

if [ -n "$COMATE_YAML" ]; then
  if grep -q 'flowchart' "$COMATE_YAML" 2>/dev/null; then
    warn "config.yaml 已有 flowchart 配置，正在更新..."
    # 删除旧的 flowchart 块（可能是错误的 stdio 格式）
    python3 - "$COMATE_YAML" "$SERVER_URL" <<'PYEOF'
import sys, re
path, url = sys.argv[1], sys.argv[2]
with open(path) as f: content = f.read()
# 移除旧的 flowchart 配置块
content = re.sub(r'\s+flowchart:\s*\n(?:[ \t]+[^\n]*\n)*', '\n', content)
with open(path, 'w') as f: f.write(content)
PYEOF
  fi

  python3 - "$COMATE_YAML" "$SERVER_URL" <<'PYEOF'
import sys, re
path, url = sys.argv[1], sys.argv[2]
with open(path) as f: content = f.read()

new_block = f"""  flowchart:
    transport: http
    url: {url}
"""

if 'mcpServers:' in content:
    content = re.sub(r'(mcpServers:\s*\n)', r'\1' + new_block, content, count=1)
else:
    content = content.rstrip() + '\nmcpServers:\n' + new_block

with open(path, 'w') as f: f.write(content)
PYEOF
  info "已写入 $COMATE_YAML（HTTP 格式）"
else
  warn "未找到 Comate config.yaml，跳过（Comate 用户请手动添加以下配置）："
  echo ""
  echo "    # ~/.comate/config.yaml"
  echo "    mcpServers:"
  echo "      flowchart:"
  echo "        transport: http"
  echo "        url: $SERVER_URL"
  echo ""
fi

# ─── 4. 配置 Cursor mcp.json（可选）────────────────────────────────────────
MCP_JSON=""
for candidate in "$PWD/.cursor/mcp.json" "$HOME/.cursor/mcp.json"; do
  if [ -f "$candidate" ]; then
    MCP_JSON="$candidate"
    break
  fi
done

if [ -n "$MCP_JSON" ]; then
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
fi

# ─── Done ─────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────"
echo "  安装完成！"
echo "  请在 IDE 的 MCP 设置中刷新连接，"
echo "  然后对 Comate/OpenClaw 说"画个流程图"即可。"
echo "  ────────────────────────────────────────────────"
echo ""
