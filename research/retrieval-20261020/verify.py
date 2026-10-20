"""Verify the committed retrieval package. Use Python 3 standard library only."""
import ast
import csv
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[1]
REPORT = REPO / 'RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


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
                require(len(cells) == len(table['headers']), 'Inconsistent Markdown table width')
                table['rows'].append(cells)
        else:
            table = None
    return result


def regenerate_recipes(protocol):
    pools = list(protocol['aliases'])
    aliases = protocol['aliases']
    queries = ['original', 'iou', 'min5', 'card5', 'crop', 'mean-iou', 'mean-card5']
    galleries = ['zero', 'cardinal', 'rot5']
    result = {}

    def add(rp, qp, query, gallery, axial, family, aggregation='max', **changes):
        recipe = dict(reference_pool=aliases.get(rp, rp), query_pool=aliases.get(qp, qp),
                      query_geometry=query, gallery=gallery, axial_union=axial,
                      aggregation=aggregation, reference_budget=512, query_budget=512,
                      reference_margin=None, query_margin=None)
        recipe.update(changes)
        key = 'x-' + hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:24]
        if key not in result:
            result[key] = dict(recipe=recipe, families=[])
        require(result[key]['recipe'] == recipe, 'Recipe hash collision')
        if str(family) not in result[key]['families']:
            result[key]['families'].append(str(family))

    for rp, qp, q, g, ax in itertools.product(pools, pools, queries, galleries, (False, True)):
        add(rp, qp, q, g, ax, 1)
    for p, q, g, ax, k in itertools.product(pools, queries, galleries, (False, True), (2, 3)):
        add(p, p, q, g, ax, 7, aggregation=f'top{k}-mean')
    for p, profile in protocol['profiles'].items():
        family = 4 if profile.get('coverage') == 'exact' else 2 if profile.get('gamma', 1) != 1 else 3
        for q, g, ax in itertools.product(queries, galleries, (False, True)):
            add(p, p, q, g, ax, family)
    for p, rm, qm, q, g in itertools.product(('u', '6b'), (0., .02, .05, .1), (0., .02, .05, .1), queries, galleries):
        add(p, p, q, g, False, 4, reference_margin=rm, query_margin=qm)
    for p, rb, qb, q, g, ax in itertools.product(('u', '6b'), (256, 512, 1024), (256, 512, 1024), queries, galleries, (False, True)):
        add(p, p, q, g, ax, 6, reference_budget=rb, query_budget=qb)
    for p, q, g in itertools.product(pools, queries, ('cartesian', 'rot5-plus-cartesian')):
        add(p, p, q, g, True, 5)
    return result


def check_links(path):
    text = path.read_text()
    anchors = set()
    fenced = False
    for line in text.splitlines():
        if line.startswith('```'):
            fenced = not fenced
        if not fenced and line.startswith('#'):
            title = line.lstrip('#').strip().lower()
            anchors.add(re.sub(r'[^\w\- ]', '', title).replace(' ', '-'))
    require(not fenced, 'Unclosed code fence: ' + str(path))
    for raw in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        url = urlsplit(raw)
        if url.scheme in ('http', 'https'):
            require(url.hostname not in ('127.0.0.1', 'localhost'), 'Local server link: ' + raw)
            continue
        require(not url.scheme and not url.path.startswith('/'), 'Non-relative file link: ' + raw)
        if not url.path:
            require(unquote(url.fragment) in anchors, 'Missing heading: ' + raw)
        else:
            target = (path.parent / unquote(url.path)).resolve()
            require(target.is_relative_to(REPO), 'Link leaves repository: ' + raw)
            require(target.exists(), 'Missing file: ' + raw)


def main():
    package_manifest = read(PACKAGE / 'package-manifest.json')
    for item in package_manifest['files']:
        path = (PACKAGE / item['path']).resolve()
        require(path.is_relative_to(PACKAGE), 'Manifest path leaves package')
        require(path.is_file() and path.stat().st_size == item['bytes'], 'Missing or changed size: ' + item['path'])
        require(sha(path) == item['sha256'], 'Changed checksum: ' + item['path'])
        if path.suffix == '.py':
            ast.parse(path.read_text())
    source_manifest = read(PACKAGE / 'provenance/source-manifest.json')
    for item in source_manifest['files']:
        if item['kind'] == 'snapshot':
            require(sha(PACKAGE / item['path']) == item['source_sha256'], 'Changed source snapshot')
    protocol = read(PACKAGE / 'sources/campaign/retrieval-extensions-20261018/protocol.json')
    stored = read(PACKAGE / 'sources/campaign/retrieval-extensions-20261018/enumeration.json')
    recipes = regenerate_recipes(protocol)
    require(recipes == stored['bottles'] and len(recipes) == 5432, 'Recipe grid differs from the frozen enumeration')
    settings = ast.parse((PACKAGE / 'sources/campaign/retrieval-extensions-20261018/settings.py').read_text())
    node = next(n for n in settings.body if isinstance(n, ast.FunctionDef) and n.name == 'profiles')
    namespace = {}
    # Execute only the pure profile factory. Do not import any historical runner.
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<frozen profiles>', 'exec'), namespace)
    require(namespace['profiles']() == protocol['profiles'], 'Pooling profile factory differs from specification')
    configs = read(PACKAGE / 'summaries/configurations.json')
    summary = read(PACKAGE / 'summaries/benchmark-summary.json')
    tables = read(PACKAGE / 'summaries/report-tables.json')
    text = REPORT.read_text()
    report_configs = {k: json.loads(body) for k, body in re.findall(r'### (R\d+)\n\n```json\n(.*?)\n```', text, re.S)}
    require(configs == report_configs and len(configs) == 53, 'Report recipe records differ from compact export')
    report_tables = [t for t in parse_tables(text) if t['section'].split('.', 1)[0].isdigit()
                     and int(t['section'].split('.', 1)[0]) < 17]
    require(tables == report_tables, 'Report result tables differ from compact export')
    metrics = list(csv.DictReader((PACKAGE / 'summaries/metrics.csv').open()))
    require(len(metrics) == summary['metrics_csv_rows'], 'Compact CSV row count differs')
    exact = {}
    for row in metrics:
        n = int(row['n'])
        require(0 <= int(row['top1']) <= int(row['top5']) <= int(row['top10']) <= n, 'Invalid recall counts')
        if row['scope'] == 'exact_recipe':
            exact[row['cohort'], row['recipe_code']] = row
    for code, cfg in configs.items():
        if cfg['source'] == 'seven-family-extension':
            key = 'x-' + hashlib.sha256(json.dumps(cfg['bottle'], sort_keys=True).encode()).hexdigest()[:24]
            require(key == cfg['variant_id'].split('__')[0], 'Invalid recipe ID: ' + code)
            require(recipes[key]['recipe'] == cfg['bottle'], 'Recipe missing from grid: ' + code)
        for cohort in summary['cohorts']:
            require(exact[cohort, code]['variant_id'] == cfg['variant_id'], 'CSV recipe identity differs')
    checked = 0
    for table in tables:
        for row in table['rows']:
            cohort = next((c for c in summary['cohorts'] if table['heading'].startswith(c + ':') or row[0] == c), None)
            for column, value in enumerate(row):
                for match in re.finditer(r'(\d+\.\d+)% \((\d+)/(\d+)\)(?:; ([+-]\d+\.\d+) pp)?', value):
                    percentage, hits, n, delta = match.groups()
                    hits, n = int(hits), int(n)
                    require(percentage == f'{100*hits/n:.2f}', 'Incorrect printed recall')
                    if delta is not None:
                        key = {'R@1':'top1', 'R@5':'top5', 'R@10':'top10'}[table['headers'][column]]
                        baseline = summary['baselines'][cohort]
                        require(n == baseline['n'], 'Incorrect baseline denominator')
                        require(delta == f'{100*(hits-baseline[key])/n:+.2f}', 'Incorrect printed delta')
                    checked += 1
            code_match = next((re.search(r'\[(R\d+)\]', value) for value in row if re.search(r'\[(R\d+)\]', value)), None)
            if cohort and code_match:
                raw = exact[cohort, code_match.group(1)]
                for key, heading in [('top1','R@1'),('top5','R@5'),('top10','R@10')]:
                    if heading in table['headers']:
                        value = row[table['headers'].index(heading)]
                        require(f'({raw[key]}/{raw["n"]})' in value, 'Report count differs from CSV')
    for table in tables:
        if table['section'].startswith('10.'):
            scope = 'controlled_pooling' if table['heading'] == 'Pooling in isolation' else 'controlled_query'
            for row in table['rows']:
                name = row[0].strip('`')
                for cohort, index in [('my-failed-2',1),('my',2)]:
                    raw = next(r for r in metrics if r['scope'] == scope and r['cohort'] == cohort and r['name'] == name)
                    expected = ' / '.join(f'{100*int(raw[k])/int(raw["n"]):.2f}%' for k in ('top1','top5','top10'))
                    require(row[index] == expected, 'Controlled table differs from CSV')
    for cohort, groups in summary['leaderboards'].items():
        for budget, objectives in groups.items():
            for objective, codes in objectives.items():
                require(len(codes) == len(set(codes)) == 5, 'Invalid top-five list')
                order = summary['sort_order'][objective]
                wanted = sorted(codes, key=lambda code: tuple(-float(exact[cohort,code][k]) for k in order) + (configs[code]['variant_id'],))
                require(codes == wanted, 'Incorrect leaderboard sort order')
                if budget == 'p512':
                    require(all(configs[c]['bottle']['reference_budget'] == configs[c]['bottle']['query_budget'] == 512 for c in codes), 'Non-p512 recipe in p512 table')
        counts = summary['cohorts'][cohort]
        require(counts['all_unique_variants'] == 353188 and counts['p512_unique_variants'] == 345796, 'Invalid coverage counts')
        require(counts['original_variants'] + counts['axial_additions'] + counts['extension_variants'] - counts['repeated_extension_controls'] == 353188, 'Invalid deduplication arithmetic')
    for path in [REPORT, PACKAGE/'README.md', PACKAGE/'summaries/README.md']:
        check_links(path)
    require(not re.search(r'/Volumes/|/Users/|/home/|http://127\.0\.0\.1', text), 'Machine-local reference remains in the published report')
    print(f'PASS: {len(package_manifest["files"])} file hashes; 5,432 recipes; 39 profiles; '
          f'53 exact result recipes; {len(metrics)} compact metric rows; {checked} printed recalls; repository links.')
    print('This check does not reproduce predictions or independently prove global leaderboard optimality without the raw datasets.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, StopIteration, OSError, AssertionError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        raise SystemExit(1)
