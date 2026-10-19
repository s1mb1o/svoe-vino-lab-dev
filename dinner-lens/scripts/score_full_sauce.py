"""Validate complete source-rule sets, then score separately frozen blind opinions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from pairing_contract import expected


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(capture_path,dataset_path,cases_path,output,reference_path=None):
    capture=json.loads(capture_path.read_bytes());data=json.loads(dataset_path.read_bytes());truth=json.loads(cases_path.read_bytes());cases={c['id']:c for c in truth['cases']}
    wine_sources={w['wine_slug']:w for w in data['wines']}
    assert capture['dataset_sha256']==sha(dataset_path) and capture['cases_sha256']==sha(cases_path)
    assert len(capture['cases'])==len(cases) and len({c['case']['id'] for c in capture['cases']})==len(cases)
    assert {c['case']['id'] for c in capture['cases']}==set(cases)
    references={}
    if reference_path:
        ref=json.loads(reference_path.read_bytes());assert ref['case_file_sha256']==sha(cases_path)
        assert len(ref['cases'])==len(cases);references={c['id']:c for c in ref['cases']};assert set(references)==set(cases)
    buckets={'first_3':lambda e:e['position']<=3,'first_5':lambda e:e['position']<=5,
             'positions_6_10':lambda e:6<=e['position']<=10,'positions_11_plus':lambda e:e['position']>10,
             'embedding_only':lambda e:e['selection_source']=='embedding','all':lambda e:True}
    totals={key:Counter() for key in buckets};rows=[];functional=[]
    for row in capture['cases']:
        case=cases[row['case']['id']];assert case==row['case']
        profile,wanted=expected(data,case['node_id'],case['confirmed_attributes'])
        actual=[e['wine_slug'] for e in row['entries']]
        checks={'source_eligible_set_equal':set(actual)==wanted,'no_duplicates':len(actual)==len(set(actual)),
                'effective_profile':row['effective_profile_id']==profile,'all_captured_functional_checks':all(row['functional_checks'].values())}
        checks['reported_facts_match_source']=all(
            entry['code']==wine_sources[entry['wine_slug']]['id'] and bool(entry['reason'])
            and entry['source_url']==wine_sources[entry['wine_slug']]['source_url']
            and all(entry['facts'][key]==wine_sources[entry['wine_slug']]['facts'][key]['value']
                    for key in ['color','sweetness','wine_kind','alcohol_percent','residual_sugar_g_l'])
            for entry in row['entries'])
        functional.append({'id':case['id'],'pages':row['page_count'],'wine_count':len(actual),'checks':checks})
        annotated=[]
        for entry in row['entries']:
            endorsed=entry['code'] in set(references[case['id']]['suitable']) if references else None
            for key,condition in buckets.items():
                if condition(entry):totals[key]['count']+=1;totals[key]['endorsed']+=int(endorsed is True)
            if endorsed is False:annotated.append({key:entry[key] for key in ['code','position','selection_source','name','producer']})
        rows.append({'id':case['id'],'node_id':case['node_id'],'variant_id':case['variant_id'],'profile':profile,
                     'wine_count':len(actual),'model_not_endorsed':annotated,'reference_rationale_en':references.get(case['id'],{}).get('reason_en')})
    metrics={key:{**dict(v),'rate':v['endorsed']/v['count'] if references and v['count'] else None} for key,v in totals.items()}
    result={'dataset_sha256':sha(dataset_path),'capture_sha256':sha(capture_path),'cases_sha256':sha(cases_path),
        'reference_sha256':sha(reference_path) if reference_path else None,'scorer_sha256':sha(Path(__file__)),
        'projection_sha256':sha(Path(__file__).with_name('pairing_contract.py')),
        'nodes':len({c['node_id'] for c in cases.values()}),
        'dishes':sum(n['kind']=='dish' for n in data['nodes'] if n['id'] in {c['node_id'] for c in cases.values()}),
        'variants':len({c['variant_id'] for c in cases.values()}),'cases':len(cases),
        'pages':sum(c['pages'] for c in functional),'functional_pass':all(all(c['checks'].values()) for c in functional),
        'availability':{'nonempty':sum(r['wine_count']>0 for r in rows),'min_wines':min(r['wine_count'] for r in rows),
                        'cases_with_at_least_3':sum(r['wine_count']>=3 for r in rows)},
        'editorial_assessment_kind':'blind_model_opinion_not_human_ground_truth' if references else 'not_scored',
        'editorial_metrics':metrics,'editorial_disagreement_cases':sum(bool(r['model_not_endorsed']) for r in rows),
        'results':rows,'functional_results':functional}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ['results','functional_results']}))
    assert result['functional_pass'],'Source contract failed; inspect functional_results'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True);p.add_argument('--cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reference',type=Path);a=p.parse_args();run(a.capture,a.dataset,a.cases,a.output,a.reference)
