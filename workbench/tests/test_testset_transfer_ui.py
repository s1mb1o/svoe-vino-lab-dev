"""Check Testset transfer requests, recovery, and submenu navigation."""
from pathlib import Path
import shutil
import subprocess
import unittest

PAGE = Path(__file__).resolve().parents[1] / 'pipeline/pages/testset.html'
SOURCE = PAGE.read_text()
TRANSFER = SOURCE[SOURCE.index('/* Move one entry to another testset.'):
                  SOURCE.index('/* End of testset transfer. */')]
SETUP = r'''
const assert=require('node:assert/strict');
let SET='my', LABEL_EPOCH=1, LABEL_BUSY=false, LB=null, CMT_AT=null, TOTAL=2, DRAWER_VIEW=null;
let SETS=[{name:'my',photos:2},{name:'target',photos:0}];
let ROWS=[{slug:'wine-a',photos:[{file:'one.jpg',sha256:'a'.repeat(64),conf:80},
 {file:'two.jpg',sha256:'b'.repeat(64),conf:60}],bottle_url:null}];
let VIEW=ROWS, V={'wine-a':{'one.jpg':{label:'positive'},'two.jpg':{label:'negative'}}};
const nodes=new Map(), events=new Map();
function node(){return {hidden:true,value:'',innerHTML:'',textContent:'',className:'',style:{},options:[],
 attrs:{},children:[],disabled:false,focus(){document.activeElement=this},
 setAttribute(k,v){this.attrs[k]=v},append(...items){this.children.push(...items)},
 addEventListener(type,fn){this.listeners??={};this.listeners[type]=fn},
 getBoundingClientRect(){return {left:10,right:210,top:200,width:200,height:150}},
 querySelector(){return this.buttons?.[0]||null},querySelectorAll(){return this.buttons||[]}}}
const $=key=>{if(!nodes.has(key))nodes.set(key,node());return nodes.get(key)};
$('#set').options=[{value:'my'},{value:'target'}];
const document={activeElement:null,addEventListener(type,fn){events.set(type,fn)},createElement:()=>node()};
const window={innerWidth:1280,innerHeight:720};
const esc=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const sameAt=(a,b)=>a?.slug===b?.slug&&a?.file===b?.file;
const photoOf=(slug,file)=>ROWS.find(x=>x.slug===slug)?.photos.find(x=>x.file===file);
const isNullRow=row=>row?.slug==='__null__', isDrawerRow=row=>row?.slug==='__drawer__';
const isSpecialRow=row=>isNullRow(row)||isDrawerRow(row);
let rendered=0, refreshed=0, drawerRendered=0, toolbarRendered=0;
const refreshRow=()=>refreshed++, photoTotal=()=>ROWS.reduce((n,r)=>n+r.photos.length,0);
const stats=()=>rendered++, renderDrawerResults=()=>drawerRendered++;
const renderReviewToolbar=()=>toolbarRendered++;
const opened=[], alerts=[], posts=[], messages=[];
const lbPhoto=()=>LB&&VIEW[LB.wine]?.photos[LB.photo];
const showLightbox=(wine,photo)=>{LB={wine,photo};opened.push({wine,photo})};
const closeLightbox=()=>LB=null;
const reviewMessage=(text,kind)=>messages.push({text,kind});
const alert=text=>alerts.push(text);
let flushComment=async()=>{$('#cmt').value=''};
let post=async(route,body)=>{posts.push({route,...body});return {file:body.file,
 sets:[{name:'my',photos:1},{name:'target',photos:1}]}};
let hideCtxMenu=()=>{hideTestsetMenu();$('#ctxmenu').hidden=true};
'''


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class TestsetTransferUiTest(unittest.TestCase):
    def run_js(self, check):
        code=SETUP+TRANSFER+'\n(async()=>{\n'+check+'''
})().catch(error=>{console.error(error);process.exitCode=1});'''
        result=subprocess.run(['node','-e',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_move_uses_identity_without_rewriting_annotations(self):
        self.run_js(r'''
assert.equal(await transferToTestset('wine-a','one.jpg','target'),true);
assert.deepEqual(posts,[{route:'/api/testset-transfer',set:'my',place:'wine-a',file:'one.jpg',
 to_set:'target',sha256:'a'.repeat(64)}]);
assert.equal(ROWS[0].photos.length,1);assert.equal(V['wine-a']['one.jpg'],undefined);
assert.deepEqual(V['wine-a']['two.jpg'],{label:'negative'});
assert.equal(ROWS[0].min_conf,60);assert.equal(TOTAL,1);assert.equal(rendered,1);
assert.match($('#set').options[1].textContent,/target \(1 photos\)/);
assert.match($('#transfer-status').textContent,/Wine and annotations kept/);
const link=$('#transfer-status').children[1];assert.equal(link.textContent,'Open destination');
assert.match(link.href,/set=target/);assert.match(link.href,/#wine-a\/one.jpg$/);
assert.equal(TRANSFER_BUSY,false);assert.equal(LABEL_BUSY,false);
''')

    def test_destination_link_uses_the_returned_unique_filename(self):
        self.run_js(r'''
post=async()=>({file:'one.jpg.moved2.jpg'});
await transferToTestset('wine-a','one.jpg','target');
assert.match($('#transfer-status').children[1].href,/#wine-a\/one.jpg.moved2.jpg$/);
''')

    def test_failed_request_preserves_the_source_and_reports_error(self):
        self.run_js(r'''
const before=JSON.stringify({ROWS,V,SETS,TOTAL});post=async()=>{throw Error('already belongs to this wine')};
assert.equal(await transferToTestset('wine-a','one.jpg','target'),false);
assert.equal(JSON.stringify({ROWS,V,SETS,TOTAL}),before);
assert.match(alerts[0],/already belongs/);assert.equal($('#transfer-status').className,'transfer-status failed');
assert.equal(TRANSFER_BUSY,false);assert.equal(LABEL_BUSY,false);
''')

    def test_pending_comment_is_saved_before_the_transfer(self):
        self.run_js(r'''
CMT_AT={slug:'wine-a',file:'one.jpg'};$('#cmt').value='keep this note';
flushComment=async()=>{posts.push({comment:$('#cmt').value});$('#cmt').value=''};
await transferToTestset('wine-a','one.jpg','target');
assert.deepEqual(posts[0],{comment:'keep this note'});assert.equal(posts[1].route,'/api/testset-transfer');
assert.equal(CMT_AT,null);
''')

    def test_a_failed_comment_save_stops_the_move(self):
        self.run_js(r'''
CMT_AT={slug:'wine-a',file:'one.jpg'};$('#cmt').value='draft';flushComment=async()=>{};
assert.equal(await transferToTestset('wine-a','one.jpg','target'),false);
assert.equal(posts.length,0);assert.equal(ROWS[0].photos.length,2);assert.equal($('#cmt').value,'draft');
''')

    def test_busy_verdict_and_repeated_moves_are_blocked(self):
        self.run_js(r'''
LABEL_BUSY=true;assert.equal(await transferToTestset('wine-a','one.jpg','target'),false);
LABEL_BUSY=false;let finish;post=async(route,body)=>{posts.push(body);return new Promise(r=>finish=r)};
const pending=transferToTestset('wine-a','one.jpg','target');
assert.equal(LABEL_BUSY,true);assert.equal(TRANSFER_BUSY,true);
assert.equal(await transferToTestset('wine-a','two.jpg','target'),false);assert.equal(posts.length,1);
finish({file:'one.jpg'});await pending;assert.equal(LABEL_BUSY,false);
''')

    def test_same_set_and_missing_photo_have_no_effect(self):
        self.run_js(r'''
assert.equal(await transferToTestset('wine-a','one.jpg','my'),false);
assert.equal(await transferToTestset('wine-a','missing.jpg','target'),false);assert.equal(posts.length,0);
''')

    def test_late_responses_cannot_remove_a_photo_in_a_different_set(self):
        self.run_js(r'''
let finish;post=async()=>new Promise(r=>finish=r);
const pending=transferToTestset('wine-a','one.jpg','target');SET='another';
const before=JSON.stringify({ROWS,V,SETS,TOTAL});finish({file:'one.jpg'});await pending;
assert.equal(JSON.stringify({ROWS,V,SETS,TOTAL}),before);assert.equal(rendered,0);
''')

    def test_a_reload_invalidates_an_old_move_response(self):
        self.run_js(r'''
let finish;post=async()=>new Promise(r=>finish=r);
const pending=transferToTestset('wine-a','one.jpg','target');LABEL_EPOCH++;
finish({file:'one.jpg'});await pending;assert.equal(ROWS[0].photos.length,2);
''')

    def test_a_set_change_during_comment_save_cancels_the_move(self):
        self.run_js(r'''
CMT_AT={slug:'wine-a',file:'one.jpg'};$('#cmt').value='draft';
flushComment=async()=>{SET='another';$('#cmt').value=''};
assert.equal(await transferToTestset('wine-a','one.jpg','target'),false);assert.equal(posts.length,0);
''')

    def test_viewer_keeps_the_next_photo_after_a_move(self):
        self.run_js(r'''
LB={wine:0,photo:0};await transferToTestset('wine-a','one.jpg','target');
assert.deepEqual(opened,[{wine:0,photo:0}]);assert.equal(lbPhoto().file,'two.jpg');
await transferToTestset('wine-a','two.jpg','target');assert.equal(LB,null);
''')

    def test_the_last_photo_closes_the_viewer_even_with_a_catalogue_image(self):
        self.run_js(r'''
LB={wine:0,photo:0};ROWS[0].bottle_url='/catalogue.jpg';ROWS[0].photos.pop();
await transferToTestset('wine-a','one.jpg','target');assert.equal(LB,null);
''')

    def test_drawer_results_refresh_after_a_move(self):
        self.run_js(r'''
ROWS[0].slug='__drawer__';V.__drawer__=V['wine-a'];DRAWER_VIEW=[];
await transferToTestset('__drawer__','one.jpg','target');assert.equal(drawerRendered,1);
''')

    def test_submenu_lists_sets_disables_current_and_clamps_to_viewport(self):
        self.run_js(r'''
SETS.push({name:'<odd"name',photos:0});
$('#ctxmenu').getBoundingClientRect=()=>({left:900,right:1200});
showTestsetMenu();const child=$('#ctx-testsets'),parent=$("#ctxmenu [data-act='to-testset']");
assert.match(child.innerHTML,/disabled aria-disabled="true">my \(current\)/);
assert.match(child.innerHTML,/data-to-testset="target"/);assert.match(child.innerHTML,/&lt;odd&quot;name/);
assert.equal(parent.attrs['aria-expanded'],'true');assert.equal(child.hidden,false);
assert.equal(child.style.left,'696px');assert.equal(child.style.top,'200px');
hideTestsetMenu();assert.equal(child.hidden,true);assert.equal(parent.attrs['aria-expanded'],'false');
''')

    def test_keyboard_navigation_stays_in_the_submenu(self):
        self.run_js(r'''
const a=node(),b=node(),menu=$('#ctx-testsets');menu.buttons=[a,b];
let stopped=0,prevented=0;const key=key=>({key,stopPropagation(){stopped++},preventDefault(){prevented++}});
a.focus();menu.listeners.keydown(key('ArrowDown'));assert.equal(document.activeElement,b);
menu.listeners.keydown(key('ArrowDown'));assert.equal(document.activeElement,a);
menu.listeners.keydown(key('ArrowUp'));assert.equal(document.activeElement,b);
menu.listeners.keydown(key('ArrowLeft'));assert.equal(menu.hidden,true);
assert.equal(document.activeElement,$("#ctxmenu [data-act='to-testset']"));
menu.listeners.keydown(key('Tab'));assert.equal(document.activeElement,$('#q'));
assert.ok(stopped>=5&&prevented>=5);
''')


if __name__=='__main__':
    unittest.main()
