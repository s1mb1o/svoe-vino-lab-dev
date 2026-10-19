from pathlib import Path
import json,sys,time
import numpy as np
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'));sys.path.insert(0,str(Path(__file__).parent))
import matcher.semantic_selector as s
from matcher.experiments.main_selector.benchmark import selected_gt
from edge_probe import edges
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};rows=json.loads((P/'comparison.json').read_text());original=s._visible_bottle_geometry;s._png=lambda _:b'diagnostic';s._crops=lambda *args:None;s._original_frame=lambda *args:None
from probe_axis import fit_axis
def refine(im,d):return fit_axis(im,original(im,d))
s._visible_bottle_geometry=refine
out=[]
for old in rows:
 if old['variant']!='semantic-v2':continue
 c=cs[old['case_id']];mode=old['mode'];ds=c['fixture_detections'] if mode=='fallback' else json.loads((P/f'predictions/{c["id"]}-{mode}.json').read_text())['instances']
 if mode=='live' and c['id'] in json.loads((P/'detector-recovery.json').read_text())['cases']:ds+=json.loads((P/'detector-recovery.json').read_text())['cases'][c['id']]['instances']
 im=Image.open(P/c['image']).convert('RGB');res=s.select(im,ds,**c['interaction']);owner=old['matched_instance_id'] if res.selected_id==old['selected_id'] else selected_gt(c,ds,res,P)[0];correct=res.status==c['expected_status'] and (res.status!='selected' or owner==c['target_instance_id']);mm=res.selection_mode==c['expected_selection_mode'] if c.get('expected_selection_mode') else None
 if mode=='fallback':correct=correct and mm and res.reason==c['expected_reason']
 before=old['correct'] and old.get('expected_mode_match') is not False;after=correct and mm is not False
 row=dict(id=c['id'],mode=mode,before=before,after=after,reason=res.reason,selected=owner)
 if before!=after:print(json.dumps(row),flush=True)
 out.append(row)
(Path(__file__).parent/'axis-replay.json').write_text(json.dumps(out,indent=2)+'\n');print('fixed',sum(not r['before'] and r['after'] for r in out),'regressed',sum(r['before'] and not r['after'] for r in out),flush=True)
