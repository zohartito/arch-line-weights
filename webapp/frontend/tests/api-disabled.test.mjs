import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

test('ALW-31: processing API typechecks and refuses calls without requests', async () => {
  const output = mkdtempSync(join(tmpdir(), 'arch-lw-api-test-'));
  execFileSync(process.execPath, [
    // TypeScript 6 refuses command-line files next to tsconfig.json without --ignoreConfig.
    resolve('node_modules/typescript/bin/tsc'), 'src/lib/api.ts', '--ignoreConfig',
    '--strict', '--noEmitOnError', '--skipLibCheck', '--target', 'es2022',
    '--module', 'esnext', '--outDir', output
  ]);
  writeFileSync(join(output, 'package.json'), '{"type":"module"}');
  const api = await import(pathToFileURL(join(output, 'api.js')).href);
  const original = globalThis.fetch;
  let requests = 0;
  globalThis.fetch = () => { requests += 1; throw new Error('unexpected request'); };
  try {
    await assert.rejects(api.createConsoleRun(null, 'section'), /permanently disabled/);
    await assert.rejects(api.getConsoleRun('synthetic'), /permanently disabled/);
    await assert.rejects(api.runConsoleStage('synthetic', 'inspect_file'), /permanently disabled/);
    await assert.rejects(api.createJob(new Blob()), /permanently disabled/);
    await assert.rejects(api.getJob('synthetic'), /permanently disabled/);
    assert.throws(() => api.consoleArtifactUrl({}), /permanently disabled/);
    assert.equal(requests, 0);
  } finally {
    globalThis.fetch = original;
  }
});
