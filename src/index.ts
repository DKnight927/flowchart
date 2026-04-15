#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import * as fs from 'fs';
import { loadConfig, initConfig, saveConfig, getOutputPath } from './config';
import { generateMermaid } from './generators/mermaid';
import { generateDrawio } from './generators/drawio';
import { generateExcalidraw } from './generators/excalidraw';
import { DiagramSpec, DiagramFormat } from './types';

// ─── Server setup ────────────────────────────────────────────────────────────

const server = new Server(
  { name: 'mcp-diagram-generator', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

// ─── Tool definitions ─────────────────────────────────────────────────────────

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'init_config',
      description: 'Initialize or reset output path configuration. Call this before first use.',
      inputSchema: {
        type: 'object',
        properties: {
          paths: {
            type: 'object',
            description: 'Custom output directories for each format',
            properties: {
              drawio:     { type: 'string' },
              mermaid:    { type: 'string' },
              excalidraw: { type: 'string' },
            },
          },
        },
      },
    },
    {
      name: 'get_config',
      description: 'Return current output path configuration.',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'liuchengtu',
      description:
        'Generate a diagram file from a structured JSON spec. Supports drawio, mermaid, and excalidraw formats.',
      inputSchema: {
        type: 'object',
        required: ['diagram_spec'],
        properties: {
          diagram_spec: {
            type: 'object',
            description: 'Diagram specification (see schema)',
            required: ['format', 'elements'],
            properties: {
              format: {
                type: 'string',
                enum: ['drawio', 'mermaid', 'excalidraw'],
              },
              title: { type: 'string' },
              elements: {
                type: 'array',
                items: {
                  type: 'object',
                  required: ['id', 'type'],
                  properties: {
                    id:       { type: 'string' },
                    type:     { type: 'string', enum: ['node', 'edge', 'container'] },
                    label:    { type: 'string' },
                    name:     { type: 'string' },
                    shape:    { type: 'string' },
                    source:   { type: 'string' },
                    target:   { type: 'string' },
                    children: { type: 'array', items: { type: 'string' } },
                    style:    { type: 'object' },
                    geometry: { type: 'object' },
                  },
                },
              },
            },
          },
          output_path: {
            type: 'string',
            description: 'Custom output file path (optional, overrides default directory)',
          },
          filename: {
            type: 'string',
            description: 'Custom filename without extension (optional)',
          },
        },
      },
    },
  ],
}));

// ─── Tool handlers ────────────────────────────────────────────────────────────

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    // ── init_config ──────────────────────────────────────────────────────────
    if (name === 'init_config') {
      const paths = (args as { paths?: Partial<{ drawio: string; mermaid: string; excalidraw: string }> })?.paths;
      const config = initConfig(paths);
      return {
        content: [
          {
            type: 'text',
            text: `Config initialized.\n${JSON.stringify(config, null, 2)}`,
          },
        ],
      };
    }

    // ── get_config ───────────────────────────────────────────────────────────
    if (name === 'get_config') {
      const config = loadConfig();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(config, null, 2),
          },
        ],
      };
    }

    // ── generate_diagram ─────────────────────────────────────────────────────
    if (name === 'liuchengtu') {
      const { diagram_spec, output_path, filename } = args as {
        diagram_spec: DiagramSpec;
        output_path?: string;
        filename?: string;
      };

      const spec = diagram_spec;
      const format: DiagramFormat = spec.format;
      const title = spec.title ?? filename ?? 'diagram';

      // generate content
      let content: string;
      if (format === 'mermaid') {
        content = generateMermaid(spec);
      } else if (format === 'drawio') {
        content = generateDrawio(spec);
      } else if (format === 'excalidraw') {
        content = generateExcalidraw(spec);
      } else {
        throw new Error(`Unsupported format: ${format}`);
      }

      // resolve output path
      let filePath: string;
      if (output_path) {
        filePath = output_path;
        const dir = require('path').dirname(filePath);
        fs.mkdirSync(dir, { recursive: true });
      } else {
        const config = loadConfig();
        if (!config.initialized) initConfig();
        filePath = getOutputPath(loadConfig(), format, title);
      }

      fs.writeFileSync(filePath, content, 'utf-8');

      return {
        content: [
          {
            type: 'text',
            text: [
              `✅ Diagram generated successfully`,
              `Format : ${format}`,
              `Title  : ${title}`,
              `File   : ${filePath}`,
              `Size   : ${content.length} bytes`,
            ].join('\n'),
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (err) {
    return {
      content: [{ type: 'text', text: `❌ Error: ${(err as Error).message}` }],
      isError: true,
    };
  }
});

// ─── Start ────────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('mcp-diagram-generator running on stdio\n');
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err.message}\n`);
  process.exit(1);
});
