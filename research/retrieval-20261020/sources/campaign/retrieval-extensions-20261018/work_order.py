"""Order shared computations by the best completed failure-cohort variant."""
import time
from settings import *

def load(scorer):
    if getattr(scorer,'scope',None)!='all':return None
    while True:
        path=HERE/'my-work-order.json'
        if path.exists():
            value=read(path)
            expected=read(HERE/'enumeration.json')
            assert value['complete'] and value['source_cohort']=='my-failed-2'
            assert value['metric_rows']==expected['variants_per_cohort']
            assert set(value['bottle_order'])==set(expected['bottles'])
            assert len(value['bottle_order'])==len(expected['bottles'])
            return {key:i for i,key in enumerate(value['bottle_order'])}
        dump(HERE/'my-order-status.json',dict(at=now(),state='Wait for complete my-failed-2 scheduling order'))
        time.sleep(5)

def sort_jobs(jobs,ranks,key_of):
    if ranks is None:return jobs
    return sorted(jobs,key=lambda job:(min(ranks[key_of(row['recipe'])] for row in job['trials']),job['id']))

def sort_trials(trials,ranks,key_of):
    return trials if ranks is None else sorted(trials,key=lambda row:ranks[key_of(row['recipe'])])
