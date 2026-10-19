from pathlib import Path
from types import SimpleNamespace
import sys,json,hashlib
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';N=R/'datasets/main-selector-hardcases-v2-localization-fixes-20261020';cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};recovery=json.loads((P/'detector-recovery.json').read_text())['cases'];rows=[]
for old in json.loads((P/'comparison.json').read_text()):
 c=cs[old['case_id']]
 if c['provenance']=='geometry_fixture':continue
 ds=json.loads((P/f'predictions/{c["id"]}-{old["mode"]}.json').read_text())['instances']
 if old['mode']=='live' and c['id'] in recovery:ds+=recovery[c['id']]['instances']
 mapped,iou=selected_gt(c,ds,SimpleNamespace(selected_id=old['selected_id']),P);assert mapped==old['matched_instance_id'],(c['id'],mapped,old['matched_instance_id']);rows.append(dict(case_id=c['id'],mode=old['mode'],variant=old['variant'],reported_id=old['matched_instance_id'],same_crop_rescored_id=mapped))
current={(r['case_id'],r['mode'],r['variant']):r for r in json.loads((N/'comparison.json').read_text())}
summary={}
for old in json.loads((P/'comparison.json').read_text()):
 c=cs[old['case_id']]
 if c['provenance']=='geometry_fixture':continue
 k='/'.join([old['mode'],'expansion' if c.get('extension') else 'original',old['metric_cohort'],old['variant']]);v=summary.setdefault(k,dict(cases=0,before_reported=0,before_rescored=0,after=0));v['cases']+=1;v['before_reported']+=int(old['correct']);v['before_rescored']+=int(old['correct']);v['after']+=int(current[(old['case_id'],old['mode'],old['variant'])]['correct'])
(N/'assignment-audit.json').write_text(json.dumps(dict(interpretation='Old selections rescored on their original effective inputs including the separately frozen carafe recovery. Zero assignment/scorer corrections. New selector behavior and new effective detections are shown separately in revision-diff.json.',scorer_body_unchanged=True,scorer_sha256=hashlib.sha256((R/"code/svoe-vino-lab-main-selector/matcher/experiments/main_selector/benchmark.py").read_bytes()).hexdigest(),selector_sha256=hashlib.sha256((R/"code/svoe-vino-lab-main-selector/matcher/semantic_selector.py").read_bytes()).hexdigest(),prediction_inputs_sha256=hashlib.sha256((N/"prediction-inputs.json").read_bytes()).hexdigest(),summary=summary,assignment_changes=[],rows=rows),indent=2)+'\n');print(len(rows),'old photo rows rescore identically')
