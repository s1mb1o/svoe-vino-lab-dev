from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import json,hashlib,sys,base64
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');repo=R/'code/svoe-vino-lab-main-selector';sys.path.insert(0,str(repo))
from matcher.experiments.main_selector.benchmark import selected_gt
from matcher.semantic_selector import IMPLEMENTATION_REVISION
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';N=R/'datasets/main-selector-hardcases-v2-localization-fixes-20261020';W=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();save=lambda name,obj:(N/name).write_text(json.dumps(obj,indent=2)+'\n')
old=json.loads((P/'comparison.json').read_text());new=json.loads((N/'comparison.json').read_text());cs={c['id']:c for c in json.loads((N/'cases.json').read_text())};enh=json.loads((N/'detector-enhancement.json').read_text())['cases']
key=lambda r:(r['case_id'],r['mode'],r['variant']);before={key(r):r for r in old};joint=lambda r:r['correct'] and r.get('expected_mode_match') is not False
changes=[];fixed=[];remaining=[];regressed=[];legacy=[];fields=['selected_id','matched_instance_id','selection_mode','reason','crop_scope','correct','expected_mode_match','label_retention','crop_box','label_boxes']
for a in new:
 b=before[key(a)]
 row=dict(case_id=a['case_id'],mode=a['mode'],cohort=a['metric_cohort'],before={f:b.get(f) for f in fields},after={f:a.get(f) for f in fields})
 if a['variant']=='scene-v1':
  if any(a.get(f)!=b.get(f) for f in fields):legacy.append(row)
  continue
 if any(a.get(f)!=b.get(f) for f in fields):changes.append(row)
 if not joint(b) and joint(a):fixed.append(row)
 if joint(b) and not joint(a):regressed.append(row)
 if not joint(a):
  c=cs[a['case_id']];items=enh[c['id']]['instances'] if c['id'] in enh and a['mode']=='live' else json.loads((N/f'predictions/{c["id"]}-{a["mode"]}.json').read_text())['instances'];geometry=[];targets=[]
  for d in a['candidates']:
   if not d['eligible_for_selection']:continue
   i=int(d['id'][1:]);item=items[i];left,top,right,bottom=d['box'];x,y=c['width']//2,c['height']//2
   with Image.open(BytesIO(base64.b64decode(item['mask_png_b64']))) as m:cover=left<=x<right and top<=y<bottom and bool(m.getpixel((x,y)))
   dist=(left+right-c['width'])**2+(top+bottom-c['height'])**2;owner,iou=selected_gt(c,items,SimpleNamespace(selected_id=d['id']),N);order=[not cover,dist,left+right,top+bottom,i]
   if owner==c['target_instance_id']:targets.append(d['id'])
   geometry.append(dict(id=d['id'],box=d['box'],contains_center=cover,distance_squared_x4=dist,mapped_gt_id=owner,assignment_iou=iou,order=order))
  oracle=min(geometry,key=lambda d:d['order'])['id'];assert oracle==a['selected_id'];annotated=[d for d in geometry if d['mapped_gt_id'] is not None];subset=min(annotated,key=lambda d:d['order']) if annotated else None
  remaining.append(dict(row,category='incomplete_annotation_candidate_set',explanation='Real closer bottles are absent from the frozen COCO polygons. Exact fallback chooses a legitimate unannotated candidate. Dropping candidates by GT membership would violate the requested input contract.',target_detection_ids=targets,independent_detector_fallback=oracle,annotated_subset_winner=subset,detector_geometry=geometry))
assert len(fixed)==7 and len(remaining)==1 and not regressed
assert {r['case_id'] for r in fixed}=={'hc-025','hc-035','hc-039','hc-041','hc-056','real-166918','real-397354'}
for name in ['comparison-inputs.json','cases.json','protocol.json','detector-recovery.json']:assert sha(P/name)==sha(N/name)
assert all(sha(p)==sha(N/'predictions'/p.name) for p in (P/'predictions').glob('*.json'))
diff=dict(revision=IMPLEMENTATION_REVISION,baseline_directory=P.name,current_directory=N.name,annotations_and_primary_caches_unchanged=True,scorer_unchanged=True,changed_rows=changes,joint_failures_fixed=fixed,joint_regressions=regressed,scene_v1_shared_input_changes=legacy,before_joint_failures=8,after_joint_failures=1)
save('revision-diff.json',diff);save('residual-failures.json',dict(revision=IMPLEMENTATION_REVISION,rows=remaining))
metrics=[]
for mode in ['controlled','live','fallback']:
 for cohort in ['passive_intent','interaction','policy_targets','no_target','rule_conformance']:
  br=[r for r in old if r['mode']==mode and r['metric_cohort']==cohort and r['variant']=='semantic-v2'];nr=[r for r in new if r['mode']==mode and r['metric_cohort']==cohort and r['variant']=='semantic-v2'];lr=[r for r in new if r['mode']==mode and r['metric_cohort']==cohort and r['variant']=='scene-v1']
  if br:metrics.append(dict(scope=mode+' / '+cohort,before=f'{sum(map(joint,br))}/{len(br)}',after=f'{sum(map(joint,nr))}/{len(nr)}',legacy='not scored' if cohort=='rule_conformance' else f'{sum(r["correct"] for r in lr)}/{len(lr)}'))
labels=json.loads((N/'additional-findings.json').read_text());semantic=[r for r in new if r['variant']=='semantic-v2'];assert all(r['selected_label_retention']==1.0 for r in labels['rows'] if r['selected_label_retention'] is not None)
metadata=dict(title='semantic-v2 localization and small-bottle recovery · 20 October 2026',legacy_heading='scene-v1 with shared enhanced inputs',revision=IMPLEMENTATION_REVISION,selector_sha256=sha(repo/'matcher/semantic_selector.py'),explanation='Same 216 cases and 319 original primary detector caches. Eight small-bottle fallback scenes receive separately frozen image-only enhancement inputs, shared by both algorithms. No target, GT mask, fallback ordering or assignment scorer changed. This is a new development revision, not an independent accuracy estimate.',crop_contract=f'{sum(bool(r.get("crop_path")) for r in semantic)}/{len(semantic)} results return crops',label_contract=f'{labels["assigned_selected_labels_ge98"]}/{labels["assigned_selected_label_trials"]} selected-subject label checks retain 100% of pixels',metrics=metrics,residual_explanation='Seven of eight failures resolved; zero new joint-contract regressions. real-117719 remains a failure: actual nearer bottles are missing from the frozen annotation set. No GT-based candidate filtering or tie tolerance was introduced.',files_sha256={name:sha(N/name) for name in ['revision-diff.json','residual-failures.json']})
save('evaluation-revision.json',metadata);print(json.dumps(dict(fixed=7,remaining=1,regressions=0,legacy_changed_rows=len(legacy),metrics=metrics,crops=metadata['crop_contract'],labels=metadata['label_contract']),indent=2))
