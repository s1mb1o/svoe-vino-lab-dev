"""Verify input preservation, media, crop invariants and portable report links."""
import ast
import base64
import hashlib
from collections import Counter
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

import numpy as np
from PIL import Image

from run import OUT, WORK, DATASETS, VARIANTS, inventory, sha, write


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.articles = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ['href', 'src']:
            if key in attrs:
                self.paths.append(attrs[key])
        if tag == 'article':
            self.articles.append(attrs['id'])


def main():
    cases = json.loads((OUT / 'cases-frozen.json').read_text())
    results = json.loads((OUT / 'results.json').read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    assert len(cases) == 152 and len(results['rows']) == 456
    assert len({c['key'] for c in cases}) == 152
    assert len({c['image_sha256'] for c in cases}) == 152
    assert Counter(r['variant'] for r in results['rows']) == {v: 152 for v in VARIANTS}
    assert all(not c['human_mask_approved'] and not c['usable_as_ground_truth'] for c in cases)
    assert sum(c['human_scene_confirmed'] for c in cases) == 50
    groups = {c['source_case_id']: c['scene_independence_group'] for c in cases if c['dataset_short'] == 'diverse-v3'}
    assert groups['GP02'] == groups['GP11']
    assert all(any(r['case_key'] == c['key'] and r['variant'] == v for r in results['rows']) for c in cases for v in VARIANTS)
    by_key = {c['key']: c for c in cases}
    source_image_checks, source_mask_checks, selected_label_checks, crop_checks, rgb_checks = 0, 0, 0, 0, 0
    label_audit = []
    for name, meta in protocol['source_files'].items():
        assert sha(OUT / 'runtime/matcher' / name) == meta['sha256']
    for c in cases:
        assert sha(OUT / c['image_path']) == c['image_sha256']
        assert sha(OUT / c['detector_path']) == c['detector_sha256']
        source_image_checks += 1
        for p in c['mask_proposals']:
            assert sha(OUT / p['mask_path']) == p['mask_sha256']
            with Image.open(OUT / p['mask_path']) as opened:
                assert opened.size == (c['width'], c['height'])
            source_mask_checks += 1
    for row in results['rows']:
        c = by_key[row['case_key']]
        d, a = row['decision'], row['assessment']
        assert a['crop_available'] and a['crop_usability_review'] == 'pending_human_review'
        for key in ['crop', 'keep_mask']:
            assert sha(OUT / row[key + '_path']) == row[key + '_sha256']
        with Image.open(OUT / row['crop_path']) as opened:
            crop = np.asarray(opened.convert('RGB'))
            assert list(opened.size) == a['crop_size_px']
        with Image.open(OUT / row['keep_mask_path']) as opened:
            keep = np.asarray(opened.convert('L'))
        assert keep.shape == (c['height'], c['width'])
        x, y, X, Y = d['crop_box']
        assert 0 <= x < X <= c['width'] and 0 <= y < Y <= c['height']
        assert crop.shape[:2] == (Y-y, X-x)
        crop_checks += 1
        if row['variant'] == 'dis-v1':
            assert a['target_agreement'] is None and d['selected_id'] in ['dis-foreground', None]
            continue
        with Image.open(OUT / c['image_path']) as opened:
            original = np.asarray(opened.convert('RGB').crop((x, y, X, Y)))
        visible = keep[y:Y, x:X] == 255
        assert np.array_equal(crop[visible], original[visible])
        rgb_checks += 1
        if row['variant'] == 'semantic-v2' and d['selected_id']:
            candidate = next(z for z in d['candidates'] if z['id'] == d['selected_id'])
            for ident in candidate.get('label_ids', []):
                proposal = next(p for p in c['mask_proposals'] if p['id'] == ident)
                with Image.open(OUT / proposal['mask_path']) as opened:
                    pixels = np.asarray(opened.convert('L')) >= 128
                retained = np.zeros(keep.shape, bool)
                retained[y:Y, x:X] = keep[y:Y, x:X] == 255
                count = int(pixels.sum())
                kept = int((retained & pixels).sum())
                label_audit.append({'case_key': c['key'], 'slug': c['slug'], 'variant': row['variant'],
                                    'label_id': ident, 'source_pixels': count, 'retained_pixels': kept,
                                    'retention': kept / max(1, count), 'fully_retained': kept == count,
                                    'mask_and_ownership_review': 'pending',
                                    'interpretation': 'Diagnostic only: clipped true paper and outlying/incorrect mask pixels need visual arbitration.'})
                selected_label_checks += 1
    write(OUT / 'selected-label-mask-audit.json', {'rows': label_audit,
          'labels_checked': selected_label_checks,
          'fully_retained': sum(r['fully_retained'] for r in label_audit),
          'unresolved_partial_proposal_masks': [r for r in label_audit if not r['fully_retained']],
          'human_label_completeness_score': None})
    if '--audit-only' in sys.argv:
        print(json.dumps({'label_masks':selected_label_checks,'fully_retained':sum(r['fully_retained'] for r in label_audit)}))
        return
    baseline=OUT.parent/'main-selector-imagegen-all152-20261020-current-v1'
    assert sha(OUT/'cases-frozen.json')==sha(baseline/'cases-frozen.json')
    fallback=next(n for n in ast.parse((OUT/'runtime/matcher/semantic_selector.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_fallback')
    assert hashlib.sha256(ast.dump(fallback,include_attributes=False).encode()).hexdigest()==protocol['fallback_ast_sha256']['frozen_baseline']
    scorer=lambda path:next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='assess')
    assert ast.dump(scorer(OUT/'run.py'),include_attributes=False)==ast.dump(scorer(baseline/'run.py'),include_attributes=False)
    context_index=json.loads((OUT/'context-index.json').read_text());context_checks=0
    for c in cases:
        path=OUT/'context'/(c['slug']+'.json')
        assert sha(path)==protocol['context_sha256'][c['slug']]
        aux=json.loads(path.read_text());assert aux['image_sha256']==c['image_sha256'] and aux['target_or_annotation_supplied'] is False
        assert len(aux['response']['instances'])==len(context_index[c['slug']])
        primary=json.loads((OUT/c['detector_path']).read_text())['response']['instances']
        for i,(item,meta) in enumerate(zip(aux['response']['instances'],context_index[c['slug']]),len(primary)):
            assert meta['id']=='d'+str(i) and meta['label']==item['label']
            mask=OUT/meta['mask_path'];assert sha(mask)==meta['sha256']
            assert mask.read_bytes()==base64.b64decode(item['mask_png_b64'],validate=True)
            with Image.open(mask) as opened:assert opened.size==(c['width'],c['height'])
            context_checks+=1
    parser = Links()
    parser.feed((OUT / 'report.html').read_text())
    assert len(parser.articles) == len(set(parser.articles)) == 152
    link_checks = 0
    for value in parser.paths:
        if value.startswith(('https:', 'http:', '#', 'data:')):
            continue
        path = OUT / unquote(urlsplit(value).path)
        assert path.exists() or path == OUT / 'verification.json', str(path)
        link_checks += 1
    for md in [OUT / 'README.md', *sorted((OUT / 'cases').glob('*.md')), *sorted((OUT / 'supplementary').rglob('*.md'))]:
        for value in re.findall(r'\]\(([^)]+)\)', md.read_text()):
            if value.startswith(('https:', 'http:', '#', 'data:')):
                continue
            path = md.parent / unquote(urlsplit(value).path)
            assert path.exists() or path == OUT / 'verification.json', str(path)
            link_checks += 1
    before = json.loads((OUT / 'preservation-before.json').read_text())
    preserved = {}
    for name in before:
        current = inventory(OUT.parent / name)
        assert current == before[name], name + ' source evidence changed'
        preserved[name] = len(current)
    log = (OUT / 'regression-tests.log').read_text()
    match=re.search(r'Ran (\d+) tests in [\d.]+s\n\nOK(?: \(skipped=\d+\))?\n',log)
    assert match, 'Complete regression suite did not pass'
    test_count=int(match.group(1))
    write(OUT / 'verification.json', {'passed': True, 'selected_cases': 152, 'result_rows': 456,
          'crop_checks': crop_checks, 'unaltered_source_RGB_crop_checks': rgb_checks,
          'source_images_hash_verified': source_image_checks, 'source_mask_files_hash_verified': source_mask_checks,
          'semantic_selected_label_masks_checked': selected_label_checks,
          'semantic_selected_label_masks_fully_preserved': sum(r['fully_retained'] for r in label_audit),
          'semantic_partial_selected_label_proposal_masks': sum(not r['fully_retained'] for r in label_audit),
          'all_historical_source_files_unchanged': preserved, 'portable_links_verified': link_checks,
          'context_mask_files_verified':context_checks, 'frozen_cases_and_scorer_and_fallback_unchanged':True, 'regression_tests': test_count, 'zero_human_approved_masks': True, 'human_crop_usability_approvals': 0,
          'current_source_snapshot_verified': True, 'GP02_GP11_same_group': True})
    print((OUT / 'verification.json').read_text())


if __name__ == '__main__':
    main()
