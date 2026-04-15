import { DiagramSpec, ContainerElement, NodeElement, EdgeElement, NodeShape, DiagramType } from '../types';

// ─── Shared helpers ──────────────────────────────────────────────────────────

function esc(label: string): string {
  return label.replace(/"/g, '#quot;');
}

// ─── Flowchart ───────────────────────────────────────────────────────────────

const SHAPE_SYNTAX: Record<NodeShape, [string, string]> = {
  rectangle:     ['[', ']'],
  diamond:       ['{', '}'],
  oval:          ['((', '))'],
  rounded:       ['(', ')'],
  hexagon:       ['{{', '}}'],
  parallelogram: ['[/', '/]'],
  cylinder:      ['[(', ')]'],
  document:      ['[/', '\\]'],
};

function flowchartNode(el: NodeElement): string {
  const [open, close] = SHAPE_SYNTAX[el.shape ?? 'rectangle'];
  return `  ${el.id}${open}"${esc(el.label)}"${close}`;
}

function flowchartEdge(el: EdgeElement): string {
  const label = el.label ? `|"${esc(el.label)}"| ` : '';
  const arrow = el.style?.dashPattern ? '-.->' : '-->';
  return `  ${el.source} ${arrow} ${label}${el.target}`;
}

function genFlowchart(spec: DiagramSpec): string {
  const containers = spec.elements.filter((e): e is ContainerElement => e.type === 'container');
  const nodes      = spec.elements.filter((e): e is NodeElement      => e.type === 'node');
  const edges      = spec.elements.filter((e): e is EdgeElement      => e.type === 'edge');
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const containedIds = new Set(containers.flatMap(c => c.children ?? []));

  const lines: string[] = [];
  if (spec.title) lines.push(`---\ntitle: ${spec.title}\n---`);
  lines.push(`flowchart ${spec.direction ?? 'TD'}`);

  for (const n of nodes) {
    if (!containedIds.has(n.id)) lines.push(flowchartNode(n));
  }
  for (const c of containers) {
    lines.push(`  subgraph ${c.id}["${c.name}"]`);
    for (const childId of c.children ?? []) {
      const child = nodeMap.get(childId);
      if (child) lines.push('  ' + flowchartNode(child));
    }
    lines.push('  end');
  }
  for (const e of edges) lines.push(flowchartEdge(e));

  // inline styles
  for (const n of nodes) {
    const s = n.style;
    if (!s) continue;
    const parts: string[] = [];
    if (s.fillColor)   parts.push(`fill:${s.fillColor}`);
    if (s.strokeColor) parts.push(`stroke:${s.strokeColor}`);
    if (s.fontColor)   parts.push(`color:${s.fontColor}`);
    if (parts.length)  lines.push(`  style ${n.id} ${parts.join(',')}`);
  }

  return lines.join('\n') + '\n';
}

// ─── Sequence Diagram ────────────────────────────────────────────────────────

function genSequence(spec: DiagramSpec): string {
  const nodes = spec.elements.filter((e): e is NodeElement => e.type === 'node');
  const edges = spec.elements.filter((e): e is EdgeElement => e.type === 'edge');
  const containers = spec.elements.filter((e): e is ContainerElement => e.type === 'container');

  const lines: string[] = [];
  if (spec.title) lines.push(`---\ntitle: ${spec.title}\n---`);
  lines.push('sequenceDiagram');

  for (const n of nodes) {
    const keyword = n.participantType === 'actor' ? 'actor' : 'participant';
    lines.push(`  ${keyword} ${n.id} as ${n.label}`);
  }

  // Build a map: edgeId -> which container it belongs to
  const edgeToContainer = new Map<string, ContainerElement>();
  for (const c of containers) {
    for (const ch of c.children ?? []) {
      edgeToContainer.set(ch, c);
    }
  }

  // Track which containers we've opened/closed
  const openedContainers = new Set<string>();
  let currentContainer: ContainerElement | null = null;

  for (const e of edges) {
    const container = edgeToContainer.get(e.id);

    // Close previous container if we've moved to a different one (or none)
    if (currentContainer && (!container || container.id !== currentContainer.id)) {
      lines.push(`  end`);
      currentContainer = null;
    }

    // Open new container if this edge belongs to one we haven't opened
    if (container && !openedContainers.has(container.id)) {
      const keyword = container.fragment ?? 'alt';
      const label = container.fragmentLabel ?? container.name;
      lines.push(`  ${keyword} ${label}`);
      openedContainers.add(container.id);
      currentContainer = container;
    }

    const arrow = e.messageType === 'async'  ? '-->>'
                : e.messageType === 'return' ? '-->'
                : '->>';
    const label = e.label ?? '';
    lines.push(`  ${e.source}${arrow}${e.target}: ${label}`);
    if (e.activate) lines.push(`  activate ${e.target}`);
    if (e.deactivate) lines.push(`  deactivate ${e.source}`);
  }

  // Close any remaining open container
  if (currentContainer) {
    lines.push(`  end`);
  }

  // Render containers that have no edge children (standalone notes/rects)
  for (const c of containers) {
    if (!openedContainers.has(c.id) && c.fragment) {
      lines.push(`  ${c.fragment} ${c.fragmentLabel ?? c.name}`);
      lines.push(`  end`);
    }
  }

  return lines.join('\n') + '\n';
}

// ─── Class Diagram ───────────────────────────────────────────────────────────

function genClass(spec: DiagramSpec): string {
  const nodes = spec.elements.filter((e): e is NodeElement => e.type === 'node');
  const edges = spec.elements.filter((e): e is EdgeElement => e.type === 'edge');

  const lines: string[] = [];
  if (spec.title) lines.push(`---\ntitle: ${spec.title}\n---`);
  lines.push('classDiagram');

  for (const n of nodes) {
    lines.push(`  class ${n.id}["${esc(n.label)}"]`);
    if (n.stereotype) lines.push(`  <<${n.stereotype}>> ${n.id}`);
    for (const p of n.properties ?? []) lines.push(`  ${n.id} : ${p}`);
    for (const m of n.methods ?? [])    lines.push(`  ${n.id} : ${m}`);
  }

  const REL_ARROW: Record<string, string> = {
    inheritance:  '<|--',
    composition:  '*--',
    aggregation:  'o--',
    association:  '-->',
    dependency:   '..>',
    realization:  '..|>',
  };

  for (const e of edges) {
    const arrow = REL_ARROW[e.relationType ?? 'association'] ?? '-->';
    const label = e.label ? ` : ${e.label}` : '';
    lines.push(`  ${e.source} ${arrow} ${e.target}${label}`);
  }

  return lines.join('\n') + '\n';
}

// ─── ER Diagram ──────────────────────────────────────────────────────────────

function genER(spec: DiagramSpec): string {
  const nodes = spec.elements.filter((e): e is NodeElement => e.type === 'node');
  const edges = spec.elements.filter((e): e is EdgeElement => e.type === 'edge');

  const lines: string[] = [];
  if (spec.title) lines.push(`---\ntitle: ${spec.title}\n---`);
  lines.push('erDiagram');

  // relationships first
  const CARDINALITY: Record<string, string> = {
    'one-to-one':   '||--||',
    'one-to-many':  '||--o{',
    'many-to-many': '}o--o{',
  };

  for (const e of edges) {
    const card = CARDINALITY[e.relationType ?? 'one-to-many'] ?? '||--o{';
    const label = e.label ? `"${esc(e.label)}"` : '""';
    lines.push(`  ${e.source} ${card} ${e.target} : ${label}`);
  }

  // entity attributes
  for (const n of nodes) {
    lines.push(`  ${n.id} {`);
    for (const attr of n.attributes ?? []) {
      const key = attr.key ? ` ${attr.key}` : '';
      lines.push(`    ${attr.type} ${attr.name}${key}`);
    }
    if (!n.attributes?.length) {
      lines.push(`    string ${n.label.replace(/\s+/g, '_')}`);
    }
    lines.push(`  }`);
  }

  return lines.join('\n') + '\n';
}

// ─── Mindmap ─────────────────────────────────────────────────────────────────

function genMindmap(spec: DiagramSpec): string {
  const nodes = spec.elements.filter((e): e is NodeElement => e.type === 'node');

  const lines: string[] = [];
  lines.push('mindmap');

  // build tree from parent references
  const childMap = new Map<string | undefined, NodeElement[]>();
  for (const n of nodes) {
    const parentId = n.parent;
    if (!childMap.has(parentId)) childMap.set(parentId, []);
    childMap.get(parentId)!.push(n);
  }

  function renderNode(node: NodeElement, depth: number) {
    const indent = '  '.repeat(depth + 1);
    lines.push(`${indent}${node.label}`);
    const children = childMap.get(node.id) ?? [];
    for (const child of children) renderNode(child, depth + 1);
  }

  // root nodes: those without parent
  const roots = childMap.get(undefined) ?? [];
  if (roots.length === 0 && nodes.length > 0) {
    // fallback: first node is root
    const indent = '  ';
    lines.push(`${indent}root((${spec.title ?? 'Root'}))`);
    for (const n of nodes) lines.push(`${'  '.repeat(2)}${n.label}`);
  } else {
    for (const root of roots) renderNode(root, 0);
  }

  return lines.join('\n') + '\n';
}

// ─── Architecture / Network (flowchart with styling) ─────────────────────────

function genArchitecture(spec: DiagramSpec): string {
  // Use flowchart rendering with some semantic sugar
  return genFlowchart(spec);
}

function genNetwork(spec: DiagramSpec): string {
  return genFlowchart(spec);
}

// ─── Entry point ─────────────────────────────────────────────────────────────

const GENERATORS: Record<DiagramType, (spec: DiagramSpec) => string> = {
  flowchart:    genFlowchart,
  sequence:     genSequence,
  class:        genClass,
  er:           genER,
  mindmap:      genMindmap,
  architecture: genArchitecture,
  network:      genNetwork,
};

export function generateMermaid(spec: DiagramSpec): string {
  const diagramType = spec.diagramType ?? 'flowchart';
  const gen = GENERATORS[diagramType];
  if (!gen) throw new Error(`Unsupported diagram type for mermaid: ${diagramType}`);
  return gen(spec);
}
