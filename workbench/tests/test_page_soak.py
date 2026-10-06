"""Repeat large card filters and navigation; record p95 and post-GC retained memory."""
import json
import shutil
import subprocess
import unittest
from test_visible_cards import SOURCE, HARNESS

SCRIPT=HARNESS[:HARNESS.index('controller.set(rows,r=>r.key,render);')]+r'''
const {performance}=require('perf_hooks');
const times=[],heaps=[];let maxMounted=0,maxSlots=0;
function cycle(n){
 const start=performance.now();
 const view=n%3===0?rows:n%3===1?rows.slice(0,250):rows.slice(9750);
 controller.set(view,r=>r.key,render);
 const slots=container.children;
 for(const slot of slots.slice(0,12))observer.cb([{target:slot,isIntersecting:true}]);
 controller.ensure(view.at(-1).key);
 maxMounted=Math.max(maxMounted,slots.filter(s=>s.firstElementChild).length);
 maxSlots=Math.max(maxSlots,slots.length);
 for(const slot of slots)observer.cb([{target:slot,isIntersecting:false}]);
 controller.sweep();
 assert.equal(slots.filter(s=>s.firstElementChild).length,0);
 times.push(performance.now()-start);
}
for(let n=0;n<12;n++)cycle(n);
global.gc();const baseline=process.memoryUsage().heapUsed;
for(let n=0;n<240;n++){cycle(n);if(n%30===0){global.gc();heaps.push(process.memoryUsage().heapUsed);}}
global.gc();const retained=process.memoryUsage().heapUsed;
assert(maxSlots<=10000);assert(maxMounted<=13);
assert(retained-baseline<8*1024*1024);
controller.destroy();global.gc();const destroyed=process.memoryUsage().heapUsed;
const sorted=times.slice(12).sort((a,b)=>a-b);
console.log(JSON.stringify({cycles:240,cards:10000,max_slots:maxSlots,max_mounted:maxMounted,
 p50_ms:sorted[Math.floor(sorted.length*.5)],p95_ms:sorted[Math.floor(sorted.length*.95)],
 baseline_heap:baseline,retained_heap:retained,retained_growth:retained-baseline,
 destroyed_heap:destroyed,heap_samples:heaps}));
'''

def run_soak():
    return json.loads(subprocess.check_output(['node','--expose-gc','-e',SOURCE.read_text()+'\n'+SCRIPT],text=True))

@unittest.skipUnless(shutil.which('node'),'Node.js required')
class PageSoakTest(unittest.TestCase):
    def test_large_filter_and_navigation_soak(self):
        result=run_soak()
        self.assertEqual(result['cycles'],240)
        self.assertLessEqual(result['max_mounted'],13)
        self.assertLess(result['retained_growth'],8*1024*1024)

if __name__=='__main__':
    print(json.dumps(run_soak(),indent=2))
