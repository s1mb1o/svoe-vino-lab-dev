"""Reuse verified p512 weights and exact indexes for the full-image experiment."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'base_p224_experiment'))
from profiles import digest,effective_profile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','production','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Preserve existing packs')
    old=json.loads((a.previous/'manifest.json').read_text())
    assert old['format_version']==2 and old['wine_count']==2093
    for name,row in old['files'].items():assert digest(a.previous/name)==row['sha256']
    with zipfile.ZipFile(a.production) as archive:
        prod=json.loads(archive.read('manifest.json'))
        assert prod['format_version']==6 and prod['wine_count']==2093 and prod['vector_dim']==768
        assert prod['model']==old['model'] and prod['model_revision']==old['revision']
        assert prod['pooling_mode']=='standard' and prod['reference_frames_per_image']==1
        candidates=[json.loads(s) for s in archive.read('candidates.jsonl').decode().splitlines()]
        assert len(candidates)==2093
        assert [r['wine_slug'] for r in candidates]==old['slugs']
        assert [r['vector_row'] for r in candidates]==list(range(2093))
        assert all(r['view']=='full' and r['angle']==0 for r in candidates)
        vectors=archive.read('vectors.f32')
        assert hashlib.sha256(vectors).hexdigest()==prod['files']['vectors.f32']['sha256']
        matrix=np.frombuffer(vectors,dtype='<f4').reshape(2093,768)
        assert np.isfinite(matrix).all() and np.max(np.abs(np.linalg.norm(matrix,axis=1)-1))<.001
        standard=old['conditions'][2];custom=old['conditions'][3]
        assert standard['model_sha256']==prod['files']['base-p512-gpu-fp16.tflite']['sha256']
        assert digest(a.previous/'position_table.bin')==prod['files']['position_table.bin']['sha256']
    a.out.mkdir(parents=True)
    needed={standard['model_manifest'],custom['model_manifest'],custom['vectors'],
        old['position_table'],old['segmenter_manifest'],old['validations']['512']}
    for name in (standard['model_manifest'],custom['model_manifest'],old['segmenter_manifest']):
        needed.add(json.loads((a.previous/name).read_text())['model_file'])
    files={}
    for name in sorted(needed):
        shutil.copy2(a.previous/name,a.out/name)
        files[name]=dict(bytes=(a.out/name).stat().st_size,sha256=digest(a.out/name))
    control_name='production-standard-p512.f32'
    (a.out/control_name).write_bytes(vectors)
    files[control_name]=dict(bytes=len(vectors),sha256=hashlib.sha256(vectors).hexdigest())
    conditions=[]
    for number,source in ((5,standard),(6,custom)):
        row=copy.deepcopy(source)
        row.update(number=number,name='full-image-p512-'+('standard-control' if number==5 else 'fractional-bg010'),
            query_frame='full-image',segmenter='NONE' if number==5 else 'CPU',
            reference_policy='production-standard' if number==5 else 'previous-matched-custom')
        if number==5:row['vectors']=control_name
        conditions.append(row)
    result=dict(old,format_version=3,version='20261020-full-image-p512-pooling-v1',conditions=conditions,files=files,
        validations={'512':old['validations']['512']},
        query_masks='On-device mask for patch weights only. Full original RGB. No cropping or whitening.',
        source_previous_manifest_sha256=digest(a.previous/'manifest.json'),production_pack_sha256=digest(a.production),
        production_vectors_sha256=files[control_name]['sha256'],custom_vectors_sha256=files[custom['vectors']]['sha256'])
    (a.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(manifest_sha256=digest(a.out/'manifest.json'),bytes=sum(r['bytes'] for r in files.values()),
        custom_vectors_unchanged=files[custom['vectors']]['sha256']==old['files'][custom['vectors']]['sha256'],
        production_vectors_unchanged=files[control_name]['sha256']==prod['files']['vectors.f32']['sha256'])),flush=True)


if __name__=='__main__':main()
