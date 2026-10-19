from pathlib import Path
from PIL import Image
from io import BytesIO
from types import SimpleNamespace
import json,base64,sys,numpy as np
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.semantic_selector import select
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};jobs=json.loads((W/'probe-declaration.json').read_text())['jobs'];out=[];groups={}
for i,j in enumerate(jobs):
 f=W/'raw'/f'{i:02d}-{j["case_id"]}-{j["profile"]}.json';a=json.loads(f.read_text());c=cs[j['case_id']];items=[]
 for d in a['instances']:
  small=Image.open(BytesIO(base64.b64decode(d['mask_png_b64']))).convert('L');full=Image.new('L',(c['width'],c['height']));full.paste(small,j['roi'][:2]);box=full.getbbox();s=BytesIO();full.save(s,'PNG');items.append(dict(d,box=box,mask_png_b64=base64.b64encode(s.getvalue()).decode()))
 im=Image.open(P/c['image']).convert('RGB');primary=json.loads((P/f'predictions/{c["id"]}-live.json').read_text())['instances']
 if j['profile']=='box-roi':
  orig=np.asarray(Image.open(BytesIO(base64.b64decode(primary[j['source_index']]['mask_png_b64']))))>0
  ious=[]
  for d in items:
   m=np.asarray(Image.open(BytesIO(base64.b64decode(d['mask_png_b64']))))>0;ious.append(float((m&orig).sum()/max(1,(m|orig).sum())))
  if ious and max(ious)>=.5:
   best=items[int(np.argmax(ious))];groups.setdefault(j['case_id'],primary.copy())[j['source_index']]=dict(best,label=primary[j['source_index']]['label'])
 else:groups.setdefault(j['case_id'],primary.copy()).extend(items)
 targetious=[selected_gt(c,items,SimpleNamespace(selected_id=f'd{k}'),P) for k in range(len(items))]
 out.append(dict(job=i,**j,detections=len(items),target_matches=[k for k,(owner,_) in enumerate(targetious) if owner==c['target_instance_id']],max_target_iou=max([iou for owner,iou in targetious if owner==c['target_instance_id']],default=0)))
for cid,ds in groups.items():
 c=cs[cid];s=select(Image.open(P/c['image']).convert('RGB'),ds);owner,iou=selected_gt(c,ds,s,P);print(cid,'selected',s.selected_id,owner,'target',c['target_instance_id'],'correct',owner==c['target_instance_id'])
(W/'probe-scores.json').write_text(json.dumps(out,indent=2)+'\n')
