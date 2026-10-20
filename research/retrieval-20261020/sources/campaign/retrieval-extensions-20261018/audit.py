"""Check enumeration coverage and independently recompute saved case metrics."""
import sqlite3
import argparse
import numpy as np
from settings import *
from scoring import known_control

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cohort',choices=['my-failed-2']);args=parser.parse_args()
    priority=args.cohort is not None
    definitions=read(HERE/'enumeration.json')['bottles']
    photos=read(HERE/'photo-paths.json');assert set(photos)==set(read(HERE/'context.json')['ids'])
    for image,url in photos.items():
        path=(HERE/url).resolve();assert path.is_relative_to(ROOT) and path.is_file()
        if path.parent.name=='query-sources':assert sha(path)==image
    stages=read(HERE/'gpu-queue.json')['stages']
    gpu_marker='gpu-priority-complete.json' if priority else 'gpu-complete.json'
    assert len(stages)==read(HERE/gpu_marker)['stages']==18
    assert read(HERE/gpu_marker)['passed'] and read(HERE/'native-pilots.json')['passed']
    worker_hash=sha(HERE/'native_worker.py');input_hash=sha(HERE/'native-inputs.json')
    recovery=read(HERE/'attention-mask-recovery.json') if (HERE/'attention-mask-recovery.json').exists() else {}
    if recovery:
        assert recovery['passed'] and recovery['original_worker_sha256']==worker_hash
        assert recovery['worker_sha256']==sha(HERE/'native_worker_explicit_mask.py')
        assert set(recovery['stages'])=={'p'+str(b)+'-'+k for b in (256,1024) for k in ('query','reference','axial')}
        assert recovery['frozen_p512_control_passed']
    cloud_plan=read(HERE/'rtx4090-20261019/stage-plan.json') if (HERE/'rtx4090-20261019/stage-plan.json').exists() else {}
    cloud_stages=cloud_plan.get('stages',[]) if cloud_plan.get('admitted') else []
    if cloud_stages:
        admission=read(HERE/'rtx4090-20261019/admission.json')
        assert admission['passed'] and cloud_plan['parity_passed']
    for stage in stages:
        root=HERE/'native'/stage
        partial=priority and stage.endswith('-query')
        complete=read(root/('priority-complete.json' if partial else 'complete.json'));pilot=read(root/'pilot.json');verified=read(root/('priority-verified.json' if partial else 'verified.json'))
        assert complete['passed'] and pilot['passed'] and verified['passed']
        assert verified['independent_remote_sha256_check'] and verified['rows']==complete['rows']
        assert verified['files']==len(complete['files'])==len(complete['recipe']['pools'])
        for record in (complete,pilot):
            expected_worker=recovery['worker_sha256'] if stage in recovery.get('stages',[]) else worker_hash
            assert record['recipe']['worker_sha256']==expected_worker and record['recipe']['input_sha256']==input_hash
            assert record['uniform_delta']<=2e-5
        assert pilot['batch_equivalence_max_delta']<2e-5
        assert set(complete['files'])=={pool+'.npy' for pool in complete['recipe']['pools']}
        if partial:assert complete['completed_sources']==read(HERE/'native-inputs.json')['priority_query_sources']
        if stage in cloud_stages:
            imported=read(HERE/'rtx4090-20261019/imported'/(stage+'.json'))
            assert imported['passed'] and imported['independent_GX10_sha256'] and imported['cross_device_parity_passed']
            if not priority and stage.endswith('-query'):assert verified['priority_prefix_preserved']
    conn=sqlite3.connect('file:'+str(HERE/'metrics.sqlite3')+'?mode=ro',uri=True);conn.row_factory=sqlite3.Row
    cohorts={};checked=0;controls=0
    for cohort,folder in FOLDERS.items():
        if priority and cohort!=args.cohort:continue
        ctx=read(ROOT/folder/'context.json');lookup={s:i for i,s in enumerate(ctx['slugs'])};images={s:i for i,s in enumerate(ctx['ids'])}
        rows=ctx['assignments'];positive=np.asarray([r.get('label','positive')=='positive' for r in rows]);assignment=np.asarray([images[r['image']] for r in rows])
        negative=np.asarray([r.get('label','positive')=='negative' for r in rows]);nomatch=np.asarray([r.get('label','positive')=='no_match' for r in rows])
        rejected=np.asarray([lookup.get(r['slug'],-2) for r in rows]);baseline=np.asarray(read(ROOT/folder/'singles/b-u-original-rot5.json')['ranks'])[positive]
        accepted=np.zeros((len(rows),len(lookup)),bool)
        for i,row in enumerate(rows):
            for slug in row['truth']:
                if slug in lookup:accepted[i,lookup[slug]]=True
        groups={}
        for row in rows:
            if row.get('label','positive')=='positive':groups.setdefault(row['image'],set()).update(row['truth'])
        im_ids=[images[s] for s in groups];im_truth=np.zeros((len(im_ids),len(lookup)),bool)
        for i,truth in enumerate(groups.values()):
            for slug in truth:
                if slug in lookup:im_truth[i,lookup[slug]]=True
        old=sqlite3.connect('file:'+str(AXM/cohort/'combined.sqlite3')+'?mode=ro',uri=True);old.row_factory=sqlite3.Row
        observed={r[0] for r in conn.execute('SELECT DISTINCT bottle_id FROM metrics WHERE cohort=?',(cohort,))};assert observed==set(definitions)
        total=conn.execute('SELECT count(*) FROM metrics WHERE cohort=?',(cohort,)).fetchone()[0];assert total==len(definitions)*11
        for number,(bottle,definition) in enumerate(definitions.items(),1):
            recipe=definition['recipe'];known=known_control(recipe)
            with np.load(HERE/'tops'/(bottle+'.npz'),allow_pickle=False) as arrays:
                metrics=list(conn.execute('SELECT * FROM metrics WHERE cohort=? AND bottle_id=?',(cohort,bottle)));assert len(metrics)==11
                for row in metrics:
                    top=arrays[cohort+'__'+row['variant_id']];assert top.shape==(len(ctx['ids']),10)
                    assert np.all((top>=-1)&(top<len(lookup)))
                    assert all(len(set(r[r>=0].tolist()))==int((r>=0).sum()) for r in top)
                    candidates=top[assignment];hit=accepted[np.arange(len(rows))[:,None],np.maximum(candidates,0)]&(candidates>=0)
                    rank=np.where(hit.any(1),hit.argmax(1)+1,11)[positive]
                    for k in (1,5,10):assert row['top'+str(k)]==int(np.count_nonzero(rank<=k)),(cohort,row['variant_id'],k)
                    assert row['n']==int(positive.sum())
                    assert abs(row['mrr']-np.where(rank<=10,1/rank,0).mean())<1e-12
                    invalid=(candidates==rejected[:,None])&negative[:,None]
                    assert row['negative_false1']==int(invalid[:,0].sum())
                    assert row['negative_false10']==int(invalid.any(1).sum())
                    assert row['no_match_false1']==int((nomatch&(candidates[:,0]>=0)).sum())
                    assert row['no_answer']==int((candidates[:,0]<0).sum())
                    for k in (1,5,10):
                        assert row['fix'+str(k)]==int(((baseline>k)&(rank<=k)).sum())
                        assert row['regression'+str(k)]==int(((baseline<=k)&(rank>k)).sum())
                    itop=top[im_ids];ihit=im_truth[np.arange(len(im_ids))[:,None],np.maximum(itop,0)]&(itop>=0)
                    irank=np.where(ihit.any(1),ihit.argmax(1)+1,11)
                    for k in (1,5,10):assert row['image_top'+str(k)]==int((irank<=k).sum())
                    assert row['image_n']==len(im_ids)
                    if known:
                        vid=known+'__'+row['label_id']+'__'+row['policy_id'] if row['label_id'] else 'single-'+known
                        expected=old.execute('SELECT * FROM metrics WHERE variant_id=?',(vid,)).fetchone();assert expected is not None,vid
                        for field in ('n','top1','top5','top10','negative_false1','negative_false10','no_match_false1','no_answer','image_n','image_top1','image_top5','image_top10'):
                            if expected[field] is not None:assert row[field]==expected[field],(cohort,vid,field,row[field],expected[field])
                        controls+=1
                    checked+=1
            if number%100==0:dump(HERE/'audit-progress.json',dict(at=now(),cohort=cohort,bottles=number,total_bottles=len(definitions),metric_rows_checked=checked))
        cohorts[cohort]=dict(variants=total,bottle_conditions=len(definitions),positive_assignments=int(positive.sum()),positive_images=len(im_ids))
    frozen=read(HERE/'protocol.json')
    for cohort,folder in FOLDERS.items():
        assert sha(ROOT/folder/'context.json')==frozen['cohorts'][cohort]['context_sha256']
        assert sha(ROOT/(folder+'/queries.json' if cohort=='my' else 'queries.json'))==frozen['cohorts'][cohort]['queries_sha256']
    for remote,value in read(HERE/'native-inputs.json')['input_hashes'].items():
        path=ROOT/remote.removeprefix(REMOTE_BASE+'/');assert path.stat().st_size==value['size'] and sha(path)==value['sha256']
    if (HERE/'input-repair.json').exists():
        for value in read(HERE/'input-repair.json')['files']:
            path=Path(value['source']);assert path.stat().st_mtime_ns==value['source_mtime_ns'] and sha(path)==value['sha256']
    result=dict(at=now(),passed=True,cohorts=cohorts,independent_metric_rows=checked,unchanged_historical_control_rows=controls,
                coverage_complete=True,saved_top10_checked=True,case_metric_counts_recomputed=True,source_image_hashes_preserved=True,
                frozen_cohorts_preserved=True,native_stages_verified=True,local_reranking=False)
    result['cohort_scope']=args.cohort if priority else 'all'
    dump(HERE/('priority-audit.json' if priority else 'audit.json'),result)
    dump(HERE/('priority-complete.json' if priority else 'complete.json'),result)

if __name__=='__main__':main()
