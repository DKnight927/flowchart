---
name: flowchart
description: 产品需求文档解构与可视化 skill。将 PRD/需求文档自动转化为流程图、序列图、类图、ER图、思维导图、架构图、网络拓扑图，并自动检测缺失分支（断网、无权限、空状态等异常场景）。当用户要求画图、分析需求文档、生成流程图、可视化产品逻辑时触发。触发词：画流程图、生成序列图、分析需求文档、PRD可视化、draw flowchart、generate diagram、ER图、类图、思维导图、架构图、网络拓扑。
---

# PRD 解构与可视化

将产品需求文档自动解构为可视化图表，并在关键节点标注可能缺失的异常分支。

## ⛔ MANDATORY RULE — READ THIS FIRST

**DO NOT generate any diagram, call any tool, or produce any output until you have completed Step 1 (Greet & Align Requirements) below AND the user has explicitly confirmed what they want.**

This means:
- DO NOT call `liuchengtu` before user confirms diagram type and requirements
- DO NOT fabricate download links, file URLs, or diagram content under any circumstances
- DO NOT skip requirement alignment even if user says "generate a flowchart" — you must still confirm specifics
- If `liuchengtu` tool is not available, run setup (see Prerequisites) — do NOT fall back to generating fake content

Violations of this rule produce incorrect, unusable output.

## Prerequisites — MCP Tool Setup

This skill relies on the `liuchengtu` MCP tool. The tool runs as a remote HTTP server. Register it with:

**Comate / OpenClaw** — add to `~/.comate/config.yaml`:
```yaml
mcpServers:
  flowchart:
    transport: http
    url: https://<ngrok-url>/mcp
```

**Cursor** — add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "flowchart": {
      "transport": "http",
      "url": "https://<ngrok-url>/mcp"
    }
  }
}
```

Or run the one-line installer (auto-detects both config files):
```bash
curl -fsSL https://raw.githubusercontent.com/DKnight927/flowchart/main/skill/scripts/setup_mcp.sh | bash
```

After completion, reload MCP in your IDE settings, then retry.

## Core Workflow

### Step 1: Greet & Align Requirements (MANDATORY — DO NOT SKIP)

When user triggers this skill, you MUST start with this step. Even if the user says "画个流程图", you must still present capabilities and ask clarifying questions before generating anything.

Present the following to the user:

---

**我可以帮你做以下事情：**

**支持的图表类型：**
- 流程图（flowchart）— 产品功能流程、业务逻辑、用户操作路径
- 序列图（sequence）— 系统交互时序、API 调用链、前后端通信
- 类图（class）— 数据模型关系、系统对象结构
- ER 图（er）— 数据库表结构、实体关系
- 思维导图（mindmap）— 需求拆解、功能模块梳理、信息架构
- 架构图（architecture）— 系统架构、模块划分、技术栈
- 网络拓扑图（network）— 部署架构、网络节点关系

**支持的输出格式：**
- Mermaid（默认）— 文本格式，可嵌入 Markdown/GitHub/Notion
- Draw.io — XML 格式，可用 draw.io 打开编辑
- Excalidraw — JSON 格式，手绘风格，Obsidian 可直接打开

**特殊能力：**
- 自动分析需求文档，提取功能逻辑并生成流程图
- 在关键节点自动标注可能缺失的异常分支

---

Then ask user:
1. 你需要哪种类型的图？
2. 输出格式偏好？（默认 mermaid）
3. 有需求文档可以直接发给我，我会自动分析
4. 对图有其他要求吗？（如方向、配色、详细程度）

**STOP HERE. Wait for user response. Do NOT proceed until user answers.**

### Step 2: Analyze Input

Two modes:

**Mode A — User describes requirements verbally:**
- Extract key entities, flows, and relationships from description
- Confirm understanding with user before generating

**Mode B — User provides a requirement document (PRD):**
- Read the entire document
- Extract all product features and their logic flows
- Identify: user actions, system responses, data flows, state transitions
- Build a structured model of the product logic
- Proceed to Step 3 (branch checking) before generating

### Step 3: Branch Completeness Check (CRITICAL)

Before generating the final diagram, analyze every decision node and interaction point for missing branches. Check for these common missing scenarios:

**Network/Infrastructure:**
- 断网 / 网络超时 / 请求失败
- 服务不可用 / 接口降级
- CDN 加载失败

**Permission/Auth:**
- 未登录 / 登录态过期
- 无权限 / 权限不足
- 账号被封禁 / 冻结

**Data/State:**
- 空状态（列表为空、搜索无结果、首次使用）
- 数据加载中（loading）
- 数据异常 / 格式错误
- 并发冲突 / 数据已被他人修改

**Input/Validation:**
- 输入校验失败
- 超出限制（字数、文件大小、次数）
- 重复提交 / 幂等

**Business Edge Cases:**
- 操作中途取消
- 退款/撤销/回退
- 过期/到期状态

**Output format for missing branches:**
For each missing branch found, add a node with:
- shape: `hexagon`
- style: `{ fillColor: "#FFF3E0", strokeColor: "#E65100", fontColor: "#E65100" }`
- label prefixed with `⚠️`

Connect these warning nodes to the relevant decision/action nodes with dashed edges.

Present the list of detected missing branches to the user BEFORE generating. Ask:
> "我检测到以下可能缺失的异常分支，是否需要加入图中？"

Then list each missing branch with explanation. User can choose which ones to include.

### Step 4: Generate Diagram

After user confirms, call `liuchengtu` with the complete spec.

**Format selection defaults:**
- Flowchart/Architecture/Network → `mermaid` format, `TD` direction
- Sequence → `mermaid` format
- Class/ER → `mermaid` format
- Mindmap → `mermaid` format
- If user requests editable file → `drawio` format
- If user uses Obsidian/wants hand-drawn style → `excalidraw` format

**Output handling after tool returns:**
The tool response contains raw diagram content between `---DIAGRAM_CONTENT_START---` and `---DIAGRAM_CONTENT_END---` markers. Extract the content and display it to the user:
- For mermaid: wrap in ` ```mermaid ` code block — renders inline in most tools
- For drawio: wrap in ` ```xml ` and tell user to save as `.drawio` file, open with draw.io
- For excalidraw: wrap in ` ```json ` and tell user to save as `.excalidraw` file

### Step 5: Iterate

After generating, ask if user needs adjustments:
- Add/remove nodes
- Change layout direction
- Adjust detail level
- Export to different format
- Generate additional diagram types from the same document

## Element Construction Guide

### Flowchart / Architecture / Network
```json
{
  "format": "mermaid",
  "diagramType": "flowchart",
  "elements": [
    { "id": "n1", "type": "node", "label": "Start", "shape": "oval" },
    { "id": "n2", "type": "node", "label": "Decision?", "shape": "diamond" },
    { "id": "e1", "type": "edge", "source": "n1", "target": "n2" },
    { "id": "warn1", "type": "node", "label": "⚠️ 断网", "shape": "hexagon",
      "style": { "fillColor": "#FFF3E0", "strokeColor": "#E65100" } },
    { "id": "ew1", "type": "edge", "source": "n2", "target": "warn1",
      "style": { "dashPattern": "5 3" } }
  ]
}
```

### Sequence
```json
{
  "format": "mermaid",
  "diagramType": "sequence",
  "elements": [
    { "id": "User", "type": "node", "label": "User", "participantType": "actor" },
    { "id": "Server", "type": "node", "label": "Server" },
    { "id": "e1", "type": "edge", "source": "User", "target": "Server",
      "label": "POST /login", "messageType": "sync" },
    { "id": "e2", "type": "edge", "source": "Server", "target": "User",
      "label": "200 OK", "messageType": "return" }
  ]
}
```

### Class
```json
{
  "format": "mermaid",
  "diagramType": "class",
  "elements": [
    { "id": "User", "type": "node", "label": "User",
      "properties": ["+String name", "+String email"],
      "methods": ["+login()", "+logout()"] },
    { "id": "Order", "type": "node", "label": "Order",
      "properties": ["+int id", "+Date createdAt"] },
    { "id": "e1", "type": "edge", "source": "User", "target": "Order",
      "relationType": "association", "label": "places" }
  ]
}
```

### ER
```json
{
  "format": "mermaid",
  "diagramType": "er",
  "elements": [
    { "id": "User", "type": "node", "label": "User",
      "attributes": [
        { "name": "id", "type": "int", "key": "PK" },
        { "name": "name", "type": "string" }
      ] },
    { "id": "Order", "type": "node", "label": "Order",
      "attributes": [
        { "name": "id", "type": "int", "key": "PK" },
        { "name": "user_id", "type": "int", "key": "FK" }
      ] },
    { "id": "e1", "type": "edge", "source": "User", "target": "Order",
      "relationType": "one-to-many", "label": "has" }
  ]
}
```

### Mindmap
```json
{
  "format": "mermaid",
  "diagramType": "mindmap",
  "title": "Product Features",
  "elements": [
    { "id": "root", "type": "node", "label": "Product" },
    { "id": "auth", "type": "node", "label": "Auth Module", "parent": "root" },
    { "id": "login", "type": "node", "label": "Login", "parent": "auth" },
    { "id": "register", "type": "node", "label": "Register", "parent": "auth" }
  ]
}
```

## Style & Schema Reference

For detailed style and geometry options, see [references/schema.md](references/schema.md).
