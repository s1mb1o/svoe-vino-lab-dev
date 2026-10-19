from pathlib import Path
from PIL import Image
from io import BytesIO
from types import SimpleNamespace
import json,base64,numpy as np,sys
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.semantic_selector import select
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;cid='real-166918';c=next(c for c in json.loads((P/'cases.json').read_text()) if c['id']==cid);jobs=json.loads((W/'augmentation-declaration.json').read_text())['jobs'];ds=json.loads((P/f'predictions/{cid}-live.json').read_text())['instances'];rows=[]
for i,j in enumerate(jobs):
 if j['profile']!='small-grid-wine-held':continue
 f=W/'augmented'/f'{i:02d}-{cid}-{j["profile"]}.json';a=json.loads(f.read_text());found=[]
 for d in a['instances']:
  small=Image.open(BytesIO(base64.b64decode(d['mask_png_b64']))).convert('L');full=Image.new('L',(c['width'],c['height']));full.paste(small,j['roi'][:2]);b=BytesIO();full.save(b,'PNG');item=dict(d,label='bottle',box=full.getbbox(),mask_png_b64=base64.b64encode(b.getvalue()).decode());owner,iou=selected_gt(c,[item],SimpleNamespace(selected_id='d0'),P);found.append(dict(box=item['box'],owner=owner,iou=iou,score=d['score']));ds.append(item)
 rows.append(dict(job=i,roi=j['roi'],detections=found));print(i,[r for r in found if r['owner']==c['target_instance_id']],flush=True)
s=select(Image.open(P/c['image']).convert('RGB'),ds);owner,iou=selected_gt(c,ds,s,P);print('SELECTED',s.selected_id,owner,s.reason,'correct',owner==c['target_instance_id'],flush=True);(W/'grid-scores.json').write_text(json.dumps(dict(rows=rows,selected=s.selected_id,owner=owner,correct=owner==c['target_instance_id']),indent=2)+'\n')
