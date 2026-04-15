#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import express, { Request, Response } from 'express';
import { randomUUID } from 'crypto';
import * as fs from 'fs';
import { loadConfig, initConfig, getOutputPath } from './config';
import { generateMermaid } from './generators/mermaid';
import { generateDrawio } from './generators/drawio';
import { generateExcalidraw } from './generators/excalidraw';
import { DiagramSpec, DiagramFormat } from './types';

const PORT = parseInt(process.env.PORT ?? '3000', 10);

function createMcpServer() {
  const server = new Server(
    { name: 'flowchart', version: '1.0.0' },
    { capabilities: { tools: {} } },
  );

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
        description: 'Generate a diagram file. Supports 7 diagram types (flowchart/sequence/class/er/mindmap/architecture/network) in 3 output formats (mermaid/drawio/excalidraw).',
        inputSchema: {
          type: 'object',
          required: ['diagram_spec'],
          properties: {
            diagram_spec: {
              type: 'object',
              description: 'Diagram specification',
              required: ['format', 'diagramType', 'elements'],
              properties: {
                format: { type: 'string', enum: ['mermaid', 'drawio', 'excalidraw'] },
                diagramType: { type: 'string', enum: ['flowchart', 'sequence', 'class', 'er', 'mindmap', 'architecture', 'network'] },
                title: { type: 'string' },
                direction: { type: 'string', enum: ['TD', 'LR', 'BT', 'RL'] },
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
                      properties: { type: 'array', items: { type: 'string' } },
                      methods:    { type: 'array', items: { type: 'string' } },
                      attributes: { type: 'array', items: { type: 'object' } },
                      parent:     { type: 'string' },
                      participantType: { type: 'string', enum: ['participant', 'actor'] },
                      stereotype: { type: 'string' },
                      messageType: { type: 'string', enum: ['sync', 'async', 'return', 'note'] },
                      relationType: { type: 'string' },
                      activate:   { type: 'boolean' },
                      deactivate: { type: 'boolean' },
                      fragment:   { type: 'string' },
                      fragmentLabel: { type: 'string' },
                    },
                  },
                },
              },
            },
            output_path: { type: 'string', description: 'Custom output file path (optional)' },
            filename:    { type: 'string', description: 'Custom filename without extension (optional)' },
          },
        },
      },
    ],
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
      if (name === 'init_config') {
        const paths = (args as any)?.paths;
        const config = initConfig(paths);
        return { content: [{ type: 'text', text: `Config initialized.\n${JSON.stringify(config, null, 2)}` }] };
      }

      if (name === 'get_config') {
        const config = loadConfig();
        return { content: [{ type: 'text', text: JSON.stringify(config, null, 2) }] };
      }

      if (name === 'liuchengtu') {
        const { diagram_spec, output_path, filename } = args as {
          diagram_spec: DiagramSpec;
          output_path?: string;
          filename?: string;
        };

        const format: DiagramFormat = diagram_spec.format;
        const title = diagram_spec.title ?? filename ?? 'diagram';

        let content: string;
        if (format === 'mermaid')         content = generateMermaid(diagram_spec);
        else if (format === 'drawio')     content = generateDrawio(diagram_spec);
        else if (format === 'excalidraw') content = generateExcalidraw(diagram_spec);
        else throw new Error(`Unsupported format: ${format}`);

        let filePath: string;
        if (output_path) {
          filePath = output_path;
          fs.mkdirSync(require('path').dirname(filePath), { recursive: true });
        } else {
          const config = loadConfig();
          if (!config.initialized) initConfig();
          filePath = getOutputPath(loadConfig(), format, title);
        }

        fs.writeFileSync(filePath, content, 'utf-8');

        // Return the diagram content inline so the AI can display it to the user
        // regardless of whether the user has access to the server's filesystem
        return {
          content: [
            {
              type: 'text',
              text: [
                `Diagram generated successfully.`,
                `Format: ${format} | Type: ${diagram_spec.diagramType} | Title: ${title}`,
                `---DIAGRAM_CONTENT_START---`,
                content,
                `---DIAGRAM_CONTENT_END---`,
              ].join('\n'),
            },
          ],
        };
      }

      throw new Error(`Unknown tool: ${name}`);
    } catch (err) {
      return { content: [{ type: 'text', text: `Error: ${(err as Error).message}` }], isError: true };
    }
  });

  return server;
}

// ─── Express HTTP server ──────────────────────────────────────────────────────

const app = express();
app.use(express.json());

const transports = new Map<string, StreamableHTTPServerTransport>();

app.all('/mcp', async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined;

  let transport: StreamableHTTPServerTransport;

  if (sessionId && transports.has(sessionId)) {
    transport = transports.get(sessionId)!;
  } else if (!sessionId && req.method === 'POST') {
    transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
      onsessioninitialized: (id) => { transports.set(id, transport); },
    });
    transport.onclose = () => { if (transport.sessionId) transports.delete(transport.sessionId); };
    await createMcpServer().connect(transport);
  } else {
    res.status(400).json({ error: 'Bad request: missing or invalid session' });
    return;
  }

  await transport.handleRequest(req, res, req.body);
});

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', sessions: transports.size });
});

app.listen(PORT, () => {
  console.log(`flowchart MCP server running on http://localhost:${PORT}/mcp`);
  console.log(`Health: http://localhost:${PORT}/health`);
});
