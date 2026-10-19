"""Detector-seeded box segmentation and fixed-grid small-object probes.
No targets, annotations or GT masks are read until separate scoring.
"""
from pathlib import Path
from io import BytesIO
import base64, hashlib, json, os, sys, time, urllib.request
import numpy as np
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.group import _multipart,_sam3_url,_NoRedirect,_validate_sam3
from matcher.semantic_selector import select
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent
client=urllib.request.build_opener(_NoRedirect())

def request(im,dest,box=None):
 b=BytesIO();im.save(b,'PNG');png=b.getvalue();digest=hashlib.sha256(png).hexdigest()
 if dest.exists():
  a=json.loads(dest.read_text());assert a['image_sha256']==digest and a['box_prompt']==box;return a['instances']
 body,kind=_multipart(png,('bottle',))
 body=body.replace(b'filename="shelf.jpg"',b'filename="shelf.png"',1).replace(b'Content-Type: image/jpeg',b'Content-Type: image/png',1)
 url=_sam3_url(os.environ['SAM3_ENDPOINT'])
 if box is not None:
  body=body.replace(b'name="texts"\r\n\r\nbottle',b'name="box"\r\n\r\n'+','.join(str(v) for v in box).encode(),1)
  url=url.removesuffix('/segment_multi')+'/segment'
 req=urllib.request.Request(url,data=body,headers={'Content-Type':kind,'Accept':'application/json'},method='POST');start=time.monotonic()
 with client.open(req,timeout=300) as resp:a=json.load(resp)
 if box is not None:
  for d in a['instances']:d['label']='bottle'
 ds=_validate_sam3(a,*im.size,labels=('bottle',));dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(dict(image_sha256=digest,box_prompt=box,instances=ds,ground_truth_supplied_to_detector=False,seconds=time.monotonic()-start))+'\n')
 print(dest.name,len(ds),round(time.monotonic()-start,2),flush=True);return ds

def main():
 cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};jobs=[]
 for cid in ['hc-025','hc-035','hc-039','hc-041','hc-056','hc-145','hc-146','real-397354']:
  c=cs[cid];im=Image.open(P/c['image']).convert('RGB');ds=json.loads((P/f'predictions/{cid}-live.json').read_text())['instances'];s=select(im,ds)
  candidates=sorted([d for d in s.candidates if d['eligible_for_selection']],key=lambda d:(d['box'][0]+d['box'][2]-im.width)**2+(d['box'][1]+d['box'][3]-im.height)**2)[:2]
  for d in candidates:
   box=d['box'];margin=round(max(box[2]-box[0],box[3]-box[1])*.2);roi=[max(0,box[0]-margin),max(0,box[1]-margin),min(im.width,box[2]+margin),min(im.height,box[3]+margin)]
   bp=[box[i]-roi[i%2] for i in range(4)]
   jobs.append(dict(case_id=cid,source_index=d['source_index'],roi=roi,box_prompt=bp,profile='box-roi'))
 # Twelve overlapping square crops spanning the complete small real photo.
 cid='real-166918';c=cs[cid];im=Image.open(P/c['image']);side=240
 for y in [0,133,267,400]:
  for x in [0,120,240]:jobs.append(dict(case_id=cid,roi=[x,y,x+side,y+side],box_prompt=None,profile='small-grid'))
 decl=dict(purpose='Improve localization and tiny-object recall using only source RGB and detector seeds',jobs=jobs,encoding='PNG',text='bottle',threshold=.4,mask_threshold=.5,ground_truth_supplied=False)
 (W/'probe-declaration.json').write_text(json.dumps(decl,indent=2)+'\n')
 for i,j in enumerate(jobs):
  im=Image.open(P/cs[j['case_id']]['image']).convert('RGB').crop(j['roi']);request(im,W/'raw'/f'{i:02d}-{j["case_id"]}-{j["profile"]}.json',j['box_prompt'])

if __name__=='__main__':main()
