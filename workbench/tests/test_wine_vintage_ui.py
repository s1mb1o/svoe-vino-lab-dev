"""Check vintage-link editing, relation isolation, and failed requests."""
from pathlib import Path
import shutil
import subprocess
import unittest

SOURCE=(Path(__file__).resolve().parents[1]/'pipeline/pages/dataset.html').read_text()
EDITOR=SOURCE[SOURCE.index('function vintageOn()'):SOURCE.index('// The free-form tags of a wine')]
ACTIONS=SOURCE[SOURCE.index('function focusVintage('):SOURCE.index('function focusTag(')]
SETUP=r'''
const assert=require('node:assert/strict');
let DATA={vintage_editor:true,vintage_pairs:0,records:[{slug:'wine',name:'Wine',_similar:['lookalike'],_tags:['generic'],_vintages:[]},
 {slug:'wine-2022',name:'Wine 2022',_similar:[],_tags:['vintage:2022'],_vintages:[]}]};
const DRAFT_VINTAGES=new Map(),BUSY_VINTAGES=new Set(),alerts=[],requests=[],renders=[];
const esc=value=>String(value??'').replaceAll('<','&lt;').replaceAll('"','&quot;');
const ICON_SAVE='save',ICON_CANCEL='cancel';
const renderCard=slug=>renders.push(slug),renderCodeCard=slug=>renders.push(slug);
const alert=text=>alerts.push(text),requestAnimationFrame=fn=>fn();
const document={querySelectorAll:()=>[],getElementById:()=>({})};
let fetch=async(route,options)=>{requests.push({route,...options});
 const removed=options.method==='DELETE';
 return {ok:true,json:async()=>({slug:'wine',other:'wine-2022',
 vintages:removed?[]:['wine-2022'],other_vintages:removed?[]:['wine'],total:removed?0:1})};};
'''


@unittest.skipUnless(shutil.which('node'),'Node.js required')
class VintageUiTest(unittest.TestCase):
    def run_js(self,check):
        code=SETUP+EDITOR+ACTIONS+'\n(async()=>{'+check+'})().catch(error=>{console.error(error);process.exitCode=1});'
        result=subprocess.run(['node','-e',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_editor_explains_the_undated_entry_and_shows_exact_slugs(self):
        self.run_js(r'''
DATA.records[0]._vintages=['wine-2022'];const html=vintageEditor(DATA.records[0]);
assert.match(html,/Same wine \/ vintages/);assert.match(html,/entry without a year/);
assert.match(html,/data-vintage-open="wine-2022"/);assert.match(html,/Wine 2022/);
''')

    def test_save_updates_both_cards_and_keeps_similar_links_and_tags(self):
        self.run_js(r'''
DRAFT_VINTAGES.set('wine','wine-2022');await saveVintage('wine');
assert.deepEqual(JSON.parse(requests[0].body),{slug:'wine',other:'wine-2022'});
assert.equal(requests[0].route,'/api/dataset-vintage');
assert.deepEqual(DATA.records.map(r=>r._vintages),[['wine-2022'],['wine']]);
assert.deepEqual(DATA.records[0]._similar,['lookalike']);assert.deepEqual(DATA.records[0]._tags,['generic']);
assert.equal(DATA.vintage_pairs,1);assert.equal(DRAFT_VINTAGES.size,0);
''')

    def test_remove_updates_both_cards(self):
        self.run_js(r'''
DATA.records[0]._vintages=['wine-2022'];DATA.records[1]._vintages=['wine'];
await removeVintage('wine','wine-2022');assert.equal(requests[0].method,'DELETE');
assert.deepEqual(DATA.records.map(r=>r._vintages),[[],[]]);assert.equal(DATA.vintage_pairs,0);
''')

    def test_failed_save_preserves_the_draft_and_existing_links(self):
        self.run_js(r'''
DRAFT_VINTAGES.set('wine','wine-2022');fetch=async()=>({ok:false,json:async()=>({error:'already linked'})});
await saveVintage('wine');assert.equal(DRAFT_VINTAGES.get('wine'),'wine-2022');
assert.deepEqual(DATA.records[0]._vintages,[]);assert.equal(BUSY_VINTAGES.size,0);assert.match(alerts[0],/already linked/);
''')

    def test_failed_remove_preserves_the_link(self):
        self.run_js(r'''
DATA.records[0]._vintages=['wine-2022'];fetch=async()=>{throw Error('offline')};
await removeVintage('wine','wine-2022');assert.deepEqual(DATA.records[0]._vintages,['wine-2022']);
assert.equal(BUSY_VINTAGES.size,0);assert.match(alerts[0],/offline/);
''')

    def test_busy_state_blocks_duplicate_submissions(self):
        self.run_js(r'''
DRAFT_VINTAGES.set('wine','wine-2022');let finish;fetch=async()=>{requests.push({});return new Promise(r=>finish=r)};
const pending=saveVintage('wine');await saveVintage('wine');await removeVintage('wine','wine-2022');
assert.equal(requests.length,1);finish({ok:true,json:async()=>({slug:'wine',other:'wine-2022',vintages:['wine-2022'],other_vintages:['wine'],total:1})});
await pending;assert.equal(BUSY_VINTAGES.size,0);
''')


if __name__=='__main__':
    unittest.main()
