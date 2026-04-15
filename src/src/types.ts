export type DiagramFormat = 'mermaid' | 'drawio' | 'excalidraw';

export type DiagramType =
  | 'flowchart'
  | 'sequence'
  | 'class'
  | 'er'
  | 'mindmap'
  | 'architecture'
  | 'network';

// ─── Styles ──────────────────────────────────────────────────────────────────

export interface NodeStyle {
  fillColor?: string;
  strokeColor?: string;
  strokeWidth?: number;
  fontColor?: string;
  fontSize?: number;
  fontStyle?: 'normal' | 'bold' | 'italic';
  borderRadius?: number;
  dashPattern?: string;
}

export interface EdgeStyle {
  strokeColor?: string;
  strokeWidth?: number;
  endArrow?: 'none' | 'arrow' | 'circle' | 'diamond';
  startArrow?: 'none' | 'arrow' | 'circle' | 'diamond';
  dashPattern?: string;
  lineStyle?: 'straight' | 'orthogonal' | 'curved';
}

export interface Geometry {
  x: number;
  y: number;
  width?: number;
  height?: number;
}

// ─── Node shapes ─────────────────────────────────────────────────────────────

export type NodeShape =
  | 'rectangle'
  | 'diamond'
  | 'oval'
  | 'rounded'
  | 'hexagon'
  | 'parallelogram'
  | 'cylinder'
  | 'document';

// ─── Elements ────────────────────────────────────────────────────────────────

export interface NodeElement {
  id: string;
  type: 'node';
  label: string;
  shape?: NodeShape;
  style?: NodeStyle;
  geometry?: Geometry;
  // class diagram: properties and methods
  properties?: string[];
  methods?: string[];
  // ER diagram: attributes
  attributes?: Array<{ name: string; type: string; key?: 'PK' | 'FK' | 'UK' }>;
  // mindmap: parent node id for hierarchy
  parent?: string;
  // sequence: participant type
  participantType?: 'participant' | 'actor';
  // architecture/network: stereotype label
  stereotype?: string;
}

export interface EdgeElement {
  id: string;
  type: 'edge';
  source: string;
  target: string;
  label?: string;
  style?: EdgeStyle;
  // sequence diagram: message type
  messageType?: 'sync' | 'async' | 'return' | 'note';
  // class/ER diagram: relationship type
  relationType?: 'inheritance' | 'composition' | 'aggregation' | 'association'
    | 'dependency' | 'realization'
    | 'one-to-one' | 'one-to-many' | 'many-to-many';
  // sequence: activation
  activate?: boolean;
  deactivate?: boolean;
}

export interface ContainerElement {
  id: string;
  type: 'container';
  name: string;
  level?: string;
  children?: string[];
  style?: NodeStyle;
  geometry?: Geometry;
  // sequence: alt/opt/loop/par fragment
  fragment?: 'alt' | 'opt' | 'loop' | 'par' | 'critical' | 'break';
  fragmentLabel?: string;
}

export type DiagramElement = ContainerElement | NodeElement | EdgeElement;

// ─── Spec & Config ───────────────────────────────────────────────────────────

export interface DiagramSpec {
  format: DiagramFormat;
  diagramType: DiagramType;
  title?: string;
  elements: DiagramElement[];
  // sequence: note elements
  direction?: 'TD' | 'LR' | 'BT' | 'RL';
}

export interface DiagramConfig {
  paths: {
    drawio: string;
    mermaid: string;
    excalidraw: string;
  };
  initialized: boolean;
}

export interface GenerateResult {
  filePath: string;
  format: DiagramFormat;
  title: string;
}
