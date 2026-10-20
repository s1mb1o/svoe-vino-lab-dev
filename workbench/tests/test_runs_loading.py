"""Exercise optional cluster loading and stale replies with actual page functions."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RunsLoadingTest(unittest.TestCase):
    def test_rows_render_before_hint_and_stale_hints_do_not_replace_current(self):
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const root=process.argv[1];
const acorn=require(require.resolve('acorn',{paths:[root+'/webui']}));
const html=fs.readFileSync(root+'/workbench/pipeline/pages/runs.html','utf8');
const source=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m=>m[1]).find(s=>s.includes('async function loadRun('));
const tree=acorn.parse(source,{ecmaVersion:'latest'});
const names=new Set(['loadClusters','loadRun','refreshClusterHints']);
const code=tree.body.filter(n=>n.type==='FunctionDeclaration'&&names.has(n.id.name))
  .map(n=>source.slice(n.start,n.end)).join('\n');
const elements=new Map(), pending=new Map();
const body={innerHTML:'', rows:[], insertAdjacentHTML(_,html){this.innerHTML+=html},
  querySelectorAll(){return this.rows}};
const field=s=>{if(s==='#res-body')return body; if(!elements.has(s))elements.set(s,{value:'',dataset:{}});return elements.get(s)};
let ctx;
const context={CUR:null, LOAD_VERSION:0, ROW_KEY:0, HINT_PENDING:false,
  SHOWN_ROWS:new Map(), CLUSTER:{}, CARDNAME:{}, CLUSTER_SRC:{},
  OFFSET:0,TOTAL:0,BOTTLES:{},PATCHED:new Set(),RUN:{},$:field,
  fetch:url=>{if(url.startsWith('/api/run-clusters')) return new Promise(resolve=>pending.set(url,resolve));
    return Promise.resolve({json:async()=>({rows:[{query_id:'q1'},{query_id:'q1'}],total:2})})},
  rowHtml:r=>'rows-'+r.query_id, evenCards:()=>{},renderMetrics:()=>{},ntsButton:()=>{},rrButton:()=>{},
  syncImageTagNames:()=>{},renderRuns:()=>{},alert:()=>{},history:{replaceState:()=>{}},
  location:{pathname:'/runs',search:''},document:{createElement:()=>({set innerHTML(value){
    this.firstElementChild={children:[{}, {innerHTML:value}]}}})}};
ctx=vm.createContext(context);vm.runInContext(code,ctx);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const resolveHint=(id,slug)=>pending.get('/api/run-clusters?id='+id)({json:async()=>({clusters:[{slugs:[slug]}]})});
(async()=>{
  let done=false;ctx.loadRun('first',false).then(()=>done=true);await tick();
  assert(done,'rows must finish while cluster request is pending');assert(body.innerHTML.includes('q1'));
  // A new load of the same run rejects the older hint by generation.
  const old=pending.get('/api/run-clusters?id=first');
  await ctx.loadRun('first',false);
  old({json:async()=>({clusters:[{slugs:['old']} ]})});await tick();
  assert(!ctx.CLUSTER.old);
  const draft={innerHTML:'pending tag edit'};
  assert.equal(ctx.SHOWN_ROWS.size,2,'duplicate query IDs must have separate row keys');
  body.rows=[{dataset:{rowKey:'0'},children:[draft,{innerHTML:'before'}]}];
  resolveHint('first','fresh');await tick();
  assert(ctx.CLUSTER.fresh);assert.equal(draft.innerHTML,'pending tag edit');
  assert.equal(body.rows[0].children[1].innerHTML,'rows-q1');
  assert.equal(ctx.SHOWN_ROWS.size,0,'release rows after the hint finishes');
  await ctx.loadRun('second',false);
  await ctx.loadRun('third',false);
  resolveHint('second','stale');await tick();assert(!ctx.CLUSTER.stale);
  pending.get('/api/run-clusters?id=third')({json:async()=>{throw Error('failed hint')}});
  await tick();assert.equal(ctx.CUR,'third');
})().catch(error=>{console.error(error);process.exitCode=1});
'''
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is required for page behavior checks")
        result = subprocess.run([node, "-e", script, str(ROOT)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_scroll_key_in_a_dialog_does_not_scroll_the_page(self):
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const root=process.argv[1];
const acorn=require(require.resolve('acorn',{paths:[root+'/webui']}));
const html=fs.readFileSync(root+'/workbench/pipeline/pages/runs.html','utf8');
const source=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m=>m[1]).find(s=>s.includes('function keepScrollInDialog('));
const code=acorn.parse(source,{ecmaVersion:'latest'}).body.filter(n=>
  n.type==='FunctionDeclaration'&&n.id.name==='keepScrollInDialog'||
  n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='PAGE_SCROLL_KEYS'))
  .map(n=>source.slice(n.start,n.end)).join('\n')+'\nthis.keep=keepScrollInDialog;';
const ctx=vm.createContext({Set});vm.runInContext(code,ctx);
const press=(key,field)=>{const ev={key,prevented:false,preventDefault(){this.prevented=true;},
  target:{closest:selector=>field&&selector.includes(field)?{}:null}};ctx.keep(ev);return ev.prevented;};
for(const key of ['ArrowDown','ArrowUp','PageDown','End']) assert(press(key,null),key);
assert(!press(' ',null),'Space presses a button');assert(!press('Enter',null));assert(!press('a',null));
assert(!press('ArrowDown','input'),'a radio button or a text field keeps its arrow keys');
assert(!press('End','textarea'));
'''
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is required for page behavior checks")
        result = subprocess.run([node, "-e", script, str(ROOT)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
