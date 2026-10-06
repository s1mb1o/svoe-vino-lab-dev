"""Exercise the actual page loaders with deliberately reordered success and failure replies."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const acorn=require(require.resolve('acorn',{paths:[process.argv[1]+'/webui']}));
const kind=process.argv[2], mode=process.argv[3];
const names={embedding:['loadEntry','ENTRY_REQUEST','ENTRY_ABORT'],clusters:['loadDetail','DETAIL_REQUEST','DETAIL_ABORT'],testset:['load','LOAD_REQUEST','LOAD_ABORT']}[kind];
const html=fs.readFileSync(process.argv[1]+`/workbench/pipeline/pages/${kind}.html`,'utf8');
const source=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes('async function '+names[0]+'('));
const code=acorn.parse(source,{ecmaVersion:'latest'}).body.filter(n=>n.type==='FunctionDeclaration' && names.includes(n.id.name) || n.type==='VariableDeclaration' && n.declarations.some(d=>names.includes(d.id.name))).map(n=>source.slice(n.start,n.end)).join('\n');
const queue=[], nodes={}, events=[], noop=()=>{};
const ctx=vm.createContext({AbortController,encodeURIComponent,Map,Set,Date,Promise});
ctx.$=s=>nodes[s]||(nodes[s]={textContent:'',innerHTML:'',value:'',options:[],insertAdjacentHTML:noop});
ctx.esc=String;ctx.entryOf=name=>({name});
for(const n of ['buttons','showSource','setMessage','updateUrl','renderTagOptions','syncDrawerRuns','scheduleAutotag','readViewFromUrl','openFromHash'])ctx[n]=noop;
ctx.photoTotal=()=>0;
ctx.render=()=>events.push(vm.runInContext(kind==='testset'?'SET':'DATA?.embedding.name',ctx));
ctx.getJson=ctx.request=ctx.fetch=(url,options)=>new Promise((resolve,reject)=>queue.push({url,options,resolve,reject}));
let releaseSources;
ctx.loadClusterSources=()=>new Promise(resolve=>releaseSources=resolve);
vm.runInContext("let NAME='A',DATA=null,SET='original',SETS=[],ROWS=[],GROUPS={},V={},TAGS={},TAG_NAMES=[],TOTAL=0,EDITED_AT=null;const WC_DRAFT=new Map(),NEW_SET='(new)',URL_VIEW=false,HEADER={};",ctx);
vm.runInContext(code,ctx);
function start(name,first=false){vm.runInContext(`NAME=${JSON.stringify(name)}`,ctx);return vm.runInContext(kind==='testset'?`load(${JSON.stringify(name)},${first})`:`${names[0]}()`,ctx);}
function reply(index,name){const q=queue[index];q.resolve(kind==='testset'?{ok:true,json:async()=>({set:name,rows:[],sets:[]})}:{embedding:{name}});}
(async()=>{
 const old=start('A',mode==='sources');
 if(mode==='sources'){reply(0,'A');await new Promise(r=>setImmediate(r));}
 const b=start('B');
 assert(queue[0].options.signal.aborted);
 let latest=b, target='B';
 if(mode==='aba'){latest=start('A');target='A';assert(queue[1].options.signal.aborted);}
 reply(queue.length-1,target);await latest;
 if(mode==='sources'){releaseSources();await old;}
 else if(mode==='error'){queue[0].reject(new Error('old error'));await old;}
 else {reply(0,'obsolete A');await old;}
 if(mode==='aba'){queue[1].reject(new Error('obsolete B'));await b;}
 assert.equal(vm.runInContext(kind==='testset'?'SET':'DATA.embedding.name',ctx),target);
 assert.equal(events.at(-1),target);
 assert(!Object.values(nodes).some(n=>n.textContent.includes('old error')||n.innerHTML.includes('old error')));
 if(kind==='testset'){vm.runInContext("WC_DRAFT.set('draft','unsaved')",ctx);assert.equal(vm.runInContext('WC_DRAFT.size',ctx),1);}
})().catch(e=>{console.error(e);process.exitCode=1});
'''

@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class PageRequestsTest(unittest.TestCase):
    def test_old_success_and_error_and_a_b_a(self):
        for page in ('embedding', 'clusters', 'testset'):
            for mode in ('success', 'error', 'aba'):
                with self.subTest(page=page, mode=mode):
                    subprocess.run(['node', '-e', SCRIPT, str(ROOT), page, mode], check=True,
                                   capture_output=True, text=True)

    def test_initial_testset_sources_cannot_resume_into_a_new_set(self):
        subprocess.run(['node', '-e', SCRIPT, str(ROOT), 'testset', 'sources'], check=True,
                       capture_output=True, text=True)

    def test_a_rule_poll_cannot_update_a_new_cluster_selection(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1]+'/workbench/pipeline/pages/clusters.html','utf8');
const start=html.indexOf('async function watchRule('),end=html.indexOf('\nfunction openHash()',start);
let resolve,reject,requests=0,updates=0,now=0;
const ctx=vm.createContext({Date:{now:()=>now},Promise,setTimeout:fn=>fn(),
 noteStatus:()=>updates++,request:()=>{requests++;return new Promise((a,b)=>{resolve=a;reject=b})},ruleOf:()=>({stale:false}),
 document:{querySelector:()=>{throw Error('stale DOM update')}},ruleHtml:()=>'',ruleTextHtml:()=>''});
vm.runInContext("let NAME='A',SPACE='full',DETAIL_REQUEST=1,DATA={name:'current'};",ctx);
vm.runInContext(html.slice(start,end),ctx);
(async()=>{
 const pending=vm.runInContext("watchRule('key','before','log')",ctx);
 await new Promise(r=>setImmediate(r));assert.equal(requests,1);
 vm.runInContext("NAME='B';DETAIL_REQUEST++",ctx);now=300001;
 if(process.argv[2]==='failure')reject(Error('old poll'));else resolve({name:'obsolete'});
 await pending;
 assert.equal(vm.runInContext('DATA.name',ctx),'current');assert.equal(updates,1);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        for mode in ('success','failure'):
            subprocess.run(['node','-e',script,str(ROOT),mode],check=True,capture_output=True,text=True)
