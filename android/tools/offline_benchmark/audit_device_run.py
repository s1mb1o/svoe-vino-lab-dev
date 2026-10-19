#!/usr/bin/env python3
"""Independently verify full-selector predictions against frozen accepted slugs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

from run_control import percentile,save


def audit(directory, queries):
    metadata=json.loads((directory/'run.json').read_text())
    responses=[json.loads(line) for line in (directory/'responses.jsonl').read_text().splitlines()]
    expected={q['query_id']:q for q in queries}
    assert len(expected)==len(queries)
    assert [r['query_id'] for r in responses]==[q['query_id'] for q in queries[:len(responses)]]
    assert len(responses)==metadata['requests']
    segments=metadata.get('process_segments',[dict(start_request=1,pid=metadata['initial_pid'])])
    starts=[s['start_request'] for s in segments]
    assert starts and starts[0]==1 and starts==sorted(set(starts))
    assert all(1<=n<=len(queries) for n in starts)
    assert segments[-1]['pid']==metadata['initial_pid']
    if metadata.get('resume'):
        inherited=metadata['resume']
        old_bytes=(directory/'inherited-run.json').read_bytes()
        assert hashlib.sha256(old_bytes).hexdigest()==inherited['source_run_sha256']
        old=json.loads(old_bytes)
        assert old['requests']==inherited['records']
        for field in ('query_file_sha256','pack_manifest_sha256','pack_version','serial','package',
                      'assignments','distinct_images','endpoint','reranking','barcode'):
            assert old[field]==metadata[field]
        assert old.get('installed_apk_sha256') in (None,metadata['installed_apk_sha256'])
        required={'responses.jsonl'}|{f'variant-{v:02d}/predictions.jsonl' for v in range(1,11)}
        assert set(inherited['prefix_files'])==required
        for name,identity in inherited['prefix_files'].items():
            with (directory/name).open('rb') as stream:prefix=stream.read(identity['bytes'])
            assert prefix.endswith(b'\n') and len(prefix.splitlines())==inherited['records']
            assert hashlib.sha256(prefix).hexdigest()==identity['sha256']
        old_segments=[s for s in old.get('process_segments',[
            dict(start_request=1,pid=old['initial_pid'])]) if s['start_request']<=inherited['records']]
        assert segments==old_segments+[dict(start_request=inherited['records']+1,pid=metadata['initial_pid'])]
    for number,record in enumerate(responses,1):
        assert record.get('request_number',number)==number
        assert record['variant']=='all' and record['accelerator']=='GPU'
        assert record['image_sha256']==expected[record['query_id']]['image_sha256']
        body=record['response']
        expected_pid=next(s['pid'] for s in reversed(segments) if s['start_request']<=number)
        assert body['pid']==expected_pid
        assert body['reranking'] is False and body['barcode'] is False
        if record['status']==200:
            assert body['offline'] is True and body['encoder_accelerator']=='GPU'
            assert body['segmenter_accelerator']=='CPU' and body['pack_version']==metadata['pack_version']
            assert [v['variant'] for v in body['variants']]==list(range(1,11))
            for encoder in body['encoders']:
                assert encoder['accelerator']=='GPU' and encoder['gpu_constant_tensor_sharing'] is True
                assert encoder['gpu_source_quantization'] is False and abs(encoder['norm']-1)<1e-4
    complete=metadata['complete'] and len(responses)==len(queries)
    errors=sum(r['status']!=200 for r in responses)
    if 'errors' in metadata:assert metadata['errors']==errors
    variants={}
    for variant in range(1,11):
        file=directory/f'variant-{variant:02d}'/'predictions.jsonl'
        predictions=[json.loads(line) for line in file.read_text().splitlines()]
        assert len(predictions)==len(responses)
        hits={str(k):0 for k in (1,5,10)}
        for record,prediction in zip(responses,predictions):
            assert prediction['query_id']==record['query_id']
            assert prediction['image_sha256']==record['image_sha256']
            if record['status']==200:
                result=record['response']['variants'][variant-1]
                assert prediction['candidates']==result['candidates'] and prediction['predicted_slug']==result['slug']
                candidates=prediction['candidates']
                assert candidates and len({c['slug'] for c in candidates})==len(candidates)
                assert all(math.isfinite(c['score']) for c in candidates)
                assert all(a['score']>=b['score'] for a,b in zip(candidates,candidates[1:]))
                assert prediction['predicted_slug']==candidates[0]['slug']
                for k in (1,5,10):
                    hits[str(k)]+=bool(set(expected[prediction['query_id']]['truth']).intersection(c['slug'] for c in candidates[:k]))
            else:
                assert prediction['predicted_slug'] is None and prediction['candidates']==[]
        assert hits==metadata['hits'][str(variant)]
        variants[str(variant)]=dict(records=len(predictions),observed_hits=hits,
            top_k_percent={k:100*n/len(queries) for k,n in hits.items()} if complete else None)
    times=[r['client_ms'] for r in responses]
    return dict(verification_passed=True,complete=complete,planned_assignments=len(queries),
        received_assignments=len(responses),errors=errors,variants=variants,
        inherited_records=metadata.get('resume',{}).get('records',0),process_segments=segments,
        timing_mode='shared-query-work',client_ms=dict(median=statistics.median(times) if times else None,
        p95=percentile(times,.95)),maximum_thermal_status=metadata['maximum_thermal_status'],
        peak_sampled_pss_kib=metadata['peak_sampled_pss_kib'],
        maximum_battery_celsius=metadata['maximum_battery_celsius'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--queries',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.run,json.loads(args.queries.read_text()))
    save(args.run/'independent-audit.json',result)
    lines=['# Android full-selector evaluation','',f'Complete: {result["complete"]}.',
        f'Received: {result["received_assignments"]} of {result["planned_assignments"]} assignments.',
        'Re-ranking and barcode recognition are disabled.','']
    if result['inherited_records']:
        lines += [f'Inherited records: {result["inherited_records"]}.',
            'The inherited prediction bytes pass SHA-256 checks.',
            'Thermal and memory maxima describe this process segment only.',
            'Client latency includes inherited requests and new requests.',
            'Read the inherited run for the earlier segment telemetry.','']
    if result['complete']:
        lines+=['| Recipe | Top-1 | Top-5 | Top-10 |','| --- | --- | --- | --- |']
        for variant,values in result['variants'].items():
            values=values['top_k_percent']
            lines.append(f'| {variant} | {values["1"]:.2f}% | {values["5"]:.2f}% | {values["10"]:.2f}% |')
    else:lines+=['This run is incomplete. Complete-cohort accuracy is not available.']
    lines+=['','Use the independent pilot for per-recipe latency.',
        'Full-selector timings share work inside each query.','']
    (args.run/'report.md').write_text('\n'.join(lines))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
