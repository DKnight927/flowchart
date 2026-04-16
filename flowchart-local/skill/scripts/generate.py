#!/usr/bin/env python3
"""
flowchart-local diagram generator.
Pure-local, zero-dependency (stdlib only). Supports 7 diagram types x 3 formats.

Usage:
  python generate.py --spec '<json>' [--output /path/to/file]
  echo '<json>' | python generate.py [--output /path/to/file]

The JSON spec schema:
{
  "format": "mermaid" | "drawio" | "excalidraw",
  "diagramType": "flowchart" | "sequence" | "class" | "er" | "mindmap" | "architecture" | "network",
  "title": "optional title",
  "direction": "TD" | "LR" | "BT" | "RL",
  "elements": [ ... ]
}

Outputs the diagram content to stdout (and optionally writes to --output file).
"""
import json
import sys
import argparse
import os
import random
import string
from datetime import date
from xml.sax.saxutils import escape as xml_escape

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def esc_mermaid(label):
    return label.replace('"', '#quot;')

def uid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

# ═══════════════════════════════════════════════════════════════════════════════
# MERMAID GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

SHAPE_SYNTAX = {
    'rectangle':     ('[', ']'),
    'diamond':       ('{', '}'),
    'oval':          ('((', '))'),
    'rounded':       ('(', ')'),
    'hexagon':       ('{{', '}}'),
    'parallelogram': ('[/', '/]'),
    'cylinder':      ('[(', ')]'),
    'document':      ('[/', '\\]'),
}

def _fc_node(el):
    shape = el.get('shape', 'rectangle')
    o, c = SHAPE_SYNTAX.get(shape, ('[', ']'))
    return f'  {el["id"]}{o}"{esc_mermaid(el["label"])}"{c}'

def _fc_edge(el):
    label = el.get('label', '')
    label_part = f'|"{esc_mermaid(label)}"| ' if label else ''
    style = el.get('style', {})
    arrow = '-.->' if style.get('dashPattern') else '-->'
    return f'  {el["source"]} {arrow} {label_part}{el["target"]}'

def gen_flowchart(spec):
    elements = spec.get('elements', [])
    containers = [e for e in elements if e['type'] == 'container']
    nodes = [e for e in elements if e['type'] == 'node']
    edges = [e for e in elements if e['type'] == 'edge']
    node_map = {n['id']: n for n in nodes}
    contained_ids = set()
    for c in containers:
        contained_ids.update(c.get('children', []))

    lines = []
    if spec.get('title'):
        lines.append(f'---\ntitle: {spec["title"]}\n---')
    lines.append(f'flowchart {spec.get("direction", "TD")}')

    for n in nodes:
        if n['id'] not in contained_ids:
            lines.append(_fc_node(n))
    for c in containers:
        lines.append(f'  subgraph {c["id"]}["{c.get("name", c["id"])}"]')
        for child_id in c.get('children', []):
            child = node_map.get(child_id)
            if child:
                lines.append('  ' + _fc_node(child))
        lines.append('  end')
    for e in edges:
        lines.append(_fc_edge(e))

    # inline styles
    for n in nodes:
        s = n.get('style')
        if not s:
            continue
        parts = []
        if s.get('fillColor'):
            parts.append(f'fill:{s["fillColor"]}')
        if s.get('strokeColor'):
            parts.append(f'stroke:{s["strokeColor"]}')
        if s.get('fontColor'):
            parts.append(f'color:{s["fontColor"]}')
        if parts:
            lines.append(f'  style {n["id"]} {",".join(parts)}')

    return '\n'.join(lines) + '\n'

def gen_sequence(spec):
    elements = spec.get('elements', [])
    nodes = [e for e in elements if e['type'] == 'node']
    edges = [e for e in elements if e['type'] == 'edge']
    containers = [e for e in elements if e['type'] == 'container']

    lines = []
    if spec.get('title'):
        lines.append(f'---\ntitle: {spec["title"]}\n---')
    lines.append('sequenceDiagram')

    for n in nodes:
        kw = 'actor' if n.get('participantType') == 'actor' else 'participant'
        lines.append(f'  {kw} {n["id"]} as {n["label"]}')

    # Build edge-to-container map
    edge_to_container = {}
    for c in containers:
        for ch in c.get('children', []):
            edge_to_container[ch] = c

    opened = set()
    current = None

    for e in edges:
        container = edge_to_container.get(e['id'])

        # Close previous container if moving to different one
        if current and (not container or container['id'] != current['id']):
            lines.append('  end')
            current = None

        # Open new container
        if container and container['id'] not in opened:
            kw = container.get('fragment', 'alt')
            label = container.get('fragmentLabel', container.get('name', ''))
            lines.append(f'  {kw} {label}')
            opened.add(container['id'])
            current = container

        mt = e.get('messageType', 'sync')
        arrow = '-->>' if mt == 'async' else '-->' if mt == 'return' else '->>'
        label = e.get('label', '')
        lines.append(f'  {e["source"]}{arrow}{e["target"]}: {label}')
        if e.get('activate'):
            lines.append(f'  activate {e["target"]}')
        if e.get('deactivate'):
            lines.append(f'  deactivate {e["source"]}')

    if current:
        lines.append('  end')

    # Standalone containers with no edge children
    for c in containers:
        if c['id'] not in opened and c.get('fragment'):
            lines.append(f'  {c["fragment"]} {c.get("fragmentLabel", c.get("name", ""))}')
            lines.append('  end')

    return '\n'.join(lines) + '\n'

def gen_class(spec):
    elements = spec.get('elements', [])
    nodes = [e for e in elements if e['type'] == 'node']
    edges = [e for e in elements if e['type'] == 'edge']

    lines = []
    if spec.get('title'):
        lines.append(f'---\ntitle: {spec["title"]}\n---')
    lines.append('classDiagram')

    for n in nodes:
        lines.append(f'  class {n["id"]}["{esc_mermaid(n["label"])}"]')
        if n.get('stereotype'):
            lines.append(f'  <<{n["stereotype"]}>> {n["id"]}')
        for p in n.get('properties', []):
            lines.append(f'  {n["id"]} : {p}')
        for m in n.get('methods', []):
            lines.append(f'  {n["id"]} : {m}')

    REL_ARROW = {
        'inheritance': '<|--',
        'composition': '*--',
        'aggregation': 'o--',
        'association': '-->',
        'dependency': '..>',
        'realization': '..|>',
    }
    for e in edges:
        arrow = REL_ARROW.get(e.get('relationType', 'association'), '-->')
        label = f' : {e["label"]}' if e.get('label') else ''
        lines.append(f'  {e["source"]} {arrow} {e["target"]}{label}')

    return '\n'.join(lines) + '\n'

def gen_er(spec):
    elements = spec.get('elements', [])
    nodes = [e for e in elements if e['type'] == 'node']
    edges = [e for e in elements if e['type'] == 'edge']

    lines = []
    if spec.get('title'):
        lines.append(f'---\ntitle: {spec["title"]}\n---')
    lines.append('erDiagram')

    CARDINALITY = {
        'one-to-one': '||--||',
        'one-to-many': '||--o{',
        'many-to-many': '}o--o{',
    }
    for e in edges:
        card = CARDINALITY.get(e.get('relationType', 'one-to-many'), '||--o{')
        label = f'"{esc_mermaid(e["label"])}"' if e.get('label') else '""'
        lines.append(f'  {e["source"]} {card} {e["target"]} : {label}')

    for n in nodes:
        lines.append(f'  {n["id"]} {{')
        attrs = n.get('attributes', [])
        if attrs:
            for attr in attrs:
                key = f' {attr["key"]}' if attr.get('key') else ''
                lines.append(f'    {attr["type"]} {attr["name"]}{key}')
        else:
            safe = n['label'].replace(' ', '_')
            lines.append(f'    string {safe}')
        lines.append('  }')

    return '\n'.join(lines) + '\n'

def gen_mindmap(spec):
    elements = spec.get('elements', [])
    nodes = [e for e in elements if e['type'] == 'node']

    lines = ['mindmap']

    child_map = {}
    for n in nodes:
        parent = n.get('parent')
        child_map.setdefault(parent, []).append(n)

    def render(node, depth):
        indent = '  ' * (depth + 1)
        lines.append(f'{indent}{node["label"]}')
        for child in child_map.get(node['id'], []):
            render(child, depth + 1)

    roots = child_map.get(None, [])
    if not roots and nodes:
        lines.append(f'  root(({spec.get("title", "Root")}))')
        for n in nodes:
            lines.append(f'    {n["label"]}')
    else:
        for root in roots:
            render(root, 0)

    return '\n'.join(lines) + '\n'

MERMAID_GENERATORS = {
    'flowchart': gen_flowchart,
    'sequence': gen_sequence,
    'class': gen_class,
    'er': gen_er,
    'mindmap': gen_mindmap,
    'architecture': gen_flowchart,
    'network': gen_flowchart,
}

def generate_mermaid(spec):
    dt = spec.get('diagramType', 'flowchart')
    gen = MERMAID_GENERATORS.get(dt)
    if not gen:
        raise ValueError(f'Unsupported mermaid diagram type: {dt}')
    return gen(spec)

# ═══════════════════════════════════════════════════════════════════════════════
# DRAWIO GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

DRAWIO_SHAPE_STYLE = {
    'rectangle': 'rounded=0;',
    'rounded': 'rounded=1;arcSize=10;',
    'diamond': 'rhombus;',
    'oval': 'ellipse;',
    'hexagon': 'shape=hexagon;perimeter=hexagonPerimeter2;',
    'parallelogram': 'shape=parallelogram;perimeter=parallelogramPerimeter;',
    'cylinder': 'shape=mxgraph.flowchart.start_2;',
    'document': 'shape=document;',
}

def _drawio_node_style(el):
    base = DRAWIO_SHAPE_STYLE.get(el.get('shape', 'rectangle'), 'rounded=0;')
    s = el.get('style', {})
    parts = [base]
    if s.get('fillColor'):
        parts.append(f'fillColor={s["fillColor"]};')
    if s.get('strokeColor'):
        parts.append(f'strokeColor={s["strokeColor"]};')
    if s.get('fontColor'):
        parts.append(f'fontColor={s["fontColor"]};')
    if s.get('fontSize'):
        parts.append(f'fontSize={s["fontSize"]};')
    if s.get('fontStyle') == 'bold':
        parts.append('fontStyle=1;')
    if s.get('fontStyle') == 'italic':
        parts.append('fontStyle=2;')
    if s.get('strokeWidth'):
        parts.append(f'strokeWidth={s["strokeWidth"]};')
    if s.get('dashPattern'):
        parts.append('dashed=1;')
    return ''.join(parts)

def _drawio_edge_style(el):
    s = el.get('style', {})
    arrow_map = {'arrow': 'classic', 'circle': 'oval', 'diamond': 'ERmanyToOne', 'none': 'none'}
    parts = ['edgeStyle=orthogonalEdgeStyle;']
    if s.get('strokeColor'):
        parts.append(f'strokeColor={s["strokeColor"]};')
    if s.get('strokeWidth'):
        parts.append(f'strokeWidth={s["strokeWidth"]};')
    if s.get('endArrow'):
        parts.append(f'endArrow={arrow_map.get(s["endArrow"], "classic")};')
    if s.get('startArrow'):
        parts.append(f'startArrow={arrow_map.get(s["startArrow"], "none")};')
    if s.get('dashPattern'):
        parts.append('dashed=1;')
    if s.get('lineStyle') == 'straight':
        parts.append('edgeStyle=none;')
    if s.get('lineStyle') == 'curved':
        parts.append('edgeStyle=elbowEdgeStyle;')
    return ''.join(parts)

def generate_drawio(spec):
    title = xml_escape(spec.get('title', 'Diagram'))
    elements = spec.get('elements', [])
    containers = [e for e in elements if e['type'] == 'container']
    nodes = [e for e in elements if e['type'] == 'node']
    edges = [e for e in elements if e['type'] == 'edge']

    node_parent = {}
    for c in containers:
        for child_id in c.get('children', []):
            node_parent[child_id] = c['id']

    indent = '        '
    cells = []

    # containers
    for c in containers:
        geo = c.get('geometry', {'x': 40, 'y': 40, 'width': 300, 'height': 200})
        w = geo.get('width', 300)
        h = geo.get('height', 200)
        s = c.get('style', {})
        style_parts = ['swimlane;']
        if s.get('fillColor'):
            style_parts.append(f'fillColor={s["fillColor"]};')
        if s.get('strokeColor'):
            style_parts.append(f'strokeColor={s["strokeColor"]};')
        if s.get('fontColor'):
            style_parts.append(f'fontColor={s["fontColor"]};')
        style = ''.join(style_parts)
        name = xml_escape(c.get('name', c['id']))
        cells.append(
            f'{indent}<mxCell id="{c["id"]}" value="{name}" style="{style}" '
            f'vertex="1" parent="1">\n'
            f'{indent}  <mxGeometry x="{geo.get("x", 40)}" y="{geo.get("y", 40)}" '
            f'width="{w}" height="{h}" as="geometry"/>\n'
            f'{indent}</mxCell>'
        )

    # nodes
    for n in nodes:
        geo = n.get('geometry', {'x': 100, 'y': 100, 'width': 120, 'height': 60})
        w = geo.get('width', 120)
        h = geo.get('height', 60)
        parent = node_parent.get(n['id'], '1')
        label = xml_escape(n['label'])
        style = _drawio_node_style(n)
        cells.append(
            f'{indent}<mxCell id="{n["id"]}" value="{label}" style="{style}" '
            f'vertex="1" parent="{parent}">\n'
            f'{indent}  <mxGeometry x="{geo.get("x", 100)}" y="{geo.get("y", 100)}" '
            f'width="{w}" height="{h}" as="geometry"/>\n'
            f'{indent}</mxCell>'
        )

    # edges
    for e in edges:
        label = xml_escape(e.get('label', ''))
        style = _drawio_edge_style(e)
        cells.append(
            f'{indent}<mxCell id="{e["id"]}" value="{label}" style="{style}" '
            f'edge="1" source="{e["source"]}" target="{e["target"]}" parent="1">\n'
            f'{indent}  <mxGeometry relative="1" as="geometry"/>\n'
            f'{indent}</mxCell>'
        )

    cells_str = '\n'.join(cells)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram name="{title}">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1"
      tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1"
      pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells_str}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''

# ═══════════════════════════════════════════════════════════════════════════════
# EXCALIDRAW GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

EX_TYPE = {
    'rectangle': 'rectangle',
    'rounded': 'rectangle',
    'diamond': 'diamond',
    'oval': 'ellipse',
    'hexagon': 'rectangle',
    'parallelogram': 'rectangle',
    'cylinder': 'ellipse',
    'document': 'rectangle',
}

def _ex_node(el):
    geo = el.get('geometry', {'x': 100, 'y': 100, 'width': 160, 'height': 70})
    s = el.get('style', {})
    shape = el.get('shape', 'rectangle')
    ex_type = EX_TYPE.get(shape, 'rectangle')
    is_rounded = shape in ('rounded', 'oval')
    w = geo.get('width', 160)
    h = geo.get('height', 70)

    rect = {
        'id': el['id'],
        'type': ex_type,
        'x': geo.get('x', 100),
        'y': geo.get('y', 100),
        'width': w,
        'height': h,
        'angle': 0,
        'strokeColor': s.get('strokeColor', '#1e1e1e'),
        'backgroundColor': s.get('fillColor', 'transparent'),
        'fillStyle': 'solid' if s.get('fillColor') else 'hachure',
        'strokeWidth': s.get('strokeWidth', 2),
        'strokeStyle': 'dashed' if s.get('dashPattern') else 'solid',
        'roughness': 1,
        'opacity': 100,
        'roundness': {'type': 3} if is_rounded else None,
    }

    label = el.get('label', '')
    text = {
        'id': uid(),
        'type': 'text',
        'x': geo.get('x', 100) + w / 2 - len(label) * 4,
        'y': geo.get('y', 100) + h / 2 - 10,
        'width': len(label) * 8 + 16,
        'height': 25,
        'angle': 0,
        'strokeColor': s.get('fontColor', '#1e1e1e'),
        'backgroundColor': 'transparent',
        'fillStyle': 'hachure',
        'strokeWidth': 1,
        'strokeStyle': 'solid',
        'roughness': 1,
        'opacity': 100,
        'roundness': None,
        'text': label,
        'fontSize': s.get('fontSize', 16),
        'fontFamily': 1,
        'textAlign': 'center',
        'verticalAlign': 'middle',
        'containerId': el['id'],
    }

    return [rect, text]

def _ex_container(el):
    geo = el.get('geometry', {'x': 40, 'y': 40, 'width': 320, 'height': 220})
    s = el.get('style', {})
    w = geo.get('width', 320)
    h = geo.get('height', 220)
    name = el.get('name', el['id'])

    rect = {
        'id': el['id'],
        'type': 'rectangle',
        'x': geo.get('x', 40),
        'y': geo.get('y', 40),
        'width': w,
        'height': h,
        'angle': 0,
        'strokeColor': s.get('strokeColor', '#4a4a8a'),
        'backgroundColor': s.get('fillColor', '#e8e8f8'),
        'fillStyle': 'solid',
        'strokeWidth': s.get('strokeWidth', 2),
        'strokeStyle': 'solid',
        'roughness': 0,
        'opacity': 80,
        'roundness': {'type': 3},
        'groupIds': [],
    }

    label = {
        'id': uid(),
        'type': 'text',
        'x': geo.get('x', 40) + 12,
        'y': geo.get('y', 40) + 8,
        'width': len(name) * 9 + 16,
        'height': 22,
        'angle': 0,
        'strokeColor': s.get('fontColor', '#4a4a8a'),
        'backgroundColor': 'transparent',
        'fillStyle': 'hachure',
        'strokeWidth': 1,
        'strokeStyle': 'solid',
        'roughness': 1,
        'opacity': 100,
        'roundness': None,
        'text': name,
        'fontSize': 14,
        'fontFamily': 1,
        'textAlign': 'left',
        'verticalAlign': 'top',
        'fontStyle': 1,
    }

    return [rect, label]

def _ex_edge(el, node_map):
    src = node_map.get(el['source'], {})
    tgt = node_map.get(el['target'], {})
    src_geo = src.get('geometry', {'x': 0, 'y': 0, 'width': 160, 'height': 70})
    tgt_geo = tgt.get('geometry', {'x': 200, 'y': 200, 'width': 160, 'height': 70})

    sx = src_geo.get('x', 0) + src_geo.get('width', 160) / 2
    sy = src_geo.get('y', 0) + src_geo.get('height', 70)
    tx = tgt_geo.get('x', 200) + tgt_geo.get('width', 160) / 2
    ty = tgt_geo.get('y', 200)

    s = el.get('style', {})

    return {
        'id': el['id'],
        'type': 'arrow',
        'x': sx,
        'y': sy,
        'width': abs(tx - sx),
        'height': abs(ty - sy),
        'angle': 0,
        'strokeColor': s.get('strokeColor', '#1e1e1e'),
        'backgroundColor': 'transparent',
        'fillStyle': 'hachure',
        'strokeWidth': s.get('strokeWidth', 2),
        'strokeStyle': 'dashed' if s.get('dashPattern') else 'solid',
        'roughness': 1,
        'opacity': 100,
        'roundness': {'type': 2},
        'points': [[0, 0], [tx - sx, ty - sy]],
        'lastCommittedPoint': None,
        'startBinding': {'elementId': el['source'], 'focus': 0, 'gap': 8},
        'endBinding': {'elementId': el['target'], 'focus': 0, 'gap': 8},
        'startArrowhead': 'arrow' if s.get('startArrow') and s['startArrow'] != 'none' else None,
        'endArrowhead': None if s.get('endArrow') == 'none' else 'arrow',
        'label': el.get('label'),
    }

def generate_excalidraw(spec):
    elements = spec.get('elements', [])
    nodes = [e for e in elements if e['type'] == 'node']
    conts = [e for e in elements if e['type'] == 'container']
    edges = [e for e in elements if e['type'] == 'edge']

    node_map = {n['id']: n for n in nodes}
    out = []
    for c in conts:
        out.extend(_ex_container(c))
    for n in nodes:
        out.extend(_ex_node(n))
    for e in edges:
        out.append(_ex_edge(e, node_map))

    doc = {
        'type': 'excalidraw',
        'version': 2,
        'source': 'flowchart-local',
        'elements': out,
        'appState': {
            'gridSize': None,
            'viewBackgroundColor': '#ffffff',
        },
        'files': {},
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

FORMAT_GENERATORS = {
    'mermaid': generate_mermaid,
    'drawio': generate_drawio,
    'excalidraw': generate_excalidraw,
}

FORMAT_EXT = {
    'mermaid': '.md',
    'drawio': '.drawio',
    'excalidraw': '.excalidraw',
}

def main():
    parser = argparse.ArgumentParser(description='Generate diagrams from JSON spec')
    parser.add_argument('--spec', type=str, help='JSON spec string')
    parser.add_argument('--spec-file', type=str, help='Path to JSON spec file')
    parser.add_argument('--output', '-o', type=str, help='Output file path')
    args = parser.parse_args()

    # Read spec from --spec, --spec-file, or stdin
    if args.spec:
        spec = json.loads(args.spec)
    elif args.spec_file:
        with open(args.spec_file) as f:
            spec = json.load(f)
    elif not sys.stdin.isatty():
        spec = json.load(sys.stdin)
    else:
        print('Error: provide --spec, --spec-file, or pipe JSON to stdin', file=sys.stderr)
        sys.exit(1)

    fmt = spec.get('format', 'mermaid')
    gen = FORMAT_GENERATORS.get(fmt)
    if not gen:
        print(f'Error: unsupported format "{fmt}"', file=sys.stderr)
        sys.exit(1)

    content = gen(spec)

    # Write to file if requested
    if args.output:
        out_path = args.output
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'File saved: {out_path}', file=sys.stderr)

    # Always output content to stdout
    print(content)

if __name__ == '__main__':
    main()
