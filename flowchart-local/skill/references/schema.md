# Schema Reference

## DiagramSpec

```json
{
  "format": "mermaid | drawio | excalidraw",
  "diagramType": "flowchart | sequence | class | er | mindmap | architecture | network",
  "title": "optional-filename",
  "direction": "TD | LR | BT | RL",
  "elements": [ ...elements ]
}
```

`diagramType` is required. `direction` only applies to flowchart/architecture/network types.

## NodeElement

```json
{
  "id": "unique-id",
  "type": "node",
  "label": "Display Text",
  "shape": "rectangle",
  "style": { ...NodeStyle },
  "geometry": { "x": 100, "y": 200, "width": 120, "height": 60 }
}
```

**shape** values: `rectangle` (default), `diamond`, `oval`, `rounded`, `hexagon`, `parallelogram`, `cylinder`, `document`

### Diagram-specific node fields

| Field | Diagram Type | Description |
|-------|-------------|-------------|
| `properties` | class | `string[]` — class properties, e.g. `["+String name"]` |
| `methods` | class | `string[]` — class methods, e.g. `["+login()"]` |
| `stereotype` | class | `string` — e.g. `"interface"`, `"abstract"` |
| `attributes` | er | `Array<{name, type, key?}>` — entity attributes |
| `parent` | mindmap | `string` — parent node ID for hierarchy |
| `participantType` | sequence | `"participant" \| "actor"` |

## EdgeElement

```json
{
  "id": "unique-id",
  "type": "edge",
  "source": "node-id-1",
  "target": "node-id-2",
  "label": "optional label",
  "style": { ...EdgeStyle }
}
```

### Diagram-specific edge fields

| Field | Diagram Type | Description |
|-------|-------------|-------------|
| `messageType` | sequence | `"sync" \| "async" \| "return" \| "note"` |
| `activate` | sequence | `boolean` — activate target lifeline |
| `deactivate` | sequence | `boolean` — deactivate source lifeline |
| `relationType` | class | `"inheritance" \| "composition" \| "aggregation" \| "association" \| "dependency" \| "realization"` |
| `relationType` | er | `"one-to-one" \| "one-to-many" \| "many-to-many"` |

## ContainerElement

```json
{
  "id": "unique-id",
  "type": "container",
  "name": "Group Name",
  "children": ["node-id-1", "node-id-2"]
}
```

### Diagram-specific container fields

| Field | Diagram Type | Description |
|-------|-------------|-------------|
| `fragment` | sequence | `"alt" \| "opt" \| "loop" \| "par" \| "critical" \| "break"` |
| `fragmentLabel` | sequence | `string` — condition text for fragment |

## NodeStyle

| Property | Type | Example |
|----------|------|---------|
| fillColor | string | "#E3F2FD" |
| strokeColor | string | "#1565C0" |
| strokeWidth | number | 2 |
| fontColor | string | "#000000" |
| fontSize | number | 14 |
| fontStyle | "normal" \| "bold" \| "italic" | "bold" |
| borderRadius | number | 8 |
| dashPattern | string | "5 3" |

## EdgeStyle

| Property | Type | Example |
|----------|------|---------|
| strokeColor | string | "#333333" |
| strokeWidth | number | 1.5 |
| endArrow | "none" \| "arrow" \| "circle" \| "diamond" | "arrow" |
| startArrow | "none" \| "arrow" \| "circle" \| "diamond" | "none" |
| dashPattern | string | "5 3" |
| lineStyle | "straight" \| "orthogonal" \| "curved" | "orthogonal" |

## Warning Node Convention

For missing branch warnings (auto-detected by the skill):

```json
{
  "id": "warn_xxx",
  "type": "node",
  "label": "⚠️ 断网/超时",
  "shape": "hexagon",
  "style": {
    "fillColor": "#FFF3E0",
    "strokeColor": "#E65100",
    "fontColor": "#E65100"
  }
}
```

Connect with dashed edge:
```json
{
  "id": "edge_warn",
  "type": "edge",
  "source": "decision_node",
  "target": "warn_xxx",
  "style": { "dashPattern": "5 3" }
}
```
