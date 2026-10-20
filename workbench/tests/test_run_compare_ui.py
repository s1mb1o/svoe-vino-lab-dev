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
const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:true,disabled:false,textContent:'',innerHTML:'',className:'',handlers:{},focus(){document.activeElement=this;},showModal(){this.open=true;},close(){this.open=false;},addEventListener(name,fn){this.handlers[name]=fn;}});return nodes.get(id)};
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
    def run_js(self, check, *, dom=False, dom_text=DOM):
        source = SETUP + (dom_text if dom else "") + (SCRIPT if dom else MODEL)
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

    def test_one_requested_run_takes_the_baseline_from_its_testset(self):
        # The `Compare runs` link of /runs gives `b` alone. The newest run of another test
        # set MUST NOT become the baseline.
        dom = DOM.replace("search:''", "search:'?b=m1'").replace(
            "runs:[run('b'),run('a')]",
            "runs:[run('f2',{set:'my-failed-2',started:'2026-10-03'}),run('m1'),"
            "run('m2',{started:'2026-09-30'})]")
        self.run_js(
            "await settle();assert.equal(node('#testset').value,'my');"
            "assert.equal(state.b,'m1');assert.equal(state.a,'m2');",
            dom=True, dom_text=dom,
        )

    def test_automatic_run_defaults_do_not_inherit_common_case_opt_in(self):
        self.run_js(
            "await settle();state.a='';state.b='';state.common=true;choices();assert.equal(state.common,false);",
            dom=True,
        )

    def test_new_testset_uses_full_loaded_filter_without_pagination(self):
        self.run_js(
            """await settle();state.offset=50;await load();assert.equal(node('#new-testset').disabled,false);
node('#new-testset').handlers.click();await settle();const params=new URLSearchParams(requests.at(-1).split('?')[1]);
assert.equal(params.get('group'),'differences');assert.equal(params.get('source'),'b');assert(!params.has('offset'));assert(!params.has('limit'));assert.equal(node('#new-dialog').open,true);""",
            dom=True,
        )

    def test_pending_search_disables_creation_of_old_filter(self):
        self.run_js(
            "await settle();node('#search').value='new';node('#search').handlers.input();assert.equal(node('#new-testset').disabled,true);clearTimeout(searchTimer);",
            dom=True,
        )

    def test_new_preview_source_race_and_cancel(self):
        self.run_js(
            """await settle();let release;read=()=>new Promise(resolve=>release=resolve);node('#new-testset').handlers.click();await settle();
read=async()=>({ok:true,json:async()=>({source:'source-a',selected:2,photos:2,photo_comments:0,can_create:true,token:'a',name:'a-1'})});
node('#new-source').value='a';await node('#new-source').handlers.change();release({ok:true,json:async()=>({source:'old-b',selected:99,photos:99,can_create:true,token:'b'})});await settle();
assert(node('#new-preview').textContent.includes('source-a'));assert.equal(newPreview.source,'a');node('#new-cancel').handlers.click();assert.equal(node('#new-dialog').open,false);""",
            dom=True,
        )

    def test_new_testset_submit_keeps_frozen_selection_and_shows_link(self):
        self.run_js(
            """await settle();read=async()=>({ok:true,json:async()=>({source:'my',selected:120,photos:121,support_photos:1,photo_comments:3,can_create:true,token:'token',name:'my-1'})});
node('#new-testset').handlers.click();await settle();assert(node('#new-preview').textContent.includes('120 filtered cases'));assert(node('#new-preview').textContent.includes('additional positive'));
state.group='both_fail';state.q='changed';let submitted;read=async(url,options)=>{submitted=JSON.parse(options.body);return {ok:true,json:async()=>({set:'my-1',selected:120,photos:121})}};
await node('#new-form').handlers.submit({preventDefault(){}});assert.equal(submitted.group,'differences');assert.equal(submitted.q,'');assert.equal(submitted.token,'token');assert(node('#status').innerHTML.includes('/testset?set=my-1'));""",
            dom=True,
        )

    def test_conflicts_and_failed_preview_disable_create(self):
        self.run_js(
            """await settle();read=async()=>({ok:true,json:async()=>({source:'my',selected:2,photos:1,photo_comments:0,conflicts:1,conflict_examples:['gone'],can_create:false,token:'x',name:'my-1'})});
node('#new-testset').handlers.click();await settle();assert.equal(node('#new-create').disabled,true);assert(node('#new-error').textContent.includes('gone'));
read=async()=>({ok:false,status:409,json:async()=>({error:'Source unavailable'})});await previewNew();assert.equal(node('#new-create').disabled,true);assert.equal(node('#new-error').textContent,'Source unavailable');""",
            dom=True,
        )

    def test_search_input_invalidates_inflight_comparison_before_debounce(self):
        self.run_js(
            """await settle();let release;read=()=>new Promise(resolve=>release=resolve);const pending=load();await settle();
node('#search').value='new filter';node('#search').handlers.input();release({ok:true,json:async()=>answer});await pending;
assert.equal(node('#new-testset').disabled,true);assert.equal(loadedSelection,null);clearTimeout(searchTimer);""",
            dom=True,
        )

    def test_stale_creation_needs_refresh_and_closed_dialog_keeps_error_visible(self):
        self.run_js(
            """await settle();read=async()=>({ok:true,json:async()=>({source:'my',selected:2,photos:2,can_create:true,token:'token',name:'my-1'})});
node('#new-testset').handlers.click();await settle();read=async()=>{node('#new-dialog').close();return {ok:false,status:409,json:async()=>({error:'Source changed. Refresh the preview.'})}};
await node('#new-form').handlers.submit({preventDefault(){}});assert.equal(newPreview,null);assert.equal(node('#new-create').disabled,true);
assert.equal(node('#status').className,'error');assert(node('#status').textContent.includes('Refresh the preview'));""",
            dom=True,
        )

    def test_name_collision_keeps_preview_and_allows_rename(self):
        self.run_js(
            """await settle();read=async()=>({ok:true,json:async()=>({source:'my',selected:2,photos:2,can_create:true,token:'token',name:'my-1'})});
node('#new-testset').handlers.click();await settle();read=async()=>({ok:false,status:409,json:async()=>({error:'The testset my-1 already exists.'})});
await node('#new-form').handlers.submit({preventDefault(){}});assert(newPreview);assert.equal(node('#new-create').disabled,false);assert(node('#new-error').textContent.includes('already exists'));""",
            dom=True,
        )

    def test_stale_preview_moves_focus_to_refresh(self):
        self.run_js(
            """await settle();read=async()=>({ok:true,json:async()=>({source:'my',selected:2,photos:2,can_create:true,token:'token',name:'my-1'})});
node('#new-testset').handlers.click();await settle();read=async()=>({ok:false,status:409,json:async()=>({error:'Source changed. Refresh the preview.'})});
await node('#new-form').handlers.submit({preventDefault(){}});assert.equal(document.activeElement,node('#new-refresh'));""",
            dom=True,
        )

    def test_inflight_create_blocks_reopen_and_success_clears_error_style(self):
        self.run_js(
            """await settle();read=async()=>({ok:true,json:async()=>({source:'my',selected:2,photos:2,can_create:true,token:'token',name:'my-1'})});
node('#new-testset').handlers.click();await settle();let release;read=()=>new Promise(resolve=>release=resolve);
const pending=node('#new-form').handlers.submit({preventDefault(){}});await settle();node('#new-dialog').close();node('#new-testset').handlers.click();assert.equal(node('#new-dialog').open,false);
node('#status').className='error';release({ok:true,json:async()=>({set:'my-1',selected:2,photos:2})});await pending;assert.equal(node('#status').className,'');assert(node('#status').innerHTML.includes('Created'));""",
            dom=True,
        )
