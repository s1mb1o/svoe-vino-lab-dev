from pathlib import Path
import sys,json
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(Path(__file__).parent))
from probe_augmented import request
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};jobs=[]
for r in json.loads((P/'comparison.json').read_text()):
 if r['mode']!='live' or r['variant']!='semantic-v2' or r['selection_mode']!='fallback':continue
 c=cs[r['case_id']];ds=[d for d in r['candidates'] if d['eligible_for_selection'] and d['kind'] in ('wine bottle','bottle')]
 if not ds or max(d['box'][3]-d['box'][1] for d in ds)>.2*max(c['width'],c['height']):continue
 x=(c['width']-160)//2;y=(c['height']-160)//2;jobs.append(dict(case_id=c['id'],roi=[x,y,x+160,y+160]))
(W/'central-production-declaration.json').write_text(json.dumps(dict(jobs=jobs,trigger='semantic fallback; every eligible bottle height <=20% photo long side',size=160,nouns=['wine bottle','bottle','bottle held in hand'],reject='any returned tight mask within 2 pixels of an interior ROI edge; truncated geometry is not a new candidate',ground_truth_supplied=False),indent=2)+'\n')
for j in jobs:
 c=cs[j['case_id']];im=Image.open(P/c['image']).convert('RGB').crop(j['roi']);request(im,('wine bottle','bottle','bottle held in hand'),W/'central'/f'{c["id"]}.json')
