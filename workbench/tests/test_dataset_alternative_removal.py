"""Check immediate additional-image removal and failed-request recovery."""
from pathlib import Path
import shutil
import subprocess
import unittest

PAGE=Path(__file__).resolve().parents[1]/'pipeline/pages/dataset.html'
SOURCE=PAGE.read_text()
REMOVE=SOURCE[SOURCE.index('async function applyAlternativeRemovals('):SOURCE.index('async function applyPendingAlternatives(')]
EDITOR=SOURCE[SOURCE.index('function alternativeEditorOn('):SOURCE.index('// Plan 58: a shared code')]
HANDLER=SOURCE[SOURCE.index('  const alternative = event.target.closest(".alternative-editor")'):
               SOURCE.index('  const editor = event.target.closest(".patch-editor")')]
SETUP=r'''
const assert=require('node:assert/strict');
const PENDING_ALTERNATIVES=new Map(),BUSY_ALTERNATIVES=new Set(),BUSY_ALTERNATIVE_TYPES=new Set();
let DATA={alternative_editor:true,alternatives:3,records:[{slug:'wine',name:'Name',_alternatives:[
 {sha256:'one',image_url:'/one',type:'full_front'},{sha256:'two',image_url:'/two',type:'label_front'}]},
 {slug:'other',_alternatives:[{sha256:'shared',type:'full_back'}]}]};
const renders=[],alerts=[],requests=[];
const renderCard=slug=>renders.push(slug), renderHead=()=>renders.push('head'),render=()=>renders.push('page');
const alert=text=>alerts.push(text),confirm=()=>{throw Error('Confirmation MUST NOT run')};
const esc=text=>String(text??'');
const describeButton=()=>'',recutButton=()=>'',ALTERNATIVE_TYPES=[],PHOTO_MOVES=[];
function dropPendingAlternatives(slug){const pending=PENDING_ALTERNATIVES.get(slug);
 if(pending&&!pending.adds.length&&!pending.removes.size)PENDING_ALTERNATIVES.delete(slug);}
let fetch=async(url,options)=>{requests.push({url,...options});
 const sha=new URL(url,'http://local').searchParams.get('sha256');
 const record=DATA.records.find(r=>r.slug==='wine');
 return {ok:true,json:async()=>({record:{...record,_alternatives:record._alternatives.filter(p=>p.sha256!==sha)},
  alternatives:DATA.alternatives-1})};};
function clickRemove(sha){const alternative={dataset:{slug:'wine'}};
 const remove={dataset:{alternativeRemove:sha}};
 onClick({target:{closest:selector=>selector==='.alternative-editor'?alternative:
  selector==='[data-alternative-remove]'?remove:null}});}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
'''


@unittest.skipUnless(shutil.which('node'),'Node.js required')
class DatasetAlternativeRemovalTest(unittest.TestCase):
    def run_js(self,check):
        code=SETUP+REMOVE+EDITOR+'\nfunction onClick(event){\n'+HANDLER+'\n}\n'
        code+='(async()=>{\n'+check+'\n})().catch(error=>{console.error(error);process.exitCode=1});'
        out=subprocess.run(['node','-e',code],capture_output=True,text=True)
        self.assertEqual(out.returncode,0,out.stderr)

    def test_x_immediately_removes_only_the_selected_photo_without_confirm_or_apply(self):
        self.run_js(r'''
const other=JSON.stringify(DATA.records[1]);clickRemove('one');await settle();
assert.deepEqual(requests,[{url:'/api/dataset-alternative?slug=wine&sha256=one',method:'DELETE'}]);
assert.deepEqual(DATA.records[0]._alternatives.map(p=>p.sha256),['two']);
assert.equal(JSON.stringify(DATA.records[1]),other);assert.equal(DATA.records[0].name,'Name');
assert.equal(PENDING_ALTERNATIVES.size,0);assert.equal(DATA.alternatives,2);
assert(!renders.includes('page'));assert.equal(alerts.length,0);
''')

    def test_an_explicit_remove_preserves_other_staged_changes(self):
        self.run_js(r'''
const add={file:{name:'new.jpg'}};PENDING_ALTERNATIVES.set('wine',{adds:[add],removes:new Set(['two'])});
await applyAlternativeRemovals('wine','one');
assert.deepEqual(PENDING_ALTERNATIVES.get('wine').adds,[add]);
assert.deepEqual([...PENDING_ALTERNATIVES.get('wine').removes],['two']);assert.equal(requests.length,1);
''')

    def test_a_failed_delete_keeps_the_photo_and_can_be_retried(self):
        self.run_js(r'''
const before=JSON.stringify(DATA),success=fetch;
fetch=async()=>({ok:false,status:503,json:async()=>({error:'database unavailable'})});
await applyAlternativeRemovals('wine','one');assert.equal(JSON.stringify(DATA),before);
assert.equal(PENDING_ALTERNATIVES.size,0);assert.equal(BUSY_ALTERNATIVES.size,0);
assert.match(alerts[0],/database unavailable/);fetch=success;
await applyAlternativeRemovals('wine','one');assert.equal(DATA.records[0]._alternatives.length,1);
''')

    def test_a_network_failure_keeps_the_photo_and_releases_busy_state(self):
        self.run_js(r'''
const before=JSON.stringify(DATA);fetch=async()=>{throw Error('offline')};
await applyAlternativeRemovals('wine','one');assert.equal(JSON.stringify(DATA),before);
assert.equal(BUSY_ALTERNATIVES.size,0);assert.match(alerts[0],/offline/);
''')

    def test_repeated_clicks_send_one_request_while_busy(self):
        self.run_js(r'''
let finish;fetch=async(url,options)=>{requests.push({url,...options});return new Promise(resolve=>finish=resolve)};
const pending=applyAlternativeRemovals('wine','one');assert(BUSY_ALTERNATIVES.has('wine'));
await applyAlternativeRemovals('wine','one');await applyAlternativeRemovals('wine','two');
assert.equal(requests.length,1);finish({ok:true,json:async()=>({alternatives:2})});await pending;
assert.equal(BUSY_ALTERNATIVES.size,0);
''')

    def test_the_editor_disables_image_actions_during_the_delete(self):
        self.run_js(r'''
BUSY_ALTERNATIVES.add('wine');const html=alternativeEditor(DATA.records[0]);
assert.match(html,/data-alternative-remove="one"[\s\S]*?aria-label="Remove this additional image" disabled/);
BUSY_ALTERNATIVES.clear();assert(!alternativeEditor(DATA.records[0]).includes('image" disabled'));
''')

    def test_existing_queued_removals_still_apply(self):
        self.run_js(r'''
PENDING_ALTERNATIVES.set('wine',{adds:[],removes:new Set(['one','two'])});
await applyAlternativeRemovals('wine');assert.equal(requests.length,2);
assert.equal(DATA.records[0]._alternatives.length,0);assert.equal(PENDING_ALTERNATIVES.size,0);
''')

    def test_the_file_review_editor_keeps_its_staged_workflow(self):
        self.run_js(r'''
DATA.alternative_editor=false;clickRemove('one');await settle();assert.equal(requests.length,0);
assert.deepEqual([...PENDING_ALTERNATIVES.get('wine').removes],['one']);
clickRemove('one');assert.equal(PENDING_ALTERNATIVES.get('wine').removes.size,0);
''')


if __name__=='__main__':
    unittest.main()
