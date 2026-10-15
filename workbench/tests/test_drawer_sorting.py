"""Check Drawer sort semantics and current-photo filtering with the page's JavaScript."""
from pathlib import Path
import shutil
import subprocess
import unittest


PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/testset.html"
SOURCE = PAGE.read_text(encoding="utf-8")
CANDIDATES = SOURCE[SOURCE.index("function drawerCandidates(row)"):
                    SOURCE.index("function drawerCandidateHtml(row, candidate)")]
SORT = SOURCE[SOURCE.index("function drawerResultSortValue(row, mode, positives)"):
              SOURCE.index("const DRAWER_RESULTS =")]
RENDER = SOURCE[SOURCE.index("function renderDrawerResults()"):
                SOURCE.index("async function loadDrawerRun(runId)")]
SETUP = r"""
const assert = require('assert');
let ROWS = ['a','b','c','d'].map(slug => ({slug, in_catalog:true,
  photos:Array.from({length:{a:2,b:0,c:4,d:1}[slug]},(_,i)=>({file:String(i)}))}));
let labels = new Map(ROWS.flatMap(wine => wine.photos.map(photo =>
  [wine.slug+'/'+photo.file,'positive'])));
const labelOf = (slug,file) => labels.get(slug+'/'+file) || null;
const candidate = (slug,score) => ({slug,score});
const row = (query_id,candidates) => ({query_id,candidates});
const ids = rows => rows.map(row=>row.query_id);
const rows = [
  row('many',[candidate('a',.9),candidate('c',.7),candidate('d',.6)]),
  row('few',[candidate('b',.8),candidate('d',.5),candidate('a',.4)]),
  row('close',[candidate('d',.7),candidate('b',.6999),candidate('a',.4)])
];
"""


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class DrawerSortingTest(unittest.TestCase):
    def run_js(self, check, setup=SETUP, render=False):
        result = subprocess.run(["node", "-e", setup + CANDIDATES + SORT
                                 + (RENDER if render else "") + check],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_top_one_uses_current_positive_labels(self):
        self.run_js("""
assert.deepStrictEqual(ids(sortDrawerResults(rows,'pos1')),['few','close','many']);
// A new positive label changes priority without a new run.
ROWS[1].photos = [{file:'new-1'},{file:'new-2'},{file:'new-3'}];
for(const photo of ROWS[1].photos) labels.set('b/'+photo.file,'positive');
assert.deepStrictEqual(ids(sortDrawerResults(rows,'pos1')),['close','many','few']);
""")

    def test_top_three_totals_distinct_candidates(self):
        self.run_js("""
assert.deepStrictEqual(ids(sortDrawerResults(rows,'pos3')),['few','close','many']);
const duplicate = row('duplicate',[candidate('b',.9),candidate('b',.8),
  candidate('a',.7),candidate('c',.6)]);
assert.equal(drawerResultSortValue(duplicate,'pos3',new Map([['a',2],['b',0],['c',4]])),6);
""")

    def test_best_and_worst_use_first_candidate_score(self):
        self.run_js("""
assert.deepStrictEqual(ids(sortDrawerResults(rows,'score_desc')),['many','few','close']);
assert.deepStrictEqual(ids(sortDrawerResults(rows,'score_asc')),['close','few','many']);
rows[1].candidates[1].score = .99;
assert.deepStrictEqual(ids(sortDrawerResults(rows,'score_desc')),['many','few','close']);
""")

    def test_near_ties_use_full_precision_absolute_gap(self):
        self.run_js("""
assert.deepStrictEqual(ids(sortDrawerResults(rows,'gap')),['close','many','few']);
const reversed = row('reversed',[candidate('a',.5),candidate('b',.50001)]);
assert.equal(sortDrawerResults([...rows,reversed],'gap')[0],reversed);
""")

    def test_zero_scores_and_empty_catalogue_wines_are_valid(self):
        self.run_js("""
const zero = row('zero',[candidate('b',0),candidate('a',0),candidate('d',-.1)]);
const negative = row('negative',[candidate('a',-.2),candidate('b',-.3),candidate('c',-.4)]);
assert.deepStrictEqual(ids(sortDrawerResults([zero,negative],'score_asc')),['negative','zero']);
assert.deepStrictEqual(ids(sortDrawerResults([zero,negative],'pos1')),['zero','negative']);
assert.equal(sortDrawerResults([zero,negative],'gap')[0],zero);
""")

    def test_unavailable_candidates_and_scores_sort_last(self):
        self.run_js("""
const missing = row('missing',[]);
const unknown = row('unknown',[candidate('unknown',.1)]);
const invalid = row('invalid',[candidate('a',null),candidate('b',NaN),candidate('c',Infinity)]);
for(const mode of ['pos1','pos3','score_desc','score_asc','gap']) {
  const input = [missing,...rows];
  assert.equal(sortDrawerResults(input,mode).at(-1),missing,mode);
}
assert.equal(sortDrawerResults([unknown,...rows],'pos1').at(-1),unknown);
assert.equal(sortDrawerResults([unknown,...rows],'pos3').at(-1),unknown);
for(const mode of ['score_desc','score_asc','gap'])
  assert.equal(sortDrawerResults([invalid,...rows],mode).at(-1),invalid);
const one = row('one',[candidate('a',.2)]);
assert.equal(sortDrawerResults([one,...rows],'gap').at(-1),one);
""")

    def test_stable_ties_original_order_and_source_rows_are_preserved(self):
        self.run_js("""
const tied = row('tied',rows[0].candidates.slice());
const input = [tied,rows[0],rows[1]], before=JSON.stringify(input);
for(const mode of ['pos1','pos3','score_desc','score_asc','gap']) {
  const sorted = sortDrawerResults(input,mode);
  assert(sorted.indexOf(tied) < sorted.indexOf(rows[0]),mode);
  assert.equal(JSON.stringify(input),before);
}
assert.strictEqual(sortDrawerResults(input,'run'),input);
assert.strictEqual(sortDrawerResults(input,'unknown-mode'),input);
""")

    def test_count_work_is_linear_and_avoided_for_score_sorts(self):
        self.run_js("""
let calls=0; const original=labels.get.bind(labels);
labels.get=key=>{calls++;return original(key)};
sortDrawerResults(Array.from({length:1000},(_,i)=>rows[i%rows.length]),'pos3');
assert.equal(calls,7);
calls=0; sortDrawerResults(rows,'score_desc');assert.equal(calls,0);
""")

    def test_tag_hash_and_move_checks_stay_before_sorting(self):
        setup = SETUP + r"""
const DRAWER_SLUG='__drawer__',TAG_NONE='~untagged';
const isDrawerRow=row=>row.slug===DRAWER_SLUG;
const drawerFile=row=>row.image_path.slice('__drawer__/'.length);
const photoTags=photo=>photo.tags||[];
const tagFilterMatches=(tags,want)=>!want||tags.includes(want);
const esc=value=>String(value??'');
const drawerCandidateHtml=()=>'';
let want='', mounted=[];
const controls=new Map();
const $=selector=>{
 if(!controls.has(selector))controls.set(selector,{value:'score_desc',textContent:''});
 return controls.get(selector);
};
const renderImageTagFilter=()=>want;
const DRAWER_RESULTS={destroy(){mounted=[]},set(rows){mounted=rows}};
ROWS.push({slug:DRAWER_SLUG,photos:[
 {file:'many.jpg',sha256:'1',tags:['front']},
 {file:'few.jpg',sha256:'2',tags:['back']},
 {file:'close.jpg',sha256:'3',tags:['front']} ]});
for(const [i,item] of rows.entries()){
 item.image_path='__drawer__/'+item.query_id+'.jpg';item.image_sha256=String(i+1);
}
const stale={...rows[0],query_id:'stale',image_sha256:'old'};
const gone={...rows[0],query_id:'gone',image_path:'__drawer__/gone.jpg'};
const DRAWER_VIEW={head:{configuration:'test'},rows:[...rows,stale,gone]};
"""
        self.run_js("""
renderDrawerResults();assert.deepStrictEqual(ids(mounted),['many','few','close']);
want='front';$('#drawer-results-sort').value='score_asc';
renderDrawerResults();assert.deepStrictEqual(ids(mounted),['close','many']);
ROWS.at(-1).photos.shift();
renderDrawerResults();assert.deepStrictEqual(ids(mounted),['close']);
""", setup=setup, render=True)


if __name__ == "__main__":
    unittest.main()
