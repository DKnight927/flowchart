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
import math
import random
import string
from collections import deque
from xml.sax.saxutils import escape as xml_escape

# ═══════════════════════════════════════════════════════════════════════════════
# 布局常量
# ═══════════════════════════════════════════════════════════════════════════════

# 节点尺寸（按形状）
NODE_SIZES = {
    'rectangle':     (160, 50),
    'rounded':       (160, 50),
    'diamond':       (160, 80),
    'oval':          (140, 50),
    'hexagon':       (170, 60),
    'parallelogram': (160, 50),
    'cylinder':      (140, 60),
    'document':      (160, 60),
}

# 间距
H_GAP = 60       # 同层节点水平间距
V_GAP = 80       # 层与层之间垂直间距
CONTAINER_PAD_TOP = 50   # 容器顶部留给标题
CONTAINER_PAD = 30       # 容器内边距

# 默认配色方案
SHAPE_COLORS = {
    'oval':          {'fill': '#E8EAF6', 'stroke': '#3F51B5', 'font': '#1A237E'},  # 开始/结束 - 靛蓝
    'diamond':       {'fill': '#FFF8E1', 'stroke': '#F57F17', 'font': '#E65100'},  # 判断 - 琥珀
    'rectangle':     {'fill': '#E3F2FD', 'stroke': '#1565C0', 'font': '#0D47A1'},  # 普通 - 蓝
    'rounded':       {'fill': '#E8F5E9', 'stroke': '#2E7D32', 'font': '#1B5E20'},  # 处理 - 绿
    'hexagon':       {'fill': '#FFF3E0', 'stroke': '#E65100', 'font': '#BF360C'},  # 警告 - 橙
    'parallelogram': {'fill': '#F3E5F5', 'stroke': '#7B1FA2', 'font': '#4A148C'},  # 数据 - 紫
    'cylinder':      {'fill': '#E0F2F1', 'stroke': '#00695C', 'font': '#004D40'},  # 数据库 - 青
    'document':      {'fill': '#FBE9E7', 'stroke': '#BF360C', 'font': '#BF360C'},  # 文档 - 深橙
}

DEFAULT_FONT_SIZE = 13

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def esc_mermaid(label):
    return label.replace('"', '#quot;')

def uid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def calc_node_size(label, shape='rectangle'):
    """根据标签文本长度动态计算节点尺寸"""
    base_w, base_h = NODE_SIZES.get(shape, (160, 50))
    # 中文字符按 14px 宽度，英文按 8px
    char_w = 0
    for ch in label:
        char_w += 14 if '\u4e00' <= ch <= '\u9fff' else 8
    text_w = char_w + 40  # 左右各留 20px padding
    w = max(base_w, text_w)
    if shape == 'diamond':
        w = int(w * 1.4)  # 菱形需要更宽
        base_h = max(base_h, 80)
    return (w, base_h)


# ═══════════════════════════════════════════════════════════════════════════════
# 自动布局算法
# ═══════════════════════════════════════════════════════════════════════════════

def auto_layout(spec):
    """
    给没有 geometry 的节点自动计算坐标。
    算法：拓扑分层 → 同层横向展开 → 支持 TD/LR/BT/RL 四个方向。
    """
    elements = spec.get('elements', [])
    direction = spec.get('direction', 'TD')
    nodes = [e for e in elements if e['type'] == 'node']
    edges = [e for e in elements if e['type'] == 'edge']
    containers = [e for e in elements if e['type'] == 'container']

    if not nodes:
        return

    node_map = {n['id']: n for n in nodes}
    node_ids = set(n['id'] for n in nodes)

    # 计算每个节点的实际尺寸
    for n in nodes:
        w, h = calc_node_size(n.get('label', ''), n.get('shape', 'rectangle'))
        if 'geometry' not in n:
            n['_w'] = w
            n['_h'] = h
        else:
            n['_w'] = n['geometry'].get('width', w)
            n['_h'] = n['geometry'].get('height', h)

    # 如果所有节点都已有 geometry 且非默认值，不做自动布局
    has_custom_geo = all(
        n.get('geometry') and
        not (n['geometry'].get('x', 100) == 100 and n['geometry'].get('y', 100) == 100)
        for n in nodes
    )
    if has_custom_geo:
        return

    # 构建邻接关系
    children = {}   # nodeId -> [childId, ...]
    parents = {}    # nodeId -> [parentId, ...]
    for e in edges:
        src, tgt = e.get('source'), e.get('target')
        if src in node_ids and tgt in node_ids:
            children.setdefault(src, []).append(tgt)
            parents.setdefault(tgt, []).append(src)

    # 容器子节点关系
    contained_ids = set()
    for c in containers:
        contained_ids.update(c.get('children', []))

    # 拓扑分层（Coffman-Graham 风格）
    in_degree = {n['id']: 0 for n in nodes}
    for e in edges:
        tgt = e.get('target')
        if tgt in in_degree:
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    # BFS 分层
    layer_of = {}
    queue = deque()
    for nid, deg in in_degree.items():
        if deg == 0:
            layer_of[nid] = 0
            queue.append(nid)

    # 处理没有入边的孤立节点
    if not queue:
        # 所有节点都有入边（存在环），取第一个作为起点
        first_id = nodes[0]['id']
        layer_of[first_id] = 0
        queue.append(first_id)

    while queue:
        nid = queue.popleft()
        cur_layer = layer_of[nid]
        for child in children.get(nid, []):
            new_layer = cur_layer + 1
            if child not in layer_of or layer_of[child] < new_layer:
                layer_of[child] = new_layer
                queue.append(child)

    # 未被遍历到的节点（孤立/环中）放到最后一层
    max_layer = max(layer_of.values()) if layer_of else 0
    for n in nodes:
        if n['id'] not in layer_of:
            max_layer += 1
            layer_of[n['id']] = max_layer

    # 按层分组
    layers = {}
    for nid, layer in layer_of.items():
        layers.setdefault(layer, []).append(nid)

    # 对每层内节点排序：尽量让有边连接的节点对齐
    for layer_idx in sorted(layers.keys()):
        layer_nodes = layers[layer_idx]
        # 按父节点在上层的位置排序
        def sort_key(nid):
            pars = parents.get(nid, [])
            if pars:
                par_positions = []
                for p in pars:
                    p_layer = layer_of.get(p, 0)
                    p_idx = layers.get(p_layer, []).index(p) if p in layers.get(p_layer, []) else 0
                    par_positions.append(p_idx)
                return sum(par_positions) / len(par_positions)
            return 0
        layers[layer_idx] = sorted(layer_nodes, key=sort_key)

    # 计算坐标
    is_horizontal = direction in ('LR', 'RL')

    # 计算每层的最大尺寸
    layer_max_size = {}
    for layer_idx, nids in layers.items():
        if is_horizontal:
            layer_max_size[layer_idx] = max(node_map[nid]['_w'] for nid in nids)
        else:
            layer_max_size[layer_idx] = max(node_map[nid]['_h'] for nid in nids)

    # 分配坐标
    sorted_layers = sorted(layers.keys())
    depth_pos = 0  # 沿主轴方向的累积位置

    for layer_idx in sorted_layers:
        nids = layers[layer_idx]
        n_count = len(nids)

        # 沿副轴方向的总宽度
        if is_horizontal:
            total_breadth = sum(node_map[nid]['_h'] for nid in nids) + H_GAP * (n_count - 1)
        else:
            total_breadth = sum(node_map[nid]['_w'] for nid in nids) + H_GAP * (n_count - 1)

        breadth_start = -total_breadth / 2  # 居中对齐
        breadth_pos = breadth_start

        for nid in nids:
            n = node_map[nid]
            w, h = n['_w'], n['_h']

            if is_horizontal:
                x = depth_pos
                y = breadth_pos
                breadth_pos += h + H_GAP
            else:
                x = breadth_pos
                y = depth_pos
                breadth_pos += w + H_GAP

            n['geometry'] = {'x': round(x), 'y': round(y), 'width': w, 'height': h}

        depth_pos += layer_max_size[layer_idx] + V_GAP

    # 方向调整：BT 翻转 Y，RL 翻转 X
    if direction == 'BT':
        max_y = max(n['geometry']['y'] + n['geometry']['height'] for n in nodes)
        for n in nodes:
            n['geometry']['y'] = max_y - n['geometry']['y'] - n['geometry']['height']
    elif direction == 'RL':
        max_x = max(n['geometry']['x'] + n['geometry']['width'] for n in nodes)
        for n in nodes:
            n['geometry']['x'] = max_x - n['geometry']['x'] - n['geometry']['width']

    # 平移使所有坐标为正数（左上角留边距）
    min_x = min(n['geometry']['x'] for n in nodes)
    min_y = min(n['geometry']['y'] for n in nodes)
    margin = 60
    for n in nodes:
        n['geometry']['x'] += -min_x + margin
        n['geometry']['y'] += -min_y + margin

    # 自动布局容器
    for c in containers:
        child_ids = c.get('children', [])
        child_nodes = [node_map[cid] for cid in child_ids if cid in node_map]
        if child_nodes:
            min_cx = min(cn['geometry']['x'] for cn in child_nodes) - CONTAINER_PAD
            min_cy = min(cn['geometry']['y'] for cn in child_nodes) - CONTAINER_PAD_TOP
            max_cx = max(cn['geometry']['x'] + cn['geometry']['width'] for cn in child_nodes) + CONTAINER_PAD
            max_cy = max(cn['geometry']['y'] + cn['geometry']['height'] for cn in child_nodes) + CONTAINER_PAD
            c['geometry'] = {
                'x': round(min_cx), 'y': round(min_cy),
                'width': round(max_cx - min_cx), 'height': round(max_cy - min_cy),
            }


def apply_default_colors(spec):
    """给没有 style 的节点应用默认配色方案"""
    for el in spec.get('elements', []):
        if el['type'] != 'node':
            continue
        if el.get('style') and el['style'].get('fillColor'):
            continue  # 用户已自定义，不覆盖
        shape = el.get('shape', 'rectangle')
        colors = SHAPE_COLORS.get(shape, SHAPE_COLORS['rectangle'])
        if 'style' not in el:
            el['style'] = {}
        el['style'].setdefault('fillColor', colors['fill'])
        el['style'].setdefault('strokeColor', colors['stroke'])
        el['style'].setdefault('fontColor', colors['font'])
        el['style'].setdefault('fontSize', DEFAULT_FONT_SIZE)


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

    edge_to_container = {}
    for c in containers:
        for ch in c.get('children', []):
            edge_to_container[ch] = c

    opened = set()
    current = None

    for e in edges:
        container = edge_to_container.get(e['id'])
        if current and (not container or container['id'] != current['id']):
            lines.append('  end')
            current = None
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
        'inheritance': '<|--', 'composition': '*--', 'aggregation': 'o--',
        'association': '-->', 'dependency': '..>', 'realization': '..|>',
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
        'one-to-one': '||--||', 'one-to-many': '||--o{', 'many-to-many': '}o--o{',
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
    'flowchart': gen_flowchart, 'sequence': gen_sequence, 'class': gen_class,
    'er': gen_er, 'mindmap': gen_mindmap, 'architecture': gen_flowchart, 'network': gen_flowchart,
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
    'rectangle': 'rounded=0;whiteSpace=wrap;html=1;',
    'rounded': 'rounded=1;arcSize=20;whiteSpace=wrap;html=1;',
    'diamond': 'rhombus;whiteSpace=wrap;html=1;',
    'oval': 'ellipse;whiteSpace=wrap;html=1;',
    'hexagon': 'shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;',
    'parallelogram': 'shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;',
    'cylinder': 'shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;',
    'document': 'shape=document;whiteSpace=wrap;html=1;boundedLbl=1;size=0.27;',
}

def _drawio_node_style(el):
    shape = el.get('shape', 'rectangle')
    base = DRAWIO_SHAPE_STYLE.get(shape, DRAWIO_SHAPE_STYLE['rectangle'])
    s = el.get('style', {})

    # 使用默认配色
    colors = SHAPE_COLORS.get(shape, SHAPE_COLORS['rectangle'])
    fill = s.get('fillColor', colors['fill'])
    stroke = s.get('strokeColor', colors['stroke'])
    font_color = s.get('fontColor', colors['font'])
    font_size = s.get('fontSize', DEFAULT_FONT_SIZE)

    parts = [base]
    parts.append(f'fillColor={fill};')
    parts.append(f'strokeColor={stroke};')
    parts.append(f'fontColor={font_color};')
    parts.append(f'fontSize={font_size};')
    parts.append('fontFamily=Helvetica;')

    if s.get('fontStyle') == 'bold':
        parts.append('fontStyle=1;')
    if s.get('strokeWidth'):
        parts.append(f'strokeWidth={s["strokeWidth"]};')
    else:
        parts.append('strokeWidth=1.5;')
    if s.get('dashPattern'):
        parts.append('dashed=1;dashPattern=8 4;')

    return ''.join(parts)

def _drawio_edge_style(el):
    s = el.get('style', {})
    parts = [
        'edgeStyle=orthogonalEdgeStyle;',
        'rounded=1;',
        'orthogonalLoop=1;',
        'jettySize=auto;',
    ]
    stroke = s.get('strokeColor', '#666666')
    parts.append(f'strokeColor={stroke};')
    parts.append(f'strokeWidth={s.get("strokeWidth", 1.5)};')
    parts.append(f'fontSize={DEFAULT_FONT_SIZE - 1};')
    parts.append('fontColor=#333333;')

    if s.get('dashPattern'):
        parts.append('dashed=1;dashPattern=8 4;')

    arrow_map = {'arrow': 'classic', 'circle': 'oval', 'diamond': 'ERmanyToOne', 'none': 'none'}
    if s.get('endArrow'):
        parts.append(f'endArrow={arrow_map.get(s["endArrow"], "classic")};')
    else:
        parts.append('endArrow=classic;endFill=1;')
    if s.get('startArrow'):
        parts.append(f'startArrow={arrow_map.get(s["startArrow"], "none")};')

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
        geo = c.get('geometry', {'x': 40, 'y': 40, 'width': 400, 'height': 300})
        w = geo.get('width', 400)
        h = geo.get('height', 300)
        s = c.get('style', {})
        style = (
            'swimlane;startSize=28;'
            f'fillColor={s.get("fillColor", "#F5F5F5")};'
            f'strokeColor={s.get("strokeColor", "#666666")};'
            f'fontColor={s.get("fontColor", "#333333")};'
            f'fontSize={DEFAULT_FONT_SIZE};'
            'fontStyle=1;'
            'rounded=1;'
            'shadow=0;'
        )
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
        geo = n.get('geometry', {'x': 100, 'y': 100, 'width': 160, 'height': 50})
        w = geo.get('width', 160)
        h = geo.get('height', 50)
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
    <mxGraphModel dx="1422" dy="800" grid="1" gridSize="10" guides="1"
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
    'rectangle': 'rectangle', 'rounded': 'rectangle', 'diamond': 'diamond',
    'oval': 'ellipse', 'hexagon': 'rectangle', 'parallelogram': 'rectangle',
    'cylinder': 'ellipse', 'document': 'rectangle',
}

def _ex_node(el):
    geo = el.get('geometry', {'x': 100, 'y': 100, 'width': 160, 'height': 70})
    s = el.get('style', {})
    shape = el.get('shape', 'rectangle')
    ex_type = EX_TYPE.get(shape, 'rectangle')
    is_rounded = shape in ('rounded', 'oval')
    w = geo.get('width', 160)
    h = geo.get('height', 70)

    colors = SHAPE_COLORS.get(shape, SHAPE_COLORS['rectangle'])

    rect = {
        'id': el['id'], 'type': ex_type,
        'x': geo.get('x', 100), 'y': geo.get('y', 100),
        'width': w, 'height': h, 'angle': 0,
        'strokeColor': s.get('strokeColor', colors['stroke']),
        'backgroundColor': s.get('fillColor', colors['fill']),
        'fillStyle': 'solid',
        'strokeWidth': s.get('strokeWidth', 2),
        'strokeStyle': 'dashed' if s.get('dashPattern') else 'solid',
        'roughness': 0, 'opacity': 100,
        'roundness': {'type': 3} if is_rounded else None,
    }

    label = el.get('label', '')
    text = {
        'id': uid(), 'type': 'text',
        'x': geo.get('x', 100) + w / 2 - len(label) * 5,
        'y': geo.get('y', 100) + h / 2 - 10,
        'width': len(label) * 10 + 16, 'height': 25, 'angle': 0,
        'strokeColor': s.get('fontColor', colors['font']),
        'backgroundColor': 'transparent',
        'fillStyle': 'hachure', 'strokeWidth': 1, 'strokeStyle': 'solid',
        'roughness': 0, 'opacity': 100, 'roundness': None,
        'text': label, 'fontSize': s.get('fontSize', DEFAULT_FONT_SIZE + 1),
        'fontFamily': 1, 'textAlign': 'center', 'verticalAlign': 'middle',
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
        'id': el['id'], 'type': 'rectangle',
        'x': geo.get('x', 40), 'y': geo.get('y', 40),
        'width': w, 'height': h, 'angle': 0,
        'strokeColor': s.get('strokeColor', '#4a4a8a'),
        'backgroundColor': s.get('fillColor', '#e8e8f8'),
        'fillStyle': 'solid', 'strokeWidth': s.get('strokeWidth', 2),
        'strokeStyle': 'solid', 'roughness': 0, 'opacity': 40,
        'roundness': {'type': 3}, 'groupIds': [],
    }
    label = {
        'id': uid(), 'type': 'text',
        'x': geo.get('x', 40) + 12, 'y': geo.get('y', 40) + 8,
        'width': len(name) * 10 + 16, 'height': 22, 'angle': 0,
        'strokeColor': s.get('fontColor', '#4a4a8a'),
        'backgroundColor': 'transparent',
        'fillStyle': 'hachure', 'strokeWidth': 1, 'strokeStyle': 'solid',
        'roughness': 0, 'opacity': 100, 'roundness': None,
        'text': name, 'fontSize': 14, 'fontFamily': 1,
        'textAlign': 'left', 'verticalAlign': 'top', 'fontStyle': 1,
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
        'id': el['id'], 'type': 'arrow',
        'x': sx, 'y': sy,
        'width': abs(tx - sx), 'height': abs(ty - sy), 'angle': 0,
        'strokeColor': s.get('strokeColor', '#666666'),
        'backgroundColor': 'transparent',
        'fillStyle': 'hachure', 'strokeWidth': s.get('strokeWidth', 2),
        'strokeStyle': 'dashed' if s.get('dashPattern') else 'solid',
        'roughness': 0, 'opacity': 100, 'roundness': {'type': 2},
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
        'type': 'excalidraw', 'version': 2, 'source': 'flowchart-local',
        'elements': out,
        'appState': {'gridSize': None, 'viewBackgroundColor': '#ffffff'},
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

    # 自动布局（drawio/excalidraw 需要坐标）
    if fmt in ('drawio', 'excalidraw'):
        auto_layout(spec)

    # 应用默认配色
    apply_default_colors(spec)

    content = gen(spec)

    if args.output:
        out_path = args.output
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'File saved: {out_path}', file=sys.stderr)

    print(content)

if __name__ == '__main__':
    main()
