"""Score every native extension stage against both frozen cohorts."""
import fcntl
import os
from contextlib import nullcontext
for name in ('VECLIB_MAXIMUM_THREADS','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS'):os.environ[name]='4'
import itertools
import time
import numpy as np
from settings import *
from scoring import Scorer,aggregate,recipe,key_of
from work_order import load,sort_jobs,sort_trials

def ready(stage):
    priority=(HERE/'active-cohort.json').exists() and read(HERE/'active-cohort.json')['cohort']=='my-failed-2'
    marker='priority-complete.json' if priority and stage.endswith('-query') else 'verified.json'
    return (HERE/'native'/stage/marker).exists()

class Inputs:
    def __init__(self,scorer):
        self.scorer=scorer;self.manifest=read(HERE/'native-inputs.json');self.owner=read(HERE/'reference-owners.json')
        self.axial_owner={}
        lookup={slug:i for i,slug in enumerate(scorer.slugs)}
        for row in read(AX/'axial-rows.json'):self.axial_owner.setdefault(row['source_sha256'],set()).add(lookup[row['wine_slug']])
        self.meta=read(HERE/'cache/reference-meta.json');self.mapping={}
    def query(self,stage,pool,q):
        path=HERE/'native'/stage
        row_of={r['id']:i for i,r in enumerate(read(path/'rows.json'))}
        vectors=np.load(path/(pool+'.npy'),mmap_mode='r',allow_pickle=False)
        def load(geometry):
            result=np.zeros((len(self.scorer.ids),1152),np.float32)
            for i,image in enumerate(self.scorer.ids):
                key=self.manifest['lookup'][image].get(geometry)
                if key:result[i]=vectors[row_of[key]]
            return result
        if q in ('mean-iou','mean-card5'):
            result=load('original')+load('iou' if q=='mean-iou' else 'card5')
            norm=np.linalg.norm(result,axis=1,keepdims=True);result/=np.where(norm>0,norm,1)
            return result
        return load(q)
    def reference(self,stage,pool,axial=False):
        directory=HERE/'native'/stage
        if stage not in self.mapping:
            rows=read(directory/'rows.json');indices=[];owners=[];angles=[]
            for i,row in enumerate(rows):
                for owner in sorted((self.axial_owner if axial else self.owner)[row['id']]):
                    indices.append(i);owners.append(owner);angles.append(row['in_plane_angle'])
            self.mapping[stage]=(np.asarray(indices),np.asarray(owners),np.asarray(angles))
        indices,owners,angles=self.mapping[stage]
        base=np.load(directory/(pool+'.npy'),allow_pickle=False)
        return base,indices,owners,angles
    def cached_reference(self,pool,axial=False):
        if axial:
            rows=read(AX/'axial-rows.json');lookup={s:i for i,s in enumerate(self.scorer.slugs)}
            values=np.load(AX/'axial-vectors.npy' if pool=='u' else AXM/'reference-vectors'/(pool+'.npy'),allow_pickle=False)
            return values,np.arange(len(rows)),np.asarray([lookup[r['wine_slug']] for r in rows]),np.zeros(len(rows),np.int32)
        values=np.load(HERE/'cache'/('reference-'+pool+'.npy'),allow_pickle=False)
        return values,np.arange(len(values)),np.asarray(self.meta['owners']),np.asarray(self.meta['angles'])

def compute(inputs,query,reference,axial=None,cartesian=None):
    matrix,indices,owners,angles=reference
    n=len(query);w=len(inputs.scorer.slugs)
    galleries=['cartesian','rot5-plus-cartesian'] if cartesian else list(GALLERIES)
    outputs={(g,ax):np.full((n,w),-np.inf,np.float32) for g in galleries for ax in ((True,) if cartesian else ((False,True) if axial else (False,)))}
    for start in range(0,n,48):
        batch=query[start:start+48];raw=matrix@batch.T
        extra=None
        if axial:
            values,picked,own,_=axial;extra=values@batch.T;extra=aggregate(extra[picked],own,w)
        cart=None
        if cartesian:
            values,picked,own,_=cartesian;cart=aggregate((values@batch.T)[picked],own,w)
        for gallery in galleries:
            mask=np.isin(angles,GALLERIES['cardinal' if gallery=='cartesian' else 'rot5' if gallery=='rot5-plus-cartesian' else gallery])
            reduced=aggregate(raw[indices[mask]],owners[mask],w)
            reduced[np.linalg.norm(batch,axis=1)==0]=-np.inf
            for add in ((True,) if cartesian else ((False,True) if axial else (False,))):
                value=np.maximum(reduced,extra) if add and extra is not None else reduced
                if cart is not None:value=np.maximum(value,cart)
                value[np.linalg.norm(batch,axis=1)==0]=-np.inf
                outputs[gallery,add][start:start+len(batch)]=value
    return outputs

def jobs(expected):
    result=[]
    for pool in profiles():
        for q in QUERIES:
            trials=[]
            for g,ax in itertools.product(GALLERIES,(False,True)):
                r=recipe(pool,pool,q,g,ax)
                trials.append(dict(gallery=g,axial=ax,recipe=r,family=expected[key_of(r)]['families'][0]))
            result.append(dict(id='profile/'+pool+'/'+q,kind='profile',pool=pool,q=q,stages=['p512-query','p512-reference','p512-axial'],trials=trials))
    for rm,rcode in ((0.,'000'),(.02,'002'),(.05,'005'),(.1,'010')):
        for qm,qcode in ((0.,'000'),(.02,'002'),(.05,'005'),(.1,'010')):
            for pool,q in itertools.product(('u','6b'),QUERIES):
                trials=[]
                for g in GALLERIES:
                    r=recipe(pool,pool,q,g);r.update(reference_margin=rm,query_margin=qm)
                    trials.append(dict(gallery=g,axial=False,recipe=r,family=4))
                result.append(dict(id='margin/'+rcode+'/'+qcode+'/'+pool+'/'+q,kind='margin',pool=pool,q=q,stages=['margin-'+rcode+'-reference','margin-'+qcode+'-query'],trials=trials))
    for rb,qb,pool in itertools.product((256,512,1024),(256,512,1024),('u','6b')):
        if rb==qb==512:continue
        for q in QUERIES:
            trials=[]
            for g,ax in itertools.product(GALLERIES,(False,True)):
                r=recipe(pool,pool,q,g,ax);r.update(reference_budget=rb,query_budget=qb)
                trials.append(dict(gallery=g,axial=ax,recipe=r,family=6))
            result.append(dict(id='budget/'+str(rb)+'/'+str(qb)+'/'+pool+'/'+q,kind='budget',pool=pool,q=q,rb=rb,qb=qb,
                               stages=['p'+str(rb)+'-reference','p'+str(rb)+'-axial','p'+str(qb)+'-query'],trials=trials))
    for pool,q in itertools.product(POOLS,QUERIES):
        trials=[dict(gallery=g,axial=True,recipe=recipe(pool,pool,q,g,True),family=5) for g in ('cartesian','rot5-plus-cartesian')]
        result.append(dict(id='cartesian/'+pool+'/'+q,kind='cartesian',pool=pool,q=q,stages=['cartesian'],trials=trials))
    return result

def job_ready(job):
    stages=job['stages']
    if job['kind']=='budget':stages=[s for s in stages if not s.startswith('p512-')]
    return all(ready(s) for s in stages)

def run_job(job,inputs,ranks=None):
    scorer=inputs.scorer
    trials=[row for row in job['trials'] if not scorer.done(row['recipe'])]
    if not trials:return
    q=job['q'];pool=job['pool'];kind=job['kind']
    if kind=='profile':
        query=inputs.query('p512-query',pool,q)
        values=compute(inputs,query,inputs.reference('p512-reference',pool),inputs.reference('p512-axial',pool,True))
    elif kind=='margin':
        rs,qs=job['stages'];p=ALIASES[pool]
        values=compute(inputs,inputs.query(qs,p,q),inputs.reference(rs,p))
    elif kind=='budget':
        rb,qb=job['rb'],job['qb'];rs,axs,qs=job['stages'];p=ALIASES[pool]
        reference=inputs.cached_reference(pool) if rb==512 else inputs.reference(rs,p)
        extra=inputs.cached_reference(pool,True) if rb==512 else inputs.reference(axs,p,True)
        query=np.load(HERE/'cache'/('query-'+pool+'-'+q+'.npy'),allow_pickle=False) if qb==512 else inputs.query(qs,p,q)
        if qb==512:query=query[getattr(scorer,'query_indices',slice(None))]
        values=compute(inputs,query,reference,extra)
    else:
        query=np.load(HERE/'cache'/('query-'+pool+'-'+q+'.npy'),allow_pickle=False)
        query=query[getattr(scorer,'query_indices',slice(None))]
        values=compute(inputs,query,inputs.cached_reference(pool),inputs.cached_reference(pool,True),inputs.reference('cartesian',ALIASES[pool],True))
    for row in sort_trials(trials,ranks,key_of):scorer.record(row['recipe'],row['family'],values[row['gallery'],row['axial']])

def main():
    lock=(HERE/'native-score.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    scorer=Scorer();inputs=Inputs(scorer);expected=read(HERE/'enumeration.json')['bottles'];ranks=load(scorer)
    work=jobs(expected)
    if ranks is not None:
        import cached
        work+=cached.jobs()
    while True:
        pending_jobs=[]
        for job in work:
            pending_trials=[row for row in job['trials'] if not scorer.done(row['recipe'])]
            if pending_trials:pending_jobs.append(dict(job,trials=pending_trials))
        pending_jobs=sort_jobs(pending_jobs,ranks,key_of);progress=False
        for job in pending_jobs:
            if not job_ready(job):
                if ranks is not None:break
                continue
            dump(HERE/'native-score-status.json',dict(at=now(),cohort=getattr(scorer,'scope','all'),state='Score next shared computation',job=job['id'],best_bottle_rank=min(ranks[key_of(r['recipe'])] for r in job['trials'])+1 if ranks is not None else None))
            if job['kind']=='cached':cached.run_job(job,scorer,ranks)
            else:run_job(job,inputs,ranks)
            progress=True
        pending=sum(not scorer.done(row['recipe']) for row in expected.values())
        dump(HERE/'native-score-status.json',dict(at=now(),cohort=getattr(scorer,'scope','all'),state='Score available native stages' if progress else 'Wait for native stages',pending_bottle_conditions=pending,order='my-failed-2 Top-1, Top-5, Top-10, MRR' if ranks is not None else 'declared'))
        if not pending:
            dump(HERE/'scoring-complete.json',dict(at=now(),bottle_conditions=len(expected),variants_per_cohort=len(expected)*11));return
        if not progress:time.sleep(20)

if __name__=='__main__':main()
