"""Capture every authenticated API page with explicit context and source provenance."""
import argparse
import hashlib
import json
from pathlib import Path
from fastapi.testclient import TestClient
from dinner_lens.api import create_app
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.paths import default_dataset,default_style,default_index,bundle_root


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cases_path,output):
    data=json.loads(default_dataset().read_bytes());codes={w['wine_slug']:w['id'] for w in data['wines']}
    source_hashes={p.name:sha(p) for p in (bundle_root()/'src/dinner_lens').glob('*.py')}
    k=Knowledge(default_dataset(),default_style());e=Engine(k,EmbeddingIndex(k,default_index()),cursor_secret=b'full-sauce-capture-only-secret-at-least-32-bytes')
    token='full-sauce-capture-only-token-at-least-24-characters';cases=json.loads(cases_path.read_bytes())['cases'];results=[]
    with TestClient(create_app(e,None,api_token=token)) as client:
        client.headers['Authorization']='Bearer '+token
        for index,case in enumerate(cases):
            r=client.post('/v1/recommendations',json={'node_id':case['node_id'],'confirmed_attributes':case['confirmed_attributes'],'user_constraints':case.get('user_constraints',{}),'limit':3});assert r.status_code==200
            first=page=r.json();entries=[];checks=[];page_number=0
            while True:
                page_number+=1;assert page_number<100
                checks.append({'page':page_number,'node_unchanged':page['resolved_node_id']==case['node_id'],
                    'profile_unchanged':page['effective_profile_id']==first['effective_profile_id'],
                    'confirmed_attributes_unchanged':page['confirmed_attributes']==case['confirmed_attributes']})
                for row in page['results']:
                    entries.append({'position':len(entries)+1,'page':page_number,'code':codes[row['wine_slug']],
                        **{key:row[key] for key in ['wine_slug','name','producer','selection_source','reason','facts','source_url','ranking_evidence']}})
                if not page['next_cursor']:break
                r=client.post('/v1/recommendations/more',json={'cursor':page['next_cursor']});assert r.status_code==200;page=r.json()
            slugs=[x['wine_slug'] for x in entries];stages=[x['selection_source'] for x in entries]
            functional={'every_page_context_preserved':all(all(v for key,v in c.items() if key!='page') for c in checks),
                'unique_wines':len(slugs)==len(set(slugs)),'complete_count':len(slugs)==first['total_eligible'],
                'curated_before_embedding':'embedding' not in stages or 'curated' not in stages[stages.index('embedding'):],
                'first_page_producer_diversity':len(first['results'])==len({r['producer'] for r in first['results']})}
            results.append({'case':case,'label_ru':k.nodes[case['node_id']]['label_ru'],'effective_profile_id':first['effective_profile_id'],
                'applied_modifier_ids':first['applied_modifier_ids'],'page_count':page_number,'wine_count':len(entries),
                'functional_checks':functional,'page_checks':checks,'entries':entries})
            if (index+1)%200==0:print(json.dumps({'captured_cases':index+1,'total':len(cases)}),flush=True)
    assert source_hashes=={p.name:sha(p) for p in (bundle_root()/'src/dinner_lens').glob('*.py')},'Production source changed during capture'
    assert k.sha256==sha(default_dataset()),'Dataset changed during capture'
    value={'mode':'authenticated ASGI HTTP; confirmed dishes/sauces; every continuation page',
        'cases_sha256':sha(cases_path),'dataset_sha256':k.sha256,'capture_script_sha256':sha(Path(__file__)),
        'source_sha256':source_hashes,
        'case_count':len(results),'wine_recommendations':sum(c['wine_count'] for c in results),
        'pages':sum(c['page_count'] for c in results),'functional_pass':all(all(c['functional_checks'].values()) for c in results),'cases':results}
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps({key:value[key] for key in ['case_count','wine_recommendations','pages','functional_pass']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.cases,a.output)
