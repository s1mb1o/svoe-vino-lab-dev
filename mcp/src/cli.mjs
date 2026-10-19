#!/usr/bin/env node
import { fileURLToPath } from 'node:url';
import { StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import { AccountClient, AccountConfigError } from './account.mjs';
import { CatalogService } from './catalog.mjs';
import { createServer } from './server.mjs';

try {
  // Optional diary access (issue #65). Without CHTOZAVINO_ACCOUNT_TOKEN the account is null.
  const account = AccountClient.fromEnv(process.env);
  const service = await CatalogService.load(process.env.WINE_MCP_REPOSITORY_ROOT || fileURLToPath(new URL('../../', import.meta.url)), {
    audioManifest: process.env.WINE_MCP_AUDIO_MANIFEST,
    audioRoot: process.env.WINE_MCP_AUDIO_ROOT,
    mediaBaseUrl: process.env.WINE_MCP_MEDIA_BASE_URL,
  });
  const server = createServer(service, account);
  const transport = new StdioServerTransport(process.stdin, process.stdout, { maxBufferSize: 64 * 1024 });
  const close = async () => { await server.close(); };
  process.once('SIGTERM', close);
  process.once('SIGINT', close);
  server.server.onerror = () => process.stderr.write('MCP protocol error.\n');
  await server.connect(transport);
} catch (error) {
  // AccountConfigError messages are fixed texts without the token.
  const detail = error instanceof AccountConfigError ? ` ${error.message}` : '';
  process.stderr.write(`Wine MCP startup failed. Check the catalog snapshot, the product-line maps, and the optional audio and account configuration.${detail}\n`);
  process.exitCode = 1;
}
