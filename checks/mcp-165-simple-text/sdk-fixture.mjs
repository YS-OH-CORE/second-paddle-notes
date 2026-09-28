import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { readFile } from 'node:fs/promises';

// Load the exact SDK installed for the conformance checkout, without installing
// another dependency graph or changing the checkout's package files.
export async function loadSdk(checkout) {
  const require = createRequire(resolve(checkout, 'package.json'));
  const mcpPath = require.resolve('@modelcontextprotocol/sdk/server/mcp.js');
  const [{ McpServer }, { StreamableHTTPServerTransport }, { createMcpExpressApp }] =
    await Promise.all([
      import(pathToFileURL(mcpPath).href),
      import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/server/streamableHttp.js')).href),
      import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/server/express.js')).href)
    ]);
  const packageJson = JSON.parse(await readFile(resolve(dirname(mcpPath), '../../../package.json'), 'utf8'));
  return { McpServer, StreamableHTTPServerTransport, createMcpExpressApp, version: packageJson.version };
}

export const variants = [
  'success-isError-absent',
  'success-isError-false',
  'error-isError-true',
  'diagnostic-tool-missing',
  'explicit-empty-inputSchema'
];

export async function startSdkFixture(sdk, variant) {
  if (!variants.includes(variant)) throw new Error(`Unknown variant: ${variant}`);
  const observations = { variant, requests: [], responses: [], handlerCalls: [], errors: [] };
  const active = new Set();
  const app = sdk.createMcpExpressApp({ host: '127.0.0.1' });

  // Observe SDK output bytes; leave their construction and transport to the SDK.
  app.use((req, res, next) => {
    const requestIndex = observations.requests.length;
    observations.requests.push({
      method: req.method,
      path: req.path,
      headers: {
        accept: req.headers.accept,
        contentType: req.headers['content-type'],
        protocolVersion: req.headers['mcp-protocol-version']
      },
      body: req.body
    });
    const chunks = [];
    const capture = (chunk) => {
      if (typeof chunk === 'string' || Buffer.isBuffer(chunk) || chunk instanceof Uint8Array) {
        chunks.push(Buffer.from(chunk));
      }
    };
    const write = res.write;
    const end = res.end;
    res.write = function (chunk, ...args) {
      capture(chunk);
      return write.call(this, chunk, ...args);
    };
    res.end = function (chunk, ...args) {
      capture(chunk);
      return end.call(this, chunk, ...args);
    };
    res.once('finish', () => observations.responses.push({
      requestIndex,
      status: res.statusCode,
      contentType: res.getHeader('content-type'),
      body: Buffer.concat(chunks).toString('utf8')
    }));
    next();
  });

  app.post('/mcp', async (req, res) => {
    // Same per-request, sessionless lifecycle as the SDK's bundled
    // examples/server/simpleStatelessStreamableHttp.js.
    const server = new sdk.McpServer({ name: 'simple-text-sdk-proof', version: '1.0.0' });
    const missingTool = variant === 'diagnostic-tool-missing';
    const explicitSchema = variant === 'explicit-empty-inputSchema';
    const toolName = missingTool ? 'unrelated_tool' : 'test_simple_text';
    const config = { description: 'Local conformance evidence fixture' };
    if (explicitSchema) config.inputSchema = {};
    server.registerTool(toolName, config, async (...args) => {
      observations.handlerCalls.push({
        name: toolName,
        inputSchemaPresent: explicitSchema,
        ...(explicitSchema ? { arguments: args[0] } : {})
      });
      const result = { content: [{ type: 'text', text: 'This is a simple text response for testing.' }] };
      if (variant === 'success-isError-false') result.isError = false;
      if (variant === 'error-isError-true') result.isError = true;
      return result;
    });
    const transport = new sdk.StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    const pair = { server, transport };
    active.add(pair);
    res.once('close', () => {
      Promise.allSettled([transport.close(), server.close()]).then(() => active.delete(pair));
    });
    try {
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (error) {
      observations.errors.push(String(error));
      if (!res.headersSent) res.status(500).json({
        jsonrpc: '2.0', id: null,
        error: { code: -32603, message: 'Fixture failed to serve SDK request' }
      });
    }
  });
  app.get('/mcp', (_req, res) => res.status(405).end());
  app.delete('/mcp', (_req, res) => res.status(405).end());

  const listener = await new Promise((resolveListen, reject) => {
    const server = app.listen(0, '127.0.0.1', () => resolveListen(server));
    server.once('error', reject);
  });
  return {
    observations,
    url: `http://127.0.0.1:${listener.address().port}/mcp`,
    async close() {
      await Promise.allSettled([...active].flatMap(({ transport, server }) => [transport.close(), server.close()]));
      listener.closeAllConnections();
      await new Promise((resolveClose, reject) => listener.close(error => error ? reject(error) : resolveClose()));
    }
  };
}
