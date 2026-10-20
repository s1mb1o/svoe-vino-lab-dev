"""Enumerate every required condition before new scoring."""
import itertools
from settings import *
from scoring import recipe,key_of

def main():
    items={}
    def add(r,family):
        key=key_of(r)
        if key in items:
            assert items[key]['recipe']==r
            if str(family) not in items[key]['families']:items[key]['families'].append(str(family))
        else:items[key]=dict(recipe=r,families=[str(family)])
    for rp,qp,q,g,ax in itertools.product(POOLS,POOLS,QUERIES,GALLERIES,(False,True)):add(recipe(rp,qp,q,g,ax),1)
    for p,q,g,ax,k in itertools.product(POOLS,QUERIES,GALLERIES,(False,True),(2,3)):add(recipe(p,p,q,g,ax,'top'+str(k)+'-mean'),7)
    for p,definition in profiles().items():
        for q,g,ax in itertools.product(QUERIES,GALLERIES,(False,True)):
            r=recipe(p,p,q,g,ax)
            if definition.get('coverage')=='exact':family=4
            elif definition.get('gamma',1)!=1:family=2
            else:family=3
            add(r,family)
    for p,rm,qm,q,g in itertools.product(('u','6b'),(0.,.02,.05,.1),(0.,.02,.05,.1),QUERIES,GALLERIES):
        r=recipe(p,p,q,g);r.update(reference_margin=rm,query_margin=qm);add(r,4)
    for p,rb,qb,q,g,ax in itertools.product(('u','6b'),(256,512,1024),(256,512,1024),QUERIES,GALLERIES,(False,True)):
        r=recipe(p,p,q,g,ax);r.update(reference_budget=rb,query_budget=qb);add(r,6)
    for p,q,g in itertools.product(POOLS,QUERIES,('cartesian','rot5-plus-cartesian')):add(recipe(p,p,q,g,True),5)
    value=dict(at=now(),bottles=items,bottle_conditions=len(items),variants_per_cohort=len(items)*11,cohorts=list(FOLDERS),fusion_anchors=10)
    if (HERE/'enumeration.json').exists():
        old=read(HERE/'enumeration.json');value['at']=old['at'];assert old==value
    else:dump(HERE/'enumeration.json',value)
    print('Enumerated',len(items),'bottle conditions and',len(items)*11,'variants per cohort',flush=True)

if __name__=='__main__':main()
