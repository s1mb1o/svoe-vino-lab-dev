"""Check verdict recovery, review scope, and filter composition in the Testset page."""
from pathlib import Path
import shutil
import subprocess
import unittest

PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/testset.html"
SOURCE = PAGE.read_text(encoding="utf-8")
REVIEW = SOURCE[SOURCE.index("let LABEL_BUSY ="):SOURCE.index("async function markDelete(")]
FILTERS = SOURCE[SOURCE.index("function activeViewFilters()"):SOURCE.index('$("#stat").addEventListener')]
NULL_ROW = SOURCE[SOURCE.index("function nullRowHtml("):SOURCE.index("function rowHtml(")]
POST = SOURCE[SOURCE.index("async function post("):SOURCE.index("/* Take the photo of a write answer")]
SETUP = r'''
const assert = require('node:assert/strict');
let SET='my', LB={wine:2,photo:0}, QT=null, GROUP_FILTER='', NULL_OPEN=false;
let EDITED_AT='before';
const localStamp=()=>'after';
const NULL_SLUG='__null__', NULL_LABELS=['positive','unusable'];
const FILTER_AXES=['#filter','#verdict','#marks','#origin','#cluster'];
const photo=(file)=>({file,sha256:'hash-'+file});
let ROWS=[{slug:'a',photos:[photo('one.jpg'),photo('two.jpg')]},
 {slug:'b',photos:[photo('three.jpg')]},
 {slug:NULL_SLUG,photos:[photo('null.jpg')]},
 {slug:'__drawer__',photos:[photo('waiting.jpg')]},
 {slug:'removed',state:'Removed',photos:[photo('removed.jpg')]}];
let VIEW=[ROWS[3],ROWS[2],ROWS[0],ROWS[1],ROWS[4]];
const isNullRow=row=>row?.slug===NULL_SLUG;
const isDrawerRow=row=>row?.slug==='__drawer__';
const isSpecialRow=row=>isNullRow(row)||isDrawerRow(row);
const entries=new Map();
const entryOf=(slug,file)=>entries.get(slug+'/'+file)||{};
const labelOf=(slug,file)=>entryOf(slug,file).label||null;
const deleteMarked=(slug,file)=>!!entryOf(slug,file).delete;
const photoOf=(slug,file)=>ROWS.find(row=>row.slug===slug)?.photos.find(photo=>photo.file===file)||null;
const lbPhoto=()=>{const row=LB&&VIEW[LB.wine], p=row?.photos[LB.photo];return p?{slug:row.slug,file:p.file}:null};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function node(value='', tagName='INPUT') {return {value,tagName,disabled:false,textContent:'',innerHTML:'',attributes:{},
 addEventListener(){},setAttribute(key,value){this.attributes[key]=value},focus(){},
 get selectedOptions(){return [{textContent:this.value==='has_pos'?'positive':this.value==='scene_photo'?'scene_photo (12)':this.value}]}}}
const controls=new Map([['#q',node('chateau')],['#filter',node('all','SELECT')],['#verdict',node('all','SELECT')],
 ['#marks',node('all','SELECT')],['#tag',node('','SELECT')],['#origin',node('all','SELECT')],
 ['#cluster',node('all','SELECT')],['#sort',node('neg_desc','SELECT')]]);
const $=id=>{if(!controls.has(id))controls.set(id,node());return controls.get(id)};
const verdictButtons=['positive','negative','unusable','variant'].map(label=>Object.assign(node(),{dataset:{reviewLabel:label}}));
const gridButtons=[node()];
const document={querySelectorAll:selector=>selector==='[data-review-label]'?verdictButtons:selector==='.btns button'?gridButtons:[]};
const posts=[], opened=[], alerts=[];
let renders=0;
const render=()=>renders++;
const alert=message=>alerts.push(message);
async function post(route,body) {
 posts.push({route,...body});
 const p=photoOf(body.place,body.file);
 return {photo:{...p,entry:{...entryOf(body.place,body.file),label:body.label}}};
}
function takePhoto(slug,p){entries.set(slug+'/'+p.file,p.entry);}
function showLightbox(wine,photo){LB={wine,photo};opened.push(lbPhoto());}
const closeLightbox=()=>{LB=null};
const cardsHtml=row=>row.photos.map(p=>'<article>'+p.file+'</article>').join('');
const rowCountsHtml=row=>row.photos.length+' photos';
const rowOf=()=>({querySelector:()=>node()});
const refreshRow=()=>{};
'''


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class TestsetReviewControlsTest(unittest.TestCase):
    def run_js(self, check, real_post=False):
        code = SETUP + REVIEW + FILTERS + NULL_ROW + (POST if real_post else "")
        code += "\n(async()=>{\n" + check + "\n})().catch(error=>{console.error(error);process.exitCode=1});"
        result = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_late_write_response_keeps_the_new_set_timestamp(self):
        self.run_js("""
let finish,sent;
fetch=async(route,options)=>{sent=JSON.parse(options.body);return await new Promise(resolve=>finish=()=>resolve({ok:true,json:async()=>({})}))};
const pending=post('/api/testset-label',{file:'one.jpg',label:'positive'});
SET='other';finish();await pending;
assert.equal(sent.set,'my');assert.equal(EDITED_AT,'before');
""", real_post=True)

    def test_a_current_write_updates_the_timestamp(self):
        self.run_js("""
fetch=async()=>({ok:true,json:async()=>({})});
await post('/api/testset-label',{file:'one.jpg',label:'positive'});
assert.equal(EDITED_AT,'after');
""", real_post=True)

    def test_save_and_undo_restore_the_previous_verdict(self):
        self.run_js("""
entries.set('a/one.jpg',{label:'positive',comments:['preserve'],box:[1,2,3,4]});
assert.equal(await setLabel('a','one.jpg','negative'),true);
assert.equal(labelOf('a','one.jpg'),'negative');
assert.equal(await undoVerdict(),true);
assert.equal(labelOf('a','one.jpg'),'positive');
assert.deepEqual(entryOf('a','one.jpg').comments,['preserve']);
assert.deepEqual(entryOf('a','one.jpg').box,[1,2,3,4]);
assert.deepEqual(posts.map(x=>x.label),['negative','positive']);
assert.equal(LABEL_HISTORY.length,0);
assert.equal(opened.length,0); // Keep a comment draft on the current photo.
""")

    def test_undo_after_navigation_opens_the_changed_photo(self):
        self.run_js("""
await setLabel('a','one.jpg','positive');LB={wine:3,photo:0};
await undoVerdict();assert.deepEqual(opened.at(-1),{slug:'a',file:'one.jpg'});
""")

    def test_a_repeated_verdict_clears_and_undo_restores_it(self):
        self.run_js("""
entries.set('a/one.jpg',{label:'positive'});
await setLabel('a','one.jpg','positive');
assert.equal(labelOf('a','one.jpg'),null);
await undoVerdict();
assert.equal(labelOf('a','one.jpg'),'positive');
""")

    def test_undo_of_a_first_label_restores_unreviewed(self):
        self.run_js("""
await setLabel('a','one.jpg','positive');await undoVerdict();
assert.equal(labelOf('a','one.jpg'),null);
assert.equal(posts.at(-1).label,null);
""")

    def test_undo_uses_successful_changes_in_reverse_order(self):
        self.run_js("""
await setLabel('a','one.jpg','positive');await setLabel('a','one.jpg','negative');
await undoVerdict();assert.equal(labelOf('a','one.jpg'),'positive');
await undoVerdict();assert.equal(labelOf('a','one.jpg'),null);
assert.equal(await undoVerdict(),false);assert.equal(posts.length,4);
""")

    def test_failed_save_does_not_change_local_labels_or_history(self):
        self.run_js("""
post=async()=>{throw Error('offline')};
assert.equal(await setLabel('a','one.jpg','positive'),false);
assert.equal(labelOf('a','one.jpg'),null);assert.equal(LABEL_HISTORY.length,0);
assert.equal(LABEL_MESSAGE,'Not saved: offline');assert.equal(LABEL_BUSY,false);
""")

    def test_failed_undo_keeps_the_history_for_retry(self):
        self.run_js("""
await setLabel('a','one.jpg','positive');
const original=post;post=async()=>{throw Error('offline')};
assert.equal(await undoVerdict(),false);assert.equal(LABEL_HISTORY.length,1);
assert.equal(labelOf('a','one.jpg'),'positive');post=original;
assert.equal(await undoVerdict(),true);assert.equal(labelOf('a','one.jpg'),null);
""")

    def test_grid_save_errors_remain_visible(self):
        self.run_js("""
LB=null;post=async()=>{throw Error('offline')};await setLabel('a','one.jpg','positive');
assert.equal(alerts.length,1);assert.match(alerts[0],/not saved/);
""")

    def test_only_one_label_request_runs_at_a_time(self):
        self.run_js("""
let finish;
post=async(route,body)=>{posts.push(body);return await new Promise(resolve=>finish=()=>resolve({photo:{...photoOf(body.place,body.file),entry:{label:body.label}}}))};
const pending=setLabel('a','one.jpg','positive');
assert.equal(gridButtons[0].disabled,true);
assert.equal(await setLabel('a','two.jpg','negative'),false);assert.equal(posts.length,1);
finish();await pending;assert.equal(gridButtons[0].disabled,false);
""")

    def test_a_response_cannot_update_another_set(self):
        self.run_js("""
let finish;post=async(route,body)=>new Promise(resolve=>finish=()=>resolve({photo:{...photoOf(body.place,body.file),entry:{label:body.label}}}));
const pending=setLabel('a','one.jpg','positive');SET='other';finish();await pending;
assert.equal(labelOf('a','one.jpg'),null);assert.equal(LABEL_HISTORY.length,0);
""")

    def test_a_reload_invalidates_old_label_responses(self):
        self.run_js("""
let finish;post=async(route,body)=>new Promise(resolve=>finish=()=>resolve({photo:{...photoOf(body.place,body.file),entry:{label:body.label}}}));
const pending=setLabel('a','one.jpg','positive');LABEL_EPOCH++;finish();await pending;
assert.equal(labelOf('a','one.jpg'),null);assert.equal(LABEL_HISTORY.length,0);
""")

    def test_undo_skips_removed_moved_or_replaced_photos(self):
        self.run_js("""
await setLabel('a','one.jpg','positive');ROWS[0].photos[0].sha256='replaced';
assert.equal(undoEntry(),null);assert.equal(await undoVerdict(),false);
await setLabel('a','two.jpg','positive');ROWS[0].photos=ROWS[0].photos.filter(p=>p.file!=='two.jpg');
assert.equal(undoEntry(),null);assert.equal(posts.length,2);
""")

    def test_undo_does_not_overwrite_a_changed_label(self):
        self.run_js("""
await setLabel('a','one.jpg','positive');entries.set('a/one.jpg',{label:'unusable'});
assert.equal(await undoVerdict(),false);assert.equal(labelOf('a','one.jpg'),'unusable');
assert.equal(posts.length,1);
""")

    def test_special_rows_keep_their_existing_label_rules(self):
        self.run_js("""
assert.equal(await setLabel('__drawer__','waiting.jpg','positive'),false);
assert.equal(await setLabel('__null__','null.jpg','negative'),false);
assert.equal(await setLabel('__null__','null.jpg','variant'),false);
assert.equal(await setLabel('__null__','null.jpg','positive'),true);
assert.equal(posts.length,1);
""")

    def test_review_queue_uses_only_current_wine_results(self):
        self.run_js("""
entries.set('a/two.jpg',{delete:true});
assert.deepEqual(reviewQueue(),[{slug:'a',file:'one.jpg'},{slug:'b',file:'three.jpg'}]);
VIEW=VIEW.filter(row=>row.slug!=='b');
assert.deepEqual(reviewQueue(),[{slug:'a',file:'one.jpg'}]);
""")

    def test_no_match_has_a_separate_review_queue(self):
        self.run_js("""
LB={wine:1,photo:0};assert.deepEqual(reviewQueue(),[{slug:'__null__',file:'null.jpg'}]);
renderReviewToolbar();assert.equal(verdictButtons[1].disabled,true);
assert.equal(verdictButtons[3].disabled,true);assert.match(verdictButtons[0].innerHTML,/Confirm No Match/);
""")

    def test_next_unreviewed_skips_reviewed_photos_and_wraps(self):
        self.run_js("""
entries.set('a/two.jpg',{label:'positive'});
assert.deepEqual(nextUnreviewed(reviewQueue(),lbPhoto()),{slug:'b',file:'three.jpg'});
LB={wine:3,photo:0};assert.deepEqual(nextUnreviewed(reviewQueue(),lbPhoto()),{slug:'a',file:'one.jpg'});
entries.set('a/one.jpg',{label:'negative'});
assert.equal(nextUnreviewed(reviewQueue(),lbPhoto()),null);
""")

    def test_drawer_review_controls_cannot_label_or_advance(self):
        self.run_js("""
LB={wine:0,photo:0};renderReviewToolbar();
assert(verdictButtons.every(button=>button.disabled));
assert.equal($('#review-unreviewed').disabled,true);
assert.equal($('#review-progress').textContent,'Move to a wine to review');
""")

    def test_a_catalogue_image_can_advance_to_unreviewed_photos(self):
        self.run_js("""
ROWS[0].photos=[];ROWS[0].bottle_url='catalogue.jpg';renderReviewToolbar();
assert.equal($('#review-unreviewed').disabled,false);openNextUnreviewed();
assert.deepEqual(opened.at(-1),{slug:'b',file:'three.jpg'});
""")

    def test_stat_filters_compose_with_search_and_other_axes(self):
        self.run_js("""
$('#tag').value='scene_photo';$('#marks').value='noted';GROUP_FILTER='same-family';
applyTestsetStat('verdict','has_pos');
assert.equal($('#q').value,'chateau');assert.equal($('#tag').value,'scene_photo');
assert.equal($('#marks').value,'noted');assert.equal(GROUP_FILTER,'same-family');
assert.equal($('#verdict').value,'has_pos');
applyTestsetStat('verdict','has_pos');assert.equal($('#verdict').value,'all');
assert.equal($('#q').value,'chateau');assert.equal($('#marks').value,'noted');
""")

    def test_clear_filters_keeps_the_selected_sort(self):
        self.run_js("""
$('#tag').value='scene_photo';$('#marks').value='noted';GROUP_FILTER='g';clearViewFilters();
assert.equal($('#q').value,'');assert.equal($('#tag').value,'');assert.equal(GROUP_FILTER,'');
assert(FILTER_AXES.every(id=>$(id).value==='all'));assert.equal($('#sort').value,'neg_desc');
""")

    def test_remove_one_filter_preserves_the_others(self):
        self.run_js("""
$('#verdict').value='has_pos';$('#tag').value='scene_photo';clearViewFilter('tag');
assert.equal($('#q').value,'chateau');assert.equal($('#verdict').value,'has_pos');
clearViewFilter('q');assert.equal($('#q').value,'');assert.equal($('#verdict').value,'has_pos');
""")

    def test_filter_chips_show_values_escape_text_and_exclude_sort(self):
        self.run_js("""
$('#q').value='img:<unsafe>.jpg';$('#tag').value='scene_photo';renderFilterState();
assert.equal(activeViewFilters().length,2);
assert.match($('#active-filters').innerHTML,/img:&lt;unsafe&gt;.jpg/);
assert.match($('#active-filters').innerHTML,/Tag: scene_photo</);
assert(!$('#active-filters').innerHTML.includes('Sort:'));
assert(!$('#active-filters').innerHTML.includes('(12)'));
""")

    def test_no_match_stays_a_compact_drop_target_until_expanded(self):
        self.run_js(r"""
const row=ROWS[2];let html=nullRowHtml(row);
assert.match(html,/data-slug="__null__"/);assert.match(html,/aria-expanded="false"/);
assert.match(html,/Drop a photo/);assert(!html.includes('<article>'));
NULL_OPEN=true;html=nullRowHtml(row);assert.match(html,/aria-expanded="true"/);
assert.match(html,/<article>null.jpg<\/article>/);
""")


if __name__ == "__main__":
    unittest.main()
