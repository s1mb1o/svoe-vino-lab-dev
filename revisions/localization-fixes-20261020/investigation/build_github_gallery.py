from pathlib import Path
from collections import defaultdict, Counter
from PIL import Image, ImageDraw, ImageFont, ImageOps
import json, hashlib, shutil, base64, io, re, textwrap

SRC=Path('/Volumes/Storage/svoe-vino-final/datasets/main-selector-hardcases-v2-localization-fixes-20261020')
OUT=Path('/private/tmp/issue-34-localization-gallery-20261020')
OUT.mkdir(exist_ok=True)
CASES=json.loads((SRC/'cases.json').read_text())
ROWS=json.loads((SRC/'comparison.json').read_text())
PROTOCOL=json.loads((SRC/'protocol.json').read_text())
GROUPS={x['id']:x for x in PROTOCOL['groups']}
GROUPS.update({'real':{'title':'Additional real photographs','description':'Real COCO bottle photos with source attribution and incomplete annotation limits.'},'fallback':{'title':'Deterministic fallback fixtures','description':'Declared geometry inputs; separate from photograph accuracy.'},'review':{'title':'Review regression fixtures','description':'Additional declared contract fixtures; legacy scene-v1 is not scored against the new contract.'}})
BY=defaultdict(list)
for r in ROWS: BY[r['case_id']].append(r)
fontfile='/System/Library/Fonts/Supplemental/Arial.ttf'
boldfile='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FONTS={n:ImageFont.truetype(fontfile,n) for n in [16,18,20,22,24,26,30,34]}
BOLD={n:ImageFont.truetype(boldfile,n) for n in [18,20,22,24,26,30,34]}
COPIED={}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy_asset(rel):
 if rel not in COPIED:
  src=SRC/rel;dst=OUT/'assets'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  a,b=sha(src),sha(dst)
  assert a==b
  COPIED[rel]={'sha256':a,'bytes':src.stat().st_size}
 return '../assets/'+rel

def esc(v):return str(v).replace('|','\\|').replace('\n',' ')
def pct(v):return 'not scored' if v is None else f'{100*v:.2f}%'
def flags(r,c):
 fixture=c['provenance']=='geometry_fixture'
 out=[]
 if fixture and r['variant']=='scene-v1':
  return ['TARGET DIFFERS (new contract not scored)'] if not r.get('correct') else ['TARGET MATCH (new contract not scored)']
 if r.get('correct') is False:
  out.append('WRONG TARGET' if r.get('metric_cohort')!='no_target' else 'NO-TARGET FAILURE')
 if r.get('label_retention') is not None and r['label_retention']<.98:out.append('EXPECTED LABEL LOSS')
 if r.get('expected_mode_match') is False:out.append('UNCERTAINTY MODE FAILURE')
 if r.get('conformance_pass') is False:out.append('CONTRACT FAILURE')
 return out

def bad(r,c):return bool(flags(r,c)) and not (c['provenance']=='geometry_fixture' and r['variant']=='scene-v1')
def row_label(r,c):
 f=flags(r,c)
 if c['provenance']=='geometry_fixture' and r['variant']=='scene-v1':return 'LEGACY: '+f[0]
 if f:return '**FAIL: '+', '.join(f)+'**'
 return 'Recorded checks pass' if r.get('correct') else 'Not scored'

def case_status(c,variant):
 rs=[r for r in BY[c['id']] if r['variant']==variant]
 if c['provenance']=='geometry_fixture' and variant=='scene-v1':return 'Contract N/A; '+', '.join(r['mode']+': '+('target match' if r['correct'] else 'target differs') for r in rs)
 fail=[r for r in rs if bad(r,c)]
 return '**FAIL** '+', '.join(r['mode']+': '+'; '.join(flags(r,c)) for r in fail) if fail else 'Recorded checks pass'

def wrapped(draw, text, xy, width, font, fill, maxlines=None, spacing=5):
 words=str(text).split();lines=[];line=''
 for word in words:
  trial=(line+' '+word).strip()
  if draw.textlength(trial,font=font)>width and line:lines.append(line);line=word
  else:line=trial
 if line:lines.append(line)
 if maxlines and len(lines)>maxlines:lines=lines[:maxlines];lines[-1]=lines[-1][:-3]+'...'
 x,y=xy
 for line in lines:draw.text((x,y),line,font=font,fill=fill);y+=font.size+spacing
 return y

def fit_canvas(im,size):
 im=im.convert('RGB');im.thumbnail(size,Image.Resampling.LANCZOS)
 canvas=Image.new('RGB',size,'#f2f4f7');canvas.paste(im,((size[0]-im.width)//2,(size[1]-im.height)//2));return canvas

def color_for(ident):
 h=hashlib.sha256(str(ident).encode()).digest();return tuple(70+x%150 for x in h[:3])

def masks_and_overlay(c):
 img=Image.open(SRC/c['image']).convert('RGB');overlay=img.convert('RGBA')
 entries=[]
 for a in c['annotations']:
  rel=copy_asset(a['mask']);mask=Image.open(SRC/a['mask']).convert('L')
  color=color_for(a['instance_id']);is_target=a['instance_id']==c.get('target_instance_id') or a.get('parent_instance_id')==c.get('target_instance_id')
  layer=Image.new('RGBA',img.size,color+(0,));layer.putalpha(mask.point(lambda x:92 if x else 0))
  overlay=Image.alpha_composite(overlay,layer)
  entries.append({'id':str(a['instance_id']),'label':a['category'],'parent':a.get('parent_instance_id'),'color':color,'box':a.get('box'),'path':rel,'target':is_target,'kind':'GT'})
 if not entries and c.get('fixture_detections'):
  for n,a in enumerate(c['fixture_detections']):
   raw=base64.b64decode(a.get('mask_png_b64',''))
   if not raw:continue
   mask=Image.open(io.BytesIO(raw)).convert('L');box=a['box'];full=Image.new('L',img.size)
   if mask.size==img.size:full=mask
   elif mask.size==(box[2]-box[0],box[3]-box[1]):full.paste(mask,box[:2])
   else:raise ValueError((c['id'],n,mask.size,box))
   rel=f'fixture-masks/{c["id"]}-d{n}.png';dest=OUT/rel;dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw)
   color=color_for('d'+str(n));layer=Image.new('RGBA',img.size,color+(0,));layer.putalpha(full.point(lambda x:92 if x else 0));overlay=Image.alpha_composite(overlay,layer)
   entries.append({'id':'d'+str(n),'label':a['label'],'parent':None,'color':color,'box':box,'path':'../'+rel,'target':c.get('expected_detection_id')=='d'+str(n),'kind':'fixture input'})
 # Drawing is a derived visualization; all RGB originals and binary masks are copied unchanged.
 d=ImageDraw.Draw(overlay)
 for e in entries:
  if e['box'] and (e['target'] or e['label'] in ['bottle','box','packet','wine bottle']):
   x1,y1,x2,y2=e['box'];color='#00ff88' if e['target'] else e['color'];d.rectangle((x1,y1,x2-1,y2-1),outline=color,width=max(2,round(img.width/300)))
   label=('TARGET ' if e['target'] else '')+e['id'];f=BOLD[18];w=d.textlength(label,font=f)
   y=max(0,y1-23);d.rectangle((x1,y,x1+w+8,y+23),fill='#111827');d.text((x1+4,y),label,font=f,fill=color)
 legendh=max(92,48+24*((len(entries)+1)//2))
 out=Image.new('RGB',(max(img.width,768),img.height+legendh),'#ffffff');out.paste(overlay.convert('RGB'),((out.width-img.width)//2,0));d=ImageDraw.Draw(out)
 heading='DECLARED FIXTURE INPUT MASKS' if c['provenance']=='geometry_fixture' else 'GROUND TRUTH MASKS | GREEN OUTLINE = EXPECTED SUBJECT'
 d.text((16,img.height+10),heading,font=BOLD[18],fill='#111827')
 if not entries:d.text((16,img.height+42),'No annotated target mask; full-frame/no-candidate control.',font=FONTS[18],fill='#374151')
 for i,e in enumerate(entries):
  col=i%2;row=i//2;x=16+col*(out.width//2);y=img.height+42+row*24
  d.rectangle((x,y+3,x+14,y+17),fill=e['color'])
  label=f'{e["id"]}: {e["label"]}'+(f' -> {e["parent"]}' if e['parent'] is not None else '')+(' [target]' if e['target'] else '')
  d.text((x+22,y),label,font=FONTS[16],fill='#111827')
 dest=OUT/'overlays'/f'{c["id"]}.png';dest.parent.mkdir(exist_ok=True);out.save(dest,optimize=True)
 return out,entries

for c in CASES:
 copy_asset(c['image'])
 for a in c['annotations']:
  copy_asset(a['mask'])
  if a.get('sha256'):assert COPIED[a['mask']]['sha256']==a['sha256']
 assert COPIED[c['image']]['sha256']==c['image_sha256']
for r in ROWS:
 for key in ['crop_path','keep_mask_path']:
  if r.get(key):copy_asset(r[key])
 for x in r.get('label_crop_paths',[]):copy_asset(x)
for directory in ['cases','groups','previews','evidence']:(OUT/directory).mkdir(exist_ok=True)
for n in ['cases.json','comparison.json','protocol.json','receipt.json','additional-findings.json','prediction-inputs.json','comparison-inputs.json','external-samples.json','real-v2-declaration.json','v2-declaration.json']:
 shutil.copyfile(SRC/n,OUT/'evidence'/n)

lookup={c['id']:c for c in CASES}
for index,c in enumerate(CASES):
 ident=c['id'];overlay,entries=masks_and_overlay(c);rs=BY[ident]
 mode='live' if any(r['mode']=='live' for r in rs) else 'fallback'
 primary={r['variant']:r for r in rs if r['mode']==mode}
 card=Image.new('RGB',(1680,940),'#ffffff');d=ImageDraw.Draw(card)
 d.rectangle((0,0,1680,132),fill='#111827')
 d.text((24,14),f'{ident} | {c["group"]} | {mode}',font=BOLD[30],fill='white')
 wrapped(d,c['name'],(24,54),1620,FONTS[24],'#e5e7eb',2)
 cols=[('INPUT PHOTO' if c['provenance']!='geometry_fixture' else 'GEOMETRY FIXTURE',Image.open(SRC/c['image'])),('ANNOTATION OVERLAY',overlay)]
 for variant in ['scene-v1','semantic-v2']:
  r=primary.get(variant)
  cols.append((variant.upper(),Image.open(SRC/r['crop_path']) if r and r.get('crop_path') else Image.new('RGB',(200,200),'white')))
 for j,(title,im) in enumerate(cols):
  x=20+j*415;d.text((x,148),title,font=BOLD[22],fill='#111827');card.paste(fit_canvas(im,(390,530)),(x,182))
  if j>1:
   variant=['scene-v1','semantic-v2'][j-2];r=primary.get(variant)
   isbad=r and bad(r,c);f=flags(r,c) if r else ['NO ROW'];legacy=c['provenance']=='geometry_fixture' and variant=='scene-v1'
   status=('CONTRACT N/A' if legacy else 'FAIL' if isbad else 'CHECKS PASS')
   fill='#b91c1c' if isbad else '#92400e' if legacy else '#166534'
   d.rounded_rectangle((x,728,x+390,770),radius=8,fill=fill);d.text((x+12,733),variant.upper()+': '+status,font=BOLD[22],fill='white')
   if r:
    wrapped(d,'; '.join(f) if f else 'Target and available label checks pass',(x,784),390,FONTS[18],fill,3)
    wrapped(d,'Reason: '+r['reason'],(x,858),390,FONTS[16],'#374151',2)
  elif j==0:
   expected=str(c.get('target_instance_id')) if c.get('target_instance_id') is not None else 'none / full frame'
   wrapped(d,'Expected subject: '+expected,(x,732),390,BOLD[22],'#111827',2)
   wrapped(d,'Not a photograph' if c['provenance']=='geometry_fixture' else 'Native render' if c['provenance']=='new_native_render' else 'COCO photo; label GT unavailable',(x,794),390,FONTS[18],'#374151',2)
  else:wrapped(d,'GT layers and legend are available at full size on the case page.',(x,732),390,FONTS[20],'#374151',3)
 d.text((20,916),'Frozen v2 inputs | Revised semantic-v2; original images, masks and emitted crops are linked unchanged.',font=FONTS[16],fill='#6b7280')
 card.save(OUT/'previews'/f'{ident}.jpg',quality=89,optimize=True)

 md=[f'# {ident} {c["name"]}', '',f'[All cases](../README.md) · [Group](../groups/{c["group"]}.md) · [Exact case metadata](../evidence/{ident}.json)', '',f'**scene-v1:** {case_status(c,"scene-v1")}  ',f'**semantic-v2:** {case_status(c,"semantic-v2")}', '',f'![{ident} comparison](../previews/{ident}.jpg)', '', '## Expected result', '',f'- Group: `{c["group"]}`; provenance: `{c["provenance"]}`.',f'- Expected subject: `{c.get("target_instance_id")}`; acceptable IDs: `{c.get("acceptable_instance_ids",[])}`.',f'- Expected status: `{c.get("expected_status")}`; expected selection mode: `{c.get("expected_selection_mode") or "not constrained"}`.',f'- Interaction: `{json.dumps(c.get("interaction",{}),ensure_ascii=False)}`.', f'- Annotation source: {c.get("annotation_source","not specified")}.', f'- Complete label GT: `{c.get("label_ground_truth",False)}`.']
 if c.get('target_explanation'):md+=['',c['target_explanation']]
 if c['provenance']=='geometry_fixture':md+=['','This is a diagnostic geometry fixture, not a photo. Input masks are declared fixture detections. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.']
 if c['provenance']=='coco_real_photo':
  source=c.get('source',{});license=source.get('license',{})
  md+=['',f'COCO image `{source.get("image_id")}` · [original source]({source.get("coco_url")}) · [Flickr source]({source.get("flickr_url")}) · [license: {license.get("name")}]({license.get("url")}).','', 'Real targets are developer judgments, not independently adjudicated user intent. COCO competitor coverage may be incomplete; no hand or complete-label ground truth is invented.']
 if c.get('review_note'):md+=['',str(c['review_note'])]
 md+=['','## Original input and masks','',f'![Original {ident}](../assets/{c["image"]})','',f'![Masks {ident}](../overlays/{ident}.png)','', '| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |','|---|---|---|---|---|']
 for e in entries:md.append(f'| `{e["id"]}` | {e["label"]} | `{e["parent"]}` | {"yes" if e["target"] else ""} | [view raw mask]({e["path"]}) |')
 if not entries:md+=['| none | no eligible masks | | full frame | |']
 md+=['','## Saved selector outputs','','`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.','']
 for m in ['live','controlled','fallback']:
  mr=[r for r in rs if r['mode']==m]
  if not mr:continue
  md+=[f'### {m}', '', '| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |','|---|---|---|---|---|---|']
  for r in mr:md.append(f'| `{r["variant"]}` | {row_label(r,c)} | `{r.get("matched_instance_id")}` | `{r.get("selection_mode")}` | {pct(r.get("label_retention"))} | `{esc(r["reason"])}` |')
  for r in mr:
   md+=['',f'#### {r["variant"]} {m} crop','',f'![{r["variant"]} {m} crop](../assets/{r["crop_path"]})' if r.get('crop_path') else 'No crop was recorded.']
   if r.get('keep_mask_path'):md+=['',f'[View original selector keep mask](../assets/{r["keep_mask_path"]})']
   if r.get('label_crop_paths'):md+=['', 'Label crop views: '+', '.join(f'[view {i+1}](../assets/{path})' for i,path in enumerate(r['label_crop_paths']))+'.']
 (OUT/'cases'/f'{ident}.md').write_text('\n'.join(md)+'\n')
 (OUT/'evidence'/f'{ident}.json').write_text(json.dumps({'case':c,'saved_outputs':rs},ensure_ascii=False,indent=2)+'\n')
 if index%30==0:print(f'Built {index+1}/{len(CASES)} cases',flush=True)

# Root and group indices make every case reachable in GitHub's Markdown renderer.
bygroup=defaultdict(list)
for c in CASES:bygroup[c['group']].append(c)
root=['# Issue 34 revised semantic-v2 photo and mask review', '', '[Tracking issue](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34)', '', f'All **{len(CASES)} cases** from frozen `main-selector-hardcases-v2`: **166 photo inputs** (153 native renders and 13 real photos) and **50 diagnostic geometry fixtures**. Each case has original input pixels, an annotated mask overlay, every available binary mask, both selectors\' saved crops and keep masks, and recorded expected results. No local files, custom viewer or downloaded archive is required: open the case links below.', '', '## How failures are marked', '', '- **SCENE-V1 FAIL / WRONG TARGET**: the frozen photo result does not match the declared target. Policy-defined choices and explicit interactions remain labeled by cohort; they are not independent user-intent accuracy.', '- **EXPECTED LABEL LOSS**: retained pixels of the expected target\'s annotated labels fall below the existing 98% threshold. This can occur with a correct target or a wrong target. Real photos without label GT are not assigned fabricated label scores.', '- **UNCERTAINTY MODE FAILURE**: semantic-v2 violates a required fallback/confident mode even if its selected ID matches.', '- **CONTRACT N/A**: geometry fixtures define the new semantic-v2 contract; legacy scene-v1 target differences are shown, not counted as failures against an unsupported contract.', '- A wrong selection that preserves its own label is still a wrong target. Crop coverage and distractor retention do not establish physical wine identity.', '', '## Groups', '', '| Group | Cases | scene-v1 photo cases with a target or label failure | Open all examples |', '|---|---:|---:|---|']
for gid,cs in bygroup.items():
 failures=sum(c['provenance']!='geometry_fixture' and any(bad(r,c) for r in BY[c['id']] if r['variant']=='scene-v1') for c in cs)
 root.append(f'| {GROUPS[gid]["title"]} | {len(cs)} | {failures if gid not in ["review","fallback"] else "contract N/A"} | [{gid}](groups/{gid}.md) |')
 gm=[f'# {GROUPS[gid]["title"]}', '', '[All groups](../README.md)', '',GROUPS[gid]['description'], '',f'{len(cs)} cases. Failures below use frozen result fields; photos and fixtures retain separate interpretation.', '', '| Case | scene-v1 | semantic-v2 |','|---|---|---|']
 for c in cs:gm.append(f'| [{c["id"]} {esc(c["name"])}](../cases/{c["id"]}.md) | {case_status(c,"scene-v1")} | {case_status(c,"semantic-v2")} |')
 gm+=['','## Visual examples','']
 for c in cs:gm+=[f'### {c["id"]} {c["name"]}', '',f'**scene-v1:** {case_status(c,"scene-v1")}', '', f'[Open original photo, all masks and every selector crop](../cases/{c["id"]}.md)', '',f'[![{c["id"]}](../previews/{c["id"]}.jpg)](../cases/{c["id"]}.md)', '']
 (OUT/'groups'/f'{gid}.md').write_text('\n'.join(gm)+'\n')
root+=['','## Every case','', '| Case | Group | scene-v1 | semantic-v2 |', '|---|---|---|---|']
for c in CASES:root.append(f'| [{c["id"]}](cases/{c["id"]}.md) | {c["group"]} | {case_status(c,"scene-v1")} | {case_status(c,"semantic-v2")} |')
root+=['','## Evidence and attribution','', '[Frozen cases](evidence/cases.json) · [Saved comparison](evidence/comparison.json) · [Original receipt](evidence/receipt.json) · [Photo sources and external samples](evidence/external-samples.json) · [Uploaded source file hashes](source-manifest.json).','', 'The source files in `assets/` are byte-for-byte copies. `overlays/` and `previews/` are derived presentation figures; their colors and resizing are not new ground truth. Original annotation ownership, mask hashes, image hashes, source provenance and saved outputs remain in each case JSON.','', 'COCO attribution and the exact source license accompany every real case. Native artwork/source geometry has no blanket redistribution license assertion; these materials are uploaded to the existing private repository for the requested review. Transparent packaging and mirror examples are proxies. Exact detector checkpoint revision was not disclosed in the frozen release.','', 'The revised selector passes 452 matcher tests, including twelve new regression methods in this revision. The current receipt and revision audit provide crop and label counts. Original targets and primary detector inputs remain frozen; optional enhancement inputs are separately hashed; no production rollout is part of this gallery.']
(OUT/'README.md').write_text('\n'.join(root)+'\n')

failrows=[]
for c in CASES:
 if c['provenance']=='geometry_fixture':continue
 for r in BY[c['id']]:
  if r['variant']=='scene-v1' and bad(r,c):failrows.append((c,r))
fm=['# scene-v1 photo failures', '', '[All cases](README.md) · [Tracking issue](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34)', '', 'Failures are listed by case and detection mode. Expected-label loss uses the saved <98% threshold; target misses use the saved `correct` field. Rows with both are listed once. These are development checks across several cohorts, not a combined accuracy estimate. Geometry fixtures are excluded because their new contract does not score legacy scene-v1.', '', '| Case | Cohort | Mode | Failure | Expected subject | Selected subject | Expected-label retention |', '|---|---|---|---|---|---|---|']
for c,r in failrows:fm.append(f'| [{c["id"]}](cases/{c["id"]}.md) | `{r["metric_cohort"]}` | {r["mode"]} | **{", ".join(flags(r,c))}** | `{c.get("target_instance_id")}` | `{r.get("matched_instance_id")}` | {pct(r.get("label_retention"))} |')
(OUT/'SCENE-V1-FAILURES.md').write_text('\n'.join(fm)+'\n')
(OUT/'source-manifest.json').write_text(json.dumps({'dataset':'main-selector-hardcases-v2-localization-fixes-20261020','source_relative_paths':COPIED,'source_case_count':len(CASES),'original_binary_mask_count':sum(len(c['annotations']) for c in CASES),'note':'Copied RGB, GT masks, emitted crops, keep masks and label crops; no regeneration.'},indent=2)+'\n')
summary={'cases':len(CASES),'groups':len(bygroup),'source_assets':len(COPIED),'source_bytes':sum(x['bytes'] for x in COPIED.values()),'scene_v1_photo_failure_rows':len(failrows),'scene_v1_photo_failure_cases':len({c['id'] for c,r in failrows}),'scene_v1_wrong_target_rows':sum(r['correct'] is False for c,r in failrows),'scene_v1_label_loss_rows':sum(r.get('label_retention') is not None and r['label_retention']<.98 for c,r in failrows)}
(OUT/'gallery-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
