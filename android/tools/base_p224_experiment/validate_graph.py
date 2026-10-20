"""Check the graph rewrite against the same deployed FP16 weights and head logits."""
import argparse
import gc
import json
from pathlib import Path

from ai_edge_litert.interpreter import Interpreter,OpResolverType
import numpy as np

from profiles import digest,log_weights


def interpreter(path):
    model=Interpreter(model_path=str(path),num_threads=4,experimental_preserve_all_tensors=True,
        experimental_op_resolver_type=OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES)
    model.allocate_tensors()
    return model


def invoke(model,values,bias=None):
    for entry in model.get_input_details():
        if entry['name']=='pooling_log_weights':value=bias
        else:value=values[next(i for i in range(3) if f'args_{i}' in entry['name'])]
        model.set_tensor(entry['index'],value)
    model.invoke()
    return model.get_tensor(model.get_output_details()[0]['index']).copy()


def heads(model,budget):
    tensors={r['index']:r for r in model.get_tensor_details()}
    return [op for op in model._get_ops_details() if op['op_name']=='SOFTMAX' and
        list(tensors[int(op['inputs'][0])]['shape'])==[1,budget]]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-manifest','candidate-manifest','fixtures','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--limit',type=int,default=4)
    a=p.parse_args();assert not a.out.exists()
    source_meta=json.loads(a.source_manifest.read_text());candidate_meta=json.loads(a.candidate_manifest.read_text())
    assert source_meta['profile']==candidate_meta['profile']
    source_path=a.source_manifest.parent/source_meta['model_file'];candidate_path=a.candidate_manifest.parent/candidate_meta['model_file']
    assert digest(source_path)==source_meta['model_sha256'] and digest(candidate_path)==candidate_meta['model_sha256']
    assert candidate_meta.get('source_model_sha256')==source_meta['model_sha256']
    assert candidate_meta.get('external_payload_unchanged') is True
    fixtures=json.loads((a.fixtures/'manifest.json').read_text())
    assert fixtures['profile_sha256']==source_meta['profile_sha256']
    budget=source_meta['profile']['max_num_patches'];rows=[]
    baseline=interpreter(source_path);ops=heads(baseline,budget);assert len(ops)==12
    for fixture in fixtures['fixtures'][:a.limit]:
        values=[]
        for name in ('patch_pixels','position_values','valid_patches'):
            spec=fixture['tensors'][name];path=a.fixtures/fixture['directory']/spec['file']
            assert digest(path)==spec['sha256']
            values.append(np.fromfile(path,dtype=spec['dtype']).reshape(spec['shape']).astype(np.float32))
        vector=invoke(baseline,values)
        logits=[baseline.get_tensor(int(op['inputs'][0])).copy() for op in ops]
        rows.append(dict(id=fixture['id'],values=values,baseline=vector,logits=logits))
    del baseline;gc.collect()
    candidate=interpreter(candidate_path);ops=heads(candidate,budget);assert len(ops)==12
    checks=[]
    for row in rows:
        values=row['values'];zero=np.zeros((1,budget),np.float32)
        standard=invoke(candidate,values,zero)
        zero_error=float(np.max(np.abs(standard-row['baseline'])))
        assert zero_error<=1e-5,zero_error
        f=(np.arange(int(values[2].sum()))%3/2).astype(np.float32)
        bias=log_weights(f,budget,'fractional-bg010')
        weighted=invoke(candidate,values,bias)
        assert np.isfinite(weighted).all() and abs(float(np.linalg.norm(weighted))-1)<.001
        largest=0.
        for original,op in zip(row['logits'],ops):
            x=(original+bias).astype(np.float64);x-=x.max(axis=-1,keepdims=True)
            expected=np.exp(x);expected/=expected.sum(axis=-1,keepdims=True)
            actual=candidate.get_tensor(int(op['outputs'][0]))
            largest=max(largest,float(np.max(np.abs(expected-actual))))
        assert largest<=1e-5,largest
        padding=(values[2]==0).astype(np.float32)*100
        padding_error=float(np.max(np.abs(invoke(candidate,values,bias+padding)-weighted)))
        assert padding_error<=1e-5,padding_error
        result=dict(id=row['id'],zero_bias_maximum_error=zero_error,
            attention_oracle_maximum_error=largest,padding_maximum_error=padding_error,heads=12)
        checks.append(result);print(json.dumps(result),flush=True)
    result=dict(passed=True,source_sha256=source_meta['model_sha256'],candidate_sha256=candidate_meta['model_sha256'],
        profile_sha256=source_meta['profile_sha256'],checks=checks,external_weights_unchanged=True,
        scope='Same FP16 weights: zero-bias equivalence, independent NumPy attention oracle, padding exclusion.',
        android_gpu_validation='pending')
    a.out.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
