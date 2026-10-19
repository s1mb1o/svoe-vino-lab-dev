"""Replay the implemented RGB-only enhancement with retained response caches."""
from pathlib import Path
from io import BytesIO
from time import monotonic
import json,hashlib,sys,os
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
import matcher.semantic_selector as s
from matcher.selector_detection import enhance,small_scene,request_optional
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;s._png=lambda _:b'diagnostic';s._crops=lambda *args:None;s._original_frame=lambda *args:None
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cs=json.loads((P/'cases.json').read_text());saved={};scores=[];catalog={}
for folder in ['central','tracker','implementation-requests']:
 for f in (W/folder).glob('*.json'):
  a=json.loads(f.read_text());catalog[(a['image_sha256'],json.dumps(a.get('points')))]=(a,f)
for c in cs:
 cache=P/f'predictions/{c["id"]}-live.json'
 if not cache.exists():continue
 im=Image.open(P/c['image']).convert('RGB');ds=json.loads(cache.read_text())['instances'];decision=s.select(im,ds,**c['interaction'])
 if not small_scene(im,decision):continue
 calls=[]
 def request(crop,*,points=None,timeout):
  b=BytesIO();crop.save(b,'PNG');digest=hashlib.sha256(b.getvalue()).hexdigest();key=(digest,json.dumps(points))
  if key in catalog:a,f=catalog[key]
  else:
   f=W/'implementation-requests'/f'{c["id"]}-{len(calls):02d}.json';f.parent.mkdir(parents=True,exist_ok=True)
   a=dict(image_sha256=digest,points=points,instances=request_optional(crop,os.environ['SAM3_ENDPOINT'],timeout,points=points),ground_truth_supplied_to_detector=False);f.write_text(json.dumps(a)+'\n');catalog[key]=(a,f)
  calls.append(str(f.relative_to(W)));return a['instances']
 effective,audit=enhance(im,ds,decision,request,deadline=monotonic()+300)
 result=s.select(im,effective,**c['interaction']);owner,iou=selected_gt(c,effective,result,P)
 saved[c['id']]=dict(image_sha256=c['image_sha256'],primary_prediction_sha256=sha(cache),instances=effective,audit=audit,raw_responses=calls)
 row=dict(case_id=c['id'],correct=owner==c['target_instance_id'] and (not c.get('expected_selection_mode') or result.selection_mode==c['expected_selection_mode']),owner=owner,selected=result.selected_id,selection_mode=result.selection_mode,added=len(effective)-len(ds));scores.append(row);print(json.dumps(row),flush=True)
(W/'detector-enhancement.json').write_text(json.dumps(dict(profile='small-bottle-localization-20261020',cases=saved,ground_truth_supplied=False),indent=2)+'\n');(W/'enhancement-scores.json').write_text(json.dumps(scores,indent=2)+'\n')
