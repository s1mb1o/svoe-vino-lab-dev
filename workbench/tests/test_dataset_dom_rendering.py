"""Check the actual viewport card controller without a browser or a service."""
from pathlib import Path
import shutil
import subprocess
import unittest

PAGE = Path(__file__).resolve().parents[1] / 'pipeline/pages/dataset.html'
ROOT = PAGE.parents[3]

SCRIPT = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const acorn = require(require.resolve('acorn', {paths: [process.argv[2] + '/webui']}));
const source = [...fs.readFileSync(process.argv[1], 'utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m=>m[1]).find(s=>s.includes('function applyView()'));
const functions = new Set(['esc','keepCardMounted','deferredCardHtml','replaceObservedCard',
  'mountCard','observeCards','render','renderCard','scrollToCard','openSimilarCard']);
const variables = new Set(['CARD_HEIGHTS','CARD_RECORDS','CARD_OBSERVER','DEFER_CARDS']);
const code = acorn.parse(source,{ecmaVersion:'latest'}).body.filter(n=>
  n.type==='FunctionDeclaration' && functions.has(n.id.name) ||
  n.type==='VariableDeclaration' && n.declarations.some(d=>variables.has(d.id.name)))
  .map(n=>source.slice(n.start,n.end)).join('\n');
let list, observer, fullCalls=0;
class Card {
  constructor(html) {this.html=html; this.id=/id="([^"]+)"/.exec(html)[1];
    this.deferred=html.includes('data-deferred'); this.isConnected=true; this.open=false;}
  hasAttribute(key) {return key==='data-deferred' && this.deferred;}
  contains(element) {return element===this.focus;}
  querySelector(selector) {return selector==='details[open]' && this.open ? {} : null;}
  matches(selector) {return selector==='article.wine';}
  replaceWith(next) {const i=list.children.indexOf(this); assert(i>=0); list.children[i]=next; next.isConnected=true; this.isConnected=false;}
  remove() {list.children=list.children.filter(c=>c!==this); this.isConnected=false;}
  scrollIntoView() {this.scrolled=true;}
  insertAdjacentHTML(where,html) {assert.equal(where,'afterend'); list.children.splice(list.children.indexOf(this)+1,0,new Card(html));}
}
function parse(html) {return [...html.matchAll(/<article\b[\s\S]*?<\/article>/g)].map(m=>new Card(m[0]));}
list = {children:[], set innerHTML(html) {for(const card of this.children) card.isConnected=false;
  this.children=parse(html);}, get innerHTML() {return this.children.map(c=>c.html).join('');}};
const document = {activeElement:{}, getElementById: id=>list.children.find(c=>c.id===id),
  createElement(tag) {assert.equal(tag,'template'); const t={content:{}};
    Object.defineProperty(t,'innerHTML',{set:html=>t.content.firstElementChild=parse(html)[0]}); return t;}};
const ctx = vm.createContext({document, DATA:{records:[]}, ROWS:[], CODE_USERS:null, EMPTY_VIEW:'empty',
  $:s=>{assert.equal(s,'#list');return list;}, recordHtml:r=>{fullCalls++;return `<article class="wine" id="${r.slug}">${r.name}</article>`},
  renderHead:()=>{}, inStateView:r=>r.state!=='Removed', inTypeView:()=>true,
  applyView:()=>ctx.ROWS=ctx.DATA.records.filter(r=>r.state!=='Removed'), requestAnimationFrame:f=>f()});
if(process.argv[3]!=='fallback') ctx.IntersectionObserver=class {
  constructor(callback,options) {this.callback=callback;this.options=options;this.observed=new Set();observer=this;}
  observe(card) {this.observed.add(card);} unobserve(card) {this.observed.delete(card);} disconnect() {this.observed.clear();}};
for(const name of ['PENDING_PATCHES','PENDING_ALTERNATIVES','DRAFT_GTINS','DRAFT_BARCODES',
 'DRAFT_QR_URLS','DRAFT_ATLAS_BINDINGS','DRAFT_SIMILAR','DRAFT_VINTAGES','DRAFT_TAGS','DRAFT_COMMENTS','DRAFT_NAMES']) ctx[name]=new Map();
vm.runInContext(code,ctx);
ctx.DATA.records=Array.from({length:2133},(_,i)=>({slug:'wine-'+i,name:'name '+i}));
ctx.render(); assert.equal(list.children.length,2133);
if(process.argv[3]==='fallback') {assert.equal(fullCalls,2133);process.exit(0);}
assert.equal(fullCalls,0);assert.equal(observer.observed.size,2133);
const enter=card=>observer.callback([{target:card,isIntersecting:true,boundingClientRect:{height:530}}]);
const exit=card=>observer.callback([{target:card,isIntersecting:false,boundingClientRect:{height:530}}]);
if(process.argv[3]==='mount') {
  const stale=list.children[0]; enter(stale);
  assert.equal(fullCalls,1);assert(!list.children[0].deferred);assert(!observer.observed.has(stale));
  exit(list.children[0]); assert(list.children[0].deferred);assert(list.children[0].html.includes('height:530px'));
  ctx.scrollToCard('wine-2132');assert(!list.children[2132].deferred);assert(list.children[2132].scrolled);
  const calls=fullCalls;ctx.render();enter(stale);assert.equal(fullCalls,calls); // ignore an old observer reply
  assert.equal(new Set(list.children.map(c=>c.id)).size,2133);
} else if(process.argv[3]==='edit') {
  enter(list.children[0]); const card=list.children[0];card.focus=document.activeElement;exit(card);
  assert.strictEqual(list.children[0],card);card.focus=null;card.open=true;exit(card);assert.strictEqual(list.children[0],card);
  card.open=false;ctx.DRAFT_NAMES.set(card.id,'unsaved');exit(card);assert.strictEqual(list.children[0],card);
  ctx.render(); assert.strictEqual(list.children[0],card); assert(card.isConnected);
  ctx.DRAFT_NAMES.clear();ctx.PENDING_PATCHES.set(card.id,{file:{}});exit(card);assert.strictEqual(list.children[0],card);
  ctx.PENDING_PATCHES.clear();exit(card);assert(list.children[0].deferred);
} else if(process.argv[3]==='update') {
  ctx.DATA.records[100].name='updated';ctx.renderCard('wine-100');
  assert(list.children[100].deferred);assert(list.children[100].html.includes('updated'));assert.equal(fullCalls,0);
  enter(list.children[100]);ctx.renderCard('wine-100');assert.equal(fullCalls,2);
  ctx.DATA.records[100].state='Removed';ctx.renderCard('wine-100');assert.equal(list.children.length,2132);
  const newRecord={slug:'hidden-wine',name:'Hidden'};ctx.DATA.records.push(newRecord);
  ctx.openSimilarCard('wine-0','hidden-wine');assert.equal(list.children[1].id,'hidden-wine');assert(list.children[1].scrolled);
}
'''


class DatasetDomRenderingTest(unittest.TestCase):
    def check_scenario(self, scenario):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node is required for page behavior checks')
        result = subprocess.run([node, '-e', SCRIPT, str(PAGE), str(ROOT), scenario],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_viewport_mount_eviction_deep_link_and_stale_observer(self):
        self.check_scenario('mount')

    def test_editors_focus_details_and_pending_files_stay_mounted(self):
        self.check_scenario('edit')

    def test_single_card_update_removal_and_hidden_similar_wine(self):
        self.check_scenario('update')

    def test_browser_without_intersection_observer_renders_every_card(self):
        self.check_scenario('fallback')


if __name__ == '__main__':
    unittest.main()
