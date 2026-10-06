"""Benchmark existing competitor adaptations on a frozen real-photo cohort.

This script does not rebuild indexes or change labels or production configuration.
Each service input is a temporary image copy dated before the submission cutoff.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workbench/pipeline'))
sys.path.insert(0, str(ROOT))
import numpy as np
import embeddings
import embedding_run
import pipelines
import yaml

NAMES = ['siglip2-p512-rot5-seg', 'competitor-stan-ocr',
         'competitor-kofeinix-ocr', 'competitor-danya-ocr-union',
         'competitor-anna-two-view', 'competitor-qacen-reject',
         'competitor-stan-full', 'competitor-kofeinix-full',
         'competitor-danya-full', 'competitor-anna-full', 'competitor-qacen-full']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def correct(row, k=1):
    return bool(row['truth']) and any(c['slug'] in row['truth'] for c in row['candidates'][:k])


def metrics(rows, baseline=None):
    positive = [r for r in rows if r['truth'] and r['label'] != 'unusable']
    accepted = [r for r in rows if r['candidates']]
    ms = [r['latency_ms'] for r in rows]
    out = dict(total=len(rows), known=len(positive),
               hits={str(k): sum(correct(r, k) for r in positive) for k in (1, 5, 10)},
               recall={str(k): sum(correct(r, k) for r in positive)/len(positive) if positive else None for k in (1, 5, 10)},
               errors=sum(bool(r.get('error')) for r in rows),
               accepted=len(accepted), accepted_correct=sum(correct(r) for r in accepted),
               accepted_unusable=sum(r['label'] == 'unusable' for r in accepted),
               median_ms=float(np.median(ms)) if ms else None,
               p95_ms=float(np.percentile(ms, 95)) if ms else None,
               max_ms=max(ms) if ms else None)
    if baseline:
        out['wins'] = sum(correct(r) and not correct(baseline[r['image_sha256']]) for r in positive)
        out['losses'] = sum(not correct(r) and correct(baseline[r['image_sha256']]) for r in positive)
    return out


def main(args):
    out = Path(args.output).resolve();out.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'internal/competitor-implementation-2026-10-06-benchmark-approved'
    old = json.loads((source/'inputs.json').read_text())
    queries = old['queries']
    config = ROOT/'workbench/config.yaml'
    settings = pipelines.load(config)
    es = embeddings.load_settings(config)
    names = args.pipeline or NAMES
    indexes = {}
    for name in names:
        p = settings.find(name)
        entries = [p.embedding]
        if p.competitor and p.competitor.get('secondary'):
            entries.append(p.competitor['secondary']['embedding'])
        for entry in entries:
            e = es.find(entry);directory = Path(embeddings.entry_dir(settings.db_path, entry))
            idx = json.loads((directory/'index.json').read_text())
            indexes[entry] = dict(index_sha256=digest(directory/'index.json'),
                                  vectors_sha256=digest(directory/idx['vectors_file']))
            if not e.base_url.startswith('http://192.168.86.14:18081/'):
                raise ValueError('An embedding service uses another destination.')
    frozen = dict(source_manifest_sha256=digest(source/'inputs.json'), queries=queries,
                  pipeline_config_sha256=digest(config), indexes=indexes, names=names,
                  code={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),
                      ROOT/'workbench/pipeline/embedding_run.py',
                      ROOT/'workbench/pipeline/competitor_steps.py']},
                  no_rebuild=True, requested_top_k=10)
    signature = hashlib.sha256(json.dumps(frozen,sort_keys=True).encode()).hexdigest()
    manifest = out/'matrix-inputs.json'
    if manifest.exists() and json.loads(manifest.read_text())['frozen_hash'] != signature:
        raise ValueError('Frozen inputs changed. Use another output directory.')
    manifest.write_text(json.dumps(dict(frozen_hash=signature,**frozen),indent=2)+'\n')
    if args.prepare_only:
        print(json.dumps(dict(queries=len(queries),pipelines=names,service_calls=0)),flush=True);return
    result = out/'matrix-results.jsonl'
    rows = [json.loads(l) for l in result.read_text().splitlines()] if result.exists() else []
    done = {(r['pipeline'],r['image_sha256']) for r in rows}
    with tempfile.TemporaryDirectory(prefix='competitor-followup-') as folder:
        for name in names:
            todo = [q for q in queries if (name,q['image_sha256']) not in done]
            if not todo:continue
            print(json.dumps(dict(event='pipeline_start',pipeline=name,queries=len(todo))),flush=True)
            backend = embedding_run.build_pipeline_backend(settings.find(name),config,top_k=10)
            for query in todo:
                data = Path(query['path']).read_bytes()
                if hashlib.sha256(data).hexdigest() != query['image_sha256']:
                    raise ValueError('Query bytes changed.')
                path = Path(folder)/Path(query['path']).name;path.write_bytes(data)
                os.utime(path,(1790636400,1790636400))
                start=time.perf_counter()
                try:
                    candidates,latency,status,error,trace=backend.ask(str(path))
                except Exception as exc:
                    candidates,latency,status,error,trace=[],(time.perf_counter()-start)*1000,None,str(exc),None
                row=dict(query,pipeline=name,candidates=candidates,latency_ms=latency,
                         wall_ms=(time.perf_counter()-start)*1000,status=status,error=error,trace=trace)
                with result.open('a') as stream:stream.write(json.dumps(row)+'\n')
                rows.append(row)
                print(json.dumps(dict(event='query',pipeline=name,completed=sum(r['pipeline']==name for r in rows),
                                      total=len(queries),query=query['image_sha256'][:12],error=error)),flush=True)
            base={r['image_sha256']:r for r in rows if r['pipeline']=='siglip2-p512-rot5-seg'}
            summary={n:metrics([r for r in rows if r['pipeline']==n],base or None) for n in names if any(r['pipeline']==n for r in rows)}
            (out/'matrix-report.json').write_text(json.dumps(dict(frozen_hash=signature,pipelines=summary,
                limitations=['Local adaptations, not original competitor trained models.',
                             'The frozen cohort contains no confirmed absent-wine photos.',
                             'Existing embedding pipelines have no cascade-equivalent total deadline.',
                             'Sequential runs reuse service and OCR caches. Latency is not a cold-load SLA.']),indent=2)+'\n')
            print(json.dumps(dict(event='pipeline_complete',pipeline=name,metrics=summary[name])),flush=True)
            del backend


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True);parser.add_argument('--pipeline',action='append')
    parser.add_argument('--prepare-only',action='store_true')
    main(parser.parse_args())
