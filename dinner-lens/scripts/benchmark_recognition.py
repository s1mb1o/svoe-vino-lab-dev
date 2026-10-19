#!/usr/bin/env python3
"""Fresh recognition comparison on frozen images/labels with v4 pairing contracts."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import statistics
import time

from fastapi.testclient import TestClient
from dinner_lens.api import create_app
from dinner_lens.configuration import load_config, asset_path
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.provider import QwenRecognizer


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect_pages(client, response):
    """Follow every page, including valid unclassified responses without a profile."""
    first=response.json();page=first
    entries=[];pages=[];functional=True
    while response.status_code==200:
        pages.append({'wine_slugs':page['wine_slugs'],'sources':[w['selection_source'] for w in page['results']]})
        entries.extend(page['results'])
        functional &= page['resolved_node_id']==first['resolved_node_id'] and page.get('effective_profile_id')==first.get('effective_profile_id')
        functional &= all(w['reason'] and w['ranking_evidence'] for w in page['results'])
        if not page['next_cursor']:break
        if len(pages)>100:raise AssertionError('Pagination did not terminate')
        response=client.post('/v1/recommendations/more',json={'cursor':page['next_cursor']});page=response.json()
    slugs=[w['wine_slug'] for w in entries];sources=[w['selection_source'] for w in entries]
    functional &= response.status_code==200 and len(slugs)==len(set(slugs)) and len(slugs)==first.get('total_eligible',0)
    functional &= 'embedding' not in sources or 'curated' not in sources[sources.index('embedding'):]
    return first,entries,pages,bool(functional),response.status_code


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    config,path=load_config(args.config)
    root=args.ground_truth_root.resolve()
    registry=json.loads((root/'prompt-registry.json').read_text())
    prompt=root/registry['current']['image_system']
    if sha(prompt)!=sha(asset_path(config.recognition.prompt,path)):
        raise ValueError('Service prompt differs from the current English prompt registry')
    reference=json.loads(args.pairing_reference.read_text())
    frozen={c['case']['node_id']:c for c in reference['cases'] if c['case']['confirmed_attributes']=={}}
    k=Knowledge(asset_path(config.assets.dataset,path),asset_path(config.assets.style,path))
    index=EmbeddingIndex(k,asset_path(config.assets.index,path))
    engine=Engine(k,index,cursor_secret=secrets.token_bytes(32))
    class ReplayRecognizer(QwenRecognizer):
        def recognize(self, image):
            image_sha=hashlib.sha256(image).hexdigest()
            record_path=args.replay_records/(image_sha+'.json')
            if record_path.exists():
                record=json.loads(record_path.read_text())
                selected=self.settings.fallback if record.get('fallback_used') else self.settings
                if selected is None:raise ValueError('Replay fallback configuration changed')
                body=json.dumps(self._backend_payload(self.payload(image),selected),ensure_ascii=False).encode()
                if hashlib.sha256(body).hexdigest()!=record['request_sha256']:
                    raise ValueError('Replay provider request changed')
                if record['primary_model']!=self.model or record['fallback_model']!=self.fallback_model:
                    raise ValueError('Replay provider chain changed')
                return record['parsed'], {k:v for k,v in record.items() if k not in {'parsed','response'}} | {'replayed':True,'source_record_sha256':sha(record_path)}
            # Preserve the original failed inference. Do not replace it with a new successful draw.
            for failed_path in (args.replay_records.parent/'cases').glob('image*.json'):
                failed=json.loads(failed_path.read_text())
                if failed['score']['http_status']!=503:continue
                payload={'image_base64':base64.b64encode(image).decode()}
                if hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()==failed['input_request_sha256']:
                    raise RuntimeError('Recorded recognition failure; no new inference')
            raise ValueError('Replay has no matching live provider record')
    recognizer=(ReplayRecognizer if args.replay_records else QwenRecognizer)(k,
        asset_path(config.recognition.prompt,path),settings=config.recognition,
        record_directory=None if args.replay_records else output/'provider-records')
    token=secrets.token_urlsafe(32)
    app=create_app(engine,recognizer,api_token=token,limits=config.limits)
    cases=[];hashes={}
    for group in ['text','fallbacks','images']:
        source=root/f'ground-truth.{group}.jsonl'
        manifest=json.loads((root/('ground-truth.manifest.json' if group=='text' else f'ground-truth.{group}.manifest.json')).read_text())
        expected=manifest.get('text_ground_truth_sha256') or manifest['ground_truth_sha256']
        if sha(source)!=expected:raise ValueError('Frozen ground truth changed')
        hashes[group]=sha(source)
        cases.extend((group,json.loads(line)) for line in source.read_text().splitlines() if line)
    source_root=Path(__file__).resolve().parents[1]
    source_hashes={p.name:sha(p) for p in (source_root/'src/dinner_lens').glob('*.py')}
    manifest={'started_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'recorded live response replay after scorer-only fix; no new model calls' if args.replay_records else 'fresh live inference through authenticated ASGI HTTP; every page',
        'replay_source':str(args.replay_records) if args.replay_records else None,'benchmark_sha256':sha(__file__),
        'ground_truth_sha256':hashes,'dataset_sha256':k.sha256,'index_version':index.version,
        'prompt_sha256':recognizer.prompt_sha256,'prompt_registry_sha256':sha(root/'prompt-registry.json'),
        'configuration_sha256':sha(path),'pairing_reference_sha256':sha(args.pairing_reference),
        'primary_model':recognizer.model,'fallback_model':recognizer.fallback_model,'instruction_language':'en',
        'source_sha256':source_hashes,'expected_labels_sent_to_model':False,
        'limitations':['Fixed75 photos with frozen model-independent assistant labels, not human expert ground truth.',
            'V4 pairing lists use frozen previous outputs, not sensory judgments.',
            'Cloud and local runs are separate fresh draws; temperature zero does not make inference deterministic.']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

    def execute(group,case):
        started=time.monotonic();inputs=case['input']
        if group=='images':
            image=(root/inputs['image_path']).read_bytes()
            if hashlib.sha256(image).hexdigest()!=case['provenance']['image_sha256']:raise ValueError('Frozen image changed')
            payload={'image_base64':base64.b64encode(image).decode()}
            endpoint='/v1/recognize-and-recommend'
        else:
            payload={'confirmed_dish':inputs['confirmed_dish'],'user_constraints':inputs['user_constraints']}
            endpoint='/v1/recommendations'
        with TestClient(app) as client:
            client.headers['Authorization']='Bearer '+token
            response=client.post(endpoint,json=payload)
            first,entries,pages,functional,status=collect_pages(client,response)
            slugs=[w['wine_slug'] for w in entries];sources=[w['selection_source'] for w in entries]
            node=first.get('resolved_node_id');ref=frozen.get(node)
            eligible={w['wine_slug'] for w in ref['wines']} if ref else set()
            if group!='images' and inputs['user_constraints']:
                eligible &= set(case['expected']['eligible_wine_slugs'])
            pairing_match=(set(slugs)==eligible) if ref else not slugs
            row={'case_id':case['case_id'],'group':group,'http_status':status,'resolved_node_id':node,
                'functional_pass':bool(functional),'frozen_v4_pairing_set_pass':pairing_match,
                'pages':len(pages),'wine_count':len(entries),'embedding_count':sources.count('embedding'),
                'latency_seconds':round(time.monotonic()-started,3)}
            if group=='images':
                expected=case['expected'];raw=first.get('recognition',{});meta=first.get('llm',{})
                row.update(raw_safe=raw.get('visual_node_id') in expected['acceptable_visual_node_ids'],
                    raw_deepest=raw.get('visual_node_id') in expected['maximum_visually_supported_node_ids'],
                    guarded_safe=node in expected['acceptable_visual_node_ids'],
                    guarded_deepest=node in expected['maximum_visually_supported_node_ids'],
                    clarification_pass=not expected['clarification_required'] or (first.get('needs_clarification') is True and bool(first.get('clarification_question'))),
                    selected_model=meta.get('returned_model'),fallback_used=meta.get('fallback_used',False))
                row['strict_pass']=bool(functional and pairing_match and row['guarded_safe'] and row['clarification_pass'])
            else:
                row['node_correct']=node==case['expected']['resolved_node_id']
                row['strict_pass']=bool(functional and pairing_match and row['node_correct'])
            target=output/'cases';target.mkdir(exist_ok=True)
            (target/(case['case_id']+'.json')).write_text(json.dumps({'score':row,'first_response':first,'pages':pages,
                'input_request_sha256':hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()},ensure_ascii=False,indent=2)+'\n')
            return row

    rows=[]
    for group,case in cases:
        if group!='images':rows.append(execute(group,case))
    print(json.dumps({'text_cases':len(rows),'strict_pass':sum(r['strict_pass'] for r in rows)}),flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(execute,g,c):c['case_id'] for g,c in cases if g=='images'}
        for future in as_completed(jobs):
            rows.append(future.result())
            print(json.dumps(rows[-1]),flush=True)
    if source_hashes!={p.name:sha(p) for p in (source_root/'src/dinner_lens').glob('*.py')}:raise ValueError('Source changed during run')
    def aggregate(items):
        fields=['functional_pass','frozen_v4_pairing_set_pass','node_correct','raw_safe','raw_deepest','guarded_safe','guarded_deepest','clarification_pass','strict_pass']
        values=sorted(r['latency_seconds'] for r in items)
        return {'cases':len(items),**{f:sum(bool(r[f]) for r in items if f in r) for f in fields if any(f in r for r in items)},
            'p50_seconds':statistics.median(values),'p95_seconds':values[min(len(values)-1,int(.95*len(values)))],
            'fallback_count':sum(r.get('fallback_used',False) for r in items),'pages':sum(r['pages'] for r in items),
            'selected_models':{m:sum(r.get('selected_model')==m for r in items) for m in sorted({r.get('selected_model') for r in items if r.get('selected_model')})}}
    result={'manifest':manifest,'text_and_constraints':aggregate([r for r in rows if r['group']=='text']),
        'fallback_classes':aggregate([r for r in rows if r['group']=='fallbacks']),
        'photos':aggregate([r for r in rows if r['group']=='images']),'complete':len(rows)==238,'cases':sorted(rows,key=lambda r:r['case_id'])}
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['manifest','cases']},indent=2),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--ground-truth-root',type=Path,required=True);p.add_argument('--pairing-reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=2)
    p.add_argument('--replay-records',type=Path,help='Explicitly replay exact matching live receipts after scorer-only changes')
    run(p.parse_args())


if __name__=='__main__':main()
