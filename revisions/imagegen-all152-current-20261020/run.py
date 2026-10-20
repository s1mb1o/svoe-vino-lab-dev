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
    preservation = {}
    for _, name, _, _ in DATASETS:
        preservation[name] = inventory(OUT.parent / name)
    write(OUT / 'preservation-before.json', preservation)
    runtime = OUT / 'runtime/matcher'
    runtime.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name in ['__init__.py', 'group.py', 'main_scene.py', 'semantic_selector.py',
                 'semantic_intent.py', 'selector_detection.py', 'dis_selector.py']:
        path = (DIS_SOURCE if name == 'dis_selector.py' else SOURCE) / 'matcher' / name
        before = sha(path)
        copy(path, runtime / name)
        assert sha(path) == before
        sources[name] = {'path': str(path), 'sha256': before}
    for name, meta in sources.items():
        assert sha(meta['path']) == meta['sha256'], 'Source changed during snapshot'
    trees = {}
    for revision, path in [('current', runtime / 'semantic_selector.py'),
                           ('prior_localization', WORK / 'datasets/main-selector-hardcases-v2-localization-fixes-20261020/implementation/matcher/semantic_selector.py')]:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_fallback')
        trees[revision] = hashlib.sha256(ast.dump(fn, include_attributes=False).encode()).hexdigest()
    if len(trees) == 2:
        assert len(set(trees.values())) == 1, 'Frozen fallback contract changed'
    registry = []
    dataset_meta = []
    for short, name, count, review_name in DATASETS:
        root = OUT.parent / name
        data = json.loads((root / 'review-data.json').read_text())
        assert data['dataset'] == name and len(data['cases']) == count
        reviews = {}
        if review_name:
            review = json.loads((root / review_name).read_text())
            assert not review.get('qa_session') and review['dataset'] == name
            reviews = {c['id']: c for c in review['cases']}
            assert len(reviews) == count and all(c['verdict'] == 'accept' for c in reviews.values())
        frozen = OUT / 'source-data' / short
        for p in sorted(root.iterdir()):
            if p.is_file() and p.suffix == '.json':
                copy(p, frozen / p.name)
        for p in (root / 'reviews').glob('*.json'):
            copy(p, frozen / 'reviews' / p.name)
        for c in data['cases']:
            ident = c['id']
            key = name + ':' + ident
            slug = short + '--' + ident
            photo = root / c['image_path']
            assert sha(photo) == c['image_sha256']
            raw = root / 'annotations' / (ident + '-sam3-proposals.json')
            copy(photo, OUT / 'images' / (slug + photo.suffix))
            copy(raw, OUT / 'detections' / (slug + '.json'))
            proposals = []
            for proposal in c['mask_proposals']:
                p = dict(proposal)
                target = OUT / 'masks' / (slug + '-' + p['id'] + '.png')
                copy(root / p['mask_path'], target)
                p['source_mask_path'] = p['mask_path']
                p['mask_path'] = str(target.relative_to(OUT))
                p['mask_sha256'] = sha(target)
                proposals.append(p)
            proposal = c['agent_target_proposal']
            rv = reviews.get(ident)
            if rv:
                assert rv.get('original_image_sha256', c['image_sha256']) == c['image_sha256']
                expectation = {k: rv.get(k) for k in ['intent', 'target', 'target_source', 'maskVerdict', 'accepted_targets', 'notes']}
                cohort = 'scene_confirmed_masks_pending'
            else:
                expectation = {'intent': proposal['proposed_intent'], 'target': proposal['target'],
                               'target_source': 'unreviewed_agent_proposal', 'maskVerdict': 'pending',
                               'accepted_targets': None}
                cohort = 'scene_pending_masks_pending'
            assert expectation['maskVerdict'] == 'pending'
            accepted = expectation.get('accepted_targets') or [expectation['target']]
            assert all(t in ['full_context', 'full_frame'] or t in {p['id'] for p in proposals} for t in accepted)
            registry.append({
                'key': key, 'slug': slug, 'dataset': name, 'dataset_short': short, 'source_case_id': ident,
                'family': c['family'], 'title_reference': c['review_title_ru'],
                'description_reference': proposal.get('description_ru'), 'declared_intent': c['declared_intent'],
                'expectation': expectation, 'accepted_targets': accepted, 'cohort': cohort,
                'human_scene_confirmed': bool(rv), 'human_mask_approved': False,
                'usable_as_ground_truth': False, 'prompt_reference': c['prompt'],
                'agent_notes_reference': c.get('agent_notes_ru', []),
                'image_path': str((OUT / 'images' / (slug + photo.suffix)).relative_to(OUT)),
                'image_sha256': sha(photo), 'width': c['width'], 'height': c['height'],
                'detector_path': 'detections/' + slug + '.json', 'detector_sha256': sha(raw),
                'mask_proposals': proposals,
                'scene_independence_group': name + ':' + ('GP02-with-GP11' if short == 'diverse-v3' and ident in ['GP02', 'GP11'] else ident),
                'split': 'development_only_no_independent_test_claim',
            })
        dataset_meta.append({'dataset': name, 'case_count': count, 'review_path': review_name,
                             'human_scene_confirmed': len(reviews), 'human_mask_approved': 0,
                             'source_manifest_sha256': sha(root / 'manifest.json')})
    assert len(registry) == 152 and len({c['key'] for c in registry}) == 152
    by_hash = defaultdict(list)
    for c in registry:
        by_hash[c['image_sha256']].append(c['key'])
    # Index original-image directories only; derived crops and masks are not test inputs.
    prior = defaultdict(list)
    for directory in sorted(OUT.parent.glob('main-selector*/images')):
        if directory.parent == OUT or any(directory.parent.name == n for _, n, _, _ in DATASETS):
            continue
        for p in sorted(directory.iterdir()):
            if p.is_file() and p.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                digest = sha(p)
                if digest in by_hash:
                    prior[digest].append(str(p.relative_to(WORK)))
    for c in registry:
        c['exact_duplicate_group'] = by_hash[c['image_sha256']]
        c['count_in_unique_source_metrics'] = c['key'] == by_hash[c['image_sha256']][0]
        c['prior_corpus_exact_matches'] = prior.get(c['image_sha256'], [])
        short = c['dataset_short']
        old = {'pilot-v1': 'main-selector-imagegen-pilot-v1-20261019/runs/three-selectors-20261020-v2',
               'hardcases-v2': 'main-selector-imagegen-hardcases-v2-20261020/runs/three-selectors-20261020-v1'}.get(short)
        c['previous_comparison'] = old
    write(OUT / 'cases-frozen.json', registry)
    write(OUT / 'deduplication.json', {'selected_records': 152, 'unique_source_hashes': len(by_hash),
          'duplicate_source_groups': [v for v in by_hash.values() if len(v) > 1],
          'matches_in_other_original_image_directories': dict(prior),
          'historically_tested_selected_images': 50, 'new_pending_selected_images': 102,
          'scene_independence_group_keys': len({c['scene_independence_group'] for c in registry}),
          'split_policy': 'No dataset split or held-out accuracy claim. GP02 and its reference edit GP11 share one group.'})
    protocol = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'variants': VARIANTS,
        'selected_case_count': 152, 'expected_results': 456, 'datasets': dataset_meta,
        'source_files': sources, 'fallback_ast_sha256': trees,
        'source_git_heads': {str(p): subprocess.check_output(['git', '-C', str(p), 'rev-parse', 'HEAD'], text=True).strip() for p in [SOURCE, DIS_SOURCE]},
        'source_dirty_status': subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--short'], text=True),
        'implementation_revision': next(n.value.value for n in ast.parse((runtime / 'semantic_selector.py').read_text()).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IMPLEMENTATION_REVISION' for t in n.targets)),
        'python': platform.python_version(), 'packages': {p: importlib.metadata.version(p) for p in ['numpy', 'Pillow', 'ai-edge-litert']},
        'dis_model_path': str(MODEL), 'dis_model_sha256': sha(MODEL),
        'execution': {'sam3_selectors': 'Fresh current-code selector replay on frozen SAM3 review proposals; unchanged response order and dN IDs; no new detector request, tracker or central recovery.',
                      'sam3_prompt_difference': 'Review proposal nouns include wine glass and omit can relative to the production semantic prompt.',
                      'dis': 'Fresh local CPU inference on all unique selected originals; pinned LiteRT model, four interpreter threads, 120 second timeout.',
                      'configuration': 'Default select_variant with supplied instances; tap=None; aim=None. Exact frozen fallback unchanged.'},
        'scoring': {'target_agreement': 'Selected dN equals an accepted target, or exact full-frame/context expectation. DIS has no native target ID and is never assigned semantic accuracy.',
                    'proxies': 'Target mask retention >=95% and other bottle mask retention <=10%, excluding proposal duplicates at IoU>=0.5; masks and owners unreviewed.',
                    'label_proxy': 'Wine-label proposals with >=80% of their mask inside the proposed target; report retained fraction and area. Ownership and legibility are not ground truth.',
                    'usability': 'Target agreement alone is not crop usefulness. No automatic PASS for legibility. Human crop-usability review remains pending for every result.',
                    'confirmed_annotation_accuracy': 'Not reported: zero human-approved masks. Separate scene-confirmed and pending-scene cohorts.'},
        'cases_sha256': sha(OUT / 'cases-frozen.json'),
        'provenance': 'Selected cases only. Rejected, blocked and canceled attempts are retained in source-data JSON provenance and excluded from accepted-scene denominators.',
        'limitations': ['Synthetic development images, including previously used development cases; not independent real-world accuracy.',
                        'Fifty scene approvals do not approve detector masks or their ownership; all mask metrics are provisional.',
                        'The 102 pending scenes, including GP11 and SP01, are exploratory only.',
                        'No visual target, ground truth, fallback contract or historical report is changed by this run.'],
    }
    write(OUT / 'protocol.json', protocol)
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
                   'execution_provenance': 'fresh_local_DIS_prediction' if variant == 'dis-v1' else 'fresh_current_selector_frozen_proposal_replay'}
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
                               'execution_counts': {'fresh_selector_replays': 304, 'fresh_DIS_predictions': 152, 'new_detector_requests': 0},
                               'confirmed_mask_annotation_score': None})
    print(json.dumps(summaries), flush=True)


if __name__ == '__main__':
    run()
