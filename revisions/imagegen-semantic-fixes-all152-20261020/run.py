"""Pinned, offline three-selector comparison; source annotations remain proposals."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent
WORK = OUT.parent.parent
SOURCE = WORK / 'code/svoe-vino-lab-main-selector'
DIS_SOURCE = Path('/private/tmp/svoe-vino-dis-v1')
MODEL = Path('/Users/ashmelev/.cache/huggingface/hub/models--litert-community--DIS-ISNet-LiteRT/snapshots/1b966dbe2f33bd5ca1299cf94fbab59265210b6b/dis.tflite')
DATASETS = [
    ('pilot-v1', 'main-selector-imagegen-pilot-v1-20261019', 30, 'reviews/user-review-amendments-20261020-v2.json'),
    ('hardcases-v2', 'main-selector-imagegen-hardcases-v2-20261020', 20, 'reviews/user-review-20261020T063637Z.json'),
    ('diverse-v3', 'main-selector-imagegen-diverse-v3-20261020', 102, None),
]
VARIANTS = ('scene-v1', 'semantic-v2', 'dis-v1')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.name != '.DS_Store'}


def copy(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    assert sha(source) == sha(dest)


def prepare():
    if (OUT / 'protocol.json').exists():
        return json.loads((OUT / 'protocol.json').read_text())
    baseline = OUT.parent / 'main-selector-imagegen-all152-20261020-current-v1'
    context_source = WORK / 'planning/selector-imagegen-fixes-20261020/context'
    preservation = {name: inventory(OUT.parent / name) for _,name,_,_ in DATASETS}
    preservation[baseline.name] = inventory(baseline)
    write(OUT / 'preservation-before.json', preservation)
    for directory in ['images','detections','masks','source-data']:
        for path in sorted((baseline/directory).rglob('*')):
            if path.is_file(): copy(path,OUT/path.relative_to(baseline))
    for name in ['cases-frozen.json','deduplication.json','additions-preservation.json']:
        copy(baseline/name,OUT/name)
    for path in sorted(context_source.glob('*.json')):
        copy(path,OUT/'context'/path.name)
    cases=json.loads((OUT/'cases-frozen.json').read_text())
    assert len(cases)==152
    context_hashes={}
    for c in cases:
        path=OUT/'context'/(c['slug']+'.json')
        aux=json.loads(path.read_text())
        assert aux['image_sha256']==c['image_sha256']
        assert aux['target_or_annotation_supplied'] is False
        context_hashes[c['slug']]=sha(path)
    runtime=OUT/'runtime/matcher';runtime.mkdir(parents=True,exist_ok=True)
    sources={}
    for path in sorted((SOURCE/'matcher').glob('*.py')):
        copy(path,runtime/path.name)
        sources[path.name]={'path':str(path),'sha256':sha(path)}
    copy(DIS_SOURCE/'matcher/dis_selector.py',runtime/'dis_selector.py')
    sources['dis_selector.py']={'path':str(DIS_SOURCE/'matcher/dis_selector.py'),'sha256':sha(runtime/'dis_selector.py')}
    for path in sorted((SOURCE/'matcher/tests').rglob('*')):
        if path.is_file() and path.suffix in ['.py','.json']:
            copy(path,OUT/'checks'/path.relative_to(SOURCE/'matcher/tests'))
    tree=ast.parse((runtime/'semantic_selector.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_fallback')
    fallback=hashlib.sha256(ast.dump(fn,include_attributes=False).encode()).hexdigest()
    prior=json.loads((baseline/'protocol.json').read_text())
    assert fallback==prior['fallback_ast_sha256']['current']
    protocol={**prior,'created_at':datetime.now(timezone.utc).isoformat(),
        'source_files':sources,'baseline_bundle':baseline.name,'baseline_protocol_sha256':sha(baseline/'protocol.json'),
        'cases_sha256':sha(OUT/'cases-frozen.json'),'context_sha256':context_hashes,
        'implementation_revision':next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IMPLEMENTATION_REVISION' for t in n.targets)),
        'fallback_ast_sha256':{'current':fallback,'frozen_baseline':fallback},
        'source_dirty_status':subprocess.check_output(['git','-C',str(SOURCE),'status','--short'],text=True),
        'python':platform.python_version(),
        'execution':{'sam3_selectors':'Fresh pinned selector replay on frozen primary proposals plus fixed image-only auxiliary context masks. Identical appended context and unchanged primary dN IDs for both selectors.',
            'context':'152 additional RGB-only SAM3 requests; fixed English nouns, default thresholds; no target, annotation or desired answer supplied. The service does not expose a checkpoint revision. Saved responses contain validated instances, not raw transport envelopes.',
            'sam3_prompt_difference':prior['execution']['sam3_prompt_difference'],
            'dis':'Fresh local CPU inference on all 152 originals, same pinned LiteRT model and configuration.',
            'configuration':'select_variant with supplied instances, tap=None, aim=None; exact frozen fallback unchanged.'}}
    write(OUT/'protocol.json',protocol)
    write(OUT/'contract-preservation.json',{'fallback_ast_sha256':fallback,'frozen_targets_byte_identical':sha(OUT/'cases-frozen.json')==sha(baseline/'cases-frozen.json'),
        'frozen_scorer_ast_identical':ast.dump(ast.parse(Path(__file__).read_text()).body[[isinstance(n,ast.FunctionDef) and n.name=='assess' for n in ast.parse(Path(__file__).read_text()).body].index(True)],include_attributes=False)==ast.dump(next(n for n in ast.parse((baseline/'run.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='assess'),include_attributes=False),
        'historical_reports_overwritten':False})
    return protocol


def assess(decision, case):
    box = list(decision.crop_box or [])
    keep = np.asarray(decision.keep_mask.convert('L'))
    assert keep.shape == (case['height'], case['width'])
    assert len(box) == 4 and 0 <= box[0] < box[2] <= case['width'] and 0 <= box[1] < box[3] <= case['height']
    inside = np.zeros(keep.shape, bool)
    inside[box[1]:box[3], box[0]:box[2]] = True
    retained = inside & (keep >= 128)
    full = box == [0, 0, case['width'], case['height']] and bool((keep == 255).all())
    with Image.open(BytesIO(decision.crop)) as crop:
        assert crop.size == (box[2] - box[0], box[3] - box[1])
        crop_size = list(crop.size)
    target = case['expectation']['target']
    agreed = decision.selected_id in case['accepted_targets']
    if 'full_context' in case['accepted_targets'] and full:
        agreed = True
    if target == 'full_frame':
        agreed = full and decision.status == 'no_target'
    result = {'target': target, 'accepted_targets': case['accepted_targets'],
              'target_agreement': bool(agreed) if decision.variant != 'dis-v1' else None,
              'cohort': case['cohort'], 'human_mask_approved': False,
              'preserves_full_original_frame': full, 'crop_size_px': crop_size,
              'crop_available': True, 'crop_usability_review': 'pending_human_review',
              'label_legibility_review': 'pending_human_review',
              'target_retention_proxy': None, 'maximum_other_bottle_retention_proxy': None,
              'isolation_proxy_pass': None, 'label_retention_proxies': []}
    if target in ['full_frame', 'full_context']:
        result['isolation_proxy_pass'] = bool(full and (target != 'full_frame' or decision.status == 'no_target'))
        return result
    masks = {}
    for p in case['mask_proposals']:
        if p['id'] == target or p['label'] in ['wine bottle', 'bottle', 'wine label']:
            with Image.open(OUT / p['mask_path']) as opened:
                masks[p['id']] = np.asarray(opened.convert('L')) >= 128
    expected = masks[target]
    result['target_retention_proxy'] = float((retained & expected).sum()) / max(1, int(expected.sum()))
    others, attributions = [], []
    for p in case['mask_proposals']:
        if p['id'] not in masks:
            continue
        mask = masks[p['id']]
        overlap = int((mask & expected).sum())
        same = overlap / max(1, int((mask | expected).sum()))
        fraction = float((retained & mask).sum()) / max(1, int(mask.sum()))
        if p['label'] == 'wine label' and overlap / max(1, int(mask.sum())) >= .8:
            result['label_retention_proxies'].append({'id': p['id'], 'retention': fraction, 'source_area_px': int(mask.sum()),
                                                        'ownership': 'unreviewed_geometric_overlap'})
        if p['label'] in ['wine bottle', 'bottle'] or p['id'] == target:
            attributions.append({'id': p['id'], 'iou': float((retained & mask).sum()) / max(1, int((retained | mask).sum()))})
            if p['id'] != target and same < .5:
                others.append({'id': p['id'], 'retention': fraction})
    result['maximum_other_bottle_retention_proxy'] = max((x['retention'] for x in others), default=0.)
    result['other_bottle_retention_proxies'] = others
    result['best_mask_attribution'] = max(attributions, key=lambda x: x['iou']) if attributions else None
    result['isolation_proxy_pass'] = result['target_retention_proxy'] >= .95 and result['maximum_other_bottle_retention_proxy'] <= .10
    result['minimum_target_label_retention_proxy'] = min((x['retention'] for x in result['label_retention_proxies']), default=None)
    return result


def run():
    protocol = prepare()
    assert sha(OUT / 'cases-frozen.json') == protocol['cases_sha256']
    for name, meta in protocol['source_files'].items():
        assert sha(OUT / 'runtime/matcher' / name) == meta['sha256']
    sys.path.insert(0, str(OUT / 'runtime'))
    from matcher.semantic_selector import select_variant
    from matcher.dis_selector import select as select_dis, MODEL_SHA256
    from matcher.group import _validate_sam3
    assert sha(MODEL) == MODEL_SHA256 == protocol['dis_model_sha256']
    cases = json.loads((OUT / 'cases-frozen.json').read_text())
    for variant in VARIANTS:
        for case in cases:
            dest = OUT / 'results' / (case['slug'] + '-' + variant + '.json')
            if dest.exists():
                continue
            assert sha(OUT / case['image_path']) == case['image_sha256']
            assert sha(OUT / case['detector_path']) == case['detector_sha256']
            raw = json.loads((OUT / case['detector_path']).read_text())
            instances = _validate_sam3(raw['response'], case['width'], case['height'],
                                       labels=tuple(x.strip() for x in raw['request_nouns'].split(',')))
            context_path = OUT / 'context' / (case['slug'] + '.json')
            assert sha(context_path) == protocol['context_sha256'][case['slug']]
            auxiliary = json.loads(context_path.read_text())
            envelope = dict(auxiliary['response'], width=case['width'], height=case['height'], count=len(auxiliary['response']['instances']))
            instances += _validate_sam3(envelope, case['width'], case['height'], labels=tuple(x.strip() for x in auxiliary['request_nouns'].split(',')))
            with Image.open(OUT / case['image_path']) as opened:
                image = opened.convert('RGB')
            start = time.perf_counter()
            decision = select_dis(image, MODEL, timeout=120) if variant == 'dis-v1' else select_variant(image, instances, variant=variant)
            elapsed = time.perf_counter() - start
            assert decision.crop is not None and decision.keep_mask is not None
            paths = {}
            for key, directory in [('crop', 'crops'), ('keep_mask', 'keep-masks')]:
                path = OUT / directory / (case['slug'] + '-' + variant + '.png')
                path.parent.mkdir(exist_ok=True)
                if key == 'crop':
                    path.write_bytes(decision.crop)
                else:
                    decision.keep_mask.save(path)
                paths[key + '_path'] = str(path.relative_to(OUT))
                paths[key + '_sha256'] = sha(path)
            labels = []
            for i, body in enumerate(decision.label_crops):
                path = OUT / 'label-crops' / (case['slug'] + '-' + variant + '-' + str(i) + '.png')
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(body)
                labels.append(str(path.relative_to(OUT)))
            row = {'case_key': case['key'], 'slug': case['slug'], 'dataset': case['dataset'], 'variant': variant,
                   'image_sha256': case['image_sha256'], 'selector_seconds': elapsed,
                   'decision': decision.as_dict(media=False), **paths, 'label_crop_paths': labels,
                   'assessment': assess(decision, case),
                   'execution_provenance': 'fresh_local_DIS_prediction' if variant == 'dis-v1' else 'fresh_selector_frozen_primary_plus_RGB_only_context_replay'}
            write(dest, row)
            print(json.dumps({'case': case['key'], 'variant': variant, 'selected': decision.selected_id,
                              'target_agreement': row['assessment']['target_agreement'],
                              'isolation_proxy': row['assessment']['isolation_proxy_pass'], 'seconds': round(elapsed, 3)}), flush=True)
    rows = [json.loads((OUT / 'results' / (c['slug'] + '-' + v + '.json')).read_text()) for c in cases for v in VARIANTS]
    unique = {c['key'] for c in cases if c['count_in_unique_source_metrics']}
    summaries = {}
    for cohort in ['all_unique_sources', 'scene_confirmed_masks_pending', 'scene_pending_masks_pending']:
        summaries[cohort] = {}
        for variant in VARIANTS:
            subset = [r for r in rows if r['case_key'] in unique and r['variant'] == variant and
                      (cohort == 'all_unique_sources' or r['assessment']['cohort'] == cohort)]
            summaries[cohort][variant] = {'rows': len(subset),
                'target_agreements': sum(r['assessment']['target_agreement'] is True for r in subset) if variant != 'dis-v1' else None,
                'isolation_proxy_passes': sum(r['assessment']['isolation_proxy_pass'] is True for r in subset),
                'crop_count': sum(r['assessment']['crop_available'] for r in subset),
                'crop_usability_approved': 0, 'median_selector_seconds': float(np.median([r['selector_seconds'] for r in subset])),
                'target_disagreement_case_keys': [r['case_key'] for r in subset if r['assessment']['target_agreement'] is False],
                'isolation_proxy_failure_case_keys': [r['case_key'] for r in subset if r['assessment']['isolation_proxy_pass'] is False]}
    write(OUT / 'results.json', {'protocol_sha256': sha(OUT / 'protocol.json'), 'summaries': summaries, 'rows': rows,
                               'execution_counts': {'fresh_selector_replays': 304, 'fresh_DIS_predictions': 152, 'new_detector_requests': 152, 'new_primary_detector_requests': 0, 'new_detector_requests_during_selector_replay': 0, 'RGB_only_context_requests_before_replay': 152},
                               'confirmed_mask_annotation_score': None})
    print(json.dumps(summaries), flush=True)


if __name__ == '__main__':
    run()
