"""Detector-seeded interactive masks; RGB/detections only, no target or GT access."""
from pathlib import Path
from io import BytesIO
import json,base64,hashlib,os,sys,time,urllib.request
import numpy as np
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'));sys.path.insert(0,str(Path(__file__).parent))
from matcher.group import _multipart,_sam3_url,_NoRedirect,_validate_sam3
from matcher.semantic_selector import select
from probe_augmented import request as text_request
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;client=urllib.request.build_opener(_NoRedirect())
def prompt(mask,roi):
 y,x=np.nonzero(mask);points=[]
 for q in [.1,.5,.9]:
  row=int(np.quantile(y,q));xs=np.flatnonzero(mask[row]);points.append([int(np.median(xs))-roi[0],row-roi[1]])
 return points

def point_request(im,points,path):
 b=BytesIO();im.save(b,'PNG');png=b.getvalue();digest=hashlib.sha256(png).hexdigest()
 if path.exists():
  a=json.loads(path.read_text());assert a['image_sha256']==digest and a['points']==points;return
 body,kind=_multipart(png,('bottle',));body=body.replace(b'filename="shelf.jpg"',b'filename="shelf.png"',1).replace(b'Content-Type: image/jpeg',b'Content-Type: image/png',1)
 body=body.replace(b'name="texts"\r\n\r\nbottle',b'name="points"\r\n\r\n'+json.dumps(points).encode(),1)
 boundary=kind.split('boundary=')[1].encode();end=b'--'+boundary+b'--\r\n';assert body.endswith(end)
 field=lambda name,data:b'--'+boundary+b'\r\nContent-Disposition: form-data; name="'+name+b'"\r\n\r\n'+data+b'\r\n'
 body=body[:-len(end)]+field(b'labels',b'[1,1,1]')+field(b'multimask',b'true')+end
 url=_sam3_url(os.environ['SAM3_ENDPOINT']).removesuffix('/segment_multi')+'/segment_point';req=urllib.request.Request(url,data=body,headers={'Content-Type':kind},method='POST');start=time.monotonic()
 with client.open(req,timeout=300) as resp:a=json.load(resp)
 for d in a['instances']:d['label']='bottle'
 ds=_validate_sam3(a,*im.size,labels=('bottle',));path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(dict(image_sha256=digest,points=points,instances=ds,ground_truth_supplied_to_detector=False,seconds=time.monotonic()-start))+'\n');print(path.name,len(ds),flush=True)
if __name__=='__main__':
 cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};jobs=[];rows={r['case_id']:r for r in json.loads((P/'comparison.json').read_text()) if r['mode']=='live' and r['variant']=='semantic-v2'}
 for c in cs.values():
  s=rows.get(c['id'])
  if not s or s['selection_mode']!='fallback':continue
  ds=sorted([d for d in s['candidates'] if d['eligible_for_selection'] and d['kind'] in ('wine bottle','bottle')],key=lambda d:np.hypot((d['box'][0]+d['box'][2]-c['width'])/2,(d['box'][1]+d['box'][3]-c['height'])/2))
  dist=lambda d:np.hypot((d['box'][0]+d['box'][2]-c['width'])/2,(d['box'][1]+d['box'][3]-c['height'])/2)
  if len(ds)<2 or dist(ds[1])-dist(ds[0])>5:continue
  primary=json.loads((P/f'predictions/{c["id"]}-live.json').read_text())['instances']
  for d in ds[:2]:
   box=d['box'];margin=round(max(box[2]-box[0],box[3]-box[1])*.2);roi=[max(0,box[0]-margin),max(0,box[1]-margin),min(c['width'],box[2]+margin),min(c['height'],box[3]+margin)];m=np.asarray(Image.open(BytesIO(base64.b64decode(primary[d['source_index']]['mask_png_b64']))))>=128
   jobs.append(dict(case_id=c['id'],source_index=d['source_index'],roi=roi,points=prompt(m,roi)))
 (W/'tracker-declaration.json').write_text(json.dumps(dict(jobs=jobs,trigger='live semantic fallback; nearest two bottle centers differ by at most 5px',roi_margin=.2,points='median visible x at 10%,50%,90% of visible-mask y distribution',selection='highest overlap mask >=0.5 IoU; conservative full mask union; no GT',ground_truth_supplied=False),indent=2)+'\n')
 for i,j in enumerate(jobs):point_request(Image.open(P/cs[j['case_id']]['image']).convert('RGB').crop(j['roi']),j['points'],W/'tracker'/f'{i:02d}-{j["case_id"]}-d{j["source_index"]}.json')
 for cid in ['real-166918','real-117719','real-397354']:
  im=Image.open(P/cs[cid]['image']).convert('RGB');side=160;x=(im.width-side)//2;y=(im.height-side)//2;text_request(im.crop((x,y,x+side,y+side)),('wine bottle','bottle','bottle held in hand'),W/'central'/f'{cid}.json')
