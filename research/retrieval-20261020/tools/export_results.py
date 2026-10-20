"""Export compact retrieval evidence. Read source databases without modification."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def read(path):
    return json.loads(path.read_text())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')


def parse_tables(text):
    result = []
    section = ''
    heading = ''
    table = None
    fenced = False
    for line in text.splitlines():
        if line.startswith('```'):
            fenced = not fenced
        if fenced:
            continue
        if line.startswith('## '):
            section, heading = line[3:], ''
        elif line.startswith('### '):
            heading = line[4:]
        if line.startswith('|'):
            cells = [x.strip().replace('\\|', '|') for x in re.split(r'(?<!\\)\|', line)[1:-1]]
            if all(re.fullmatch(r':?-+:?', x) for x in cells):
                continue
            if table is None:
                table = dict(section=section, heading=heading, headers=cells, rows=[])
                result.append(table)
            else:
                assert len(cells) == len(table['headers']), (section, heading, cells)
                table['rows'].append(cells)
        else:
            table = None
    return result


def connect(path):
    conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def export(campaign, report, output):
    ext = campaign / 'retrieval-extensions-20261018'
    text = report.read_text()
    # Publication-only wording and source-link changes do not change these tables.
    tables = [t for t in parse_tables(text) if t['section'].split('.', 1)[0].isdigit()
              and int(t['section'].split('.', 1)[0]) < 17]
    configs = {key: json.loads(body) for key, body in re.findall(r'### (R\d+)\n\n```json\n(.*?)\n```', text, re.S)}
    assert len(configs) == 53
    protocol = read(ext / 'protocol.json')
    data = read(campaign / 'complete-report-20261018/data.json')
    extension_summary = read(ext / 'summary.json')
    assert read(ext / 'complete.json')['passed']
    baselines = {c: data['cohorts'][c]['baseline'] for c in ('my-failed-2', 'my')}
    csv_rows = []
    raw_fields = ['n', 'top1', 'top5', 'top10', 'mrr', 'image_n', 'image_top1',
                  'image_top5', 'image_top10', 'image_mrr', 'negative_false1',
                  'negative_false10', 'no_match_false1', 'no_answer']
    inventory = []
    for cohort, folder in [('my-failed-2', 'matrix-20261017'), ('my', 'my-matrix-20261017')]:
        context = read(campaign / folder / 'context.json')
        old_path = campaign / 'axial-matrix-20261018' / cohort / 'combined.sqlite3'
        old = connect(old_path)
        ext_conn = connect(ext / 'metrics.sqlite3')
        ext_rows = [dict(r) for r in ext_conn.execute('SELECT * FROM metrics WHERE cohort=?', (cohort,))]
        ext_by_id = {r['variant_id']: r for r in ext_rows}
        bottle_rows = [r for r in ext_rows if not r['label_id']]
        for row in bottle_rows:
            row['_recipe'] = json.loads(row['recipe'])

        def record(scope, row, code='', name=''):
            item = dict(scope=scope, cohort=cohort, recipe_code=code,
                        variant_id=row['variant_id'], name=name)
            item.update({k: row.get(k) for k in raw_fields})
            csv_rows.append(item)

        for code, cfg in configs.items():
            key = cfg['variant_id']
            row = ext_by_id.get(key)
            if row is None:
                raw = old.execute('SELECT * FROM metrics WHERE variant_id=?', (key,)).fetchone()
                assert raw is not None, key
                row = dict(raw)
            if cfg['source'] == 'seven-family-extension':
                assert json.loads(row['recipe']) == cfg['bottle']
            record('exact_recipe', row, code)
        for key in protocol['profiles']:
            found = [r for r in bottle_rows if r['_recipe'] == dict(
                reference_pool=key, query_pool=key, query_geometry='original', gallery='rot5',
                axial_union=False, aggregation='max', reference_budget=512, query_budget=512,
                reference_margin=None, query_margin=None)]
            assert len(found) == 1, key
            record('controlled_pooling', found[0], name=key)
        for q in ('original', 'iou', 'min5', 'card5', 'crop', 'mean-iou', 'mean-card5'):
            key = 'single-b-u-' + q + '-rot5'
            row = dict(old.execute('SELECT * FROM metrics WHERE variant_id=?', (key,)).fetchone())
            record('controlled_query', row, name=q)
        record('baseline', baselines[cohort], name='siglip2-p512-rot5-seg')
        inventory.append(dict(source='axial-matrix-20261018/' + cohort + '/combined.sqlite3',
                              bytes=old_path.stat().st_size, sha256=digest(old_path),
                              cohort=cohort, variants=old.execute('SELECT count(*) FROM metrics').fetchone()[0],
                              bundled=False))
        assert len(ext_rows) == 59752
        assert sum(r['bottle_id'] not in extension_summary['repeated_control_bottle_ids'] for r in ext_rows) == 56518
        assert len(context['assignments']) == (668 if cohort == 'my-failed-2' else 3409)
        old.close()
        ext_conn.close()
    named = []
    for raw in data['named']:
        item = {k: raw[k] for k in ['cohort', 'family', 'name', 'method', 'variant_id', 'n', 'top1', 'top5', 'top10'] if k in raw}
        named.append(item)
        row = dict(scope='historical_named', cohort=raw['cohort'], recipe_code='',
                   variant_id=raw['variant_id'], name=raw['name'])
        row.update({k: raw.get(k) for k in raw_fields})
        csv_rows.append(row)
    fields = ['scope', 'cohort', 'recipe_code', 'variant_id', 'name', *raw_fields]
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'metrics.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(csv_rows)
    leaders = {c: dict(all_budgets={}, p512={}) for c in baselines}
    for table in tables:
        if not table['section'].startswith(('11.', '12.')) or 'Rank' not in table['headers']:
            continue
        cohort, objective = table['heading'].split(': ', 1)
        budget = 'p512' if objective.startswith('p512 ') else 'all_budgets'
        objective = objective.removeprefix('p512 ')
        codes = [re.search(r'\[(R\d+)\]', r[1]).group(1) for r in table['rows']]
        assert len(codes) == 5
        leaders[cohort][budget][objective] = codes
    schema = dict(version=1, generated_from='committed research report and read-only campaign databases',
                  model=protocol['model'], checkpoint=protocol['checkpoint'], hardware='GX10',
                  local_reranking=False, profiles=len(protocol['profiles']), policies=42,
                  cohorts={c: dict(positive_assignments=baselines[c]['n'],
                                  positive_images=baselines[c]['image_n'],
                                  all_unique_variants=353188, p512_unique_variants=345796,
                                  original_variants=148347, axial_additions=148323,
                                  extension_variants=59752, repeated_extension_controls=3234,
                                  new_extension_variants=56518) for c in baselines},
                  shared_images=619, baselines=baselines, leaderboards=leaders,
                  sort_order={'Top-1':['top1','top5','top10','mrr'],
                              'Top-5':['top5','top10','top1','mrr'],
                              'Top-10':['top10','top5','top1','mrr']},
                  metrics_csv_rows=len(csv_rows), report_recipe_count=len(configs),
                  limits='Summaries preserve reported counts. They do not contain per-image predictions or accepted answers.')
    # Keep only portable baseline fields. The original source link is local to the old report server.
    for row in schema['baselines'].values():
        for key in list(row):
            if key not in ['variant_id', 'cohort', *raw_fields]:
                del row[key]
    inventory.append(dict(source='retrieval-extensions-20261018/metrics.sqlite3',
                          bytes=(ext/'metrics.sqlite3').stat().st_size,
                          sha256=digest(ext/'metrics.sqlite3'), variants=119504, bundled=False))
    write(output / 'benchmark-summary.json', schema)
    write(output / 'configurations.json', configs)
    write(output / 'report-tables.json', tables)
    write(output / 'named-results.json', named)
    write(output / 'dataset-inventory.json', dict(version=1, raw_datasets=inventory,
          omitted=['images', 'segmentation masks', 'model weights', 'accepted-answer files',
                   'per-image candidate lists', 'complete metric databases and CSV files']))
    print(json.dumps(dict(metric_rows=len(csv_rows), exact_recipes=len(configs), tables=len(tables))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.campaign_root.resolve(), args.report.resolve(), args.output.resolve())
