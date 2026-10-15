"""Exercise the rendered comparison and filter behavior in JavaScript."""

from pathlib import Path
import shutil
import subprocess
import unittest

SOURCE = (
    Path(__file__).resolve().parents[1] / "pipeline/pages/attribute_comparison.js"
).read_text()
SETUP = r"""
const assert=require('node:assert/strict');
const handlers={},calls=[],nodes=new Map();
const document={addEventListener:(name,fn)=>handlers[name]=fn,querySelectorAll:()=>[]};
const $=selector=>{if(!nodes.has(selector))nodes.set(selector,{value:'all',textContent:''});return nodes.get(selector);};
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const shaOfUrl=url=>/\/([a-f0-9]{64})\./.exec(url||'')?.[1]||'';
const setTimeout=fn=>{calls.push('poll');return 1};
const renderCard=slug=>calls.push(slug),render=()=>calls.push('render'),changeAdvancedFilter=()=>calls.push('filter'),saveHeader=()=>{};
const showImagePreview=(slug,kind)=>calls.push([slug,kind]);
let fetch=async()=>{throw Error('unexpected request')};
const row={field:'vintage',label:'Vintage',metadata:['2021'],image:['2022'],evidence:'<script>alert(1)</script>',image_state:'observed',result:'conflict',image_disagreement:false};
const record={slug:'wine',name:'Wine',main_image_original_url:'/images/main/'+ 'a'.repeat(64)+'.jpg',_tags:[]};
record._attribute_comparison={metadata_inputs:['Wine','','','','',[],''],source:'Main image',sha256:'a'.repeat(64),state:'ready',rows:[row],conflicts:1,additional:0};
let DATA={attribute_comparison:true,attribute_counts:{worker_active:true,paused:false},records:[record]};
"""


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class AttributeUiTest(unittest.TestCase):
    def run_js(self, check):
        result = subprocess.run(
            [
                "node",
                "-e",
                SETUP
                + SOURCE
                + "\n(async()=>{"
                + check
                + "})().catch(e=>{console.error(e);process.exitCode=1});",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_result_column_and_evidence_are_escaped(self):
        self.run_js(
            "const html=attributeTable(record);assert.match(html,/<th scope=\"col\">Result<\\/th>/);assert.match(html,/&lt;script>/);assert(!html.includes('<script>'));assert.match(html,/1 conflict/);"
        )

    def test_rendering_does_not_start_inference(self):
        self.run_js(
            "record._attribute_comparison.state='pending';attributeTable(record);assert(calls.includes('poll'));assert(!calls.includes('fetch'));"
        )

    def test_conflict_filter_and_field_selection(self):
        self.run_js(
            "$('#attribute-filter').value='conflict';assert(inAttributeView(record));$('#attribute-field').value='grape';assert(!inAttributeView(record));$('#attribute-filter').value='additional';$('#attribute-field').value='all';assert(!inAttributeView(record));"
        )

    def test_image_disagreement_is_separate_from_metadata_conflict(self):
        self.run_js(
            "row.result='match';row.image_disagreement=true;$('#attribute-filter').value='conflict';assert(!inAttributeView(record));$('#attribute-filter').value='images_differ';assert(inAttributeView(record));"
        )

    def test_changed_metadata_or_image_invalidates_the_comparison(self):
        self.run_js(
            "record.name='Changed';assert.equal(attributeOf(record),null);record.name='Wine';record._patch_url='/images/patched/'+'b'.repeat(64)+'.jpg';assert.equal(attributeOf(record),null);"
        )

    def test_only_explicit_refresh_queues_work(self):
        self.run_js(
            "fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>({queued:1,message:'queued'})};};refreshAttributes=async()=>{};await queueAttributes({sha256:'a'.repeat(64)},{disabled:false});assert.equal(calls[0][0],'/api/dataset-attributes');assert.equal(calls[0][1].method,'POST');"
        )

    def test_paused_and_inactive_worker_do_not_poll(self):
        self.run_js(
            "DATA.attribute_counts.paused=true;record._attribute_comparison.state='pending';attributeTable(record);assert(!calls.includes('poll'));DATA.attribute_counts.paused=false;DATA.attribute_counts.worker_active=false;attributeTable(record);assert(!calls.includes('poll'));"
        )

    def test_updating_table_retains_raw_metadata(self):
        self.run_js(
            "record.grapes='Muscat';record.category='Розовое';record.name='Changed';const html=attributeTable(record);assert.match(html,/Muscat/);assert.match(html,/Розовое/);assert.match(html,/>Result</);"
        )

    def test_filter_refresh_preserves_active_editor(self):
        self.run_js(
            "ROWS=[record];const card={id:'wine',querySelector:()=>null};document.querySelectorAll=()=>[card];keepCardMounted=()=>true;applyView=()=>{ROWS=[]};$('#attribute-filter').value='conflict';const fresh={...record,_attribute_comparison:{...record._attribute_comparison,rows:[{...row,result:'match'}]}};fetch=async()=>({ok:true,json:async()=>({records:[fresh],attribute_counts:{worker_active:false}})});await refreshAttributes();assert(!calls.includes('render'));"
        )

    def test_stale_cached_heartbeat_does_not_keep_polling(self):
        self.run_js(
            "DATA.attribute_counts.worker_active=true;DATA.attribute_counts.heartbeat_at='2000-01-01T00:00:00Z';record._attribute_comparison.state='pending';attributeTable(record);assert(!calls.includes('poll'));"
        )

    def test_initial_paused_label_matches_resume_action(self):
        self.run_js(
            "DATA.attribute_counts.paused=true;updateAttributeQueueControls();assert.equal($('#attribute-pause').textContent,'Resume image facts');let body;queueAttributes=async value=>{body=value};const button={disabled:false};handlers.click({target:{closest:s=>s==='#attribute-pause'?button:null}});assert.deepEqual(body,{action:'resume'});"
        )

    def test_queue_action_waits_for_older_snapshot_then_refreshes(self):
        self.run_js(
            "ROWS=[record];let release;const old=new Promise(resolve=>{release=resolve});let gets=0;"
            "fetch=async(url)=>url==='/api/dataset-attributes'?{ok:true,json:async()=>({message:'resumed'})}:"
            "{ok:true,json:async()=>{gets++;if(gets===1){await old;return {records:[record],attribute_counts:{paused:true}}}"
            "return {records:[record],attribute_counts:{paused:false,worker_active:true}}}};"
            "const first=refreshAttributes();const action=queueAttributes({action:'resume'},{disabled:false});"
            "await new Promise(resolve=>global.setTimeout(resolve,0));assert.equal(gets,1);release();"
            "await Promise.all([first,action]);assert.equal(gets,2);assert.equal(DATA.attribute_counts.paused,false);"
            "assert.equal($('#attribute-pause').textContent,'Pause image facts');"
        )
