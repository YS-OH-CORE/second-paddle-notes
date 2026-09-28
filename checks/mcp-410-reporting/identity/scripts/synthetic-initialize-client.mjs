// Synthetic HTTP client for identity field validation, not a real SDK claim.
import assert from 'node:assert/strict';
import { identityCases } from './identity-cases.mjs';

const [caseName, serverUrl] = process.argv.slice(2);
const testCase = identityCases.find((entry) => entry.name === caseName);
assert(testCase, `Unknown identity case: ${caseName}`);
assert(serverUrl, 'The existing conformance CLI must append its server URL');
assert.equal(process.env.MCP_CONFORMANCE_SCENARIO, 'initialize');
assert.equal(process.env.MCP_CONFORMANCE_PROTOCOL_VERSION, '2025-11-25');

const initialize = {
  jsonrpc: '2.0', id: 1, method: 'initialize',
  params: {
    protocolVersion: '2025-11-25',
    capabilities: {},
    clientInfo: testCase.identity
  }
};
const response = await fetch(serverUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' },
  body: JSON.stringify(initialize),
  signal: AbortSignal.timeout(5000)
});
assert.equal(response.status, 200);
const payload = await response.json();
assert.equal(payload.id, initialize.id);
assert.equal(payload.result.protocolVersion, '2025-11-25');
assert.equal(payload.error, undefined);
const initialized = await fetch(serverUrl, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json', Accept: 'application/json, text/event-stream',
    'MCP-Protocol-Version': '2025-11-25'
  },
  body: JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }),
  signal: AbortSignal.timeout(5000)
});
assert.equal(initialized.status, 202);
await initialized.arrayBuffer();
console.log(JSON.stringify({ fixture: 'synthetic-raw-http-client', caseName, initialize, response: payload }));
