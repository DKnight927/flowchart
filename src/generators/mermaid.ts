import { DiagramSpec, ContainerElement, NodeElement, EdgeElement, NodeShape } from '../types';

const SHAPE_SYNTAX: Record<NodeShape, [string, string]> = {
  rectangle:    ['[', ']'],
  diamond:      ['{', '}'],
  oval:         ['((', '))'],
  rounded:      ['(', ')'],
  hexagon:      ['{{', '}}'],
  parallelogram:['[/', '/]'],
  cylinder:     ['[(', ')]'],
  document:     ['[/', '\\]'],
};

function escapeLabel(label: string): string {
  return label.replace(/"/g, '#quot;');
}

function nodeToMermaid(el: NodeElement): string {
  const [open, close] = SHAPE_SYNTAX[el.shape ?? 'rectangle'];
  return `  ${el.id}${open}"${escapeLabel(el.label)}"${close}`;
}

function edgeToMermaid(el: EdgeElement): string {
  const label = el.label ? `|"${escapeLabel(el.label)}"| ` : '';
  const arrow = el.style?.dashPattern ? '-.->' : '-->';
  return `  ${el.source} ${arrow} ${label}${el.target}`;
}

function containerToMermaid(
  el: ContainerElement,
  nodeMap: Map<string, NodeElement>,
): string {
  const lines: string[] = [`  subgraph ${el.id}["${el.name}"]`];
  for (const childId of el.children ?? []) {
    const child = nodeMap.get(childId);
    if (child) lines.push('  ' + nodeToMermaid(child));
  }
  lines.push('  end');
  return lines.join('\n');
}

export function generateMermaid(spec: DiagramSpec): string {
  const containers = spec.elements.filter((e): e is ContainerElement => e.type === 'container');
  const nodes      = spec.elements.filter((e): e is NodeElement      => e.type === 'node');
  const edges      = spec.elements.filter((e): e is EdgeElement      => e.type === 'edge');

  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  // nodes that belong to a container are rendered inside subgraph
  const containedIds = new Set(containers.flatMap(c => c.children ?? []));

  const lines: string[] = [];

  if (spec.title) lines.push(`---\ntitle: ${spec.title}\n---`);
  lines.push('flowchart TD');

  // standalone nodes
  for (const node of nodes) {
    if (!containedIds.has(node.id)) {
      lines.push(nodeToMermaid(node));
    }
  }

  // containers (subgraphs)
  for (const container of containers) {
    lines.push(containerToMermaid(container, nodeMap));
  }

  // edges
  for (const edge of edges) {
    lines.push(edgeToMermaid(edge));
  }

  // inline styles
  for (const node of nodes) {
    const s = node.style;
    if (!s) continue;
    const parts: string[] = [];
    if (s.fillColor)   parts.push(`fill:${s.fillColor}`);
    if (s.strokeColor) parts.push(`stroke:${s.strokeColor}`);
    if (s.fontColor)   parts.push(`color:${s.fontColor}`);
    if (parts.length)  lines.push(`  style ${node.id} ${parts.join(',')}`);
  }

  return lines.join('\n') + '\n';
}
