"""Validate and preserve one finalized full-run prefix before device continuation."""
import json
import math
from pathlib import Path
import shutil

from profiles import digest


def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('Reject symbolic links in a saved attempt')
        if path.is_file():result[str(path.relative_to(root))]=dict(bytes=path.stat().st_size,sha256=digest(path))
    return result


def lines(path):
    raw=path.read_bytes()
    if not raw or not raw.endswith(b'\n'):raise ValueError('Incomplete JSONL file: '+str(path))
    return raw,[json.loads(row) for row in raw.splitlines()]


def verify_preserved(source,destination,record):
    if inventory(source)!=record['source_inventory']:raise RuntimeError('Raw resume source changed')
    for name in ('responses.jsonl','predictions.jsonl'):
        if not (destination/name).read_bytes().startswith((source/name).read_bytes()):
            raise RuntimeError('Inherited prefix changed: '+name)


def restore_prefix(source,destination,queries,metadata,pack,expected_records):
    source=source.resolve();destination=destination.resolve()
    if source==destination or source in destination.parents:raise ValueError('Require a new sibling attempt')
    before=inventory(source)
    original=json.loads((source/'run.json').read_text())
    if original.get('complete') is not False or original.get('mode')!='full' or 'elapsed_s' not in original:
        raise ValueError('Require a finalized incomplete full run')
    for field in ('mode','condition','package','serial','query_file_sha256','pack_manifest_sha256',
                  'pack_version','installed_apk_sha256','assignments','reranking','barcode'):
        if original[field]!=metadata[field]:raise ValueError('Resume identity changed: '+field)
    if original['reranking'] is not False or original['barcode'] is not False:
        raise ValueError('Optional recognition must remain disabled')
    if json.loads((source/'queries.json').read_text())!=queries:raise ValueError('Frozen assignments changed')
    response_bytes,responses=lines(source/'responses.jsonl')
    prediction_bytes,predictions=lines(source/'predictions.jsonl')
    if not 0<expected_records<len(queries) or len(responses)!=expected_records or len(predictions)!=expected_records:
        raise ValueError('Unexpected saved prefix length')
    if original['requests']!=expected_records:raise ValueError('Saved request count changed')
    condition=metadata['condition'];slugs=set(pack['slugs']);errors=0
    for number,(query,response,prediction) in enumerate(zip(queries,responses,predictions),1):
        if (response['request_number']!=number or response['query_id']!=query['query_id'] or
            prediction['query_id']!=query['query_id'] or response['image_sha256']!=query['image_sha256'] or
            prediction['image_sha256']!=query['image_sha256'] or prediction['image_path']!=query['image_path']):
            raise ValueError('Prefix assignment order or image changed')
        if (not query['truth'] or not math.isfinite(response['client_ms']) or response['client_ms']<0 or
            prediction['client_request_ms']!=response['client_ms'] or prediction['timing_mode']!='independent' or
            response['accelerator']!='GPU'):raise ValueError('Prefix timing or accelerator changed')
        answer=response['response']
        if prediction['pipeline_ms']!=answer.get('latency_ms'):raise ValueError('Prefix pipeline timing changed')
        if response['status']!=200:
            errors+=1
            if (answer.get('error') not in {'Сегментатор не нашёл бутылку.','Сегментатор вернул пустую маску бутылки.',
                 'Сегментация не нашла объект.'} or prediction['error']!=answer['error'] or
                prediction['candidates'] or prediction['predicted_slug'] is not None):
                raise ValueError('Unexpected saved inference failure')
            continue
        if (answer['image_sha256']!=query['image_sha256'] or answer['encoder_accelerator']!='GPU' or
            answer['segmenter_accelerator']!=condition.get('segmenter','CPU') or answer['dimension']!=768 or
            answer['pack_version']!=metadata['pack_version'] or answer['reranking'] is not False or
            answer['barcode'] is not False or answer['offline'] is not True or answer['encoder_passes']!=1 or
            len(answer['variants'])!=1):raise ValueError('Saved inference contract changed')
        result=answer['variants'][0]
        if (result['variant']!=condition['number'] or result['budget']!=condition['budget'] or
            result['pooling']!=condition['pooling'] or result['timing_mode']!='independent' or
            result['candidates']!=prediction['candidates'] or result['slug']!=prediction['predicted_slug'] or
            prediction['error'] is not None or not result['candidates'] or
            any(c['slug'] not in slugs or not math.isfinite(c['score']) for c in result['candidates'])):
            raise ValueError('Saved candidates or condition changed')
        if condition.get('segmenter_model')=='DIS' and answer['segmentation'].get('model')!='DIS':
            raise ValueError('Saved segmenter changed')
        if condition.get('query_frame')=='full-image':
            trace=answer['encoders'][0]
            if (answer.get('query_frame')!='full-image' or result['reference_policy']!=condition['reference_policy'] or
                trace['frame_width']!=trace['source_width'] or trace['frame_height']!=trace['source_height']):
                raise ValueError('Saved full-image frame changed')
    if errors!=original['errors']:raise ValueError('Saved error count changed')
    _,received=lines(source/'received-responses.jsonl')
    measured=[r for r in received if not r['warmup']]
    if [{k:v for k,v in r.items() if k!='warmup'} for r in measured]!=responses:
        raise ValueError('Received but unsaved or changed response needs explicit reconciliation')
    _,samples=lines(source/'telemetry.jsonl')
    if any('error' in s or s['thermal_status']>=4 for s in samples):raise ValueError('Unsafe or unknown saved telemetry')
    shutil.copytree(source,destination/'inherited-attempt')
    for name,raw in (('responses.jsonl',response_bytes),('predictions.jsonl',prediction_bytes)):
        with (destination/name).open('xb') as stream:stream.write(raw)
    record=dict(source=str(source),records=expected_records,next_assignment=expected_records+1,
        source_inventory=before,original_run=original,prefix_byte_identical=True,
        stability_caveat='USB interruption; resumed cohort is not an uninterrupted stability pass.')
    if before!=inventory(source):raise ValueError('Raw source changed during recovery')
    return record,responses,samples
