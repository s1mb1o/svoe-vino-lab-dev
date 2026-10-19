from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from collections import defaultdict
import json,math,hashlib
p=Path('/private/tmp/issue-34-localization-gallery-20261020');cases=json.loads((p/'evidence/cases.json').read_text());groups=defaultdict(list)
for c in cases:groups[c['group']].append(c)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',30)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22)
(p/'contact-sheets').mkdir(exist_ok=True)
records={}
for gid,cs in groups.items():
 cols=3 if len(cs)>14 else 2 if len(cs)>1 else 1
 tw,th=720,403;gap=12;header=108
 sheet=Image.new('RGB',(cols*tw+(cols+1)*gap,math.ceil(len(cs)/cols)*(th+gap)+header),'#e5e7eb');d=ImageDraw.Draw(sheet)
 d.rectangle((0,0,sheet.width,header-8),fill='#111827');d.text((20,12),f'{gid} | {len(cs)} cases',font=font,fill='white')
 d.text((20,56),'Red = recorded failure. Full-size evidence and all modes are linked per case.',font=small,fill='#e5e7eb')
 for i,c in enumerate(cs):
  im=Image.open(p/'previews'/f'{c["id"]}.jpg').convert('RGB').resize((tw,th),Image.Resampling.LANCZOS)
  sheet.paste(im,(gap+(i%cols)*(tw+gap),header+(i//cols)*(th+gap)))
 f=p/'contact-sheets'/f'{gid}.jpg';sheet.save(f,quality=87,optimize=True)
 records[gid]={'cases':[c['id'] for c in cs],'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size,'width':sheet.width,'height':sheet.height}
assert sum(len(r['cases']) for r in records.values())==216
(p/'contact-sheet-manifest.json').write_text(json.dumps({'baseline_gallery_commit':'3a927638f8ef94188e47147b197dcbb61c0faba8','sheets':records,'purpose':'Compact issue previews avoid hundreds of simultaneous private-asset requests; full-size per-case evidence is linked separately.'},indent=2)+'\n')
print(json.dumps({'sheets':len(records),'cases':216,'total_bytes':sum(r['bytes'] for r in records.values()),'max_bytes':max(r['bytes'] for r in records.values())}))
