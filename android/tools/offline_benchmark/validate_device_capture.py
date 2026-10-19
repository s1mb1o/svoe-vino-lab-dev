#!/usr/bin/env python3
"""Compare captured Android encoder inputs with desktop LiteRT and exact reference scores."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
from ai_edge_litert.interpreter import Interpreter


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--pack',type=Path,required=True)
    parser.add_argument('--allow-incomplete',action='store_true',help='Write partial diagnostics, not a passed complete-run gate.')
    args=parser.parse_args()
    run=json.loads((args.run/'run.json').read_text())
    if not run['complete'] and not args.allow_incomplete:
        raise RuntimeError('The device run is incomplete. Use --allow-incomplete only for partial diagnostics.')
    assert run['mode']=='parity'
    assert run['pack_manifest_sha256']==hashlib.sha256((args.pack/'manifest.json').read_bytes()).hexdigest()
    pack=json.loads((args.pack/'manifest.json').read_text())
    model=json.loads((args.pack/pack['encoder_manifest']).read_text())
    interpreter=Interpreter(model_path=str(args.pack/model['model_file']),num_threads=4)
    interpreter.allocate_tensors()
    inputs=interpreter.get_input_details();output=interpreter.get_output_details()[0]
    segmentation=json.loads((args.pack/pack['segmenter_manifest']).read_text())
    segmenter=Interpreter(model_path=str(args.pack/segmentation['model_file']),num_threads=4)
    segmenter.allocate_tensors()
    checks=[];vectors={}
    rows=[json.loads(line) for line in (args.run/'responses.jsonl').read_text().splitlines()]
    start=time.monotonic()
    for row in rows:
        assert row['status']==200
        answer=row['response'];capture=args.run/f'capture-{row["request_number"]:02d}'
        if row['request_number']<=3:
            segmentation_input=segmenter.get_input_details()[0]
            values=np.fromfile(capture/'segmenter/input.f32',dtype='<f4').reshape(1,3,640,640)
            segmenter.set_tensor(segmentation_input['index'],values);segmenter.invoke()
            for specification in segmenter.get_output_details():
                expected=segmenter.get_tensor(specification['index']).reshape(-1)
                name='detections' if expected.size==38*8400 else 'prototypes'
                actual=np.fromfile(capture/'segmenter'/(name+'.f32'),dtype='<f4')
                error=float(np.max(np.abs(expected-actual)))
                threshold=.05 if name=='detections' else .001
                check=dict(request=row['request_number'],stage='segmenter-'+name,
                    maximum_component_error=error,passed=error<=threshold)
                checks.append(check);print(json.dumps(check),flush=True)
                if not check['passed']:raise RuntimeError('Android segmenter raw-output parity failed')
        for index,trace in enumerate(answer['encoders']):
            directory=capture/f'pass-{index}'
            fg=np.fromfile(directory/'foreground.f32',dtype='<f4').reshape(trace['frame_height'],trace['frame_width'])
            label=np.fromfile(directory/'label.f32',dtype='<f4').reshape(fg.shape) if (directory/'label.f32').exists() else None
            gw,gh=trace['grid_columns'],trace['grid_rows'];profile=trace['profile']
            expected_bias=np.zeros(512,dtype=np.float32)
            def coverage(mask):
                if profile.endswith('-exact'):
                    im=Image.fromarray(mask).resize((gw*16,gh*16),Image.Resampling.BILINEAR)
                    return np.asarray(im).reshape(gh,16,gw,16).mean(axis=(1,3)).reshape(-1)
                im=Image.fromarray(np.rint(mask.clip(0,1)*255).astype(np.uint8))
                return np.asarray(im.resize((gw,gh),Image.Resampling.BOX),dtype=np.float32).reshape(-1)/255
            if profile!='u':
                f=coverage(fg).clip(0,1);l=np.minimum(f,coverage(label).clip(0,1)) if label is not None else 0
                background=.1 if 'bg010' in profile else 0
                boost=3 if '-l3-' in profile else 2
                weights=background*(1-f)+f+(boost-1)*l
                if not weights.sum():weights[:]=1
                expected_bias[:len(weights)]=np.where(weights>0,np.log(np.maximum(weights,1e-30)),-10000)
            actual_bias=np.fromfile(directory/'pooling_log_weights.f32',dtype='<f4')
            error=float(np.max(np.abs(expected_bias-actual_bias)))
            check=dict(request=row['request_number'],stage='mask-coverage-to-log-weights',profile=profile,
                maximum_component_error=error,passed=error<=1e-4)
            checks.append(check);print(json.dumps(check),flush=True)
            if not check['passed']:raise RuntimeError('Android mask-coverage parity failed')
            for specification,contract in zip(inputs,model['inputs']):
                values=np.fromfile(directory/(contract['logical_name']+'.f32'),dtype='<f4').reshape(contract['shape'])
                interpreter.set_tensor(specification['index'],values)
            interpreter.invoke()
            expected=interpreter.get_tensor(output['index']).reshape(-1).astype(np.float64)
            actual=np.fromfile(directory/'embedding.f32',dtype='<f4').astype(np.float64)
            cosine=float(expected@actual/np.linalg.norm(expected)/np.linalg.norm(actual))
            error=float(np.max(np.abs(expected-actual)))
            check=dict(request=row['request_number'],accelerator=row['accelerator'],pass_index=index,
                profile=trace['profile'],space=trace['space'],cosine=cosine,maximum_component_error=error,
                passed=cosine>=.99999 and error<=.001)
            checks.append(check);print(json.dumps(check),flush=True)
            if not check['passed']:raise RuntimeError('Desktop/device encoder parity failed')
        # Check the complete reference scores, not only the first returned slug.
        for result in answer['variants']:
            query=np.asarray(result['embedding'],dtype=np.float32)
            spec=next(v for v in pack['variants'] if v['number']==result['variant'])
            index=pack['indices'][spec['bottle_index']]
            matrix=np.memmap(args.pack/index['vectors'],mode='r',dtype='<f4',shape=(index['rows'],1152))
            owners=np.fromfile(args.pack/index['owners'],dtype='<i4')
            raw=np.asarray(matrix@query)
            top={'max':1,'top2-mean':2,'top3-mean':3}[spec['recipe']['aggregation']]
            scores=np.full(len(pack['slugs']),-np.inf,dtype=np.float64)
            for wine in np.unique(owners):
                selected=raw[owners==wine]
                scores[wine]=np.sort(selected)[-top:].astype(np.float64).mean()
            actual=np.array([float(v) if v is not None else -np.inf for v in result['bottle_scores']])
            finite=np.isfinite(scores)
            error=float(np.max(np.abs(scores[finite]-actual[finite])))
            check=dict(request=row['request_number'],stage='bottle-reference-scores',maximum_component_error=error,
                       passed=bool(np.array_equal(finite,np.isfinite(actual)) and error<=2e-6))
            checks.append(check);print(json.dumps(check),flush=True)
            if not check['passed']:raise RuntimeError('On-device reference score parity failed')
            vectors.setdefault((row['image_sha256'],result['variant']),[]).append((row['accelerator'],query))
    for identity,values in vectors.items():
        if not args.allow_incomplete:assert [a for a,v in values]==['GPU','CPU','GPU']
        if not any(a=='CPU' for a,v in values):continue
        reference=next(v for a,v in values if a=='CPU').astype(np.float64)
        for accelerator,vector in values:
            actual=vector.astype(np.float64)
            cosine=float(reference@actual/np.linalg.norm(reference)/np.linalg.norm(actual))
            error=float(np.max(np.abs(reference-actual)))
            check=dict(image_sha256=identity[0],variant=identity[1],stage='CPU/GPU and GPU-recreation',
                accelerator=accelerator,cosine=cosine,maximum_component_error=error,
                passed=cosine>=.99999 and error<=.001)
            checks.append(check)
            if not check['passed']:raise RuntimeError('CPU/GPU parity failed')
    report=dict(passed=bool(run['complete'] and all(c['passed'] for c in checks)),
                captured_checks_passed=all(c['passed'] for c in checks),complete_run=run['complete'],
                checks=checks,elapsed_s=time.monotonic()-start,
                scope='Captured identical inputs, weighted pooling, and complete bottle scoring',
                accelerator_sequences=[dict(image_sha256=i[0],variant=i[1],sequence=[a for a,v in values]) for i,values in vectors.items()])
    filename='numerical-validation.json' if run['complete'] else 'numerical-validation-partial.json'
    (args.run/filename).write_text(json.dumps(report,indent=2)+'\n')
    print('Complete numerical gate passed' if report['passed'] else 'Partial checks passed; complete numerical gate remains required',flush=True)


if __name__=='__main__':main()
