"""Finalize only a recovery copy. Preserve every raw interrupted-run byte."""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

_frozen_tools=str(Path(__file__).resolve().parents[1]/'offline_benchmark')
sys.path.insert(0,_frozen_tools)
from audit_device_run import audit
from resume_run import restore_prefix
sys.path.remove(_frozen_tools)


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inventory(directory):
    result={}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():raise ValueError('Do not recover a run with symbolic links')
        if path.is_file():result[str(path.relative_to(directory))]=dict(bytes=path.stat().st_size,sha256=sha(path))
    return result


def finalize_metadata(original,telemetry,recorded_at,source,source_sha):
    if original.get('mode')!='full' or original.get('complete') or original.get('finished_at'):
        raise ValueError('Require an abruptly interrupted, incomplete full run')
    if original.get('reranking') is not False or original.get('barcode') is not False:
        raise ValueError('Optional recognition must remain disabled')
    values={}
    for field,key in (('maximum_thermal_status','thermal_status'),('peak_sampled_pss_kib','pss_kib'),
                      ('maximum_battery_celsius','battery_celsius')):
        samples=[r[key] for r in telemetry if r.get(key) is not None]
        if not samples:raise ValueError('No saved telemetry for '+key)
        values[field]=max(samples)
    result=copy.deepcopy(original)
    result.update(values,finished_at=recorded_at,
        failure='Host workers absent at recovery. Original termination time and cause are unknown.',
        interrupted_run_recovery=dict(source=str(source),source_run_sha256=source_sha,
            metadata_finalized_at=recorded_at,actual_worker_exit_at=None,
            finished_at_basis='Recovery metadata finalization time; not the original worker exit time.',
            telemetry_basis='Saved telemetry from the interrupted process segment; no inferred samples.'))
    return result


def recover(source,destination,queries,expected_records):
    source=source.resolve();destination=destination.resolve()
    if destination==source or source in destination.parents or destination.exists():
        raise ValueError('Require a new sibling recovery directory')
    before=inventory(source);original=json.loads((source/'run.json').read_text())
    if original['requests']!=expected_records:raise ValueError('Unexpected saved assignment count')
    names=['responses.jsonl']+[f'variant-{v:02d}/predictions.jsonl' for v in range(1,11)]
    for name in names:
        raw=(source/name).read_bytes()
        if len(raw.splitlines())!=expected_records or not raw.endswith(b'\n'):
            raise ValueError('Incomplete saved prefix: '+name)
    telemetry=[json.loads(line) for line in (source/'telemetry.jsonl').read_text().splitlines()]
    recorded_at=dt.datetime.now(dt.timezone.utc).isoformat()
    metadata=finalize_metadata(original,telemetry,recorded_at,source,sha(source/'run.json'))
    shutil.copytree(source,destination)
    (destination/'raw-interrupted-run.json').write_bytes((source/'run.json').read_bytes())
    (destination/'run.json').write_text(json.dumps(metadata,indent=2)+'\n')
    result=audit(destination,queries)
    if not result['verification_passed'] or result['complete']:raise RuntimeError('Recovery prefix audit failed')
    (destination/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    # Exercise the frozen continuation logic without a device request.
    with tempfile.TemporaryDirectory(prefix='chtozavino-resume-audit-') as temporary:
        candidate=copy.deepcopy(metadata)
        restored=restore_prefix(destination,Path(temporary),queries,candidate)
        if restored!=expected_records:raise RuntimeError('Dry resume did not restore the complete prefix')
        for name in names:
            if (Path(temporary)/name).read_bytes()!=(source/name).read_bytes():
                raise RuntimeError('Dry resume changed prediction bytes')
    after=inventory(source)
    if before!=after:raise RuntimeError('Raw interrupted run changed during recovery')
    record=dict(passed=True,recorded_at=recorded_at,source=str(source),recovery=str(destination),
        assignments=expected_records,next_assignment=expected_records+1,source_inventory=before,
        source_preserved=True,predictions_byte_identical=True,independent_audit_passed=True,
        dry_resume_passed=True,reranking=False,barcode=False)
    (destination/'recovery-record.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','out','queries'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-records',type=int,required=True);a=p.parse_args()
    result=recover(a.source,a.out,json.loads(a.queries.read_text()),a.expected_records)
    print(json.dumps({k:v for k,v in result.items() if k!='source_inventory'}))


if __name__=='__main__':main()
