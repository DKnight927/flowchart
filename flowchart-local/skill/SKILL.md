---
name: flowchart
description: 产品需求文档解构与可视化 skill。将 PRD/需求文档自动转化为流程图、序列图、类图、ER图、思维导图、架构图、网络拓扑图，并自动检测缺失分支（断网、无权限、空状态等异常场景）。当用户要求画图、分析需求文档、生成流程图、可视化产品逻辑时触发。触发词：画流程图、生成序列图、分析需求文档、PRD可视化、draw flowchart、generate diagram、ER图、类图、思维导图、架构图、网络拓扑。
---

# PRD 解构与可视化

将产品需求文档自动解构为可视化图表，并在关键节点标注可能缺失的异常分支。

## ⛔ 强制规则 — 必须先读

**在完成第一步（问候与需求对齐）并且用户明确确认需求之前，禁止生成任何图表或产出任何内容。**

具体要求：
1. 即使用户说"画个流程图"，也必须先确认具体需求，禁止跳过需求对齐
2. 任何情况下禁止伪造下载链接、文件地址或图表内容
3. 用户要求生成时，先对齐需求，再生成

违反此规则会导致输出错误、不可用。

## 工作原理（纯本地，无需服务器）

本 skill 使用**随 skill 一起安装的本地 Python 脚本**生成图表。无需 MCP 服务器，无需网络，无外部依赖。

**生成脚本位置：** `~/.comate/skills/flowchart/scripts/generate.py`

**调用方式：**

```bash
# 通过 --spec 参数传入 JSON：
python3 ~/.comate/skills/flowchart/scripts/generate.py --spec '{ ... }' -o ~/Desktop/diagram.md

# 通过 --spec-file 传入 JSON 文件：
python3 ~/.comate/skills/flowchart/scripts/generate.py --spec-file /tmp/spec.json -o ~/Desktop/diagram.drawio

# 内容输出到 stdout，同时可通过 -o 写入文件
```

**关键：必须使用 `execute_code`（Python）或 `run_command` 来调用 generate.py，按以下步骤执行：**

1. 将 JSON 规格构建为 Python 字典
2. 写入临时文件
3. 调用 `generate.py --spec-file <临时文件> -o <输出路径>`
4. 读取 stdout 结果并展示给用户
5. 清理临时文件

`execute_code` 调用示例：
```python
import subprocess, json, tempfile, os

spec = {
    "format": "mermaid",
    "diagramType": "flowchart",
    "direction": "TD",
    "elements": [
        {"id": "n1", "type": "node", "label": "开始", "shape": "oval"},
        {"id": "n2", "type": "node", "label": "结束", "shape": "oval"},
        {"id": "e1", "type": "edge", "source": "n1", "target": "n2", "label": "执行"}
    ]
}

# 写入临时文件
spec_path = '/tmp/_flowchart_spec.json'
with open(spec_path, 'w') as f:
    json.dump(spec, f, ensure_ascii=False)

# 调用生成器
script = os.path.expanduser('~/.comate/skills/flowchart/scripts/generate.py')
output_path = os.path.expanduser('~/Desktop/diagram.md')
result = subprocess.run(
    ['python3', script, '--spec-file', spec_path, '-o', output_path],
    capture_output=True, text=True
)

# 清理临时文件
os.remove(spec_path)

print(result.stdout)  # 图表内容
if result.returncode != 0:
    print('错误:', result.stderr)
```

## 核心工作流

### 第一步：问候与需求对齐（强制执行，禁止跳过）

当用户触发本 skill 时，必须从此步骤开始。

向用户展示以下内容：

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

然后向用户提问：
1. 你需要哪种类型的图？
2. 输出格式偏好？（默认 mermaid）
3. 有需求文档可以直接发给我，我会自动分析
4. 对图有其他要求吗？（如方向、配色、详细程度）

**在此停下，等待用户回复。用户回答之前禁止继续。**

### 第二步：分析输入

两种模式：

**模式 A — 用户口头描述需求：**
- 从描述中提取关键实体、流程和关系
- 生成前先与用户确认理解是否正确

**模式 B — 用户提供需求文档（PRD）：**
- 通读整个文档
- 提取所有产品功能及其逻辑流程
- 识别：用户操作、系统响应、数据流向、状态转换
- 构建产品逻辑的结构化模型
- 生成前先进入第三步（分支检查）

### 第三步：分支完整性检查（关键步骤）

生成最终图表之前，分析每个决策节点和交互点是否存在遗漏分支。检查以下常见遗漏场景：

**网络/基础设施：**
- 断网 / 网络超时 / 请求失败
- 服务不可用 / 接口降级
- CDN 加载失败

**权限/认证：**
- 未登录 / 登录态过期
- 无权限 / 权限不足
- 账号被封禁 / 冻结

**数据/状态：**
- 空状态（列表为空、搜索无结果、首次使用）
- 数据加载中（loading）
- 数据异常 / 格式错误
- 并发冲突 / 数据已被他人修改

**输入/校验：**
- 输入校验失败
- 超出限制（字数、文件大小、次数）
- 重复提交 / 幂等

**业务边界场景：**
- 操作中途取消
- 退款/撤销/回退
- 过期/到期状态

**遗漏分支的输出格式：**
对于每个发现的遗漏分支，添加一个节点：
- shape: `hexagon`
- style: `{ "fillColor": "#FFF3E0", "strokeColor": "#E65100", "fontColor": "#E65100" }`
- label 以 `⚠️` 开头

使用虚线边将这些警告节点连接到相关的决策/操作节点。

在生成之前，将检测到的遗漏分支列表展示给用户，询问：
> "我检测到以下可能缺失的异常分支，是否需要加入图中？"

然后逐一列出每个遗漏分支及说明。用户可以选择需要加入的分支。

### 第四步：生成图表

用户确认后，构建 JSON 规格并调用 `generate.py`。

**格式选择默认值：**
- 流程图/架构图/网络拓扑 → `mermaid` 格式，`TD` 方向
- 序列图 → `mermaid` 格式
- 类图/ER 图 → `mermaid` 格式
- 思维导图 → `mermaid` 格式
- 用户要求可编辑文件 → `drawio` 格式
- 用户使用 Obsidian / 想要手绘风格 → `excalidraw` 格式

**生成步骤：**
1. 构建完整的 JSON 规格（参见下方元素构建指南）
2. 使用 `execute_code` 调用 `generate.py`
3. 将输出保存到用户指定位置（默认：`~/Desktop/`）
4. mermaid 格式：同时在 ` ```mermaid ` 代码块中展示，方便用户在线预览
5. drawio 格式：告知用户用 draw.io 打开 `.drawio` 文件
6. excalidraw 格式：告知用户用 Excalidraw 或 Obsidian 打开 `.excalidraw` 文件

### 第五步：迭代优化

生成后，询问用户是否需要调整：
- 增加/删除节点
- 更改布局方向
- 调整详细程度
- 导出为其他格式
- 基于同一文档生成其他类型的图表

## 元素构建指南

### 流程图 / 架构图 / 网络拓扑
```json
{
  "format": "mermaid",
  "diagramType": "flowchart",
  "elements": [
    { "id": "n1", "type": "node", "label": "开始", "shape": "oval" },
    { "id": "n2", "type": "node", "label": "是否有效？", "shape": "diamond" },
    { "id": "e1", "type": "edge", "source": "n1", "target": "n2" },
    { "id": "warn1", "type": "node", "label": "⚠️ 断网", "shape": "hexagon",
      "style": { "fillColor": "#FFF3E0", "strokeColor": "#E65100" } },
    { "id": "ew1", "type": "edge", "source": "n2", "target": "warn1",
      "style": { "dashPattern": "5 3" } }
  ]
}
```

### 序列图
```json
{
  "format": "mermaid",
  "diagramType": "sequence",
  "elements": [
    { "id": "User", "type": "node", "label": "用户", "participantType": "actor" },
    { "id": "Server", "type": "node", "label": "服务器" },
    { "id": "e1", "type": "edge", "source": "User", "target": "Server",
      "label": "POST /login", "messageType": "sync" },
    { "id": "e2", "type": "edge", "source": "Server", "target": "User",
      "label": "200 OK", "messageType": "return" }
  ]
}
```

### 类图
```json
{
  "format": "mermaid",
  "diagramType": "class",
  "elements": [
    { "id": "User", "type": "node", "label": "用户",
      "properties": ["+String name", "+String email"],
      "methods": ["+login()", "+logout()"] },
    { "id": "Order", "type": "node", "label": "订单",
      "properties": ["+int id", "+Date createdAt"] },
    { "id": "e1", "type": "edge", "source": "User", "target": "Order",
      "relationType": "association", "label": "下单" }
  ]
}
```

### ER 图
```json
{
  "format": "mermaid",
  "diagramType": "er",
  "elements": [
    { "id": "User", "type": "node", "label": "用户",
      "attributes": [
        { "name": "id", "type": "int", "key": "PK" },
        { "name": "name", "type": "string" }
      ] },
    { "id": "Order", "type": "node", "label": "订单",
      "attributes": [
        { "name": "id", "type": "int", "key": "PK" },
        { "name": "user_id", "type": "int", "key": "FK" }
      ] },
    { "id": "e1", "type": "edge", "source": "User", "target": "Order",
      "relationType": "one-to-many", "label": "拥有" }
  ]
}
```

### 思维导图
```json
{
  "format": "mermaid",
  "diagramType": "mindmap",
  "title": "产品功能",
  "elements": [
    { "id": "root", "type": "node", "label": "产品" },
    { "id": "auth", "type": "node", "label": "认证模块", "parent": "root" },
    { "id": "login", "type": "node", "label": "登录", "parent": "auth" },
    { "id": "register", "type": "node", "label": "注册", "parent": "auth" }
  ]
}
```

## 样式与结构参考

详细的样式和布局选项，请参阅 [references/schema.md](references/schema.md)。
