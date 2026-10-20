"""Collect fixed image-only contextual masks separately from frozen primaries."""
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import time

from PIL import Image

WORK=Path('/Volumes/Storage/svoe-vino-final')
ROOT=WORK/'datasets/main-selector-imagegen-all152-20261020-current-v1'
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'baseline'))
from matcher.group import _request_sam3

NOUNS=('poster','screen','mirror','bottle held in hand','transparent wrapping','empty gift bag')
cases=json.loads((ROOT/'cases-frozen.json').read_text())
(HERE/'context').mkdir(exist_ok=True)
for c in cases:
 dest=HERE/'context'/f"{c['slug']}.json"
 if dest.exists():continue
 with Image.open(ROOT/c['image_path']) as opened:
  photo=opened.convert('RGB')
 stream=BytesIO();photo.save(stream,'JPEG',quality=95);payload=stream.getvalue()
 start=time.perf_counter()
 try:
  items=_request_sam3(payload,*photo.size,os.environ['SAM3_ENDPOINT'],90,nouns=NOUNS)
 except Exception as error:
  print(c['slug'],'ERROR',str(error),flush=True)
  (HERE/'context'/f"{c['slug']}-error.json").write_text(json.dumps({'error':str(error),'request_nouns':NOUNS},indent=2)+'\n')
  continue
 row={'image_sha256':c['image_sha256'],'request_image_sha256':hashlib.sha256(payload).hexdigest(),
      'request_nouns':', '.join(NOUNS),'request_threshold':.4,'mask_threshold':.5,
      'source':'fixed_RGB_only_context_request','target_or_annotation_supplied':False,
      'response':{'instances':items},'elapsed_seconds':time.perf_counter()-start,
      'created_at':datetime.now(timezone.utc).isoformat(),'endpoint':os.environ['SAM3_ENDPOINT'],
      'model_checkpoint_revision':'not disclosed by existing service'}
 dest.write_text(json.dumps(row,indent=2)+'\n')
 print(c['slug'],[(p['label'],round(p['score'],3)) for p in items],flush=True)
