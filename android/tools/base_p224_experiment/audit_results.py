"""Audit ordered assignments and calculate accepted-slug Top-1/5/10 metrics."""
import argparse
import json
from pathlib import Path
import statistics

from profiles import digest


def audit(run_path,pack_path):
    run=json.loads((run_path/'run.json').read_text());pack=json.loads((pack_path/'manifest.json').read_text())
    if run['mode'] not in ('pilot','full'):raise ValueError('Require a quality run')
    if run['reranking'] or run['barcode']:raise ValueError('Optional recognition was enabled')
    if run['pack_manifest_sha256']!=digest(pack_path/'manifest.json'):raise ValueError('Wrong model pack')
    queries=json.loads((run_path/'queries.json').read_text())
    predictions=[json.loads(line) for line in (run_path/'predictions.jsonl').read_text().splitlines()]
    responses=[json.loads(line) for line in (run_path/'responses.jsonl').read_text().splitlines()]
    if len(predictions)!=len(queries) or len(responses)!=len(queries) or not run['complete']:
        raise ValueError('Incomplete cohort cannot produce full accuracy')
    slugs=set(pack['slugs']);hits={str(k):0 for k in (1,5,10)};outcomes={};errors=0
    for number,(query,prediction,response) in enumerate(zip(queries,predictions,responses),1):
        if (response['request_number']!=number or response['query_id']!=query['query_id'] or
            prediction['query_id']!=query['query_id'] or prediction['image_sha256']!=query['image_sha256'] or
            response['image_sha256']!=query['image_sha256']):raise ValueError('Assignment order or image changed')
        candidates=prediction['candidates'];expected=set(query['truth'])
        if not expected:raise ValueError('Missing accepted answer')
        if response['status']!=200:
            if candidates or prediction['predicted_slug'] is not None:raise ValueError('Failure has a fabricated prediction')
            errors+=1
        elif (response['response']['reranking'] or response['response']['barcode'] or
              response['response']['variants'][0]['candidates']!=candidates or
              response['response']['variants'][0]['variant']!=run['condition']['number']):raise ValueError('Response contract changed')
        if any(c['slug'] not in slugs for c in candidates):raise ValueError('Candidate is not in the catalogue')
        success={str(k):bool(expected.intersection(c['slug'] for c in candidates[:k])) for k in (1,5,10)}
        for k,value in success.items():hits[k]+=value
        outcomes[query['query_id']]=success
    timings=[r['client_ms'] for r in responses]
    ordered=sorted(timings);pos=(len(ordered)-1)*.95;lo=int(pos);hi=min(lo+1,len(ordered)-1)
    median=statistics.median(timings);p95=ordered[lo]*(hi-pos)+ordered[hi]*(pos-lo) if hi!=lo else ordered[lo]
    latency_passed=median<=3000 and p95<=5000 and max(timings)<=10000
    smooth=(latency_passed and not run.get('resume') and
        run['initial_pid']==run['final_pid'] and run['maximum_thermal_status']<4 and not run['cleanup_errors'])
    return dict(passed=True,complete=True,condition=run['condition']['name'],assignments=len(queries),errors=errors,
        reranking=False,barcode=False,hits=hits,top_k_percent={k:100*v/len(queries) for k,v in hits.items()},
        client_median_ms=median,client_p95_ms=p95,client_max_ms=max(timings),smoothness_passed=smooth,
        latency_targets_passed=latency_passed,resumed=bool(run.get('resume')),
        peak_sampled_pss_kib=run['peak_sampled_pss_kib'],maximum_thermal_status=run['maximum_thermal_status'],
        query_file_sha256=run['query_file_sha256'],pack_manifest_sha256=run['pack_manifest_sha256'],outcomes=outcomes)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--pack',type=Path,required=True)
    a=p.parse_args();result=audit(a.run,a.pack)
    (a.run/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='outcomes'}))


if __name__=='__main__':main()
