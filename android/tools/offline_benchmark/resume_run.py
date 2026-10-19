"""Copy an independently audited result prefix. Never edit its source run."""
import copy
import hashlib
import json
from pathlib import Path
import shutil



def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def restore_prefix(source,destination,queries,metadata):
    # Import here because the independent audit also verifies inherited prefixes.
    from audit_device_run import audit
    source=source.resolve();destination=destination.resolve()
    if source==destination:raise ValueError('Resume requires a new output directory')
    previous=json.loads((source/'run.json').read_text())
    if previous['mode']!='full' or previous['complete'] or not previous.get('finished_at'):
        raise ValueError('Resume requires an incomplete full-selector run')
    for field in ('serial','package','query_file_sha256','pack_manifest_sha256','pack_version',
                  'assignments','distinct_images','endpoint','reranking','barcode'):
        if previous[field]!=metadata[field]:raise ValueError(f'Resume identity mismatch: {field}')
    if previous.get('installed_apk_sha256') not in (None,metadata['installed_apk_sha256']):
        raise ValueError('Resume APK mismatch')
    if not audit(source,queries)['verification_passed']:raise ValueError('Source audit failed')
    count=previous['requests']
    if not 0<count<len(queries):raise ValueError('Invalid resume prefix length')
    files=['responses.jsonl']+[f'variant-{v:02d}/predictions.jsonl' for v in range(1,11)]
    prefix={}
    for name in files:
        path=source/name
        if len(path.read_bytes().splitlines())!=count:raise ValueError(f'Incomplete prefix: {name}')
        if not path.read_bytes().endswith(b'\n'):raise ValueError(f'Truncated prefix: {name}')
        prefix[name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    # Validate all files before copying any prediction.
    for name in files:
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source/name,target)
    shutil.copy2(source/'run.json',destination/'inherited-run.json')
    metadata.update(requests=count,errors=previous['errors'],hits=copy.deepcopy(previous['hits']),
        resume=dict(source_directory=str(source),records=count,source_run_sha256=sha(source/'run.json'),
                    prefix_files=prefix,source_elapsed_s=previous['elapsed_s']))
    metadata['process_segments']=copy.deepcopy(previous.get('process_segments',
        [dict(start_request=1,pid=previous['initial_pid'])]))
    # A prior continuation can stop before it receives its first new response.
    metadata['process_segments']=[s for s in metadata['process_segments'] if s['start_request']<=count]
    metadata['process_segments'].append(dict(start_request=count+1,pid=metadata['initial_pid']))
    return count
