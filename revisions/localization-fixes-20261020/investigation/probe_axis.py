"""Upright-bottle outline fitting. Uses only the supplied visible mask."""
from io import BytesIO
import base64,math
import numpy as np
from PIL import Image

def fit_axis(image,item):
 if item['label'] not in ('bottle','wine bottle'):return item
 m=np.asarray(Image.open(BytesIO(base64.b64decode(item['mask_png_b64']))).convert('L'))>=128
 bounds=Image.fromarray(m).getbbox()
 if bounds is None:return item
 l,t,r,b=bounds;w,h=r-l,b-t;box=item['box']
 if h<80 or w<20 or not 2.5<h/w<6:return item
 if max(abs(a-b) for a,b in zip(bounds,box))>max(2,w*.05):return item
 centers=[];widths=[]
 for row in m[t+max(2,round(h*.02)):t+round(h*.15)]:
  xs=np.flatnonzero(row)
  if len(xs):centers.append(int(xs[0]+xs[-1]+1));widths.append(int(xs[-1]-xs[0]+1))
 if len(centers)<5 or not .2*w<=np.median(widths)<=.65*w:return item
 axis=int(round(float(np.median(centers))))
 if np.percentile(np.abs(np.asarray(centers)-axis),90)>max(2,w*.06):return item
 # Evidence of a broad lower body, rather than a partial neck/hand component.
 bodies=[]
 for row in m[t+round(h*.25):t+round(h*.95)]:
  xs=np.flatnonzero(row)
  if len(xs):bodies.append(int(xs[-1]-xs[0]+1))
 if len(bodies)<h*.1 or sum(v>=w*.75 for v in bodies)<h*.1:return item
 nl=min(l,axis-r);nr=max(r,axis-l)
 if max(l-nl,nr-r)>max(2,w*.05) or nl<0 or nr>image.width:return item
 return dict(item,box=(nl,t,nr,b),axis_x2=axis)

if __name__=='__main__':
 from pathlib import Path
 import json,sys
 R=Path('/Volumes/Storage/svoe-vino-final');P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
 import matcher.semantic_selector as s
 original=s._visible_bottle_geometry
 def fitted(im,d):return fit_axis(im,original(im,d))
 s._visible_bottle_geometry=fitted;s._png=lambda _:b'x';s._crops=lambda *args:None;s._original_frame=lambda *args:None
 cs={c['id']:c for c in json.loads((P/'cases.json').read_text())}
 for cid in ['hc-025','hc-035','hc-039','hc-041','hc-056','hc-145','hc-146']:
  for mode in ['live','controlled']:
   im=Image.open(P/cs[cid]['image']).convert('RGB');ds=json.loads((P/f'predictions/{cid}-{mode}.json').read_text())['instances'];a=s.select(im,ds);print(cid,mode,a.selected_id,a.reason,[(d['id'],d['box']) for d in a.candidates],flush=True)
