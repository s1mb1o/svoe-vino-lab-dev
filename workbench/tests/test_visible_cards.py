"""Exercise viewport mounting, unchanged rerenders, focus, drag, and retained slots."""
from pathlib import Path
import shutil
import subprocess
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'pipeline/pages/visible_cards.js'
HARNESS=r'''
const assert=require('assert');let observer, calls=0;
class Slot {
 constructor(){this.dataset={};this.style={};this.children=[];this.events={};this.html='';this.height=317;this.focus=null;this.drag=false;this.details=false;}
 contains(element){return !!element && element===this.focus;}
 querySelector(){return this.drag||this.details?{}:null;}
 getBoundingClientRect(){return {height:this.height};}
 replaceChildren(...children){this.children=children;this.html='';this.mutations=(this.mutations||0)+1;}
 addEventListener(n,fn){this.events[n]=fn;}
 set innerHTML(html){this.html=html;this.children=html?[{html,slot:this}]:[];}
 get innerHTML(){return this.html;}
 get firstElementChild(){return this.children[0]||null;}
}
const document={activeElement:null,createElement:()=>new Slot()};
const queueMicrotask=fn=>fn();
const IntersectionObserver=class {
 constructor(cb,options){this.cb=cb;this.options=options;this.targets=new Set();observer=this;}
 observe(slot){this.targets.add(slot);}disconnect(){this.targets.clear();}
};
const container=new Slot();
const rows=Array.from({length:10000},(_,n)=>({key:'photo-'+n,text:'photo '+n}));
const render=row=>{calls++;return `<article>${row.text}</article>`};
const controller=VisibleCards.create(container,{root:container});
controller.set(rows,r=>r.key,render);
assert.equal(calls,0);assert.equal(container.children.length,10000);
const enter=s=>observer.cb([{target:s,isIntersecting:true}]),exit=s=>observer.cb([{target:s,isIntersecting:false}]);
const first=container.children[0];enter(first);assert.equal(calls,1);
const child=first.firstElementChild,mutations=container.mutations;
controller.set(rows,r=>r.key,render);assert.strictEqual(first.firstElementChild,child);assert.equal(container.mutations,mutations);
exit(first);assert(!first.firstElementChild);assert.equal(first.style.height,'317px');
enter(first);first.focus={};document.activeElement=first.focus;exit(first);assert(first.firstElementChild);
first.focus=null;document.activeElement=null;first.drag=true;exit(first);assert(first.firstElementChild);
first.drag=false;first.details=true;exit(first);assert(first.firstElementChild);
first.details=false;controller.sweep();assert(!first.firstElementChild);
const last=controller.ensure('photo-9999');assert(last);assert.equal(calls,3);
rows[9999].text='changed';controller.refresh('photo-9999');assert(container.children[9999].firstElementChild.html.includes('changed'));
const oldObserver=observer,oldSlot=container.children[1];
controller.set(rows.slice(9900),r=>r.key,render);const count=calls;
oldObserver.cb([{target:oldSlot,isIntersecting:true}]);assert.equal(calls,count);
controller.set([],r=>r.key,render,'empty');assert.equal(container.innerHTML,'empty');assert.equal(observer.targets.size,0);
controller.destroy();assert.equal(container.children.length,0);
'''

@unittest.skipUnless(shutil.which('node'),'Node.js required')
class VisibleCardsTest(unittest.TestCase):
    def run_js(self,code):
        subprocess.run(['node','-e',SOURCE.read_text()+'\n'+code],check=True,capture_output=True,text=True)

    def test_mount_reuse_eviction_pin_refresh_removal_and_stale_observer(self):
        self.run_js(HARNESS)

    def test_initial_cards_start_before_observer_and_keep_scroll_position(self):
        code=HARNESS[:HARNESS.index('const controller=VisibleCards.create')]
        code+="""
const controller=VisibleCards.create(container,{root:container,initial:4});
controller.set(rows,r=>r.key,render);assert.equal(calls,4);
const first=container.children[0].firstElementChild;
observer.cb([{target:container.children[0],isIntersecting:true}]);
assert.strictEqual(container.children[0].firstElementChild,first);assert.equal(calls,4);
controller.destroy();container.scrollTop=5000;calls=0;
controller.set(rows,r=>r.key,render);assert.equal(calls,0);
"""
        self.run_js(code)

    def test_missing_observer_renders_every_card(self):
        code=HARNESS[:HARNESS.index('const IntersectionObserver=class')]+HARNESS[HARNESS.index('const container=new Slot();'):HARNESS.index('controller.set(rows,r=>r.key,render);')]
        code+='controller.set(rows,r=>r.key,render);assert.equal(calls,10000);'
        self.run_js(code)

    def test_real_pages_wire_the_shared_controller(self):
        for page,marker in [('embedding','ENTRY_CARDS.set(rows'),('testset','DRAWER_CARDS.set(shown')]:
            source=(SOURCE.parent/(page+'.html')).read_text()
            self.assertIn('/* VISIBLE_CARDS_JS */',source)
            self.assertIn(marker,source)
