import { DiagramSpec, ContainerElement, NodeElement, EdgeElement, NodeShape } from '../types';

let _cellId = 100;
function nextId(): number { return _cellId++; }

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

const SHAPE_STYLE: Record<NodeShape, string> = {
  rectangle:    'rounded=0;',
  rounded:      'rounded=1;arcSize=10;',
  diamond:      'rhombus;',
  oval:         'ellipse;',
  hexagon:      'shape=hexagon;perimeter=hexagonPerimeter2;',
  parallelogram:'shape=parallelogram;perimeter=parallelogramPerimeter;',
  cylinder:     'shape=mxgraph.flowchart.start_2;',
  document:     'shape=document;',
};

function nodeStyle(el: NodeElement): string {
  const base = SHAPE_STYLE[el.shape ?? 'rectangle'];
  const s = el.style ?? {};
  return [
    base,
    s.fillColor   ? `fillColor=${s.fillColor};`   : '',
    s.strokeColor ? `strokeColor=${s.strokeColor};` : '',
    s.fontColor   ? `fontColor=${s.fontColor};`   : '',
    s.fontSize    ? `fontSize=${s.fontSize};`     : '',
    s.fontStyle === 'bold'   ? 'fontStyle=1;' : '',
    s.fontStyle === 'italic' ? 'fontStyle=2;' : '',
    s.strokeWidth ? `strokeWidth=${s.strokeWidth};` : '',
    s.borderRadius ? `arcSize=${s.borderRadius};` : '',
    s.dashPattern ? `dashed=1;` : '',
  ].join('');
}

function edgeStyle(el: EdgeElement): string {
  const s = el.style ?? {};
  const arrow = { arrow: 'classic', circle: 'oval', diamond: 'ERmanyToOne', none: 'none' };
  return [
    'edgeStyle=orthogonalEdgeStyle;',
    s.strokeColor ? `strokeColor=${s.strokeColor};` : '',
    s.strokeWidth ? `strokeWidth=${s.strokeWidth};` : '',
    s.endArrow   ? `endArrow=${arrow[s.endArrow]};` : '',
    s.startArrow ? `startArrow=${arrow[s.startArrow]};` : '',
    s.dashPattern ? 'dashed=1;' : '',
    s.lineStyle === 'straight' ? 'edgeStyle=none;' : '',
    s.lineStyle === 'curved'   ? 'edgeStyle=elbowEdgeStyle;' : '',
  ].join('');
}

function renderNode(el: NodeElement, parentId: string, indent: string): string {
  const geo = el.geometry ?? { x: 100, y: 100, width: 120, height: 60 };
  const w = geo.width ?? 120;
  const h = geo.height ?? 60;
  return (
    `${indent}<mxCell id="${el.id}" value="${esc(el.label)}" style="${nodeStyle(el)}" ` +
    `vertex="1" parent="${parentId}">\n` +
    `${indent}  <mxGeometry x="${geo.x}" y="${geo.y}" width="${w}" height="${h}" as="geometry"/>\n` +
    `${indent}</mxCell>`
  );
}

function renderContainer(el: ContainerElement, indent: string): string {
  const geo = el.geometry ?? { x: 40, y: 40, width: 300, height: 200 };
  const w = geo.width ?? 300;
  const h = geo.height ?? 200;
  const s = el.style ?? {};
  const style = [
    'swimlane;',
    s.fillColor    ? `fillColor=${s.fillColor};`    : '',
    s.strokeColor  ? `strokeColor=${s.strokeColor};`  : '',
    s.fontColor    ? `fontColor=${s.fontColor};`    : '',
  ].join('');
  return (
    `${indent}<mxCell id="${el.id}" value="${esc(el.name)}" style="${style}" ` +
    `vertex="1" parent="1">\n` +
    `${indent}  <mxGeometry x="${geo.x}" y="${geo.y}" width="${w}" height="${h}" as="geometry"/>\n` +
    `${indent}</mxCell>`
  );
}

function renderEdge(el: EdgeElement, indent: string): string {
  return (
    `${indent}<mxCell id="${el.id}" value="${esc(el.label ?? '')}" style="${edgeStyle(el)}" ` +
    `edge="1" source="${el.source}" target="${el.target}" parent="1">\n` +
    `${indent}  <mxGeometry relative="1" as="geometry"/>\n` +
    `${indent}</mxCell>`
  );
}

export function generateDrawio(spec: DiagramSpec): string {
  _cellId = 100;
  const title = esc(spec.title ?? 'Diagram');

  const containers = spec.elements.filter((e): e is ContainerElement => e.type === 'container');
  const nodes      = spec.elements.filter((e): e is NodeElement      => e.type === 'node');
  const edges      = spec.elements.filter((e): e is EdgeElement      => e.type === 'edge');

  // map nodeId -> containerId
  const nodeParent = new Map<string, string>();
  for (const c of containers) {
    for (const childId of c.children ?? []) {
      nodeParent.set(childId, c.id);
    }
  }

  const cells: string[] = [];

  // containers first
  for (const c of containers) {
    cells.push(renderContainer(c, '        '));
  }

  // nodes
  for (const n of nodes) {
    const parent = nodeParent.get(n.id) ?? '1';
    cells.push(renderNode(n, parent, '        '));
  }

  // edges
  for (const e of edges) {
    cells.push(renderEdge(e, '        '));
  }

  return `<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram name="${title}">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1"
      tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1"
      pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
${cells.join('\n')}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
`;
}
