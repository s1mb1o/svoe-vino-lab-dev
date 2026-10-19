"""Validate all320 canonical API routes and complete continuation sets."""
from pathlib import Path
import hashlib
import json
import jsonschema
from fastapi.testclient import TestClient
from dinner_lens.api import create_app
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.paths import default_dataset,default_style,default_index,bundle_root
from pairing_contract import expected


def run():
    root=bundle_root();path=default_dataset();d=json.loads(path.read_bytes())
    jsonschema.Draft202012Validator(json.loads((root/'data/pairing-dataset.v4.schema.json').read_bytes())).validate(d)
    old=json.loads((root/'data/pairing-dataset.v3.json').read_bytes());oldnodes={n['id']:n for n in old['nodes']}
    for key in ['wines','catalog_snapshot','root_class_ids','disambiguation_rules','embedding_documents']:assert d[key]==old[key],key
    for a,b in zip(d['profiles'],old['profiles']):
        assert a['id']==b['id']
        for key in set(a)|set(b):
            if a['id']=='spicy_meat' and key=='curation_pool':continue
            if a['id']=='spicy' and key=='match_rationale_ru':continue
            assert a.get(key)==b.get(key),(a['id'],key)
    assert len(d['nodes'])==320 and sum(n['kind']=='dish' for n in d['nodes'])==200
    k=Knowledge(path,default_style());e=Engine(k,EmbeddingIndex(k,default_index()),cursor_secret=b'v4-contract-validation-secret-at-least-32-bytes');token='v4-contract-validation-token-at-least-24-characters';results=[]
    with TestClient(create_app(e,None,api_token=token)) as client:
        client.headers['Authorization']='Bearer '+token
        for n in d['nodes']:
            for key in ['label_ru','parent_id','hierarchy_path','aliases','kind']:assert n[key]==oldnodes[n['id']][key]
            assert 1<=len(n['curated'])<=5
            profile,wanted=expected(d,n['id'],{})
            r=client.post('/v1/recommendations',json={'confirmed_dish':n['label_ru']});assert r.status_code==200;r=r.json();first=r;actual=[];stages=[];pages=0
            while True:
                pages+=1;assert pages<100 and r['resolved_node_id']==n['id'] and r['effective_profile_id']==profile
                actual.extend(r['wine_slugs']);stages.extend(x['selection_source'] for x in r['results'])
                if not r['next_cursor']:break
                r=client.post('/v1/recommendations/more',json={'cursor':r['next_cursor']});assert r.status_code==200;r=r.json()
            assert set(actual)==wanted and len(actual)==len(set(actual))==first['total_eligible'] and len(actual)>=1,n['id']
            assert len(first['results'])==len({x['producer'] for x in first['results']})
            if 'embedding' in stages:assert 'curated' not in stages[stages.index('embedding'):]
            results.append({'node_id':n['id'],'pages':pages,'wine_count':len(actual),'passed':True})
    value={'passed':True,'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'canonical_cases':320,'pages':sum(r['pages'] for r in results),'source_facts_taxonomy_queries_preserved':True,'quality_is_independent_tasting_evidence':False,'results':results}
    (root/'data/pairing-dataset.v4.validation.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in value.items() if k!='results'}))

if __name__=='__main__':run()
