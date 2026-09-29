// Test-only follow-up to MCP #526/#533; no production code modifications.
// Zero × Youngseok Oh. Actual runner and SDK, synthetic local HTTP server.
import http from 'http';
import { mkdirSync, writeFileSync } from 'fs';
import path from 'path';
import type { AddressInfo } from 'net';
import { expect, onTestFinished, test } from 'vitest';
import { runServerConformanceTest } from './server';

type Mode = 'rpc-error' | 'no-elicitation' | 'late-ack';
const scenarios = ['elicitation-sep1034-defaults', 'elicitation-sep1330-enums'];
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
function fixture(mode: Mode) {
  const live = new Set<string>();
  const events: Array<{method: string; sid?: string; protocol?: string}> = [];
  const initialized = deferred<http.ServerResponse>();
  const activity = deferred<void>();
  let issued = 0;
  const respond = (res: http.ServerResponse, body: unknown) => {
    res.writeHead(200, {'Content-Type': 'application/json'});
    res.end(JSON.stringify(body));
  };
  const server = http.createServer((req, res) => {
    const sid = req.headers['mcp-session-id'] as string | undefined;
    if (req.method === 'DELETE') {
      events.push({method: 'DELETE', sid});
      if (sid) live.delete(sid);
      res.writeHead(204).end();
      if (sid === 's1') activity.resolve();
      return;
    }
    if (req.method === 'GET') {
      events.push({method: 'GET', sid});
      res.writeHead(200, {'Content-Type': 'text/event-stream'});
      res.write(': open\n\n');
      return;
    }
    let raw = '';
    req.on('data', (chunk) => { raw += chunk; });
    req.on('end', () => {
      const msg = JSON.parse(raw);
      if (msg.method === 'initialize') {
        if (live.size) {
          events.push({method: 'REJECT initialize'});
          res.writeHead(503).end('Synthetic one-session capacity exhausted');
          return;
        }
        const session = `s${++issued}`;
        live.add(session);
        events.push({method: 'POST initialize', sid: session, protocol: msg.params.protocolVersion});
        res.setHeader('mcp-session-id', session);
        respond(res, {jsonrpc: '2.0', id: msg.id, result: {
          protocolVersion: msg.params.protocolVersion,
          capabilities: {prompts: {}, tools: {}},
          serverInfo: {name: 'bypass-cleanup-fixture', version: '0.0.1'}
        }});
        return;
      }
      events.push({method: `POST ${msg.method}`, sid});
      if (msg.method === 'notifications/initialized') {
        if (mode === 'late-ack' && sid === 's1') initialized.resolve(res);
        else res.writeHead(202).end();
        return;
      }
      if (sid === 's2' && msg.method === 'prompts/list') {
        respond(res, {jsonrpc: '2.0', id: msg.id, result: {prompts: [{name: 'p', description: 'Healthy successor prompt'}]}});
        return;
      }
      if (mode === 'no-elicitation' && msg.method === 'tools/call') {
        respond(res, {jsonrpc: '2.0', id: msg.id, result: {content: [{type: 'text', text: 'No elicitation was requested'}]}});
      } else {
        respond(res, {jsonrpc: '2.0', id: msg.id, error: {code: -32601, message: 'Deliberate fixture method failure'}});
      }
      if (sid === 's1') activity.resolve();
    });
  });
  onTestFinished(async () => {
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });
  return {server, live, events, initialized, activity};
}
async function start(mode: Mode) {
  const f = fixture(mode);
  await new Promise<void>((resolve) => f.server.listen(0, '127.0.0.1', resolve));
  return {...f, url: `http://127.0.0.1:${(f.server.address() as AddressInfo).port}/mcp`};
}
function save(name: string, result: unknown) {
  const directory = process.env.ZERO_RECEIPTS!;
  mkdirSync(directory, {recursive: true});
  writeFileSync(path.join(directory, `${name}.json`), JSON.stringify(result, null, 2) + '\n');
}
async function settled(name: string, mode: Mode) {
  const f = await start(mode);
  const first = await runServerConformanceTest(f.url, name, undefined, '2025-11-25', false, 3000);
  const beforeSuccessor = {live: [...f.live], events: [...f.events]};
  const next = await runServerConformanceTest(f.url, 'prompts-list', undefined, '2025-11-25', false, 3000);
  const observation = {
    firstReportedFailure: first.checks.some((c) => c.status === 'FAILURE'),
    firstDeletes: f.events.filter((e) => e.method === 'DELETE' && e.sid === 's1').length,
    healthyStatus: next.checks.find((c) => c.id === 'prompts-list')?.status ?? null,
    healthyDeletes: f.events.filter((e) => e.method === 'DELETE' && e.sid === 's2').length,
    liveSessions: [...f.live]
  };
  save(`${name}-${mode}`, {mode, scenario: name, observation, beforeSuccessor, events: f.events, firstChecks: first.checks, successorChecks: next.checks});
  expect(observation).toEqual({firstReportedFailure: true, firstDeletes: 1, healthyStatus: 'SUCCESS', healthyDeletes: 1, liveSessions: []});
}
for (const name of scenarios) {
  test(`${name}: rpc-error must not poison its successor`, () => settled(name, 'rpc-error'), 10000);
  test(`${name}: explicit early-close control`, () => settled(name, 'no-elicitation'), 10000);
  test(`${name}: late connection must not reach abandoned scenario`, async () => {
    const f = await start('late-ack');
    const pending = runServerConformanceTest(f.url, name, undefined, '2025-11-25', false, 1000);
    const acknowledgment = await f.initialized.promise;
    const first = await pending;
    expect(first.checks).toContainEqual(expect.objectContaining({id: 'scenario-timeout', status: 'FAILURE'}));
    expect(f.events.some((e) => e.method === 'POST tools/call')).toBe(false);
    f.events.push({method: 'runner returned scenario-timeout'});
    acknowledgment.writeHead(202).end();
    // Positive barrier: a late DELETE or an abandoned tool request; no quiet-time sleep.
    await f.activity.promise;
    const observation = {abandonedToolCalls: f.events.filter((e) => e.sid === 's1' && e.method === 'POST tools/call').length};
    save(`${name}-late-ack`, {mode: 'late-ack', scenario: name, observation, events: f.events, firstChecks: first.checks, scope: 'Observation at first post-timeout activity, not an eventual-cleanup claim'});
    expect(observation).toEqual({abandonedToolCalls: 0});
  }, 10000);
}
test('tracked prompts error remains isolated under #533', () => settled('prompts-list', 'rpc-error'), 10000);
