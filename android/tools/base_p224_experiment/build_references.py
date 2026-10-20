"""Build four matching indexes. Reuse immutable matching baseline vectors."""
import argparse
import gc
import json
from pathlib import Path
import re
import subprocess
import shutil
import time

from ai_edge_litert.compiled_model import CompiledModel,Options,GpuOptions,HardwareAccelerator
from ai_edge_litert.interpreter import Interpreter
import numpy as np
from PIL import Image
import torch
from siglip2_naflex_litert.preprocessing import prepare_image
from siglip2_naflex_litert.positions import resize_positions

from profiles import CONDITIONS,MODEL,REVISION,coverage,digest,effective_profile,log_weights


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','p224','p512','p512-custom','positions','validation','p512-validation','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reuse',type=Path)
    a=p.parse_args();torch.set_num_threads(2)
    assert not a.out.exists(),'Preserve each completed reference build'
    data=json.loads(a.inputs.read_text());validation=json.loads(a.validation.read_text())
    assert validation['passed']
    p512_validation=json.loads(a.p512_validation.read_text());assert p512_validation['passed']
    previous=json.loads(a.reuse.read_text()) if a.reuse else None
    if previous:
        assert previous['complete'] and previous['inputs_sha256']==digest(a.inputs)
        assert previous['slugs']==data['slugs'] and previous['dimension']==768
    table=torch.from_numpy(np.fromfile(a.positions,dtype='<f4').reshape(256,768).copy())
    assert digest(a.positions)=='3ba1ba032ad8d97e0a1afebf4513615fbfedb56f646c14dcdb83d3c228c12860'
    a.out.mkdir(parents=True);results=[]
    for condition in CONDITIONS:
        metadata_path=a.p224 if condition['budget']==224 else (a.p512_custom if condition['number']==4 else a.p512)
        metadata=json.loads(metadata_path.read_text());model_path=metadata_path.parent/metadata['model_file']
        assert metadata['profile']['model_id']==MODEL and metadata['profile']['model_revision']==REVISION
        assert metadata['profile']['max_num_patches']==condition['budget'] and digest(model_path)==metadata['model_sha256']
        if condition['budget']==224:assert validation['candidate_sha256']==metadata['model_sha256']
        else:assert p512_validation['candidate_sha256' if condition['number']==4 else 'source_sha256']==metadata['model_sha256']
        profile=effective_profile(metadata,condition['pooling'])
        reusable=next((r for r in previous['conditions'] if r['number']==condition['number']),None) if previous else None
        if reusable:
            assert all(reusable[k]==v for k,v in condition.items())
            assert reusable['model_sha256']==metadata['model_sha256'] and reusable['effective_profile']==profile
            source=a.reuse.parent/reusable['vectors'];assert digest(source)==reusable['sha256']
            assert reusable['rows']==len(data['slugs']) and reusable['dimension']==768
            shutil.copy2(source,a.out/reusable['vectors'])
            row=dict(reusable,reused_from=str(a.reuse),reused_manifest_sha256=digest(a.reuse))
            results.append(row);(a.out/(condition['name']+'.json')).write_text(json.dumps(row,indent=2)+'\n')
            print(json.dumps(dict(condition=condition['name'],reused_rows=row['rows'])),flush=True)
            continue
        pressure=subprocess.check_output(['memory_pressure','-Q'],text=True)
        percent=int(re.search(r'memory free percentage: (\d+)%',pressure)[1])
        ram=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))
        if ram*percent/100<8*1024**3:raise RuntimeError('Require 8 GiB free before the local GPU model load')
        compiled=CompiledModel.from_file(str(model_path),options=Options(
            hardware_accelerators=HardwareAccelerator.GPU,gpu_options=GpuOptions(enforce_f32=True)))
        if not compiled.is_fully_accelerated():raise RuntimeError('Reference graph has CPU fallback')
        signature,spec=next(iter(compiled.get_signature_list().items()))
        buffers={name:compiled.create_input_buffer_by_name(signature,name) for name in spec['inputs']}
        output_name=spec['outputs'][0];output=compiled.create_output_buffer_by_name(signature,output_name)
        positions={};matrix=[];started=time.monotonic();directory=a.out/condition['name'];directory.mkdir()
        identity=dict(condition=condition,model_sha256=metadata['model_sha256'],profile=profile,
            inputs_sha256=digest(a.inputs),position_table_sha256=digest(a.positions),
            backend='Mac Metal GPU; FP32 execution; no CPU fallback')
        (directory/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
        cpu=Interpreter(model_path=str(model_path),num_threads=4);cpu.allocate_tensors();cpu_checks=[]
        try:
            for index,row in enumerate(data['references']):
                rgb=Path(row['rgb']);mask=Path(row['mask'])
                assert digest(rgb)==row['rgb_sha256'] and digest(mask)==row['mask_sha256']
                with Image.open(rgb) as image:pixels,valid,grid=prepare_image(image,condition['budget'])
                if grid not in positions:
                    positions[grid]=resize_positions(table,grid,condition['budget']).numpy()
                with Image.open(mask) as image:alpha=np.asarray(image,dtype=np.float32)/255
                bias=log_weights(coverage(alpha,*grid),condition['budget'],condition['pooling'])
                values=dict(patch_pixels=pixels,valid_patches=valid,position_values=positions[grid],pooling_log_weights=bias)
                for contract in metadata['inputs']:
                    buffers[contract['signature_name']].write(values[contract['logical_name']])
                compiled.run_by_name(signature,buffers,{output_name:output})
                vector=output.read(768,np.float32)
                if not np.isfinite(vector).all() or abs(float(np.linalg.norm(vector))-1)>.001:
                    raise RuntimeError('Reference vector is invalid')
                if index<3:
                    for contract in metadata['inputs']:
                        cpu.set_tensor(contract['index'],values[contract['logical_name']])
                    cpu.invoke();expected=cpu.get_tensor(cpu.get_output_details()[0]['index']).ravel().astype(np.float64)
                    actual=vector.astype(np.float64)
                    cosine=float(expected@actual/np.linalg.norm(expected)/np.linalg.norm(actual))
                    error=float(np.max(np.abs(expected-actual)))
                    if cosine<.99999 or error>.001:raise RuntimeError(f'Desktop GPU parity failed: {cosine}, {error}')
                    cpu_checks.append(dict(wine=row['wine_slug'],cosine=cosine,maximum_component_error=error))
                    if index==2:del cpu;gc.collect()
                matrix.append(vector.copy())
                if (index+1)%100==0:
                    progress=dict(condition=condition['name'],rows=index+1,total=len(data['references']),elapsed_s=time.monotonic()-started)
                    (a.out/'progress.json').write_text(json.dumps(progress)+'\n');print(json.dumps(progress),flush=True)
        finally:
            for buffer in buffers.values():buffer.destroy()
            output.destroy();compiled.close();gc.collect()
        path=a.out/(condition['name']+'.f32');np.asarray(matrix,dtype='<f4').tofile(path)
        assert path.stat().st_size==len(data['slugs'])*768*4
        results.append(dict(**condition,vectors=path.name,rows=len(matrix),dimension=768,
            sha256=digest(path),bytes=path.stat().st_size,model_manifest=str(metadata_path),
            model_sha256=metadata['model_sha256'],effective_profile=profile,desktop_cpu_gpu_checks=cpu_checks,
            elapsed_s=time.monotonic()-started))
        (a.out/(condition['name']+'.json')).write_text(json.dumps(results[-1],indent=2)+'\n')
    result=dict(format='base-naflex-p224-comparison-references',complete=True,slugs=data['slugs'],
        wine_count=len(data['slugs']),dimension=768,conditions=results,inputs_sha256=digest(a.inputs),
        reference_views=1,reranking=False,barcode=False,android_latency_measured=False)
    (a.out/'references.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
