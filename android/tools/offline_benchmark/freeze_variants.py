#!/usr/bin/env python3
"""Resolve the owner's ten rows to exact read-only desktop experiment recipes."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


IDENTITIES = [
    'x-5413e26b22a393fd785d1e18__l-7f-rot5__always-mean75',
    'x-9aad7b1ad6a16ae00fb54a78__l-7f-rot5__always-mean75',
    'x-adaace72b66523656e44f3f3__l-7f-rot5__always-mean75',
    'x-dea1ff540b7528ec273a556b__l-7f-rot5__always-mean75',
    'x-90ada0100559c6de5f514f57',
    'x-03b72d911e5a6152f4154088',
    'x-0f8d10c1d088bfdbee097a81__l-7f-rot5__always-mean75',
    'x-c9dec897f1fd146420891822',
    'x-0bea225d7c4b344eba15215d__l-7f-rot5__always-mean75',
    'x-1979dff348a23e64b79390ad__l-7f-rot5__always-mean50',
]
EXPECTED_HARD_HITS = [436,436,435,434,409,402,404,361,431,442]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Do not replace a frozen recipe set.')
    extension = args.campaign / 'retrieval-extensions-20261018'
    connection = sqlite3.connect('file:' + str(extension / 'metrics.sqlite3') + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    protocol = json.loads((extension / 'protocol.json').read_text())
    matrix = json.loads((args.campaign / 'my-matrix-20261017/manifest.json').read_text())
    report = json.loads((args.campaign / 'complete-report-20261018/data.json').read_text())
    variants = []
    for number, identity in enumerate(IDENTITIES, 1):
        rows = connection.execute('SELECT * FROM metrics WHERE variant_id=?', (identity,)).fetchall()
        metrics = {row['cohort']:dict(row) for row in rows}
        if metrics['my-failed-2']['top1'] != EXPECTED_HARD_HITS[number-1]:
            raise ValueError(f'Desktop hard-cohort metrics changed for variant {number}.')
        recipe = json.loads(metrics['my-failed-2']['recipe'])
        label_id = metrics['my-failed-2']['label_id']
        policy_id = metrics['my-failed-2']['policy_id']
        bottle_views = {'zero':1,'cardinal':4,'rot5':72}[recipe['gallery']] + (12 if recipe['axial_union'] else 0)
        geometry = recipe['query_geometry']
        passes = (2 if geometry.startswith('mean-') else 1) + bool(label_id)
        variants.append(dict(number=number, desktop_variant_id=identity, recipe=recipe,
                             nominal_bottle_views=bottle_views, encoder_passes=int(passes),
                             label_id=label_id, label_geometry=report['legend']['label_geometry']['7f'] if label_id else None,
                             label_reference_angles=list(range(0,360,5)) if label_id else [],
                             fusion=matrix['policies'][policy_id] if policy_id else None,
                             desktop_metrics={cohort:{key:row[key] for key in ('n','top1','top5','top10')}
                                              for cohort,row in metrics.items()}))
    query_path = args.campaign / 'queries.json'
    result = dict(model=protocol['model'], revision=protocol['checkpoint'], budget=512,
                  cohort='my-failed-2', assignments=668,
                  queries_sha256=hashlib.sha256(query_path.read_bytes()).hexdigest(),
                  reranking=False, barcode=False, query_masks='on-device mobile segmentation only',
                  reference_masks='frozen off-device catalogue preparation', variants=variants)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print('Frozen recipes:',len(variants))
    print('Bottle views:',[v['nominal_bottle_views'] for v in variants])
    print('Encoder passes:',[v['encoder_passes'] for v in variants])


if __name__ == '__main__':
    main()
