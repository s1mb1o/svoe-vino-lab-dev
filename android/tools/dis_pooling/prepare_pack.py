"""Reuse existing encoder/index bytes and the pinned production DIS graph."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

import numpy as np
from ai_edge_litert.interpreter import Interpreter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'base_p224_experiment'))
from profiles import digest

DIS_SHA='0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('previous','production','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Preserve existing packs')
    previous=json.loads((a.previous/'manifest.json').read_text())
    assert previous['format_version']==3 and [r['number'] for r in previous['conditions']]==[5,6]
    for name,row in previous['files'].items():assert digest(a.previous/name)==row['sha256']
    with zipfile.ZipFile(a.production) as archive:dis=archive.read('dis.tflite')
    assert hashlib.sha256(dis).hexdigest()==DIS_SHA
    cpu=Interpreter(model_content=dis,num_threads=4)
    inputs=cpu.get_input_details();outputs=cpu.get_output_details()
    assert len(inputs)==len(outputs)==1
    assert inputs[0]['shape'].tolist()==[1,3,1024,1024] and outputs[0]['shape'].tolist()==[1,1,1024,1024]
    assert inputs[0]['dtype']==outputs[0]['dtype']==np.float32
    a.out.mkdir(parents=True)
    old_segmenter=json.loads((a.previous/previous['segmenter_manifest']).read_text())['model_file']
    files={}
    for name,row in previous['files'].items():
        if name in (old_segmenter,previous['segmenter_manifest']):continue
        shutil.copy2(a.previous/name,a.out/name);files[name]=row
    (a.out/'dis.tflite').write_bytes(dis)
    metadata=dict(format='chtozavino-mobile-dis',model_file='dis.tflite',model_sha256=DIS_SHA,
        input_shape=[1,3,1024,1024],output_shape=[1,1,1024,1024],precision='float32',
        source_verification=dict(passed=True,scope='Pinned production graph hash, FP32 tensor shapes, prior device evaluation'),
        normalization='RGB / 255 - 0.5; NCHW; stretched 1024x1024',mask_normalization='per-image min-max')
    (a.out/'dis.manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    for name in ('dis.tflite','dis.manifest.json'):
        files[name]=dict(bytes=(a.out/name).stat().st_size,sha256=digest(a.out/name))
    control=copy.deepcopy(previous['conditions'][0]);control['segmenter_model']='NONE'
    conditions=[control]
    for number,frame in ((7,'full-image'),(8,'bottle-crop-white')):
        row=copy.deepcopy(previous['conditions'][1]);row.update(number=number,
            name='dis-p512-custom-'+frame,query_frame=frame,segmenter='GPU',segmenter_model='DIS')
        conditions.append(row)
    result=dict(previous,format_version=4,version='20261020-dis-p512-pooling-v1',conditions=conditions,
        files=files,segmenter_manifest='dis.manifest.json',source_previous_manifest_sha256=digest(a.previous/'manifest.json'),
        production_pack_sha256=digest(a.production),query_masks='DIS GPU; no label; unchanged custom references')
    (a.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(manifest_sha256=digest(a.out/'manifest.json'),bytes=sum(r['bytes'] for r in files.values()),
        encoder_and_index_bytes_unchanged=True,conditions=[r['number'] for r in conditions])))


if __name__=='__main__':main()
