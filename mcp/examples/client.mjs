import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { fileURLToPath } from 'node:url';

const transport = new StdioClientTransport({ command: process.execPath, args: [fileURLToPath(new URL('../src/cli.mjs', import.meta.url))], stderr: 'pipe' });
const client = new Client({ name: 'wine-catalog-demo', version: '0.1.0' });
let errors = '';
transport.stderr?.on('data', data => { errors += data.toString(); });
const payload = result => result.structuredContent?.result ?? result.structuredContent;
try {
  await client.connect(transport);
  const tools = await client.listTools();
  const selection = payload(await client.callTool({ name: 'find_wines', arguments: { filters: { color: 'white', sweetness: 'dry' }, limit: 2 } }));
  if (selection?.results?.length !== 2) throw new Error('The catalog did not return two wines');
  const slugs = selection.results.map(item => item.wine.slug);
  const card = payload(await client.callTool({ name: 'get_wine', arguments: { slug: slugs[0] } }));
  const comparison = payload(await client.callTool({ name: 'compare_wines', arguments: { slugs } }));
  const line = payload(await client.callTool({ name: 'get_producer_line', arguments: { slug: 'abrau-dyurso-victor-dravigny-bryut' } }));
  const audio = payload(await client.callTool({ name: 'get_audio', arguments: { slug: slugs[0], kind: 'summary' } }));
  console.log(JSON.stringify({ tools: tools.tools.map(tool => tool.name), catalog_count: selection.catalog.catalog_count, active_count: selection.catalog.active_count, selected: slugs, first_wine: card.wine.name, comparison: comparison.comparison_kind, shared_fields: comparison.shared.map(item => item.field), producer_line: line.status, producer_line_resolution: line.resolution, audio: audio.status }, null, 2));
  if (errors) throw new Error('The server wrote an error to stderr');
} finally { await client.close(); }
