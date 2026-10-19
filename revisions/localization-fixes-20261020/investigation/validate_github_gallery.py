from pathlib import Path
import json,re,hashlib
from PIL import Image
p=Path('/private/tmp/issue-34-localization-gallery-20261020')
cases=json.loads((p/'evidence/cases.json').read_text());rows=json.loads((p/'evidence/comparison.json').read_text())
manifest=json.loads((p/'source-manifest.json').read_text())
assert len(cases)==216
assert len(list((p/'cases').glob('*.md')))==216
assert len(list((p/'previews').glob('*.jpg')))==216
assert len(list((p/'overlays').glob('*.png')))==216
for rel,meta in manifest['source_relative_paths'].items():
 f=p/'assets'/rel
 assert f.stat().st_size==meta['bytes']
 assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256'],rel
for c in cases:
 page=(p/'cases'/f'{c["id"]}.md').read_text()
 assert 'scene-v1' in page and 'semantic-v2' in page
 for r in rows:
  if r['case_id']==c['id']:
   assert f'### {r["mode"]}' in page
   if c['provenance']!='geometry_fixture' and r['variant']=='scene-v1' and r['correct'] is False:
    assert '**FAIL: WRONG TARGET' in page or 'NO-TARGET FAILURE' in page
 for a in c['annotations']:
  assert a['mask'] in page
 for x in ['previews','overlays']:
  with Image.open(p/x/(c['id']+('.jpg' if x=='previews' else '.png'))) as im:im.verify()
links=0
for f in p.rglob('*.md'):
 for match in re.finditer(r'\]\(([^)]+)\)',f.read_text()):
  target=match.group(1)
  if target.startswith(('http:','https:','#','mailto:')):continue
  assert (f.parent/target.split('#')[0]).resolve().is_file(),(str(f),target)
  links+=1
result={'passed':True,'cases':len(cases),'comparison_rows':len(rows),'raw_assets_hash_verified':len(manifest['source_relative_paths']),'local_links_verified':links,'source_dataset_unchanged':True}
(p/'gallery-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
