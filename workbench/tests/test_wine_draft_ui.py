"""Run the real draft controller with deterministic browser events and delayed replies."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const nodes = new Map(), requests = [], timers = new Map(); let timer = 0, confirmed = false;
function node(id) {
  if (!nodes.has(id)) nodes.set(id,{value:'',hidden:true,innerHTML:'',textContent:'',inert:false,
    listeners:{},isConnected:true, addEventListener(k,f){this.listeners[k]=f;},
    replaceChildren(){this.innerHTML='';}, focus(){ctx.document.activeElement=this;},
    fire(k,target){return this.listeners[k]?.({target});}});
  return nodes.get(id);
}
const controls = ['name','producer','beverage_type_code','category','color','region','grapes','description','sweetness','vintage','slug']
 .map(name=>Object.assign(node(name),{name,tagName:name==='beverage_type_code'||name==='category'?'SELECT':'INPUT',
   options:[],add(option){this.options.push(option);}}));
node('#wine-form').elements=Object.fromEntries(controls.map(e=>[e.name,e]));
node('#wine-form').querySelectorAll=()=>controls;
const ctx = vm.createContext({console,AbortController,Map,JSON,String,Number,Option:function(text,value){this.value=value;},
  $:node,DATA:{records:[]},WINE_FORM:{file:null,slugTyped:false,busy:false},
  document:{activeElement:null,addEventListener(k,f){this[k]=f;}},
  setTimeout:f=>{timers.set(++timer,f);return timer;},clearTimeout:id=>timers.delete(id),
  esc:s=>String(s).replaceAll('<','&lt;'),slugOfName:s=>s.toLowerCase().replaceAll(' ','-'),
  wineFormValues:()=>Object.fromEntries(controls.map(e=>[e.name,e.value])),
  updateWineForm:()=>{},fileBase64:async file=>file.name,
  fetch:(url,options)=>new Promise((resolve,reject)=>requests.push({url,options,resolve,reject})),
  window:{confirm:()=>confirmed}});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8')+'\nthis.controller=wineDraft;',ctx);
const controller=ctx.controller, form=node('#wine-form'), field=name=>form.elements[name];
const tick=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
const reply=(request,result)=>request.resolve({ok:true,json:async()=>result});
const flush=()=>{const pending=[...timers.values()];timers.clear();for(const f of pending)f();};
(async()=>{
 field('name').value='Graphite';field('vintage').value='2024';ctx.DATA.records=[{slug:'__graphite-2024'}];controller.suggestSlug();assert.equal(node('#wine-slug').value,'graphite-2024-2');
 field('name').value='';field('vintage').value='';
 const first={name:'first.png'}, second={name:'second.png'};
 ctx.WINE_FORM.file=first; const old=controller.recognize(first);await tick();
 field('producer').value='Typed winery';form.fire('input',field('producer'));
 // A user who clears a field while recognition runs keeps that empty field.
 field('region').value='';form.fire('input',field('region'));
 reply(requests[0],{values:{name:'First wine',producer:'Model winery',region:'Model region',grapes:'Merlot'}});
 await old;assert.equal(field('name').value,'First wine');assert.equal(field('producer').value,'Typed winery');assert.equal(field('region').value,'');
 ctx.WINE_FORM.file=second; const current=controller.recognize(second);await tick();
 assert.equal(field('name').value,'');assert.equal(field('producer').value,'Typed winery');
 const newest=requests.at(-1);controller.close();
 reply(newest,{values:{name:'Stale wine'}});await current;assert.equal(field('name').value,'');assert(!controller.busy);
 // Replacement also rejects replies even when the transport ignores browser abort.
 ctx.WINE_FORM.file=first;const a=controller.recognize(first);await tick();const ar=requests.at(-1);
 ctx.WINE_FORM.file=second;const b=controller.recognize(second);await tick();const br=requests.at(-1);
 reply(br,{values:{name:'Current wine'}});await b;reply(ar,{values:{name:'Wrong wine'}});await a;
 assert.equal(field('name').value,'Current wine');
 controller.open();flush();await tick();
 const record={slug:'__existing',name:'Current wine',producer:'Existing winery',state:'Active'};
 const match={record,values:{name:'Existing wine',producer:'Existing winery',grapes:'Merlot',vintage:'2023',region:'Crimea'},relation:'exact',reasons:[]};
 reply(requests.at(-1),{matches:[match],total:1,conflicts:[{relation:'exact'}]});await tick();
 assert(node('#wine-similar-list').innerHTML.includes('Exact same wine'));
 const trigger={isConnected:true,focus(){this.focused=true;},dataset:{wineDraftCard:'0'},closest(){return this;}};
 node('#wine-similar-list').fire('click',trigger);assert(!node('#wine-similar-modal').hidden);assert(node('#wine-modal').inert);
 let stopped=false;ctx.document.keydown({key:'Escape',preventDefault(){},stopImmediatePropagation(){stopped=true;}});
 assert(stopped);assert(node('#wine-similar-modal').hidden);assert(!node('#wine-modal').inert);
 node('#wine-similar-list').fire('click',trigger);node('#wine-similar-copy').fire('click',{});
 assert.equal(field('name').value,'Current wine');assert.equal(field('producer').value,'Typed winery');assert.equal(field('region').value,'Crimea');
 assert.equal(field('vintage').value,'2023');assert(node('#wine-similar-modal').hidden);assert(trigger.focused);assert(!node('#wine-modal').inert);
 // Confirmation cancellation does not return create authorization.
 let save=controller.beforeSave();await tick();reply(requests.at(-1),{matches:[match],total:1,
   conflicts:[{relation:'exact',slug:'__existing',identity:{years:['2023']},state:'Active'}],acknowledgement:'one'});
 assert.equal(await save,null);confirmed=true;
 save=controller.beforeSave();await tick();reply(requests.at(-1),{matches:[match],total:1,
   conflicts:[{relation:'different_vintage',slug:'__existing',identity:{years:['2022']},state:'Active'}],acknowledgement:'two'});
 assert.equal((await save).duplicate_acknowledgement,'two');
 save=controller.beforeSave();await tick();requests.at(-1).reject(new Error('offline'));
 await assert.rejects(save,/offline/);assert(!controller.busy);
 // Copy respects a year already present in the draft name.
 field('name').value='Graphite 2024';field('vintage').value='';
 controller.open();flush();await tick();reply(requests.at(-1),{matches:[match],total:1,conflicts:[]});await tick();
 node('#wine-similar-list').fire('click',trigger);node('#wine-similar-copy').fire('click',{});
 assert.equal(field('vintage').value,'2024');controller.suggestSlug();assert(!node('#wine-slug').value.includes('2023'));
 field('name').value='Vision 2099';field('vintage').value='';
 controller.open();flush();await tick();reply(requests.at(-1),{matches:[match],total:1,conflicts:[]});await tick();
 node('#wine-similar-list').fire('click',trigger);node('#wine-similar-copy').fire('click',{});assert.equal(field('vintage').value,'2023');
 // Similarity omits large descriptions and non-identity fields.
 field('description').value='x'.repeat(100000);controller.open();flush();await tick();
 const body=JSON.parse(requests.at(-1).options.body);assert(!('description' in body));assert(!('slug' in body));
 reply(requests.at(-1),{matches:[],conflicts:[],total:0});await tick();
 // A busy server retries the current image after the old server request releases its slot.
 ctx.WINE_FORM.file=first;let retrying=controller.recognize(first);await tick();
 requests.at(-1).resolve({ok:false,status:429,json:async()=>({error:'busy'})});await tick();
 assert(node('#wine-recognition-status').textContent.includes('Waiting'));flush();await tick();
 reply(requests.at(-1),{values:{name:'Current retry'}});await retrying;
 // Cancelling a pending retry does not submit another image request.
 retrying=controller.recognize(first);await tick();requests.at(-1).resolve({ok:false,status:429,json:async()=>({error:'busy'})});await tick();
 const count=requests.length;node('#wine-recognition-cancel').fire('click',{});await retrying;flush();await tick();
 assert.equal(requests.filter(r=>r.url==='/api/wine-draft-recognize').length,requests.slice(0,count).filter(r=>r.url==='/api/wine-draft-recognize').length);
 const staleSave=controller.beforeSave();await tick();const oldSearch=requests.at(-1);field('name').value='Changed during check';form.fire('input',field('name'));
 reply(oldSearch,{matches:[],conflicts:[],total:0,acknowledgement:'stale'});await assert.rejects(staleSave,/draft changed/);
 // The `change` after the `input` events of the same text keeps the similar cards, so the
 // press on a card that took the focus from the field lands.
 field('producer').value='Typed again';form.fire('input',field('producer'));flush();await tick();
 reply(requests.at(-1),{matches:[match],total:1,conflicts:[]});await tick();
 const searches=requests.length;form.fire('change',field('producer'));
 assert(node('#wine-similar-list').innerHTML.includes('Exact same wine'));
 assert.equal(timers.size,0);flush();await tick();assert.equal(requests.length,searches);
 field('producer').value='Changed by paste';form.fire('change',field('producer'));
 assert.equal(node('#wine-similar-list').innerHTML,'');assert.equal(timers.size,1);
 controller.reset();assert.equal(node('#wine-recognition-status').textContent,'');
 console.log('Draft controller scenarios passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''


class DraftUiTest(unittest.TestCase):
    def test_delayed_recognition_edits_copy_and_save_confirmation(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required")
        result = subprocess.run([node, "-e", SCRIPT, str(ROOT / "pipeline/pages/wine_draft.js")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("scenarios passed", result.stdout)
