from pathlib import Path
from types import SimpleNamespace
import json,base64,sys
R=Path('/Volumes/Storage/svoe-vino-final');sys.path.insert(0,str(R/'code/svoe-vino-lab-main-selector'))
from matcher.experiments.main_selector.benchmark import selected_gt
P=R/'datasets/main-selector-hardcases-v2-detector-fixes-20261020';W=Path(__file__).parent;cs={c['id']:c for c in json.loads((P/'cases.json').read_text())};enh=json.loads((W/'detector-enhancement.json').read_text())['cases'];rows=[]
for cid in ['hc-025','hc-035','hc-039','hc-041','hc-056','real-166918','real-397354','real-117719']:
 c=cs[cid];primary=json.loads((P/f'predictions/{cid}-live.json').read_text())['instances'];ds=enh[cid]['instances'] if cid in enh else primary;owners={f'd{i}':selected_gt(c,ds,SimpleNamespace(selected_id=f'd{i}'),P)[0] for i in range(len(ds))};labels={}
 for a in c['annotations']:
  if a['category'].startswith('label_'):labels.setdefault(str(a['instance_id']),[]).append(base64.b64encode((P/a['mask']).read_bytes()).decode())
 row=dict(case_id=cid,mode='live',size=[c['width'],c['height']],instances=ds,primary=primary,detector_owners=owners,target_detection_ids=[k for k,v in owners.items() if v==c['target_instance_id']],labels_by_gt_owner=labels,expected_target_id=c['target_instance_id'],expected_selection_mode=c['expected_selection_mode'])
 if cid in enh:row['responses']=[json.loads((W/f).read_text())['instances'] for f in enh[cid]['raw_responses']]
 rows.append(row)
out=R/'code/svoe-vino-lab-main-selector/matcher/tests/data/semantic-v2-localization-regressions-20261020.json';out.write_text(json.dumps(dict(provenance='Frozen detector masks from development cases; RGB for unit replay is synthetic, actual RGB retention checked by full comparison',rows=rows),indent=2)+'\n');print(out,out.stat().st_size)
