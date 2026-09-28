// Fixed evidence matrix. The repository CLI performs all conformance execution,
// reporting, and exit-code decisions; this script asserts its saved outputs.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { createServer, request as httpRequest } from 'node:http';
import { createHash } from 'node:crypto';
import { appendFileSync } from 'node:fs';
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { identityCases } from './identity-cases.mjs';

// Convenience copy: only path configuration changed; this copy was not rerun.
const fixtureDirectory = path.dirname(fileURLToPath(import.meta.url));
for (const key of ['IDENTITY_BASELINE', 'IDENTITY_CANDIDATE', 'IDENTITY_OUTPUT']) {
  assert(process.env[key], `${key} must name a local path`);
}
const evidence = path.resolve(process.env.IDENTITY_OUTPUT);
const revisions = {
  baseline: path.resolve(process.env.IDENTITY_BASELINE),
  candidate: path.resolve(process.env.IDENTITY_CANDIDATE)
};
const rows = [];
const resultsRoot = path.join(evidence, 'results');
await mkdir(resultsRoot, { recursive: true });
const provenance = Object.fromEntries(await Promise.all(Object.entries(revisions).map(async ([name, repo]) => [name, {
  repo,
  commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim(),
  cliSha256: createHash('sha256').update(await readFile(path.join(repo, 'dist/index.js'))).digest('hex')
}])));
await writeFile(path.join(evidence, 'provenance.json'), JSON.stringify({ node: process.version, ...provenance }, null, 2));

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return server.address().port;
}
async function closeServer(server) {
  server.closeAllConnections();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}
const portReservation = createServer();
const upstreamPort = await listen(portReservation);
await closeServer(portReservation);
const upstream = spawn(process.execPath, ['--import', 'tsx', path.join(revisions.baseline, 'examples/servers/typescript/everything-server.ts')], {
  cwd: revisions.baseline,
  env: { ...process.env, PORT: String(upstreamPort) },
  stdio: ['ignore', 'pipe', 'pipe']
});
let upstreamOutput = '';
upstream.stderr.on('data', (chunk) => appendFileSync(path.join(evidence, 'upstream.log'), chunk));
upstream.stdout.on('data', (chunk) => {
  upstreamOutput += chunk.toString();
  appendFileSync(path.join(evidence, 'upstream.log'), chunk);
});
await new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error('everything-server startup timed out')), 15000);
  upstream.stdout.on('data', () => {
    if (upstreamOutput.includes('running on')) { clearTimeout(timer); resolve(); }
  });
  upstream.once('error', (error) => { clearTimeout(timer); reject(error); });
  upstream.once('exit', (code) => { clearTimeout(timer); reject(new Error(`everything-server exited: ${code}`)); });
});

const proxy = createServer((incoming, outgoing) => {
  const caseName = incoming.url.split('/')[1];
  const testCase = identityCases.find((entry) => entry.name === caseName);
  if (!testCase) { outgoing.writeHead(404).end(); return; }
  const chunks = [];
  incoming.on('data', (chunk) => chunks.push(chunk));
  incoming.on('end', () => {
    const body = Buffer.concat(chunks);
    const rpc = JSON.parse(body.toString('utf8'));
    const forwarded = httpRequest({
      hostname: '127.0.0.1', port: upstreamPort, path: '/mcp', method: incoming.method,
      headers: { ...incoming.headers, host: `localhost:${upstreamPort}` }
    }, (response) => {
      if (rpc.method !== 'server/discover') {
        outgoing.writeHead(response.statusCode, response.headers);
        response.pipe(outgoing);
        return;
      }
      const responseChunks = [];
      response.on('data', (chunk) => responseChunks.push(chunk));
      response.on('end', () => {
        const payload = JSON.parse(Buffer.concat(responseChunks).toString('utf8'));
        if (payload.result) {
          assert.equal(payload.result.resultType, 'complete');
          payload.result._meta ??= {};
          payload.result._meta['io.modelcontextprotocol/serverInfo'] = testCase.identity;
        }
        appendFileSync(path.join(evidence, 'discover-responses.jsonl'), JSON.stringify({ caseName, requestId: rpc.id, status: response.statusCode, payload }) + '\n');
        const bytes = Buffer.from(JSON.stringify(payload));
        const headers = { ...response.headers, 'content-length': String(bytes.length) };
        delete headers['transfer-encoding'];
        outgoing.writeHead(response.statusCode, headers);
        outgoing.end(bytes);
      });
    });
    forwarded.on('error', (error) => {
      if (!outgoing.headersSent) outgoing.writeHead(502);
      outgoing.end(String(error));
    });
    outgoing.once('close', () => forwarded.destroy());
    forwarded.end(body);
  });
});
const proxyPort = await listen(proxy);

async function runCli(revision, leg, testCase) {
  const repo = revisions[revision];
  const resultRoot = path.join(resultsRoot, `${leg}-${testCase.name}-${revision}`);
  await mkdir(resultRoot, { recursive: true });
  const cliArgs = leg === 'client'
    ? ['client', '--scenario', 'initialize', '--spec-version', '2025-11-25', '--command', `${process.execPath} ${path.join(fixtureDirectory, 'synthetic-initialize-client.mjs')} ${testCase.name}`]
    : ['server', '--scenario', 'server-stateless', '--spec-version', '2026-07-28', '--url', `http://127.0.0.1:${proxyPort}/${testCase.name}/mcp`];
  const args = [path.join(repo, 'dist/index.js'), ...cliArgs, '--timeout', '10000', '--output-dir', resultRoot];
  const execution = await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { cwd: repo, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    child.stdout.on('data', (chunk) => stdout += chunk.toString());
    child.stderr.on('data', (chunk) => stderr += chunk.toString());
    const timer = setTimeout(() => child.kill('SIGKILL'), 20000);
    child.once('error', (error) => { clearTimeout(timer); reject(error); });
    child.once('close', (exitCode, signal) => { clearTimeout(timer); resolve({ exitCode, signal, stdout, stderr }); });
  });
  await writeFile(path.join(resultRoot, 'cli.stdout.txt'), execution.stdout);
  await writeFile(path.join(resultRoot, 'cli.stderr.txt'), execution.stderr);
  await writeFile(path.join(resultRoot, 'execution.json'), JSON.stringify({ command: [process.execPath, ...args], exitCode: execution.exitCode, signal: execution.signal }, null, 2));
  const directories = (await readdir(resultRoot, { withFileTypes: true })).filter((entry) => entry.isDirectory());
  assert.equal(directories.length, 1, `${leg}/${testCase.name}/${revision}: CLI result directory`);
  const resultDir = path.join(resultRoot, directories[0].name);
  const checks = JSON.parse(await readFile(path.join(resultDir, 'checks.json'), 'utf8'));
  const targetId = leg === 'client' ? 'mcp-client-initialization' : 'sep-2575-server-identifies-in-result-meta';
  const targets = checks.filter((check) => check.id === targetId);
  assert.equal(targets.length, 1, `Expected one ${targetId}`);
  const target = targets[0];
  const counts = Object.fromEntries(['SUCCESS', 'FAILURE', 'WARNING', 'INFO', 'SKIPPED'].map((status) => [status, checks.filter((check) => check.status === status).length]));
  const row = { revision, leg, caseName: testCase.name, identity: testCase.identity, target, exitCode: execution.exitCode, counts, checksFile: path.join(resultDir, 'checks.json'), wireChecks: checks.filter((check) => check.id.includes('wire')), nonTargetChecks: checks.filter((check) => check.id !== targetId).map(({ id, status }) => ({ id, status })) };
  rows.push(row);
  await writeFile(path.join(evidence, 'partial-results.json'), JSON.stringify(rows, null, 2));
  const invalid = revision === 'baseline'
    ? ['empty-name', 'empty-version', 'missing-fields'].includes(testCase.name)
    : ['numeric-fields', 'missing-fields'].includes(testCase.name);
  const expectedStatus = invalid ? (leg === 'client' ? 'FAILURE' : 'WARNING') : 'SUCCESS';
  assert.equal(target.status, expectedStatus, `${leg}/${testCase.name}/${revision}: named check`);
  assert.equal(execution.signal, null);
  assert.equal(execution.exitCode, leg === 'client' && invalid ? 1 : 0, `${leg}/${testCase.name}/${revision}: existing CLI exit`);
  assert.equal(checks.some((check) => check.id !== targetId && ['FAILURE', 'WARNING'].includes(check.status)), false, `Unrelated failure/warning in ${leg}/${testCase.name}/${revision}`);
  if (leg === 'client') {
    const fixture = JSON.parse((await readFile(path.join(resultDir, 'stdout.txt'), 'utf8')).trim());
    assert.deepEqual(fixture.initialize.params.clientInfo, testCase.identity);
  } else {
    const receivedIdentity = target.details.serverInfo ?? target.details.result?._meta?.['io.modelcontextprotocol/serverInfo'];
    assert.deepEqual(receivedIdentity, testCase.identity);
  }
  console.log(JSON.stringify({ revision, leg, caseName: testCase.name, status: target.status, exitCode: execution.exitCode, counts }));
  return row;
}

try {
  for (const leg of ['client', 'server']) {
    for (const testCase of identityCases) {
      const baseline = await runCli('baseline', leg, testCase);
      const candidate = await runCli('candidate', leg, testCase);
      assert.deepEqual(candidate.nonTargetChecks, baseline.nonTargetChecks, `${leg}/${testCase.name}: non-target check statuses unchanged`);
    }
  }
  await writeFile(path.join(evidence, 'identity-cli-results.json'), JSON.stringify({ fixtureDescription: 'Synthetic raw HTTP initialize client; baseline everything-server behind a synthetic loopback proxy that replaces only successful server/discover identity metadata. Existing repository CLI owns all scenario execution and reporting.', provenance, runs: rows.length, allAssertionsPassed: true, rows }, null, 2));
  console.log('All 20 existing-CLI identity runs and non-target comparisons passed.');
} finally {
  await closeServer(proxy);
  if (upstream.exitCode === null && upstream.signalCode === null) {
    await new Promise((resolve) => {
      const timer = setTimeout(() => upstream.kill('SIGKILL'), 5000);
      upstream.once('exit', () => { clearTimeout(timer); resolve(); });
      upstream.kill('SIGTERM');
    });
  }
}
