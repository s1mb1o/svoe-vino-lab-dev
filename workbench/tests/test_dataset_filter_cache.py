"""Check the page search fast path and in-place edits with the actual JavaScript."""
from pathlib import Path
import shutil
import subprocess
import unittest

PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/dataset.html"
ROOT = PAGE.parents[3]


class DatasetFilterCacheTest(unittest.TestCase):
    def test_empty_query_and_in_place_edits(self):
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const acorn = require(require.resolve('acorn', {paths: [process.argv[2] + '/webui']}));
const html = fs.readFileSync(process.argv[1], 'utf8');
const source = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).find(s => s.includes('function applyView()'));
const tree = acorn.parse(source, {ecmaVersion: 'latest'});
const names = new Set(['applyView', 'searchText', 'rawRecord', 'norm', 'compareText']);
const code = tree.body.filter(n => n.type === 'FunctionDeclaration' && names.has(n.id.name))
  .map(n => source.slice(n.start, n.end)).join('\n');
const fields = {'#filter':'all', '#package-filter':'all', '#identifier-filter':'all',
  '#alternative-filter':'all', '#q':'', '#sort':'name'};
let normalized = 0;
const r = {slug:'wine', name:'old', _gtins:[], _barcodes:[], _qr_urls:[], _comments:[], _atlas:[]};
const ctx = vm.createContext({DATA:{records:[r]}, ROWS:[], SEARCH_TEXT:new WeakMap(),
  $:s=>({value:fields[s]}), catalogImageUrl:()=>null, packageOf:()=>'', hasIdentifier:()=>true,
  inTypeView:()=>true, inStateView:()=>true, hasAlternatives:()=>false,
  atlasProducts:r=>r._atlas, imagePixels:()=>0});
vm.runInContext(code,ctx);
const norm = ctx.norm; ctx.norm = value=>{if(String(value).startsWith('{')) normalized++; return norm(value)};
ctx.applyView(); assert.equal(ctx.ROWS.length,1); assert.equal(normalized,0);
fields['#q']='old'; ctx.applyView(); ctx.applyView(); assert.equal(normalized,1);
r.name='new'; ctx.applyView(); assert.equal(ctx.ROWS.length,0); assert.equal(normalized,2);
for(const [query, edit] of [
  ['123',()=>r._gtins.push('123')], ['456',()=>r._barcodes.push('456')],
  ['example',()=>r._qr_urls.push('https://example.test')],
  ['note-special',()=>r._comments.push({text:'note-special'})],
  ['product-unique-987',()=>r._atlas.push({product_uuid:'product-unique-987'})]]) {
  fields['#q']=query; ctx.applyView(); assert.equal(ctx.ROWS.length,0);
  edit(); ctx.applyView(); assert.equal(ctx.ROWS.length,1);
}
'''
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is required for page behavior checks")
        result = subprocess.run([node, "-e", script, str(PAGE), str(ROOT)],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
