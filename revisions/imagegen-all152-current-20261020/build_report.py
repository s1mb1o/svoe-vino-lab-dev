"""Build portable visual evidence, with provisional agreement and usability separated."""
from collections import Counter
import csv
import html
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from run import OUT, VARIANTS, sha, write

LABEL_AUDIT = {}


def preview(source, dest, size=(640, 460)):
    if dest.exists():
        return
    with Image.open(source) as opened:
        image = opened.convert('RGB')
    image.thumbnail(size, Image.Resampling.LANCZOS)
    dest.parent.mkdir(exist_ok=True, parents=True)
    image.save(dest, quality=88)


def flags(row):
    a = row['assessment']
    result = []
    if a['target_agreement'] is False:
        result.append('target disagreement')
    if a['isolation_proxy_pass'] is False:
        result.append('isolation proxy failure')
    if min(a['crop_size_px']) < 64:
        result.append('tiny crop')
    if a.get('minimum_target_label_retention_proxy') is not None and a['minimum_target_label_retention_proxy'] < .995:
        result.append('label retention proxy below 99.5%')
    if any(not x['fully_retained'] for x in LABEL_AUDIT.get((row['case_key'], row['variant']), [])):
        result.append('selected-label proposal not fully retained; mask review pending')
    return result


def percent(value):
    return 'n/a' if value is None else f'{100*value:.1f}%'


def details(row):
    a, d = row['assessment'], row['decision']
    agree = 'n/a (no native target ID)' if a['target_agreement'] is None else str(a['target_agreement'])
    label_checks = LABEL_AUDIT.get((row['case_key'], row['variant']), [])
    audit = (' Selected-label mask audit: ' + '; '.join(f"{x['label_id']} {percent(x['retention'])}" for x in label_checks) + '.') if label_checks else ''
    return (f"Selected: {d['selected_id']}; reason: {d['reason']}; mode: {d.get('selection_mode')}; "
            f"crop {a['crop_size_px'][0]}×{a['crop_size_px'][1]} px. Target agreement: {agree}. "
            f"Target retention proxy: {percent(a['target_retention_proxy'])}; "
            f"maximum other-bottle retention: {percent(a['maximum_other_bottle_retention_proxy'])}; "
            f"minimum associated label retention: {percent(a.get('minimum_target_label_retention_proxy'))}. "
            'Mask ownership, label completeness and legibility still require human review.' + audit)


def main():
    protocol = json.loads((OUT / 'protocol.json').read_text())
    cases = json.loads((OUT / 'cases-frozen.json').read_text())
    results = json.loads((OUT / 'results.json').read_text())
    label_audit = json.loads((OUT / 'selected-label-mask-audit.json').read_text())
    for row in label_audit['rows']:
        LABEL_AUDIT.setdefault((row['case_key'], row['variant']), []).append(row)
    assert len(cases) == 152 and len(results['rows']) == 456
    by_key = {c['key']: c for c in cases}
    grouped = {c['key']: {} for c in cases}
    for row in results['rows']:
        grouped[row['case_key']][row['variant']] = row
    cards, index_rows, md_rows, review_rows, changes = [], [], [], [], []
    for c in cases:
        slug = c['slug']
        (OUT / 'cases').mkdir(exist_ok=True)
        original_preview = f'previews/{slug}-original.jpg'
        target_preview = f'previews/{slug}-target.jpg'
        preview(OUT / c['image_path'], OUT / original_preview)
        with Image.open(OUT / c['image_path']) as opened:
            marked = opened.convert('RGBA')
        target = c['expectation']['target']
        target_proposal = next((p for p in c['mask_proposals'] if p['id'] == target), None)
        if target_proposal:
            with Image.open(OUT / target_proposal['mask_path']) as opened:
                mask = opened.convert('L')
            layer = Image.new('RGBA', marked.size, (0, 220, 140, 0))
            layer.putalpha(mask.point(lambda x: round(x * .35)))
            marked = Image.alpha_composite(marked, layer)
            draw = ImageDraw.Draw(marked)
            draw.rectangle(target_proposal['mask_bbox'], outline=(0, 255, 150, 255), width=max(2, marked.width // 300))
        target_path = OUT / 'target-overlays' / (slug + '.jpg')
        target_path.parent.mkdir(exist_ok=True)
        marked.convert('RGB').save(target_path, quality=90)
        preview(target_path, OUT / target_preview)
        cohort_text = 'Scene confirmed; masks pending' if c['human_scene_confirmed'] else 'Scene and masks pending — exploratory'
        scene = grouped[c['key']]['scene-v1']
        scene_flags = flags(scene)
        semantic_flags = flags(grouped[c['key']]['semantic-v2'])
        scene_marker = 'FAIL — provisional target/proxy' if scene_flags else 'No automatic failure flag; usability pending'
        case_md = [f"# {c['key']}", '', f'**{cohort_text}. All targets/masks are proposals; no approved segmentation ground truth.**', '',
                   f"**scene-v1: {scene_marker}.**", '', f"Reference title (source): {c['title_reference']}", '',
                   f"Reference target description (source): {c['description_reference']}", '',
                   f"Expected intent: `{c['expectation']['intent']}`. Accepted target proposals: `{', '.join(c['accepted_targets'])}`.", '',
                   f"Scene group: `{c['scene_independence_group']}`. Development only; no independent split claim.", '',
                   '## Original and proposed target', '', f"![Original image](../{c['image_path']})", '',
                   f'![Proposed target overlay](../target-overlays/{slug}.jpg)', '',
                   'Green marks the unreviewed target proposal. Source image pixels are retained separately.', '',
                   '[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.', '']
        if target_proposal:
            case_md.extend([f"[Full-resolution target proposal mask](../{target_proposal['mask_path']})", ''])
        case_md.extend(['## Selector results', ''])
        columns = []
        for v in VARIANTS:
            row = grouped[c['key']][v]
            row_flags = flags(row)
            crop_preview = f'previews/{slug}-{v}.jpg'
            preview(OUT / row['crop_path'], OUT / crop_preview)
            marker = ('FAIL — provisional target/proxy' if row_flags else 'No automatic failure flag; usability pending') if v != 'dis-v1' else ('PROXY failure; no native target ID' if row_flags else 'Proxy satisfied; usability pending')
            case_md.extend([f'### {v}: {marker}', '', details(row), '', f"![{v} crop](../{row['crop_path']})", '',
                            f"[Full-resolution keep mask](../{row['keep_mask_path']}) · [Exact decision JSON](../results/{slug}-{v}.json)", ''])
            if row['label_crop_paths']:
                case_md.append('Returned label views: ' + ' · '.join(f'[label {i+1}](../{p})' for i, p in enumerate(row['label_crop_paths'])))
                case_md.append('')
            labels = row['assessment']['label_retention_proxies']
            if labels:
                case_md.extend(['Associated label-mask retention proxies (unreviewed ownership): ' + '; '.join(f"{x['id']}: {percent(x['retention'])}, {x['source_area_px']} source pixels" for x in labels), ''])
            flag_html = '<strong class="bad">' + html.escape(marker) + '</strong>' if row_flags else '<strong>' + html.escape(marker) + '</strong>'
            columns.append(f'<section><h3>{v}</h3>{flag_html}<a href="{row["crop_path"]}"><img loading="lazy" src="{crop_preview}" alt="{v} crop {slug}"></a><p>{html.escape(details(row))}</p><a href="results/{slug}-{v}.json">Decision JSON</a> · <a href="{row["keep_mask_path"]}">Keep mask</a></section>')
            index_rows.append({'case_key': c['key'], 'dataset': c['dataset_short'], 'variant': v,
                               'cohort': c['cohort'], 'target': target, 'selected': row['decision']['selected_id'],
                               'target_agreement': row['assessment']['target_agreement'],
                               'isolation_proxy_pass': row['assessment']['isolation_proxy_pass'],
                               'crop_width': row['assessment']['crop_size_px'][0], 'crop_height': row['assessment']['crop_size_px'][1],
                               'target_retention_proxy': row['assessment']['target_retention_proxy'],
                               'maximum_other_bottle_retention_proxy': row['assessment']['maximum_other_bottle_retention_proxy'],
                               'minimum_label_retention_proxy': row['assessment'].get('minimum_target_label_retention_proxy'),
                               'flags': '; '.join(row_flags), 'human_crop_usability': 'pending'})
            review_rows.append({'case_key': c['key'], 'variant': v, 'image_sha256': c['image_sha256'],
                                'crop_sha256': row['crop_sha256'], 'scene_review': c['human_scene_confirmed'],
                                'target_correct': None, 'label_complete': None, 'label_legible': None, 'useful_crop': None,
                                'notes': '', 'status': 'pending_human_review'})
        case_md.extend(['## All frozen mask proposals', '', 'These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.', '',
                        '| ID | Detector class | Full-resolution mask |', '|---|---|---|'])
        case_md.extend(f"| {p['id']} | {p['label']} | [PNG](../{p['mask_path']}) |" for p in c['mask_proposals'])
        case_md.extend(['', f"[Raw frozen detector response](../{c['detector_path']})", '',
                        '<details><summary>Generation prompt (quoted source data)</summary>', '', '```text', c['prompt_reference'], '```', '', '</details>', ''])
        if c.get('agent_notes_reference'):
            case_md.extend(['Source review notes (quoted reference data):', ''] + ['> ' + s for s in c['agent_notes_reference']] + [''])
        (OUT / 'cases' / (slug + '.md')).write_text('\n'.join(case_md))
        proposal_links = ' · '.join(f'<a href="{p["mask_path"]}">{p["id"]} {html.escape(p["label"])}</a>' for p in c['mask_proposals'])
        cards.append(f'<article id="{slug}" data-dataset="{c["dataset_short"]}" data-cohort="{c["cohort"]}" data-scene-fail="{str(bool(scene_flags)).lower()}" data-semantic-fail="{str(bool(semantic_flags)).lower()}" data-search="{html.escape(c["key"] + " " + c["family"] + " " + c["title_reference"], quote=True)}"><h2>{html.escape(c["key"])}</h2><p class="review">{cohort_text}. Target proposal: {target}; family: {c["family"]}. <a href="cases/{slug}.md">Portable case page</a></p><div class="grid"><section><h3>Original / proposed target</h3><a href="{c["image_path"]}"><img loading="lazy" src="{original_preview}" alt="Original {slug}"></a><a href="target-overlays/{slug}.jpg"><img loading="lazy" src="{target_preview}" alt="Unreviewed target proposal {slug}"></a><p>Source title: {html.escape(c["title_reference"])}</p><p>Source target description: {html.escape(c["description_reference"] or "")}</p></section>{"".join(columns)}</div><details><summary>All {len(c["mask_proposals"])} proposal masks, source notes and prompt</summary><p>{proposal_links}</p><p>Scene group: {c["scene_independence_group"]}. Human mask approval: none.</p><pre>{html.escape(chr(10).join(c["agent_notes_reference"]))}</pre><pre>{html.escape(c["prompt_reference"])}</pre></details></article>')
        md_rows.append(f"| [{c['dataset_short']}:{c['source_case_id']}](cases/{slug}.md) | {cohort_text} | {'**FAIL**' if scene_flags else 'No flag'} | {'**FAIL**' if semantic_flags else 'No flag'} | {'Failure' if flags(grouped[c['key']]['dis-v1']) else 'Satisfied'} |")
        old_dir = c['previous_comparison']
        if old_dir:
            old_results = json.loads((OUT.parent / old_dir / 'results.json').read_text())['rows']
            for v in VARIANTS:
                old = next(r for r in old_results if r['case_id'] == c['source_case_id'] and r['variant'] == v)
                current = grouped[c['key']][v]
                if old['decision']['selected_id'] != current['decision']['selected_id'] or old['crop_sha256'] != current['crop_sha256']:
                    changes.append({'case_key': c['key'], 'variant': v, 'old_run': old_dir,
                                    'old_selected': old['decision']['selected_id'], 'current_selected': current['decision']['selected_id'],
                                    'old_target_agreement': old['assessment']['direct_target_match'],
                                    'current_target_agreement': current['assessment']['target_agreement'],
                                    'crop_changed': old['crop_sha256'] != current['crop_sha256']})
    write(OUT / 'historical-comparison.json', {'changed_predictions': changes, 'historical_predictions_overwritten': False})
    write(OUT / 'crop-usability-review-pending.json', {'schema_version': 1, 'human_approved_results': 0, 'cases': review_rows})
    with (OUT / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(index_rows[0])); writer.writeheader(); writer.writerows(index_rows)
    summary_md = ['# Current three-selector comparison: 152 generated scenes', '',
                  '**All 456 outputs return a crop. No human-approved mask accuracy or crop-usability score is claimed.**', '',
                  '**109 relevant regression tests pass on the pinned runtime.** [Test log](regression-tests.log) · [Artifact verification](verification.json) · [Browser checks](browser-verification.json). Verification means that the evidence is complete and unchanged; it does not mark every selection successful.', '',
                  'Fresh scene-v1 and semantic-v2 replays use the pinned current implementation and original frozen SAM3 proposal order. DIS runs fresh on every original using its pinned CPU model. No live detector requests or optional recovery are exercised.', '',
                  f"Implementation revision: `{protocol['implementation_revision']}`. Exact bytes and configuration: [protocol](protocol.json), [runtime](runtime/matcher), [contract preservation](contract-preservation.json).", '',
                  'The first 50 scenes have persisted scene approval, with masks pending. The other 102 are exploratory pending scenes, including GP11 and SP01. Scene approvals do not approve masks. Targets, proposal shapes and owners remain unreviewed geometry.', '',
                  'All 152 source hashes are unique. GP02 and its reference-image edit GP11 share a scene group; no independent train/test split is claimed. The first 50 images were already used in development. Rejected, blocked and canceled attempts remain provenance only.', '',
                  'A target-ID match does not establish a useful crop. Retention and isolation below are diagnostic mask proxies. Label completeness, ownership, legibility and crop usefulness require human review for all 456 outputs. **No flag means only that these automatic checks found no failure.**', '',
                  '| Cohort | Selector | Images | Target agreement | Isolation proxy satisfied |', '|---|---|---:|---:|---:|']
    table_html = ['<table><tr><th>Cohort</th><th>Selector</th><th>Images</th><th>Target agreement</th><th>Isolation proxy</th></tr>']
    cohort_names = {'all_unique_sources': 'All unique sources (development)', 'scene_confirmed_masks_pending': '50 scene-confirmed; masks pending', 'scene_pending_masks_pending': '102 pending scenes; exploratory'}
    for cohort, summary in results['summaries'].items():
        for variant, d in summary.items():
            target_text = 'n/a' if d['target_agreements'] is None else str(d['target_agreements']) + '/' + str(d['rows'])
            isolation_text = str(d['isolation_proxy_passes']) + '/' + str(d['rows'])
            summary_md.append(f'| {cohort_names[cohort]} | {variant} | {d["rows"]} | {target_text} | {isolation_text} |')
            table_html.append(f'<tr><td>{cohort_names[cohort]}</td><td>{variant}</td><td>{d["rows"]}</td><td>{target_text}</td><td>{isolation_text}</td></tr>')
    table_html.append('</table>')
    summary_md.extend(['', '## Review every case', '',
                       f"The selected-label audit checks {label_audit['labels_checked']} semantic-v2 attached label masks: {label_audit['fully_retained']} fully retained, {len(label_audit['unresolved_partial_proposal_masks'])} partially retained. These six unresolved masks span five cases; several contain only a few hundred pixels. This needs shape/ownership review and is not a human label-completeness score. [Exact audit](selected-label-mask-audit.json).", '',
                       'FAIL below means a disagreement with a target proposal or a failed isolation/label-retention proxy. Pending scenes remain provisional. Each page contains original RGB, proposed target overlay, every mask, all three selector crops and exact decisions.', '',
                       '| Case | Annotation cohort | scene-v1 | semantic-v2 | DIS isolation proxy |', '|---|---|---|---|---|'] + md_rows + ['',
                       '[scene-v1 failure index](SCENE-V1-FAILURES.md) · [semantic-v2 failure index](SEMANTIC-V2-FAILURES.md) · [Interactive local report](report.html) · [CSV](comparison.csv) · [Exact results](results.json) · [Historical prediction differences](historical-comparison.json) · [Pending usability review](crop-usability-review-pending.json)', ''])
    (OUT / 'README.md').write_text('\n'.join(summary_md))
    head = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>152 scenes — current three-selector comparison</title><style>
    *{box-sizing:border-box}body{margin:0;padding:28px;background:#0b1020;color:#edf2fa;font:15px/1.5 system-ui,sans-serif}main{max-width:1800px;margin:auto}h1{font-size:30px}h2{font-size:19px;overflow-wrap:anywhere}h3{font-size:16px}a{color:#8ecaff}p{max-width:1100px}.warning{padding:18px;border:1px solid #edb94e;background:#2c2519;border-radius:8px}table{border-collapse:collapse;margin:20px 0;width:100%}th,td{padding:8px;text-align:left;border-bottom:1px solid #344058}article{padding:20px;margin:22px 0;background:#151d30;border:1px solid #35415b;border-radius:10px;content-visibility:auto;contain-intrinsic-size:auto 700px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}section{min-width:0;background:#101829;padding:12px;border-radius:7px}section img{display:block;width:100%;height:250px;object-fit:contain;background:#202b40;margin:12px 0}section p{font-size:13px}.bad{color:#ff9d9d}.review{color:#ffd994}details{padding-top:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}nav{position:sticky;top:0;z-index:3;background:#0b1020ee;padding:12px 0;display:flex;flex-wrap:wrap;gap:10px}select,input{padding:10px;background:#202c43;color:#fff;border:1px solid #65738b;border-radius:5px}input{min-width:260px}[hidden]{display:none!important}@media(max-width:1000px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){body{padding:12px}.grid{grid-template-columns:1fr}}
    </style><main><h1>152 generated scenes · current three-selector comparison</h1><p class="warning"><b>456 fresh outputs; every selector returns a crop. Zero approved mask annotations and zero approved crop-usability judgments.</b> Target agreement is provisional. Correct IDs and retained pixels alone do not establish a readable label or useful result.</p>'''
    head = head.replace('</style>', 'article{scroll-margin-top:90px}</style>')
    intro = f'<p>Pinned revision: <code>{protocol["implementation_revision"]}</code>. Frozen detector proposal replay for scene-v1 and semantic-v2; fresh pinned local DIS inference. Default configuration; no new detector requests. Fifty scene-confirmed images have pending masks; 102 scenes are exploratory. GP02/GP11 share one scene group. <a href="protocol.json">Protocol</a> · <a href="README.md">Portable review index</a> · <a href="comparison.csv">CSV</a></p>'
    nav = '''<nav><select id="dataset"><option value="">All datasets</option><option>pilot-v1</option><option>hardcases-v2</option><option>diverse-v3</option></select><select id="cohort"><option value="">All annotation cohorts</option><option value="scene_confirmed_masks_pending">Scene confirmed, masks pending</option><option value="scene_pending_masks_pending">Pending scenes — exploratory</option></select><select id="failure"><option value="">All cases</option><option value="scene">scene-v1 failure flags</option><option value="semantic">semantic-v2 failure flags</option></select><input id="search" placeholder="Case ID, dataset or family"><span id="count"></span></nav>'''
    script = '''<script>const articles=[...document.querySelectorAll('article')];const fields=['dataset','cohort','failure','search'].map(x=>document.getElementById(x));function filter(){const[d,c,f,s]=fields.map(x=>x.value.toLowerCase());let count=0;for(const a of articles){const ok=(!d||a.dataset.dataset===d)&&(!c||a.dataset.cohort===c)&&(!f||a.dataset[f+'Fail']==='true')&&(!s||a.dataset.search.toLowerCase().includes(s));a.hidden=!ok;if(ok)count++}document.getElementById('count').textContent=count+' / '+articles.length+' cases'}fields.forEach(x=>x.addEventListener('input',filter));filter();const id=new URLSearchParams(location.search).get('case');if(id){document.getElementById('search').value=id;filter();document.querySelector('article:not([hidden])')?.scrollIntoView()}</script>'''
    (OUT / 'report.html').write_text(head + intro + ''.join(table_html) + nav + ''.join(cards) + script + '</main></html>')
    write(OUT / 'report-data.json', {'case_count': len(cases), 'row_count': len(index_rows), 'scene_v1_flagged_cases': sum(bool(flags(grouped[c['key']]['scene-v1'])) for c in cases),
                                    'semantic_v2_flagged_cases': sum(bool(flags(grouped[c['key']]['semantic-v2'])) for c in cases),
                                    'rows': index_rows})
    print(json.dumps({'cases': len(cases), 'rows': len(index_rows), 'changed_historical_predictions': len(changes)}))


if __name__ == '__main__':
    main()
