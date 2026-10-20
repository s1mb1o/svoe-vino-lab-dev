"""Run independent pooling and reference aggregation from frozen vectors."""
import fcntl
import os
for name in ('VECLIB_MAXIMUM_THREADS','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS'):os.environ[name]='4'
import time
import numpy as np
from settings import *
from scoring import Scorer,aggregate,controls,recipe,key_of
from work_order import load,sort_trials

def jobs():
    result=[]
    for rp in POOLS:
        for qp in ['6b']+[p for p in POOLS if p!='6b']:
            for q in QUERIES:
                trials=[]
                for g in GALLERIES:
                    for add in (False,True):
                        for agg in (('max','top2-mean','top3-mean') if rp==qp else ('max',)):
                            trials.append(dict(gallery=g,axial=add,aggregation=agg,recipe=recipe(rp,qp,q,g,add,agg),family='7' if agg!='max' else '1'))
                result.append(dict(id='cached/'+rp+'/'+qp+'/'+q,kind='cached',rp=rp,qp=qp,q=q,stages=[],trials=trials))
    return result

def run_job(job,scorer,ranks=None):
    trials=[row for row in job['trials'] if not scorer.done(row['recipe'])]
    if not trials:return
    rp,qp,q=job['rp'],job['qp'],job['q'];meta=read(HERE/'cache/reference-meta.json')
    owners=np.asarray(meta['owners'],np.int32);angles=np.asarray(meta['angles'])
    axial_rows=read(AX/'axial-rows.json');lookup={slug:i for i,slug in enumerate(scorer.slugs)}
    axial_owners=np.asarray([lookup[r['wine_slug']] for r in axial_rows],np.int32)
    matrix=np.load(HERE/'cache'/('reference-'+rp+'.npy'),allow_pickle=False)
    axial=np.load(AX/'axial-vectors.npy' if rp=='u' else AXM/'reference-vectors'/(rp+'.npy'),allow_pickle=False)
    query=np.load(HERE/'cache'/('query-'+qp+'-'+q+'.npy'),allow_pickle=False)
    query=query[getattr(scorer,'query_indices',slice(None))]
    n=len(scorer.ids);w=len(scorer.slugs)
    arrays={(row['gallery'],row['axial'],row['aggregation']):np.full((n,w),-np.inf,np.float32) for row in trials}
    masks={g:np.isin(angles,a) for g,a in GALLERIES.items()}
    for start in range(0,n,48):
        batch=query[start:start+48];raw=matrix@batch.T;extra=axial@batch.T
        for row in trials:
            g,add,agg=row['gallery'],row['axial'],row['aggregation'];mask=masks[g]
            values=np.concatenate([raw[mask],extra]) if add else raw[mask]
            own=np.r_[owners[mask],axial_owners] if add else owners[mask]
            value=aggregate(values,own,w,{'max':1,'top2-mean':2,'top3-mean':3}[agg])
            value[np.linalg.norm(batch,axis=1)==0]=-np.inf
            arrays[g,add,agg][start:start+len(batch)]=value
        if start%480==0:dump(HERE/'cached-progress.json',dict(at=now(),cohort=getattr(scorer,'scope','all'),reference_pool=rp,query_pool=qp,query=q,images=start,total_images=n))
    for row in sort_trials(trials,ranks,key_of):
        g,add,agg=row['gallery'],row['axial'],row['aggregation'];merged=arrays[g,add,agg]
        # Preserve imported controls exactly. The remote scorer skips these controls.
        if rp==qp and agg=='max':
            for cohort,folder in reversed(list(FOLDERS.items())):
                source=(AXM/cohort if add else ROOT/folder)/'components'/(f'b-{rp}-{q}-{g}'+('+axial' if add else '')+'.npy')
                merged[scorer.indices[cohort]]=np.load(source,allow_pickle=False)
        scorer.record(row['recipe'],row['family'],merged)

def main():
    lock=(HERE/'cached.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    controls();scorer=Scorer()
    if getattr(scorer,'scope',None)=='all':
        load(scorer)
        dump(HERE/'cached-complete.json',dict(at=now(),complete=True,state='The ordered native worker scores cached and native my jobs',families=[1,7],delegated=True));return
    began=time.monotonic()
    for job in jobs():run_job(job,scorer)
    dump(HERE/'cached-complete.json',dict(at=now(),complete=True,seconds=time.monotonic()-began,families=[1,7]))

if __name__=='__main__':main()
