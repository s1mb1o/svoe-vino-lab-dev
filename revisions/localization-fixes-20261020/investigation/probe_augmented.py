"""Flip-consistency localization and interaction-aware small-object nouns.
Only RGB and primary detections are used to construct requests.
"""
from pathlib import Path
from io import BytesIO
import base64,hashlib,json,os,sys,time,urllib.request
import numpy as np
from PIL import Image,ImageOps
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.group import _multipart,_sam3_url,_NoRedirect,_validate_sam3
from matcher.semantic_selector import select
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;client=urllib.request.build_opener(_NoRedirect())
def request(im,nouns,path):
 b=BytesIO();im.save(b,'PNG');png=b.getvalue();digest=hashlib.sha256(png).hexdigest()
 if path.exists():
  a=json.loads(path.read_text());assert a['image_sha256']==digest and a['nouns']==list(nouns);return a['instances']
 body,kind=_multipart(png,nouns);body=body.replace(b'filename="shelf.jpg"',b'filename="shelf.png"',1).replace(b'Content-Type: image/jpeg',b'Content-Type: image/png',1)
 req=urllib.request.Request(_sam3_url(os.environ['SAM3_ENDPOINT']),data=body,headers={'Content-Type':kind},method='POST');start=time.monotonic()
 with client.open(req,timeout=300) as resp:a=json.load(resp)
 ds=_validate_sam3(a,*im.size,labels=nouns);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(dict(image_sha256=digest,nouns=nouns,instances=ds,ground_truth_supplied_to_detector=False,seconds=time.monotonic()-start))+'\n');print(path.name,len(ds),flush=True);return ds
if __name__=='__main__':
 cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};jobs=[]
 # All live fallback scenes with two leading bottle centers within 5 pixels of equal distance.
 for c in cs.values():
  f=P/f'predictions/{c["id"]}-live.json'
  if not f.exists():continue
  im=Image.open(P/c['image']).convert('RGB');ds=json.loads(f.read_text())['instances'];s=select(im,ds)
  if s.selection_mode!='fallback':continue
  ds=sorted([d for d in s.candidates if d['eligible_for_selection'] and d['kind'] in ('wine bottle','bottle')],key=lambda d:np.hypot((d['box'][0]+d['box'][2]-im.width)/2,(d['box'][1]+d['box'][3]-im.height)/2))
  if len(ds)<2:continue
  dist=lambda d:np.hypot((d['box'][0]+d['box'][2]-im.width)/2,(d['box'][1]+d['box'][3]-im.height)/2)
  if dist(ds[1])-dist(ds[0])<=5:jobs.append(dict(case_id=c['id'],profile='mirror',nouns=['wine bottle']))
 for j in json.loads((W/'probe-declaration.json').read_text())['jobs']:
  if j['profile']=='small-grid':jobs.append(dict(case_id=j['case_id'],roi=j['roi'],profile='small-grid-wine-held',nouns=['wine bottle','bottle held in hand']))
 (W/'augmentation-declaration.json').write_text(json.dumps(dict(jobs=jobs,trigger='all close live fallback bottle contests; fixed complete-image grid for tiny bottles',ground_truth_supplied=False),indent=2)+'\n')
 for i,j in enumerate(jobs):
  im=Image.open(P/cs[j['case_id']]['image']).convert('RGB');im=ImageOps.mirror(im) if j['profile']=='mirror' else im.crop(j['roi']);request(im,j['nouns'],W/'augmented'/f'{i:02d}-{j["case_id"]}-{j["profile"]}.json')
