"""Evaluate frozen real photos with base DINOv3, ArcFace, and the unchanged cascade.

No index rebuild, training, or production configuration write occurs. Exact source
families in training or references are excluded. Query files are copied and dated
before any service call. Results are resumable by query hash and frozen input hash.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workbench/pipeline'))
sys.path.insert(0, str(ROOT))
import numpy as np
import yaml
import arcface
import build_embeddings
import derive
import embedding_run
import embeddings
import labdb
import production_errors
from matcher.cascade_run import Run, Budget
from matcher import rerank
from matcher.service import load_matcher


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentiles(values):
    if not values:return None
    return dict(median_ms=float(np.median(values)), p95_ms=float(np.percentile(values,95)), max_ms=float(max(values)))


def gate(candidates, evidence, verified=False):
    if not candidates:return False
    score=candidates[0]['score']
    margin=score-candidates[1]['score'] if len(candidates)>1 else score
    baseline=score>=.70 and margin>=.015
    # A conservative evaluation rule: retain the baseline unless explicit evidence
    # contradicts or cannot distinguish a triggered verification. No membership label.
    return baseline and (not verified or evidence not in ('contradicted','unsure','error'))


def acceptance(rows, verified=False):
    accepted=[r for r in rows if gate(r['cascade']['candidates'],r['cascade']['evidence'],verified)]
    correct=[r for r in accepted if r['truth'] and r['cascade']['candidates'][0]['slug'] in r['truth'] and r['label']!='unusable']
    known=[r for r in rows if r['truth'] and r['label']!='unusable']
    correct_predictions=[r for r in known if r['cascade']['candidates'] and r['cascade']['candidates'][0]['slug'] in r['truth']]
    accepted_ids={r['image_sha256'] for r in accepted}
    return dict(total=len(rows),accepted=len(accepted),accepted_correct=len(correct),accepted_accuracy=len(correct)/len(accepted) if accepted else None,coverage=len(accepted)/len(rows) if rows else None,false_acceptance=len(accepted)-len(correct),false_rejection=sum(r['image_sha256'] not in accepted_ids for r in correct_predictions),known_rejected=sum(r['image_sha256'] not in accepted_ids for r in known),latency=percentiles([r['cascade']['latency_ms'] for r in rows]))


def evidence_of(run, answer):
    if answer is None:return 'error'
    if answer.code is not None and len(answer.code.get('slugs',[]))==1:return 'unique-code'
    explanation=answer.rerank
    if explanation is None:
        if any(s['id'].startswith('vlm:') and s['status']=='error' for s in run.stages):return 'error'
        return 'untriggered'
    rule=run.cascade.rules.by_slug[answer.pairs[0][0]]
    response=run.vlm.get(explanation['cluster'])
    parsed=response if isinstance(response,dict) else rerank.parse_json(response)
    if not parsed:return 'unsure'
    if rule['mode']=='verdict':
        chosen=rerank.verdict_choice(rule,parsed)
        return 'supported' if chosen==answer.pairs[0][0] else 'contradicted' if chosen else 'unsure'
    selected=answer.pairs[0][0]
    agreements=0
    for q in rule.get('questions',[]):
        if not q.get('valid'):continue
        expected=rerank.normalize((q.get('answers') or {}).get(selected))
        actual=rerank.compared_answer(q,rerank.normalize(parsed.get(q['id'])))
        if expected is None or actual is None:continue
        if actual!=expected:return 'contradicted'
        agreements+=1
    return 'supported' if agreements else 'unsure'


def split_group(row):
    # All photos of one reviewed identity stay in the same evaluation split.
    value='|'.join(sorted(row['truth'])) if row['truth'] else row['image_sha256']
    return 'calibration' if int(hashlib.sha256(value.encode()).hexdigest()[:8],16)%3==0 else 'test'


def freeze_queries(conn, sets, excluded):
    rows=[];skipped=[];seen=set()
    for set_name in sets:
        for place,label,sha,name,folder,ext,deleted in conn.execute('SELECT p.place,p.label,p.sha256,p.file_name,i.folder,i.extension,p.marked_delete FROM test_photo p JOIN image i ON p.sha256=i.sha256 WHERE p.set_name=? ORDER BY p.place,p.file_name',(set_name,)):
            if deleted or place=='__drawer__' or (label!='positive' and label!='unusable'):continue
            if sha in seen:continue
            seen.add(sha)
            if production_errors.related_hashes(conn,sha)&excluded:
                skipped.append(dict(set=set_name,image_sha256=sha,reason='source family occurs in training or references'));continue
            path=Path(labdb.image_dir(str(ROOT/'workbench/data/catalog/catalog.sqlite3'),folder))/(sha+'.'+ext)
            if not path.is_file() or digest(path)!=sha:raise ValueError('query bytes do not match image store hash')
            rows.append(dict(set=set_name,place=place,label=label,image_sha256=sha,path=str(path),file=name,truth=[] if place=='__null__' or label=='unusable' else [place]))
    return rows,skipped


def recall(rows,model):
    positives=[r for r in rows if r['truth'] and r['label']!='unusable']
    return dict(positive=len(positives), **{f'recall_at_{k}':sum(any(c['slug'] in r['truth'] for c in r[model]['candidates'][:k]) for r in positives)/len(positives) if positives else None for k in (1,5,10)},latency=percentiles([r[model]['latency_ms'] for r in rows]))


async def main(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    db=ROOT/'workbench/data/catalog/catalog.sqlite3'
    artifact=ROOT/'workbench/data/models/dinov3-vitl16-arcface-20261006-v2'
    snapshot=json.loads((artifact/'training-snapshot.json').read_text())
    config=yaml.safe_load((artifact/'config.yaml').read_text())
    entry=next(e for e in config['embeddings'] if e['name']=='gx10-dinov3-vitl16')
    embed=embeddings.Embedding(entry)
    catalogue=embedding_run.Catalogue(embed,str(db))
    checkpoint=artifact/'projection.npz'
    projection=arcface.Projection.load(dict(checkpoint=str(checkpoint),sha256=digest(checkpoint)),embed.model,embed.extra_body)
    projected=copy.copy(catalogue);projected.dim=projection.weight.shape[0]
    projected.views={v:(projection.transform(matrix),numbers) for v,(matrix,numbers) in catalogue.views.items()}
    index_dir=Path(embeddings.entry_dir(str(db),embed.name))
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        excluded={r[0] for r in conn.execute('SELECT sha256 FROM wine_image')}
        excluded|={v for s in snapshot['samples'] for v in (s['source_sha256'],s['group'])}
        queries,skipped=freeze_queries(conn,args.set,excluded)
    if args.limit:queries=queries[:args.limit]
    base_index=json.loads((index_dir/'index.json').read_text())
    frozen=dict(queries=queries,excluded=skipped,deadline_seconds=args.deadline,benchmark_script_sha256=digest(__file__),base_vectors_sha256=digest(index_dir/base_index['vectors_file']),reference_identity_sha256=hashlib.sha256(json.dumps(dict(slugs=catalogue.slugs,items=catalogue.items),sort_keys=True).encode()).hexdigest(),checkpoint_sha256=digest(checkpoint),training_snapshot_sha256=digest(artifact/'training-snapshot.json'),base_index_sha256=digest(index_dir/'index.json'))
    matcher_config=yaml.safe_load((ROOT/'matcher/config.yaml').read_text())
    matcher_config['matcher']={'pipeline':'cascade-p512-rot5'}
    selected=next(e for e in matcher_config['pipeline'] if e['name']=='cascade-p512-rot5')
    selected['catalog']=str(db.parent)
    selected['endpoint']=args.gateway
    selected['sam3']['endpoint']=args.gateway+'/upstream/sam3'
    selected['barcode']['endpoint']=args.gateway+'/upstream/qr-scanner'
    selected['rerank']['endpoint']=args.gateway+'/v1'
    frozen['cascade_config']=selected
    frozen['siglip2_index_sha256']=digest(db.parent/'embeddings'/selected['embedding']/'index.json')
    frozen_hash=hashlib.sha256(json.dumps(frozen,sort_keys=True).encode()).hexdigest()
    manifest=out/'inputs.json'
    if manifest.exists() and json.loads(manifest.read_text())['frozen_hash']!=frozen_hash:raise ValueError('frozen benchmark inputs changed; use a new output directory')
    manifest.write_text(json.dumps(dict(frozen_hash=frozen_hash,**frozen),indent=2)+'\n')
    cfg=out/'cascade-config.yaml';cfg.write_text(yaml.safe_dump(matcher_config));os.utime(cfg,(1790636400,1790636400))
    if args.prepare_only:
        print(json.dumps(dict(prepared=len(queries),excluded=len(skipped),frozen_hash=frozen_hash,service_calls=0)),flush=True)
        return
    matcher=load_matcher(cfg)
    await matcher.startup()
    model=build_embeddings.OpenAIBackend(embed,timeout=30,waits=())
    segmenter=derive.Sam3Client()
    results_path=out/'results.jsonl'
    rows=[json.loads(l) for l in results_path.read_text().splitlines()] if results_path.exists() else []
    finished={r['image_sha256'] for r in rows}
    try:
        with tempfile.TemporaryDirectory(prefix='wine-audit-') as directory:
            for q in queries:
                if q['image_sha256'] in finished:continue
                path=Path(directory)/Path(q['path']).name;path.write_bytes(Path(q['path']).read_bytes());os.utime(path,(1790636400,1790636400))
                row=dict(q,split=split_group(q))
                started=time.perf_counter()
                try:
                    image,_=derive.open_image(str(path))
                    inputs,missing=embedding_run.query_inputs(image,embed.views,segmenter,scene_selection=True)
                    pngs=[embeddings.png_bytes(im) for im in inputs.values()]
                    if not pngs:raise ValueError('no query input views')
                    vectors=model.embed(pngs);vectors=arcface.normalize(vectors)
                    query=dict(zip(inputs,vectors))
                    embed_ms=(time.perf_counter()-started)*1000
                    before=time.perf_counter();base=catalogue.rank(query,10);base_search=(time.perf_counter()-before)*1000
                    before=time.perf_counter();pq=dict(zip(inputs,projection.transform(vectors)));arc=projected.rank(pq,10);arc_search=(time.perf_counter()-before)*1000
                    row['base']=dict(candidates=[dict(slug=c['slug'],score=c['score']) for c in base],latency_ms=embed_ms+base_search,search_ms=base_search)
                    row['arcface']=dict(candidates=[dict(slug=c['slug'],score=c['score']) for c in arc],latency_ms=embed_ms+arc_search,search_ms=arc_search)
                except Exception as exc:
                    row['base']=row['arcface']=dict(candidates=[],latency_ms=(time.perf_counter()-started)*1000,error=str(exc))
                started=time.perf_counter()
                run=Run(matcher.cascade,path.read_bytes(),Budget(started,None,started+args.deadline),'match')
                try:
                    answer,reason=await run.execute()
                    evidence=evidence_of(run,answer)
                    row['cascade']=dict(candidates=[dict(slug=s,score=float(v)) for s,v in (answer.pairs[:10] if answer else [])],evidence=evidence,latency_ms=(time.perf_counter()-started)*1000,trace=run.trace(answer,reason),vlm_answers=run.vlm)
                except Exception as exc:
                    row['cascade']=dict(candidates=[],evidence='error',latency_ms=(time.perf_counter()-started)*1000,error=str(exc))
                with results_path.open('a') as f:f.write(json.dumps(row)+'\n')
                rows.append(row)
                print(json.dumps(dict(completed=len(rows),total=len(queries),query=q['image_sha256'][:12],base=row['base']['candidates'][:1],arcface=row['arcface']['candidates'][:1],cascade=row['cascade']['candidates'][:1],evidence=row['cascade']['evidence'])),flush=True)
    finally:await matcher.shutdown()
    report=dict(frozen_hash=frozen_hash,query_count=len(rows),excluded_source_families=len(skipped),reference_wines=len(catalogue.slugs),deadline_seconds=args.deadline,models={m:recall(rows,m) for m in ('base','arcface','cascade')},acceptance={s:{'baseline':acceptance([r for r in rows if r['split']==s]),'verification_rule':acceptance([r for r in rows if r['split']==s],True)} for s in ('calibration','test')},failure_classes=dict(absent=sum(not r['truth'] and r['label']!='unusable' for r in rows),unreadable=sum(r['label']=='unusable' for r in rows),wrong_identity=sum(bool(r['truth']) and bool(r['cascade']['candidates']) and r['cascade']['candidates'][0]['slug'] not in r['truth'] for r in rows),candidate_window_miss=sum(bool(r['truth']) and not any(c['slug'] in r['truth'] for c in r['cascade']['candidates'][:10]) for r in rows)),limitations=['Existing reviewed photos; labels and exact source-family exclusions are frozen. Near duplicates without source links can remain.','Base DINOv3 and ArcFace use identical inputs and current base reference vectors. Cascade uses its own unchanged reference index and verifier.','No gate fitting or model selection uses this test split. A conservative rule is an evaluation only.','Model latencies include LAN calls and shared service load. DINOv3 query embedding is shared between base and ArcFace.'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


def offline_projection(output):
    """Measure the local projection alone on cached reference features. No service calls."""
    artifact=ROOT/'workbench/data/models/dinov3-vitl16-arcface-20261006-v2'
    config=yaml.safe_load((artifact/'config.yaml').read_text())
    entry=next(e for e in config['embeddings'] if e['name']=='gx10-dinov3-vitl16')
    index_dir=ROOT/'workbench/data/catalog/embeddings/gx10-dinov3-vitl16'
    index=json.loads((index_dir/'index.json').read_text())
    vectors=np.load(index_dir/index['vectors_file'],allow_pickle=False)
    checkpoint=artifact/'projection.npz'
    projection=arcface.Projection.load(dict(checkpoint=str(checkpoint),sha256=digest(checkpoint)),entry['model'],entry.get('extra_body') or {})
    single=[];batch=[]
    for i in range(300):
        start=time.perf_counter();q=projection.transform(vectors[i%len(vectors):i%len(vectors)+1]);single.append((time.perf_counter()-start)*1000)
        if not np.isfinite(q).all() or not np.allclose(np.linalg.norm(q,axis=1),1,atol=1e-5):raise ValueError('projection output is invalid')
    for i in range(8):
        start=time.perf_counter();projected=projection.transform(vectors);batch.append((time.perf_counter()-start)*1000)
    report=dict(kind='offline cached-reference projection performance',cached_vectors=len(vectors),input_dimension=vectors.shape[1],output_dimension=projected.shape[1],checkpoint_sha256=digest(checkpoint),vectors_sha256=digest(index_dir/index['vectors_file']),single_query=percentiles(single),cached_index_batch=percentiles(batch),base_vector_bytes=vectors.nbytes,projected_vector_bytes=projected.nbytes,accuracy_measured=False,limitations=['This measures the local projection only. It excludes query image preprocessing, embedding services, and retrieval.','The inputs include current and stale index-cache rows. This is not an independent real-photo accuracy test.'])
    path=Path(output);path.mkdir(parents=True,exist_ok=True);(path/'projection-performance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--set',action='append',default=[]);p.add_argument('--output',required=True);p.add_argument('--limit',type=int);p.add_argument('--gateway',default='http://192.168.86.14:18081');p.add_argument('--deadline',type=float,default=9.5);p.add_argument('--offline-projection',action='store_true');p.add_argument('--prepare-only',action='store_true')
    args=p.parse_args();args.set=args.set or ['official-test-2026-10-01','test-1','2026sep26superlenta']
    if args.offline_projection:offline_projection(args.output)
    else:asyncio.run(main(args))
