from pathlib import Path
from PIL import Image,ImageOps
from io import BytesIO
import json,base64,numpy as np,sys
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
import matcher.semantic_selector as s
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};s._png=lambda _:b'diagnostic'
def mask(d):return np.asarray(Image.open(BytesIO(base64.b64decode(d['mask_png_b64']))).convert('L'))>=128
if __name__=='__main__':
 jobs=json.loads((W/'augmentation-declaration.json').read_text())['jobs'];out=[]
 for i,j in enumerate(jobs):
  f=W/'augmented'/f'{i:02d}-{j["case_id"]}-{j["profile"]}.json'
  if not f.exists():continue
  c=cs[j['case_id']];im=Image.open(P/c['image']).convert('RGB');ds=json.loads((P/f'predictions/{c["id"]}-live.json').read_text())['instances'];extra=json.loads(f.read_text())['instances']
  if j['profile']!='mirror':continue
  for d in ds:
   if d['label'] not in ('wine bottle','bottle'):continue
   orig=mask(d);matches=[(float((orig&m).sum()/max(1,(orig|m).sum())),m) for e in extra for m in [np.fliplr(mask(e))]]
   if not matches:continue
   iou,mirror=max(matches,key=lambda x:x[0])
   if iou<.5:continue
   # Union preserves every primary visible pixel. No target or distance read.
   new=orig|mirror;d['box']=Image.fromarray(new).getbbox();b=BytesIO();Image.fromarray(new.astype('uint8')*255).save(b,'PNG');d['mask_png_b64']=base64.b64encode(b.getvalue()).decode()
  res=s.select(im,ds);owner,iou=selected_gt(c,ds,res,P);r=dict(case_id=c['id'],correct=owner==c['target_instance_id'] and (not c.get('expected_selection_mode') or res.selection_mode==c['expected_selection_mode']),owner=owner,selected=res.selected_id,reason=res.reason,boxes=[(i,d['box']) for i,d in enumerate(ds) if d['label']=='wine bottle']);out.append(r);print(json.dumps(r),flush=True)
 (W/'augmentation-scores.json').write_text(json.dumps(out,indent=2)+'\n')
