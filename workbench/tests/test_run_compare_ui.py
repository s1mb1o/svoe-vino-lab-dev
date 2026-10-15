"""Check comparison rendering and asynchronous page controls with Node.js."""

from pathlib import Path
import shutil
import subprocess
import unittest

PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/run_compare.html"
SCRIPT = PAGE.read_text().split("<script>", 1)[1].split("</script>", 1)[0]
MODEL = SCRIPT[: SCRIPT.index("/* Page state uses")]
SETUP = r"""
const assert=require('node:assert/strict');
const run=(id,extra={})=>({id,set:'my',configuration:id,started:'2026-10-01',finished:'2026-10-02',queries:4,...extra});
const side={status:'pass',label:'positive',truth:['wine-a'],outcome:'hit',candidates:[{slug:'wine-a',rank:1,score:.8}],rank_of_truth:1,latency_ms:100,inspect_url:'/runs#r/wine-a/image.jpg'};
const pair={image_sha256:'a'.repeat(64),image_path:'wine-a/image.jpg',group:'improvements',a:{...side,status:'fail'},b:side};
"""
DOM = r"""
const nodes=new Map(),requests=[];
const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:true,disabled:false,textContent:'',innerHTML:'',className:'',handlers:{},focus(){document.activeElement=this;},addEventListener(name,fn){this.handlers[name]=fn;}});return nodes.get(id)};
const document={body:{},activeElement:null,querySelector:selector=>selector==='#common'&&!node('#compatibility').innerHTML.includes('id="common"')?null:node(selector)};
const location={search:'',pathname:'/runs/compare'};let lastURL='';
const history={replaceState:(a,b,url)=>{lastURL=url}};
const answer={a:run('a'),b:run('b'),compatibility:{exact:true,status:'exact',a_cases:4,b_cases:4,unchanged:4,changed:0,only_a:0,only_b:0},comparison_enabled:true,common:false,warnings:[],counts:{differences:2,regressions:1,improvements:1,both_succeed:1,both_fail:1,all:4},rows:[pair],total:2};
let read=async()=>({ok:true,json:async()=>answer});
let fetch=async(url,options)=>{requests.push(url);return url==='/api/runs'?{ok:true,json:async()=>({runs:[run('b'),run('a')]})}:read(url,options)};
const settle=async()=>{for(let i=0;i<20;i++)await Promise.resolve()};
"""


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class ComparisonUiTest(unittest.TestCase):
    def run_js(self, check, *, dom=False):
        source = SETUP + (DOM if dom else "") + (SCRIPT if dom else MODEL)
        result = subprocess.run(
            [
                "node",
                "-e",
                source
                + "\n(async()=>{"
                + check
                + "})().catch(e=>{console.error(e);process.exitCode=1});",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_filter_and_four_groups(self):
        self.run_js(
            "assert.equal(RunCompare.parameters({a:'a',b:'b'}).get('group'),'differences');for(const key of ['both_succeed','regressions','improvements','both_fail'])assert(RunCompare.labels[key]);"
        )

    def test_picker_excludes_unfinished_dry_and_drawer_runs(self):
        self.run_js(
            "assert.deepEqual(RunCompare.eligible([run('a'),run('b',{finished:null}),run('c',{dry_run:true}),run('d',{query_scope:'drawer'}),run('e',{set:null})]).map(r=>r.id),['a']);"
        )

    def test_escaping_and_unavailable_image(self):
        self.run_js(
            "const html=RunCompare.row({...pair,image_path:'<img onerror=evil()>',a:{...side,truth:['<script>']},b:{...side,truth:['<script>']}});assert(!html.includes('<script>'));assert(!html.includes('<img onerror'));assert(html.includes('&lt;script&gt;'));assert(html.includes('Image unavailable'));"
        )

    def test_changed_annotations_are_visible_on_both_sides(self):
        self.run_js(
            "const html=RunCompare.row({...pair,group:'not_compared',reason:'Expected answers changed',a:{...side,truth:['old']},b:{...side,truth:['new']}});assert(html.includes('<b>A:</b> old'));assert(html.includes('<b>B:</b> new'));assert(html.includes('Not compared'));"
        )

    def test_success_error_and_no_answer_are_distinct(self):
        self.run_js(
            "const html=RunCompare.row({...pair,a:{...side,status:'error',note:'Timeout',candidates:[]}});assert(html.includes('Error'));assert(html.includes('Timeout'));assert(html.includes('No answer'));assert(html.includes('Success'));assert(html.includes('Inspect steps'));"
        )

    def test_initial_page_compares_differences(self):
        self.run_js(
            "await settle();assert(requests.some(url=>url.includes('group=differences')));assert.equal(state.a,'a');assert.equal(state.b,'b');assert(lastURL.includes('group=differences'));assert.equal(node('#results').hidden,false);",
            dom=True,
        )

    def test_swap_and_group_controls_request_new_comparison(self):
        self.run_js(
            "await settle();node('#swap').handlers.click();await settle();assert.equal(state.a,'b');assert.equal(state.b,'a');node('#groups').handlers.click({target:{closest:()=>({dataset:{group:'regressions'}})}});await settle();assert(requests.at(-1).includes('group=regressions'));",
            dom=True,
        )

    def test_incompatibility_requires_explicit_common_case_selection(self):
        self.run_js(
            "await settle();show({...answer,compatibility:{...answer.compatibility,exact:false,status:'partial',unchanged:3,changed:1},comparison_enabled:false,rows:[],total:0});assert(node('#compatibility').innerHTML.includes('Dataset snapshots differ'));assert(node('#groups').innerHTML.includes('disabled'));node('#common').checked=true;node('#common').handlers.change();await settle();assert.equal(state.common,true);assert(requests.at(-1).includes('common=1'));",
            dom=True,
        )

    def test_changing_run_clears_old_results_and_common_opt_in(self):
        self.run_js(
            "await settle();state.common=true;node('#run-a').value='different';node('#run-a').handlers.change();assert.equal(state.common,false);assert.equal(node('#results').hidden,true);assert.equal(node('#compatibility').hidden,true);",
            dom=True,
        )

    def test_late_response_cannot_replace_newer_selection(self):
        self.run_js(
            "await settle();let release;read=()=>new Promise(resolve=>{release=resolve});const old=load();await settle();node('#run-a').value='new';node('#run-a').handlers.change();read=async()=>({ok:true,json:async()=>({...answer,total:7})});await load();release({ok:true,json:async()=>({...answer,total:99})});await old;assert(node('#status').textContent.includes('7 case(s)'));assert(!node('#status').textContent.includes('99'));",
            dom=True,
        )

    def test_api_failure_clears_stale_results(self):
        self.run_js(
            "await settle();read=async()=>({ok:false,json:async()=>({error:'Snapshot unavailable'})});await load();assert.equal(node('#results').hidden,true);assert.equal(node('#status').textContent,'Snapshot unavailable');",
            dom=True,
        )

    def test_replaced_run_choice_clears_common_case_opt_in(self):
        self.run_js(
            "await settle();state.b='outside';state.common=true;choices();assert.equal(state.common,false);assert.notEqual(state.b,'outside');",
            dom=True,
        )

    def test_group_focus_is_restored_after_the_results_reload(self):
        self.run_js(
            "await settle();const old={dataset:{group:'regressions'}};document.activeElement=old;await load();assert.equal(document.activeElement,node('[data-group=\"regressions\"]'));",
            dom=True,
        )

    def test_disabled_group_does_not_start_a_request(self):
        self.run_js(
            "await settle();const before=requests.length;node('#groups').handlers.click({target:{closest:()=>({disabled:true,dataset:{group:'both_fail'}})}});await settle();assert.equal(requests.length,before);",
            dom=True,
        )

    def test_automatic_run_defaults_do_not_inherit_common_case_opt_in(self):
        self.run_js(
            "await settle();state.a='';state.b='';state.common=true;choices();assert.equal(state.common,false);",
            dom=True,
        )
