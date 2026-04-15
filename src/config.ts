import * as fs from 'fs';
import * as path from 'path';
import { DiagramConfig, DiagramFormat } from './types';

const CONFIG_FILE = '.diagram-config.json';

const DEFAULT_CONFIG: DiagramConfig = {
  paths: {
    drawio: 'diagrams/drawio',
    mermaid: 'diagrams/mermaid',
    excalidraw: 'diagrams/excalidraw',
  },
  initialized: true,
};

export function loadConfig(): DiagramConfig {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      const raw = fs.readFileSync(CONFIG_FILE, 'utf-8');
      return JSON.parse(raw) as DiagramConfig;
    }
  } catch {
    // fall through to default
  }
  return { ...DEFAULT_CONFIG, initialized: false };
}

export function saveConfig(config: DiagramConfig): void {
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8');
}

export function initConfig(customPaths?: Partial<DiagramConfig['paths']>): DiagramConfig {
  const config: DiagramConfig = {
    paths: { ...DEFAULT_CONFIG.paths, ...customPaths },
    initialized: true,
  };
  saveConfig(config);
  return config;
}

export function getOutputPath(config: DiagramConfig, format: DiagramFormat, filename: string): string {
  const dir = config.paths[format];
  const ext = { drawio: '.drawio', mermaid: '.md', excalidraw: '.excalidraw' }[format];
  const date = new Date().toISOString().slice(0, 10);
  const safe = filename.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '-');
  const fullPath = path.join(dir, `${safe}-${date}${ext}`);
  fs.mkdirSync(dir, { recursive: true });
  return fullPath;
}
