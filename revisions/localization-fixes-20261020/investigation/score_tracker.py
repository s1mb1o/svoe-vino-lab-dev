from pathlib import Path
from PIL import Image
from io import BytesIO
import json,base64,numpy as np,sys
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
import matcher.semantic_selector as s
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};s._png=lambda _:b'diagnostic';s._crops=lambda *args:None;s._original_frame=lambda *args:None

def mask(d):return np.asarray(Image.open(BytesIO(base64.b64decode(d['mask_png_b64']))).convert('L'))>=128

def refine(ds,raw,j,size,union):
 original=mask(ds[j['source_index']]);choices=[]
 for d in raw:
  full=np.zeros(original.shape,bool);roi=j['roi'];full[roi[1]:roi[3],roi[0]:roi[2]]=mask(d);iou=float((original&full).sum()/max(1,(original|full).sum()));choices.append((iou,full,d))
 if not choices:return None
 iou,m,d=max(choices,key=lambda a:a[0])
 if iou<.5:return None
 bounds=Image.fromarray(m).getbbox();old=Image.fromarray(original).getbbox();limit=max(4,min(old[2]-old[0],old[3]-old[1])*.1)
 if max(abs(a-b) for a,b in zip(bounds,old))>limit:return dict(rejected=True,iou=iou,box=bounds,old=old)
 new=original|m if union else m;bounds=Image.fromarray(new).getbbox();b=BytesIO();Image.fromarray(new.astype('uint8')*255).save(b,'PNG');ds[j['source_index']]=dict(ds[j['source_index']],box=bounds,mask_png_b64=base64.b64encode(b.getvalue()).decode());return dict(iou=iou,box=bounds,old=old)
if __name__=='__main__':
 jobs=json.loads((W/'tracker-declaration.json').read_text())['jobs'];out=[]
 for union in [True,False]:
  groups={};audits={}
  for i,j in enumerate(jobs):
   f=W/'tracker'/f'{i:02d}-{j["case_id"]}-d{j["source_index"]}.json'
   if not f.exists():continue
   c=cs[j['case_id']];ds=groups.setdefault(c['id'],json.loads((P/f'predictions/{c["id"]}-live.json').read_text())['instances']);a=refine(ds,json.loads(f.read_text())['instances'],j,(c['width'],c['height']),union);audits.setdefault(c['id'],[]).append(dict(source_index=j['source_index'],refinement=a))
  for cid,ds in groups.items():
   c=cs[cid];res=s.select(Image.open(P/c['image']).convert('RGB'),ds,**c['interaction']);owner,iou=selected_gt(c,ds,res,P);r=dict(case_id=cid,union=union,correct=owner==c['target_instance_id'] and (not c.get('expected_selection_mode') or res.selection_mode==c['expected_selection_mode']),owner=owner,selected=res.selected_id,reason=res.reason,audit=audits[cid]);out.append(r);print(json.dumps(r),flush=True)
 (W/'tracker-scores.json').write_text(json.dumps(out,indent=2)+'\n')
