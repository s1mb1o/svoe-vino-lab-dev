"""Bounded RGB crop resegmentation, without target or GT-mask access."""
from pathlib import Path
from io import BytesIO
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request

import numpy as np
from PIL import Image

ROOT=Path('/Volumes/Storage/svoe-vino-final')
sys.path.insert(0,str(ROOT/'code/svoe-vino-lab-main-selector'))
from matcher.group import _multipart,_sam3_url,_validate_sam3,_NoRedirect
from matcher.semantic_selector import select
SRC=ROOT/'datasets/main-selector-hardcases-v2-selector-fixes-20261019'
OUT=Path(__file__).parent
client=urllib.request.build_opener(_NoRedirect())

def request(image, dest):
    if dest.exists(): return json.loads(dest.read_text())['instances']
    stream=BytesIO();image.save(stream,'PNG');png=stream.getvalue()
    body,kind=_multipart(png,('bottle',))
    body=body.replace(b'filename="shelf.jpg"',b'filename="shelf.png"',1).replace(b'Content-Type: image/jpeg',b'Content-Type: image/png',1)
    req=urllib.request.Request(_sam3_url(os.environ['SAM3_ENDPOINT']),data=body,headers={'Content-Type':kind,'Accept':'application/json'},method='POST')
    with client.open(req,timeout=300) as response: raw=json.load(response)
    items=_validate_sam3(raw,*image.size,labels=('bottle',))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps({'image_sha256':hashlib.sha256(png).hexdigest(),'instances':items,'ground_truth_supplied_to_detector':False})+'\n')
    return items

if __name__ == '__main__':
    declaration={'trigger':'fallback with two bottle candidates, both eligible, center-distance difference at most 5px',
                 'roi':'each candidate box plus 20% of its long side on every side, clamped to source image',
                 'prompt':'bottle','encoding':'PNG','match':'maximum mask IoU with original seed, minimum 0.5',
                 'geometry':'tight binary-mask bounding box projected into source pixels; no distance tolerance added',
                 'purpose':'investigate candidate localization jitter separately from fallback ordering'}
    (OUT/'roi-probe-declaration.json').write_text(json.dumps(declaration,indent=2)+'\n')
    cases=json.loads((SRC/'cases.json').read_text())
    records=[]
    for case in cases:
        if case['provenance']=='geometry_fixture':continue
        cache=SRC/'predictions'/f"{case['id']}-live.json"
        ds=json.loads(cache.read_text())['instances']
        image=Image.open(SRC/case['image']).convert('RGB')
        decision=select(image,ds)
        candidates=decision.candidates
        if decision.selection_mode!='fallback' or len(candidates)!=2 or any(c['kind'] not in ('bottle','wine bottle') for c in candidates):continue
        distances=[np.hypot((c['box'][0]+c['box'][2]-image.width)/2,(c['box'][1]+c['box'][3]-image.height)/2) for c in candidates]
        if abs(distances[0]-distances[1])>5:continue
        for candidate in candidates:
            i=candidate['source_index'];box=candidate['box'];margin=round(max(box[2]-box[0],box[3]-box[1])*.20)
            roi=(max(0,box[0]-margin),max(0,box[1]-margin),min(image.width,box[2]+margin),min(image.height,box[3]+margin))
            items=request(image.crop(roi),OUT/'roi-probes'/f"{case['id']}-d{i}.json")
            original=np.asarray(Image.open(BytesIO(base64.b64decode(ds[i]['mask_png_b64']))))>=128
            choices=[]
            for item in items:
                small=np.asarray(Image.open(BytesIO(base64.b64decode(item['mask_png_b64']))))>=128
                full=np.zeros(original.shape,bool);full[roi[1]:roi[3],roi[0]:roi[2]]=small
                iou=float((full&original).sum()/max(1,(full|original).sum()))
                choices.append((iou,full,item))
            if choices:
                iou,full,item=max(choices,key=lambda x:x[0]);bounds=Image.fromarray(full).getbbox()
                record={'case_id':case['id'],'source_index':i,'roi':roi,'match_iou':iou,'original_box':box,'refined_box':bounds}
                print(json.dumps(record),flush=True);records.append(record)
            else:print(case['id'],i,'empty',flush=True)
    (OUT/'roi-probe-results.json').write_text(json.dumps(records,indent=2)+'\n')
