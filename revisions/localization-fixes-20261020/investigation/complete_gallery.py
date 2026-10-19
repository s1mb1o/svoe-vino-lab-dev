from pathlib import Path
from collections import Counter
from io import BytesIO
from types import SimpleNamespace
import base64,hashlib,json,re,shutil,sys
from PIL import Image,ImageDraw,ImageFont
R=Path('/Volumes/Storage/svoe-vino-final');S=R/'datasets/main-selector-hardcases-v2-localization-fixes-20261020';P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;O=Path('/private/tmp/issue-34-localization-gallery-20261020');repo=R/'code/svoe-vino-lab-main-selector';sys.path.insert(0,str(repo))
from matcher.experiments.main_selector.benchmark import selected_gt
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in S.glob('*.json'):shutil.copyfile(p,O/'evidence'/p.name)
for name in ['implementation.patch']:shutil.copyfile(S/name,O/name)
shutil.copyfile(S/'report.html',O/'evidence/comparison-report.html');shutil.copyfile(W/'full-matcher-tests.log',O/'evidence/full-matcher-tests.log')
for folder in ['raw','augmented','tracker','central']:shutil.copytree(S/folder,O/'evidence'/folder,dirs_exist_ok=True)
for p in W.glob('*.py'):
 dest=O/'investigation'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
for name,digest in read(S/'tested-source-hashes.json').items():
 assert sha(repo/name)==digest;dest=O/'implementation'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,dest)
summary=(S/'README.md').read_text();summary=re.sub(r'\]\(([^/)]+\.json)\)',r'](evidence/\1)',summary).replace('[Interactive comparison](report.html)','[HTML comparison source](evidence/comparison-report.html)')
f=O/'README.md';text=f.read_text().replace('# Issue 34 revised semantic-v2 photo and mask review','# Issue 34 localization fixes · 20 October 2026',1);text=text.replace('## How failures are marked',summary+'\n\n[All eight investigated cases](INVESTIGATION.md) · [Exact source patch](implementation.patch) · [New detector helper](implementation/matcher/selector_detection.py) · [New regression tests](implementation/matcher/tests/test_selector_localization.py).\n\n## How failures are marked',1).replace('[Original receipt]','[Current receipt]');f.write_text(text)
cs={c['id']:c for c in read(S/'cases.json')};rows={(r['case_id'],r['mode'],r['variant']):r for r in read(S/'comparison.json')};old={(r['case_id'],r['mode'],r['variant']):r for r in read(P/'comparison.json')};enh=read(S/'detector-enhancement.json')['cases'];ids=['hc-025','hc-035','hc-039','hc-041','hc-056','real-166918','real-397354','real-117719'];extras={};invest=['# Investigation of all eight remaining mismatches','','**Seven corrected; one frozen annotation conflict still fails.** Every example below has original RGB, GT masks, all primary/effective detector mask PNGs, both current selector crops and a saved preceding semantic crop. No local files are required.','','| Case | Before semantic-v2 | Current semantic-v2 | Current scene-v1 | Mechanism / remaining issue |','|---|---|---|---|---|']
for cid in ids:
 c=cs[cid];new=rows[(cid,'live','semantic-v2')];before=old[(cid,'live','semantic-v2')];legacy=rows[(cid,'live','scene-v1')];primary=read(S/f'predictions/{cid}-live.json')['instances'];effective=enh[cid]['instances'] if cid in enh else primary;byid={d['id']:d for d in new['candidates']}
 reason='Stable-neck bilateral outline fit' if cid.startswith('hc-') else 'Central 160px scan recovers the tiny held bottle' if cid=='real-166918' else 'Highest-quality admissible tracker mask, preserving original RGB rectangle' if cid=='real-397354' else 'Actual unannotated bottle covers photo center; GT subset chooses d37; still FAIL'
 flags=[]
 if not legacy['correct']:flags.append('WRONG TARGET')
 if legacy.get('label_retention') is not None and legacy['label_retention']<.98:flags.append('EXPECTED LABEL LOSS')
 legacy_label='FAIL: '+', '.join(flags) if flags else 'Recorded checks pass'
 current='PASS' if new['correct'] and new.get('expected_mode_match') is not False else '**FAIL — frozen annotation conflict**'
 invest.append(f'| [{cid}](cases/{cid}.md) | FAIL | {current} | {legacy_label} | {reason} |')
 dest=O/'before'/f'{cid}-semantic-v2.png';dest.parent.mkdir(exist_ok=True);shutil.copyfile(P/before['crop_path'],dest);extras[str(dest.relative_to(O))]=dict(source_directory=P.name,source_path=before['crop_path'],sha256=sha(dest))
 table=['','## Localization investigation · current revision','',f'**Before semantic-v2: FAIL. Current semantic-v2: {current}. Current scene-v1: {legacy_label}.**', '',reason+'.','',f'Before: `{before["selected_id"]}` → GT `{before["matched_instance_id"]}`; current: `{new["selected_id"]}` → GT `{new["matched_instance_id"]}`; frozen target `{c["target_instance_id"]}`. Required/current mode: `{c.get("expected_selection_mode")}` / `{new["selection_mode"]}`.','',f'![Preceding semantic-v2 crop](../before/{cid}-semantic-v2.png)','', '### Exact detector inputs and localization geometry','','Primary masks/caches remain unchanged. Effective masks include separately recorded image-only recovery/localization. Numeric detector IDs are distinct from GT IDs. Owner assignment below is an offline review annotation, never detector input.','','| Detector | Class | Score | Effective input box | Current selector box / source | Offline assigned GT | Primary mask | Effective mask |','|---|---|---:|---|---|---|---|---|']
 folder=O/'detector-masks'/cid;folder.mkdir(parents=True,exist_ok=True)
 for i,item in enumerate(effective):
  raw=base64.b64decode(item['mask_png_b64']);f=folder/f'effective-d{i}.png';f.write_bytes(raw);extras[str(f.relative_to(O))]=dict(sha256=sha(f),kind='effective_detector_mask')
  before_link='new recovery'
  if i<len(primary):
   f=folder/f'primary-d{i}.png';f.write_bytes(base64.b64decode(primary[i]['mask_png_b64']));extras[str(f.relative_to(O))]=dict(sha256=sha(f),kind='primary_detector_mask');before_link=f'[PNG](../detector-masks/{cid}/primary-d{i}.png)'
  d=byid.get(f'd{i}');owner,iou=selected_gt(c,effective,SimpleNamespace(selected_id=f'd{i}'),S);geometry=f"`{d['box']}` / {d.get('geometry_source','detector_box')}" if d else 'not an eligible output candidate';table.append(f'| `d{i}` | {item["label"]} | {item["score"]:.4f} | `{item["box"]}` | {geometry} | `{owner}` (IoU {iou:.3f}) | {before_link} | [PNG](../detector-masks/{cid}/effective-d{i}.png) |')
 if cid in enh:
  table+=['','### Raw responses used by the declared enhancement','']+[f'- [{name}](../evidence/{name})' for name in enh[cid]['raw_responses']]
 if cid=='real-117719':
  table+=['','### Why this remains a failure','','The independently detected `d96` has visible pixels at the photo center, while the frozen annotated target `1492244` maps to `d37` away from the center. Both are eligible. With the exact unchanged fallback, `d96` wins. Restricting candidates to those having COCO polygons would make `d37` win, but would remove real bottles using evaluation knowledge. That filtering is not implemented. The case stays failed. No missing label GT is invented.','', '[Exact candidate ordering and annotated-subset counterfactual](../evidence/residual-failures.json).']
 page=O/'cases'/f'{cid}.md';page.write_text(page.read_text()+'\n'+'\n'.join(table)+'\n')
 invest+=['',f'## {cid} · {current}','',f'[Open full photos, masks, selector crops and geometry](cases/{cid}.md)', '',f'![{cid} comparison](previews/{cid}.jpg)','',reason+'.']
# Present the unannotated center bottle and frozen target on the same original RGB.
c=cs['real-117719'];im=Image.open(S/c['image']).convert('RGB');canvas=Image.new('RGB',(im.width,im.height+78),'white');canvas.paste(im);draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16);residual=read(S/'residual-failures.json')['rows'][0]
for ident,color,label in [('d96','#ff4757','actual center bottle: no GT polygon'),('d37','#44ee88','frozen annotated target')]:
 d=next(d for d in residual['detector_geometry'] if d['id']==ident);draw.rectangle(tuple(d['box']),outline=color,width=2);draw.text((8,im.height+8+(0 if ident=='d96' else 30)),f'{ident}: {label}',fill=color,font=font)
f=O/'bar-annotation-conflict.png';canvas.save(f);invest+=['','## Remaining annotation conflict','','![Actual center bottle versus frozen annotated target](bar-annotation-conflict.png)','','This derived overlay is for review; the original RGB, GT masks and detector PNGs above remain unmodified. The raw response and crop show the actual unannotated rack bottle. `augmentation-scores.json` contains passive diagnostic probes including interaction photographs without their taps; those scores are not used as the final interaction result or accuracy. All final interaction metrics come from the complete paired replay.','','[99 raw RGB-only diagnostic responses and declarations](evidence/detector-investigation.json) · [Enhancement policy](evidence/enhancement-policy.json) · [Full comparison JSON](evidence/comparison.json) · [All scene-v1 failures](SCENE-V1-FAILURES.md).'];(O/'INVESTIGATION.md').write_text('\n'.join(invest)+'\n');(O/'extra-assets-manifest.json').write_text(json.dumps(extras,indent=2)+'\n');print(json.dumps(dict(affected_case_pages=8,extra_assets=len(extras),raw_responses=99,source_files=13)))
