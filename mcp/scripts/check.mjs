import { readdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

for (const folder of ['src', 'tests', 'examples', 'scripts']) {
  const directory = new URL(`../${folder}/`, import.meta.url);
  for (const name of await readdir(directory)) {
    if (!name.endsWith('.mjs')) continue;
    const result = spawnSync(process.execPath, ['--check', fileURLToPath(new URL(name, directory))], { stdio: 'inherit' });
    if (result.status !== 0) process.exit(result.status || 1);
  }
}
console.log('MCP JavaScript syntax checks passed.');
