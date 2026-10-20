"""Validate captured Base vectors, fractional coverage, and all reference scores."""
import argparse
import json
import base64
import hashlib
import sys
from pathlib import Path

from ai_edge_litert.interpreter import Interpreter
import numpy as np
from PIL import Image
from siglip2_naflex_litert.preprocessing import prepare_image
from profiles import coverage,digest,log_weights
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dis_pooling'))
from contracts import normalized_dis,dis_foreground


def compare(expected,actual):
    expected=np.asarray(expected,dtype=np.float64).ravel();actual=np.asarray(actual,dtype=np.float64).ravel()
    if expected.shape!=actual.shape or not np.isfinite(actual).all():raise ValueError('Invalid captured vector')
    cosine=float(expected@actual/np.linalg.norm(expected)/np.linalg.norm(actual))
    error=float(np.max(np.abs(expected-actual)))
    return dict(cosine=cosine,maximum_component_error=error,passed=bool(cosine>=.99999 and error<=.001))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--baseline',type=Path)
    a=p.parse_args();run=json.loads((a.run/'run.json').read_text());pack=json.loads((a.pack/'manifest.json').read_text())
    assert run['complete'] and run['mode']=='parity' and run['requests']==run['assignments']*3
    assert run['assignments']==(5 if run['condition']['number']>=5 else 3)
    assert run['pack_manifest_sha256']==digest(a.pack/'manifest.json')
    condition=next(c for c in pack['conditions'] if c['number']==run['condition']['number'])
    model=json.loads((a.pack/condition['model_manifest']).read_text())
    assert digest(a.pack/model['model_file'])==condition['model_sha256']
    cpu=Interpreter(model_path=str(a.pack/model['model_file']),num_threads=4);cpu.allocate_tensors()
    matrix=np.memmap(a.pack/condition['vectors'],mode='r',dtype='<f4',shape=(pack['wine_count'],768))
    segment=json.loads((a.pack/pack['segmenter_manifest']).read_text())
    dis_size=segment.get('input_shape',[1,3,1024,1024])[2]
    segmenter=None
    if condition.get('segmenter','CPU')!='NONE':
        segmenter=Interpreter(model_path=str(a.pack/segment['model_file']),num_threads=4);segmenter.allocate_tensors()
    baseline={}
    if condition['number']==5:
        if a.baseline is None:raise ValueError('Require the frozen production control')
        original=json.loads((a.baseline/'run.json').read_text())
        assert original['complete'] and original['errors']==0 and not original['reranking'] and not original['barcode']
        assert original['queries_sha256']==run['query_file_sha256']
        baseline={r['query_id']:r['response'] for r in map(json.loads,(a.baseline/'responses.jsonl').read_text().splitlines())}
    checks=[];vectors={}
    for row in map(json.loads,(a.run/'responses.jsonl').read_text().splitlines()):
        assert row['status']==200
        answer=row['response'];capture=a.run/f'capture-{row["request_number"]:02d}'
        if row['request_number']<=run['assignments'] and segmenter is not None and condition.get('segmenter_model')=='DIS':
            values=np.fromfile(capture/'segmenter/input.f32',dtype='<f4').reshape(1,3,dis_size,dis_size)
            segmenter.set_tensor(segmenter.get_input_details()[0]['index'],values);segmenter.invoke()
            expected=segmenter.get_tensor(segmenter.get_output_details()[0]['index']).ravel()
            actual=np.fromfile(capture/'segmenter/raw-mask.f32',dtype='<f4')
            error=float(np.max(np.abs(expected-actual)))
            checks.append(dict(stage='DIS-raw-mask',request=row['request_number'],maximum_component_error=error,passed=bool(error<=.001)))
            actual=np.fromfile(capture/'segmenter/normalized-mask.f32',dtype='<f4')
            error=float(np.max(np.abs(normalized_dis(expected)-actual)))
            checks.append(dict(stage='DIS-normalized-mask',request=row['request_number'],maximum_component_error=error,passed=bool(error<=.001)))
        elif row['request_number']<=run['assignments'] and segmenter is not None:
            values=np.fromfile(capture/'segmenter/input.f32',dtype='<f4').reshape(1,3,640,640)
            segmenter.set_tensor(segmenter.get_input_details()[0]['index'],values);segmenter.invoke()
            for output in segmenter.get_output_details():
                expected=segmenter.get_tensor(output['index']).ravel()
                name='detections' if expected.size==38*8400 else 'prototypes'
                actual=np.fromfile(capture/'segmenter'/(name+'.f32'),dtype='<f4')
                error=float(np.max(np.abs(expected-actual)))
                checks.append(dict(stage='segmenter-'+name,request=row['request_number'],maximum_component_error=error,
                    passed=bool(error<=(.05 if name=='detections' else .001))))
        trace=answer['encoders'][0];directory=capture/'pass-0'
        if condition.get('query_frame')=='full-image':
            checks.append(dict(stage='full-source-geometry-and-pixels',request=row['request_number'],passed=bool(
                trace['query_frame']=='full-image' and trace['frame_width']==trace['source_width'] and
                trace['frame_height']==trace['source_height'] and trace['source_pixel_sha256']==trace['frame_pixel_sha256'])))
            raw=(directory/'frame.rgb').read_bytes()
            assert trace['pixel_contract']=='raw-rgb-ignore-alpha'
            assert hashlib.sha256(raw).hexdigest()==trace['frame_pixel_sha256']
            image=Image.frombytes('RGB',(trace['source_width'],trace['source_height']),raw)
            expected_pixels,expected_mask,grid=prepare_image(image,512)
            actual_pixels=np.fromfile(directory/'patch_pixels.f32',dtype='<f4').reshape(expected_pixels.shape)
            error=float(np.max(np.abs(expected_pixels-actual_pixels)))
            checks.append(dict(stage='full-image-released-preprocessor',request=row['request_number'],
                maximum_component_error=error,passed=bool(error<=1e-6 and grid==(trace['grid_rows'],trace['grid_columns']))))
            valid=np.fromfile(directory/'valid_patches.f32',dtype='<f4').reshape(expected_mask.shape)
            checks.append(dict(stage='full-image-valid-patches',request=row['request_number'],passed=bool(np.array_equal(valid,expected_mask))))
        foreground=np.fromfile(directory/'foreground.f32',dtype='<f4').reshape(trace['frame_height'],trace['frame_width'])
        if condition.get('segmenter_model')=='DIS':
            mask=np.fromfile(capture/'segmenter/normalized-mask.f32',dtype='<f4').reshape(dis_size,dis_size)
            expected=dis_foreground(mask,trace['source_width'],trace['source_height'],condition['query_frame'])
            assert expected.shape==foreground.shape
            error=float(np.max(np.abs(expected-foreground)))
            checks.append(dict(stage='DIS-source-mask-projection',request=row['request_number'],maximum_component_error=error,passed=bool(error<=1e-6)))
        expected=log_weights(coverage(foreground,trace['grid_rows'],trace['grid_columns']),condition['budget'],condition['pooling']).ravel()
        actual=np.fromfile(directory/'pooling_log_weights.f32',dtype='<f4')
        error=float(np.max(np.abs(expected-actual)))
        checks.append(dict(stage='fractional-mask-coverage',request=row['request_number'],maximum_component_error=error,passed=bool(error<=1e-4)))
        for contract in model['inputs']:
            values=np.fromfile(directory/(contract['logical_name']+'.f32'),dtype='<f4').reshape(contract['shape'])
            cpu.set_tensor(contract['index'],values)
        cpu.invoke();expected=cpu.get_tensor(cpu.get_output_details()[0]['index']).ravel()
        actual=np.fromfile(directory/'embedding.f32',dtype='<f4')
        checks.append(dict(stage='identical-input-desktop-device',request=row['request_number'],**compare(expected,actual)))
        result=answer['variants'][0]
        if condition['number']==5:
            previous=baseline[row['query_id']]
            old=np.frombuffer(base64.b64decode(previous['embedding_base64_f32le']),dtype='<f4')
            checks.append(dict(stage='production-control-vector',request=row['request_number'],**compare(old,actual)))
            checks.append(dict(stage='production-control-ranking',request=row['request_number'],passed=
                [c['slug'] for c in previous['candidates']]==[c['slug'] for c in result['candidates']]))
        checks.append(dict(stage='response-embedding',request=row['request_number'],**compare(actual,result['embedding'])))
        scores=np.asarray(matrix@actual);actual_scores=np.asarray(result['bottle_scores'])
        error=float(np.max(np.abs(scores-actual_scores)))
        checks.append(dict(stage='all-reference-scores',request=row['request_number'],maximum_component_error=error,passed=bool(error<=2e-6)))
        order=sorted(range(len(scores)),key=lambda i:(-float(scores[i]),pack['slugs'][i]))[:20]
        checks.append(dict(stage='ranking',request=row['request_number'],
            passed=[pack['slugs'][i] for i in order]==[c['slug'] for c in result['candidates']]))
        vectors.setdefault(row['image_sha256'],[]).append((row['accelerator'],actual))
    assert len(vectors)==run['assignments']
    for identity,sequence in vectors.items():
        assert [s[0] for s in sequence]==['GPU','CPU','GPU']
        for accelerator,vector in sequence:
            checks.append(dict(stage='CPU-GPU-GPU-recreation',image_sha256=identity,accelerator=accelerator,
                **compare(sequence[1][1],vector)))
    report=dict(passed=all(c['passed'] for c in checks),condition=condition['name'],checks=checks,
        scope='Same FP16 model weights; captured Android tensors; raw segmenter outputs; full reference scoring')
    (a.run/'numerical-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],checks=len(checks),condition=condition['name'])),flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
