"""Image-only boundary refinement diagnostic; GT is used by the scorer only."""
from pathlib import Path
from io import BytesIO
import base64
import copy
import json
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = Path('/Volumes/Storage/svoe-vino-final')
sys.path.insert(0, str(ROOT / 'code/svoe-vino-lab-main-selector'))
sys.path.insert(0, str(ROOT / 'code/svoe-vino-lab-main-selector/matcher/experiments/main_selector'))
from matcher.semantic_selector import select
from benchmark import selected_gt

SRC = ROOT / 'datasets/main-selector-hardcases-v2-selector-fixes-20261019'
OUT = Path(__file__).parent

def refine(image, instances, method):
    items = copy.deepcopy(instances)
    for d in items:
        if d['label'] not in ('wine bottle', 'bottle'):
            continue
        mask = np.asarray(Image.open(BytesIO(base64.b64decode(d['mask_png_b64']))).convert('L')) >= 128
        if not mask.any():
            continue
        if method == 'grabcut':
            y, x = np.nonzero(mask)
            margin = max(5, round(min(x.ptp() if hasattr(x,'ptp') else np.ptp(x), np.ptp(y)) * .10))
            l, t = max(0, x.min()-margin-2), max(0, y.min()-margin-2)
            r, b = min(image.width, x.max()+margin+3), min(image.height, y.max()+margin+3)
            region = np.asarray(image)[t:b,l:r].copy()
            seed = mask[t:b,l:r].astype('uint8')
            outer = cv2.dilate(seed, np.ones((margin*2+1,margin*2+1), 'uint8'))
            inner = cv2.erode(seed, np.ones((3,3), 'uint8'))
            if inner.sum() < 8:
                continue
            gc = np.where(outer, cv2.GC_PR_BGD, cv2.GC_BGD).astype('uint8')
            gc[seed>0] = cv2.GC_PR_FGD
            gc[inner>0] = cv2.GC_FGD
            cv2.setRNGSeed(0)
            cv2.grabCut(region, gc, None, np.zeros((1,65)), np.zeros((1,65)), 5, cv2.GC_INIT_WITH_MASK)
            mask = np.zeros_like(mask)
            mask[t:b,l:r] = (gc==cv2.GC_PR_FGD)|(gc==cv2.GC_FGD)
        bbox = Image.fromarray(mask).getbbox()
        d['box'] = bbox
        stream = BytesIO()
        Image.fromarray(mask.astype('uint8')*255).save(stream,'PNG')
        d['mask_png_b64'] = base64.b64encode(stream.getvalue()).decode()
    return items

if __name__ == '__main__':
    cases = {c['id']:c for c in json.loads((SRC/'cases.json').read_text())}
    residuals = json.loads((SRC/'residual-failures.json').read_text())['rows']
    results=[]
    for case in residuals:
        c=cases[case['case_id']]
        image=Image.open(SRC/c['image']).convert('RGB')
        instances=json.loads((SRC/f"predictions/{c['id']}-live.json").read_text())['instances']
        for method in ['mask_bbox','grabcut']:
            ds=refine(image, instances, method)
            decision=select(image,ds)
            matched,iou=selected_gt(c,ds,decision,SRC)
            row={'case_id':c['id'],'method':method,'selected_id':decision.selected_id,
                 'matched_gt':matched,'correct':matched==c['target_instance_id'],'reason':decision.reason,
                 'boxes':[(i,d['box']) for i,d in enumerate(ds) if d['label']=='wine bottle']}
            results.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='boxes'}),flush=True)
    (OUT/'geometry-probes.json').write_text(json.dumps(results,indent=2)+'\n')
