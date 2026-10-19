from pathlib import Path
import sys,json,importlib.util,hashlib
from PIL import Image
R=Path('/Volumes/Storage/svoe-vino-final');repo=R/'code/svoe-vino-lab-main-selector';W=Path(__file__).parent;N=R/'datasets/main-selector-hardcases-v2-localization-fixes-20261020';sys.path.insert(0,str(repo))
from matcher.semantic_selector import select
from matcher.experiments.main_selector.benchmark import selected_gt
spec=importlib.util.spec_from_file_location('matcher.prior_selector',W/'before/matcher/semantic_selector.py');prior=importlib.util.module_from_spec(spec);sys.modules[spec.name]=prior;spec.loader.exec_module(prior)
cs={c['id']:c for c in json.loads((N/'cases.json').read_text())};enh=json.loads((N/'detector-enhancement.json').read_text())['cases'];rows=[]
for cid in ['hc-025','hc-035','hc-039','hc-041','hc-056','real-166918','real-397354','real-117719']:
 c=cs[cid];im=Image.open(N/c['image']).convert('RGB');primary=json.loads((N/f'predictions/{cid}-live.json').read_text())['instances'];effective=enh[cid]['instances'] if cid in enh else primary;b=prior.select(im,primary);a=select(im,effective);bo=selected_gt(c,primary,b,N)[0];ao=selected_gt(c,effective,a,N)[0];bp=bo==c['target_instance_id'] and b.selection_mode==c['expected_selection_mode'];ap=ao==c['target_instance_id'] and a.selection_mode==c['expected_selection_mode'];assert not bp;assert ap==(cid!='real-117719');rows.append(dict(case_id=cid,before_pass=bp,after_pass=ap,before_selected=b.selected_id,after_selected=a.selected_id,before_owner=bo,after_owner=ao,after_crop=bool(a.crop)))
(N/'regression-proof.json').write_text(json.dumps(dict(prior_source_sha256=hashlib.sha256((W/'before/matcher/semantic_selector.py').read_bytes()).hexdigest(),interpretation='Prior selector with original primary inputs vs new selector with declared image-only enhanced inputs. No GT was provided during enhancement. Diagnostic frozen target IDs are used by this scorer only.',rows=rows),indent=2)+'\n');print('seven fail-before/pass-after cases; one honest residual')
