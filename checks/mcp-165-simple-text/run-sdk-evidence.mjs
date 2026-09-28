import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { loadSdk, startSdkFixture, variants } from './sdk-fixture.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({ options: {
  candidate: { type: 'string' }, baseline: { type: 'string' }, output: { type: 'string' }
} });
if (!values.candidate || !values.baseline) {
  throw new Error('Usage: node run-sdk-evidence.mjs --candidate CHECKOUT --baseline CHECKOUT [--output DIR]');
}
const output = resolve(values.output ?? join(here, 'runs', new Date().toISOString().replaceAll(':', '-')));
await mkdir(output, { recursive: true });

function execute(command, args, cwd, timeoutMs = 30000) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, { cwd, env: { ...process.env, NO_COLOR: '1' }, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    const timer = setTimeout(() => { timedOut = true; child.kill('SIGKILL'); }, timeoutMs);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', (exitCode, signal) => {
      clearTimeout(timer);
      resolveRun({ exitCode, signal, timedOut, stdout, stderr });
    });
  });
}

async function findChecks(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await findChecks(path));
    else if (entry.name === 'checks.json') files.push(path);
  }
  return files;
}

const sdk = await loadSdk(resolve(values.candidate));
const summary = {
  recordedAt: new Date().toISOString(),
  runtime: { node: process.version, platform: process.platform, architecture: process.arch, sdk: sdk.version },
  scenario: 'tools-call-simple-text',
  specVersion: '2025-11-25',
  method: 'Existing built conformance CLI against a real McpServer and StreamableHTTPServerTransport on loopback',
  sources: {},
  runs: [],
  assertions: []
};

for (const [label, path] of Object.entries({ baseline: values.baseline, candidate: values.candidate })) {
  const checkout = resolve(path);
  const revision = await execute('git', ['rev-parse', 'HEAD'], checkout);
  const lock = await readFile(join(checkout, 'package-lock.json'));
  summary.sources[label] = { commit: revision.stdout.trim(), lockSha256: createHash('sha256').update(lock).digest('hex') };
  const build = await execute('npm', ['run', 'build'], checkout, 60000);
  await writeFile(join(output, `${label}-build.stdout.log`), build.stdout);
  await writeFile(join(output, `${label}-build.stderr.log`), build.stderr);
  if (build.exitCode !== 0 || build.timedOut) throw new Error(`${label} build failed; see ${output}`);

  for (const variant of variants) {
    const runDir = join(output, label, variant);
    await mkdir(runDir, { recursive: true });
    const fixture = await startSdkFixture(sdk, variant);
    let processResult;
    const args = ['dist/index.js', 'server', '--url', fixture.url,
      '--scenario', summary.scenario, '--spec-version', summary.specVersion,
      '--timeout', '15000', '-o', join(runDir, 'results')];
    try {
      processResult = await execute(process.execPath, args, checkout, 20000);
    } finally {
      await fixture.close();
    }
    await writeFile(join(runDir, 'cli.stdout.log'), processResult.stdout);
    await writeFile(join(runDir, 'cli.stderr.log'), processResult.stderr);
    await writeFile(join(runDir, 'invocation.json'), JSON.stringify({ executable: process.execPath, cwd: checkout, args,
      exitCode: processResult.exitCode, signal: processResult.signal, timedOut: processResult.timedOut }, null, 2) + '\n');
    await writeFile(join(runDir, 'server-observations.json'), JSON.stringify(fixture.observations, null, 2) + '\n');
    const checkFiles = await findChecks(runDir);
    if (checkFiles.length !== 1) throw new Error(`Expected one CLI checks.json for ${label}/${variant}, found ${checkFiles.length}`);
    const checks = JSON.parse(await readFile(checkFiles[0], 'utf8'));
    const scenarioCheck = checks.find(check => check.id === summary.scenario);
    const wireCheck = checks.find(check => check.id === 'wire-schema-valid');
    const calls = fixture.observations.requests.filter(request => request.body?.method === 'tools/call');
    summary.runs.push({
      label, variant, exitCode: processResult.exitCode, signal: processResult.signal, timedOut: processResult.timedOut,
      checkId: scenarioCheck?.id, status: scenarioCheck?.status, errorMessage: scenarioCheck?.errorMessage,
      result: scenarioCheck?.details?.result,
      wireSchemaCheckId: wireCheck?.id, wireSchemaStatus: wireCheck?.status,
      allChecks: checks.map(({ id, status }) => ({ id, status })),
      toolRequests: calls.map(({ body }) => body.params),
      handlerCalls: fixture.observations.handlerCalls,
      fixtureErrors: fixture.observations.errors,
      checksPath: relative(output, checkFiles[0]),
      observationsPath: relative(output, join(runDir, 'server-observations.json'))
    });
    console.log(`${label}/${variant}: exit=${processResult.exitCode}, check=${scenarioCheck?.status}, wire=${wireCheck?.status}, handlerCalls=${fixture.observations.handlerCalls.length}`);
  }
}

for (const run of summary.runs) {
  const shouldFail = run.label === 'candidate' && ['error-isError-true', 'diagnostic-tool-missing'].includes(run.variant);
  const expectedHandlers = run.variant === 'diagnostic-tool-missing' ||
    (run.label === 'baseline' && run.variant === 'explicit-empty-inputSchema') ? 0 : 1;
  const expectations = {
    expectedCliExit: run.exitCode === (shouldFail ? 1 : 0),
    expectedScenarioStatus: run.status === (shouldFail ? 'FAILURE' : 'SUCCESS'),
    stableCheckId: run.checkId === summary.scenario,
    validWireSchema: run.wireSchemaStatus === 'SUCCESS',
    actualHandlerCount: run.handlerCalls.length === expectedHandlers,
    oneToolCall: run.toolRequests.length === 1,
    expectedArguments: run.toolRequests.length === 1 && (run.label === 'candidate'
      ? JSON.stringify(run.toolRequests[0].arguments) === '{}'
      : !Object.hasOwn(run.toolRequests[0], 'arguments')),
    cleanFixture: run.fixtureErrors.length === 0,
    completed: !run.timedOut && run.signal === null
  };
  summary.assertions.push({ label: run.label, variant: run.variant, expectations,
    passed: Object.values(expectations).every(Boolean) });
}
summary.allAssertionsPassed = summary.assertions.every(assertion => assertion.passed);
await writeFile(join(output, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(`Evidence saved to ${output}`);
if (!summary.allAssertionsPassed) process.exitCode = 1;
