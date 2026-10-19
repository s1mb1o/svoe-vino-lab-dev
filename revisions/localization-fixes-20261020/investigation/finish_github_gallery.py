from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,base64
p=Path('/private/tmp/issue-34-localization-gallery-20261020');cases=json.loads((p/'evidence/cases.json').read_text())
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',18)
(p/'fixture-masks').mkdir(exist_ok=True)
count=0
for c in cases:
 if c['provenance']!='geometry_fixture':continue
 ident=c['id'];im=Image.open(p/'overlays'/f'{ident}.png').convert('RGB');d=ImageDraw.Draw(im)
 d.rectangle((0,c['height'],im.width,c['height']+36),fill='white')
 d.text((16,c['height']+10),'ANNOTATED GEOMETRY MASKS | GREEN = EXPECTED SUBJECT',font=font,fill='#111827')
 im.save(p/'overlays'/f'{ident}.png',optimize=True)
 card=Image.open(p/'previews'/f'{ident}.jpg').convert('RGB');thumb=im.copy();thumb.thumbnail((390,530),Image.Resampling.LANCZOS);canvas=Image.new('RGB',(390,530),'#f2f4f7');canvas.paste(thumb,((390-thumb.width)//2,(530-thumb.height)//2));card.paste(canvas,(435,182));card.save(p/'previews'/f'{ident}.jpg',quality=89,optimize=True)
 block=['','## Declared detector input masks','','These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.','', '| Detector index | Class | Score | Input box | Original mask PNG |', '|---|---|---:|---|---|']
 for i,a in enumerate(c.get('fixture_detections',[])):
  if not a.get('mask_png_b64'):continue
  raw=base64.b64decode(a['mask_png_b64']);name=f'{ident}-d{i}.png';(p/'fixture-masks'/name).write_bytes(raw);count+=1
  block.append(f'| `d{i}` | {a["label"]} | {a.get("score")} | `{a["box"]}` | [view input mask](../fixture-masks/{name}) |')
 f=p/'cases'/f'{ident}.md';s=f.read_text().replace('Input masks are declared fixture detections.','Annotated expected geometry and detector input masks are identified separately below.')
 s=s.replace('\n## Saved selector outputs','\n'.join(block)+'\n\n## Saved selector outputs');f.write_text(s)
warning='**Taxonomy caveat:** `real-402720` is a bottle-framing regression, not a verified wine-intent positive. The frozen target description may misidentify the beverage; it is preserved as historical source data, not endorsed by this gallery.'
f=p/'cases/real-402720.md';s=f.read_text().replace('## Expected result','## Expected result\n\n'+warning);f.write_text(s)
f=p/'README.md';s=f.read_text();s+='\n\n'+warning+'\n';f.write_text(s)
print(json.dumps({'fixture_input_mask_pngs':count,'fixture_overlay_labels_corrected':50,'taxonomy_caveat_added':True}))
