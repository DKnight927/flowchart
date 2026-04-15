import { DiagramSpec, ContainerElement, NodeElement, EdgeElement, NodeShape } from '../types';

const EX_TYPE: Record<NodeShape, string> = {
  rectangle:    'rectangle',
  rounded:      'rectangle',
  diamond:      'diamond',
  oval:         'ellipse',
  hexagon:      'rectangle',  // excalidraw has no native hexagon; use rectangle
  parallelogram:'rectangle',
  cylinder:     'ellipse',
  document:     'rectangle',
};

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

function hex2rgb(hex: string): string {
  return hex; // excalidraw accepts hex directly
}

interface ExElement {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  angle: number;
  strokeColor: string;
  backgroundColor: string;
  fillStyle: string;
  strokeWidth: number;
  strokeStyle: string;
  roughness: number;
  opacity: number;
  roundness: { type: number } | null;
  [key: string]: unknown;
}

function makeNode(el: NodeElement): ExElement[] {
  const geo = el.geometry ?? { x: 100, y: 100, width: 160, height: 70 };
  const s = el.style ?? {};
  const exType = EX_TYPE[el.shape ?? 'rectangle'];
  const isRounded = el.shape === 'rounded' || el.shape === 'oval';

  const rect: ExElement = {
    id: el.id,
    type: exType,
    x: geo.x,
    y: geo.y,
    width: geo.width ?? 160,
    height: geo.height ?? 70,
    angle: 0,
    strokeColor: s.strokeColor ?? '#1e1e1e',
    backgroundColor: s.fillColor ?? 'transparent',
    fillStyle: s.fillColor ? 'solid' : 'hachure',
    strokeWidth: s.strokeWidth ?? 2,
    strokeStyle: s.dashPattern ? 'dashed' : 'solid',
    roughness: 1,
    opacity: 100,
    roundness: isRounded ? { type: 3 } : null,
  };

  // label as separate text element
  const text: ExElement = {
    id: uid(),
    type: 'text',
    x: geo.x + (geo.width ?? 160) / 2 - el.label.length * 4,
    y: geo.y + (geo.height ?? 70) / 2 - 10,
    width: el.label.length * 8 + 16,
    height: 25,
    angle: 0,
    strokeColor: s.fontColor ?? '#1e1e1e',
    backgroundColor: 'transparent',
    fillStyle: 'hachure',
    strokeWidth: 1,
    strokeStyle: 'solid',
    roughness: 1,
    opacity: 100,
    roundness: null,
    text: el.label,
    fontSize: s.fontSize ?? 16,
    fontFamily: 1,
    textAlign: 'center',
    verticalAlign: 'middle',
    containerId: el.id,
  };

  return [rect, text];
}

function makeContainer(el: ContainerElement): ExElement[] {
  const geo = el.geometry ?? { x: 40, y: 40, width: 320, height: 220 };
  const s = el.style ?? {};

  const rect: ExElement = {
    id: el.id,
    type: 'rectangle',
    x: geo.x,
    y: geo.y,
    width: geo.width ?? 320,
    height: geo.height ?? 220,
    angle: 0,
    strokeColor: s.strokeColor ?? '#4a4a8a',
    backgroundColor: s.fillColor ?? '#e8e8f8',
    fillStyle: 'solid',
    strokeWidth: s.strokeWidth ?? 2,
    strokeStyle: 'solid',
    roughness: 0,
    opacity: 80,
    roundness: { type: 3 },
    groupIds: [],
  };

  const label: ExElement = {
    id: uid(),
    type: 'text',
    x: geo.x + 12,
    y: geo.y + 8,
    width: el.name.length * 9 + 16,
    height: 22,
    angle: 0,
    strokeColor: s.fontColor ?? '#4a4a8a',
    backgroundColor: 'transparent',
    fillStyle: 'hachure',
    strokeWidth: 1,
    strokeStyle: 'solid',
    roughness: 1,
    opacity: 100,
    roundness: null,
    text: el.name,
    fontSize: 14,
    fontFamily: 1,
    textAlign: 'left',
    verticalAlign: 'top',
    fontStyle: 1, // bold
  };

  return [rect, label];
}

function makeEdge(el: EdgeElement, nodeMap: Map<string, NodeElement>): ExElement {
  const src = nodeMap.get(el.source);
  const tgt = nodeMap.get(el.target);
  const sx = src ? (src.geometry?.x ?? 0) + (src.geometry?.width ?? 160) / 2 : 0;
  const sy = src ? (src.geometry?.y ?? 0) + (src.geometry?.height ?? 70) : 0;
  const tx = tgt ? (tgt.geometry?.x ?? 200) + (tgt.geometry?.width ?? 160) / 2 : 200;
  const ty = tgt ? (tgt.geometry?.y ?? 200) : 200;
  const s = el.style ?? {};

  return {
    id: el.id,
    type: 'arrow',
    x: sx,
    y: sy,
    width: Math.abs(tx - sx),
    height: Math.abs(ty - sy),
    angle: 0,
    strokeColor: s.strokeColor ?? '#1e1e1e',
    backgroundColor: 'transparent',
    fillStyle: 'hachure',
    strokeWidth: s.strokeWidth ?? 2,
    strokeStyle: s.dashPattern ? 'dashed' : 'solid',
    roughness: 1,
    opacity: 100,
    roundness: { type: 2 },
    points: [[0, 0], [tx - sx, ty - sy]],
    lastCommittedPoint: null,
    startBinding: { elementId: el.source, focus: 0, gap: 8 },
    endBinding: { elementId: el.target, focus: 0, gap: 8 },
    startArrowhead: s.startArrow && s.startArrow !== 'none' ? 'arrow' : null,
    endArrowhead: s.endArrow === 'none' ? null : 'arrow',
    label: el.label,
  };
}

export function generateExcalidraw(spec: DiagramSpec): string {
  const nodes   = spec.elements.filter((e): e is NodeElement      => e.type === 'node');
  const conts   = spec.elements.filter((e): e is ContainerElement => e.type === 'container');
  const edges   = spec.elements.filter((e): e is EdgeElement      => e.type === 'edge');

  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  const elements: ExElement[] = [];

  for (const c of conts)  elements.push(...makeContainer(c));
  for (const n of nodes)  elements.push(...makeNode(n));
  for (const e of edges)  elements.push(makeEdge(e, nodeMap));

  const doc = {
    type: 'excalidraw',
    version: 2,
    source: 'mcp-diagram-generator',
    elements,
    appState: {
      gridSize: null,
      viewBackgroundColor: '#ffffff',
    },
    files: {},
  };

  return JSON.stringify(doc, null, 2);
}
