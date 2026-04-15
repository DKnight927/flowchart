export type DiagramFormat = 'mermaid' | 'drawio' | 'excalidraw';

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

export interface ContainerElement {
  id: string;
  type: 'container';
  name: string;
  level?: string;
  children?: string[];
  style?: NodeStyle;
  geometry?: Geometry;
}

export type NodeShape =
  | 'rectangle'
  | 'diamond'
  | 'oval'
  | 'rounded'
  | 'hexagon'
  | 'parallelogram'
  | 'cylinder'
  | 'document';

export interface NodeElement {
  id: string;
  type: 'node';
  label: string;
  shape?: NodeShape;
  style?: NodeStyle;
  geometry?: Geometry;
}

export interface EdgeElement {
  id: string;
  type: 'edge';
  source: string;
  target: string;
  label?: string;
  style?: EdgeStyle;
}

export type DiagramElement = ContainerElement | NodeElement | EdgeElement;

export interface DiagramSpec {
  format: DiagramFormat;
  title?: string;
  elements: DiagramElement[];
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
