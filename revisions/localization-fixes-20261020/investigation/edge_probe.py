from pathlib import Path
import json,sys
import numpy as np
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.semantic_selector import _read
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';CS={c['id']:c for c in json.loads((P/'cases.json').read_text())}
def edges(im,box,band=(.70,.95)):
 a=np.asarray(im).astype(float);dx=np.linalg.norm(a[:,1:]-a[:,:-1],axis=2)
 l,t,r,b=map(int,box);span=max(3,round((r-l)*.1));av=np.median(dx[round(t+(b-t)*band[0]):round(t+(b-t)*band[1])],axis=0);bounds=[];noiseout=[]
 for x,left in [(l,True),(r,False)]:
  start=max(0,x-span);end=min(len(av),x+span);v=av[start:end];noise=np.median(v[:3] if left else v[-3:]);th=max(2.5,noise*2);hits=np.flatnonzero(v>th)
  bounds.append((int(start+hits[0]+1) if left else int(start+hits[-1]+1)) if len(hits) else x);noiseout.append(round(noise,2))
 return bounds,noiseout
if __name__=='__main__':
 for cid in ['hc-025','hc-035','hc-039','hc-041','hc-056','hc-145','hc-146']:
  im=Image.open(P/CS[cid]['image']).convert('RGB');ds=json.loads((P/f'predictions/{cid}-live.json').read_text())['instances'];ds=[d for d in _read(im,ds) if d['label']=='wine bottle'];print(cid)
  for band in [(.6,.9),(.7,.95),(.8,.95),(.85,.95)]:print(band,[(d['source_index'],*edges(im,d['box'],band)) for d in ds])
