"""Declared detector-only probes; annotations are used only after collection."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import os
import sys
import time
import urllib.request

ROOT = Path('/Volumes/Storage/svoe-vino-final')
sys.path.insert(0, str(ROOT / 'code/svoe-vino-lab-main-selector'))
from matcher.group import _normalize_image, _multipart, _validate_sam3, _sam3_url, _NoRedirect
from matcher.semantic_selector import NOUNS

SRC = ROOT / 'datasets/main-selector-hardcases-v2-selector-fixes-20261019'
OUT = Path(__file__).parent
IDS = ['hc-025', 'hc-035', 'hc-039', 'hc-041', 'hc-056', 'hc-145', 'hc-146',
       'real-520871', 'real-166918', 'real-117719', 'real-397354']
PROFILES = {'lossless_wine': NOUNS, 'lossless_generic': ('bottle', *NOUNS[1:])}
declaration = {'case_ids': IDS, 'profiles': PROFILES, 'image_encoding': 'lossless PNG of oriented source RGB',
               'purpose': 'Test compression and noun coverage without GT-assisted detection or changing fallback ordering.',
               'all_attempts_retained': True, 'original_predictions_read_only': True}
path = OUT / 'detector-probe-declaration.json'
if path.exists():
    assert json.loads(path.read_text()) == json.loads(json.dumps(declaration))
else:
    path.write_text(json.dumps(declaration, indent=2) + '\n')
cases = {c['id']: c for c in json.loads((SRC / 'cases.json').read_text())}
client = urllib.request.build_opener(_NoRedirect())
for profile, nouns in PROFILES.items():
    for cid in IDS:
        dest = OUT / 'detector-probes' / profile / f'{cid}.json'
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        case = cases[cid]
        image, _ = _normalize_image((SRC / case['image']).read_bytes())
        stream = BytesIO()
        image.save(stream, 'PNG')
        png = stream.getvalue()
        body, content_type = _multipart(png, nouns)
        body = body.replace(b'filename="shelf.jpg"', b'filename="shelf.png"', 1).replace(
            b'Content-Type: image/jpeg', b'Content-Type: image/png', 1)
        request = urllib.request.Request(_sam3_url(os.environ['SAM3_ENDPOINT']), data=body,
                                        headers={'Content-Type': content_type, 'Accept': 'application/json'}, method='POST')
        start = time.monotonic()
        with client.open(request, timeout=300) as response:
            result = json.load(response)
        instances = _validate_sam3(result, *image.size, labels=nouns)
        saved = {'profile': profile, 'case_id': cid, 'nouns': nouns, 'encoding': 'PNG',
                 'image_sha256': hashlib.sha256(png).hexdigest(), 'instances': instances,
                 'ground_truth_supplied_to_detector': False, 'seconds': time.monotonic()-start}
        dest.write_text(json.dumps(saved) + '\n')
        print(profile, cid, len(instances), round(saved['seconds'], 2), flush=True)
