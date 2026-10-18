import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { tmpdir } from 'node:os';
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';

const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
const data = result => result.structuredContent?.result ?? result.structuredContent;

test('real SDK client discovers and calls all tools repeatedly over one stdio connection', { timeout: 20000 }, async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [cli], cwd: tmpdir(), stderr: 'pipe' });
  let stderr = ''; transport.stderr.on('data', chunk => { stderr += chunk; });
  const client = new Client({ name: 'catalog-integration-test', version: '1.0.0' });
  try {
    await client.connect(transport);
    const listing = await client.listTools();
    assert.deepEqual(listing.tools.map(tool => tool.name).sort(), ['compare_wines', 'find_wines', 'get_audio', 'get_producer_line', 'get_wine']);
    assert(listing.tools.every(tool => tool.annotations.readOnlyHint && tool.outputSchema));
    const found = await client.callTool({ name: 'find_wines', arguments: { filters: { color: 'white', sweetness: 'dry' }, limit: 2 } });
    assert(!found.isError, JSON.stringify(found));
    const selection = data(found);
    assert.equal(selection.results.length, 2);
    const slugs = selection.results.map(item => item.wine.slug);
    for (let i = 0; i < 3; i++) {
      const result = await client.callTool({ name: 'get_wine', arguments: { slug: slugs[0] } });
      assert(!result.isError, JSON.stringify(result)); assert.equal(data(result).wine.slug, slugs[0]);
    }
    const comparison = await client.callTool({ name: 'compare_wines', arguments: { slugs } });
    assert(!comparison.isError, JSON.stringify(comparison)); assert.equal(data(comparison).taste_match, false);
    const producerLine = await client.callTool({ name: 'get_producer_line', arguments: { slug: 'abrau-dyurso-victor-dravigny-bryut' } });
    assert(!producerLine.isError, JSON.stringify(producerLine)); assert.equal(data(producerLine).status, 'ok'); assert.equal(data(producerLine).resolution, 'alias');
    const audio = await client.callTool({ name: 'get_audio', arguments: { slug: slugs[0], kind: 'summary' } });
    assert(!audio.isError, JSON.stringify(audio)); assert.equal(data(audio).status, 'unavailable');
    for (const request of [
      { name: 'find_wines', arguments: { limit: 11 } },
      { name: 'find_wines', arguments: { filters: { price: 100 } } },
      { name: 'find_wines', arguments: { filters: { color: 'purple' } } },
      { name: 'get_wine', arguments: { slug: 'missing-wine-id' } },
      { name: 'compare_wines', arguments: { slugs: [slugs[0], slugs[0]] } },
      { name: 'get_audio', arguments: { slug: slugs[0], kind: 'generate' } },
    ]) {
      const result = await client.callTool(request);
      assert.equal(result.isError, true, JSON.stringify(result));
    }
    const valid = await client.callTool({ name: 'get_wine', arguments: { slug: slugs[0] } });
    assert(!valid.isError); assert.equal(stderr, '');
  } finally { await client.close(); }
});

test('server exits cleanly on stdin EOF without a client or a network listener', { timeout: 10000 }, async () => {
  const child = spawn(process.execPath, [cli], { stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  child.stdout.on('data', value => { stdout += value; }); child.stderr.on('data', value => { stderr += value; });
  child.stdin.end();
  const code = await new Promise((resolve, reject) => { child.once('exit', resolve); child.once('error', reject); });
  assert.equal(code, 0); assert.equal(stdout, ''); assert.equal(stderr, '');
});

test('startup failure has sanitized stderr and no protocol output', { timeout: 10000 }, async () => {
  const child = spawn(process.execPath, [cli], { env: { ...process.env, WINE_MCP_REPOSITORY_ROOT: '/private/tmp/absent-wine-catalog-private-path' }, stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  child.stdout.on('data', value => { stdout += value; }); child.stderr.on('data', value => { stderr += value; });
  const code = await new Promise((resolve, reject) => { child.once('exit', resolve); child.once('error', reject); });
  assert.equal(code, 1); assert.equal(stdout, ''); assert(stderr.includes('startup failed')); assert(!stderr.includes('private-path'));
});
