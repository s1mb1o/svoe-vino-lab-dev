"""Build private NaFlex vectors for one declared retrieval stage."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from PIL import Image
import torch
import transformers
from transformers import AutoImageProcessor,AutoModel

def read(path):return json.loads(Path(path).read_text())
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp");temp.write_text(json.dumps(value));temp.replace(path)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def normalize(value):
    value=np.asarray(value,np.float32);norm=np.linalg.norm(value,axis=-1,keepdims=True)
    assert np.isfinite(value).all() and (norm>0).all()
    return value/norm

def guard(floor=24):
    while True:
        available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))/1024**2
        temperature=int(subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])
        if available>=floor and temperature<83:return available,temperature
        print(json.dumps(dict(state="Wait for resource admission",available_gib=available,temperature_c=temperature)),flush=True)
        time.sleep(20)

def stages(manifest):
    standard=list(manifest['profiles'])
    pair=['u',manifest['aliases']['6b']]
    result=[]
    def add(name,kind,budget=512,margin=None,pools=None):
        result.append(dict(name=name,kind=kind,budget=budget,margin=margin,pools=pools or standard))
    for kind in ('query','reference','axial'):add('p512-'+kind,kind)
    for margin,code in ((0.,'000'),(.02,'002'),(.05,'005'),(.1,'010')):
        for kind in ('query','reference'):add('margin-'+code+'-'+kind,kind,margin=margin,pools=pair)
    for budget in (256,1024):
        for kind in ('query','reference','axial'):add('p'+str(budget)+'-'+kind,kind,budget=budget,pools=pair)
    add('cartesian','cartesian',pools=[manifest['aliases'][p] for p in ('u','5a','5b','6a','6b','6c','6d')])
    return result

def records(manifest,stage):
    kind=stage['kind']
    if kind in ('query','reference'):
        return [dict(id=r['id'],views=[dict(r,in_plane_angle=a,axial_angle=0) for a in (range(0,360,5) if kind=='reference' else [0])]) for r in manifest[kind]]
    result=[]
    for r in manifest['axial']:
        if not r['views']:continue
        views=[]
        for view in r['views']:
            for angle in ([0] if kind=='axial' else [90,180,270]):
                views.append(dict(view,id=r['source_sha256'],in_plane_angle=angle,axial_angle=view['angle'],resize=None))
        result.append(dict(id=r['source_sha256'],views=views))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--pilot',action='store_true');parser.add_argument('--preflight',action='store_true');parser.add_argument('--priority-only',action='store_true');args=parser.parse_args()
    manifest=read('native-inputs.json');stage=next(s for s in stages(manifest) if s['name']==args.stage)
    root=Path('native')/stage['name'];root.mkdir(parents=True,exist_ok=True)
    lock=(root/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (root/'complete.json').exists() and not args.pilot:return
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    checkpoint=Path.home()/'.cache/huggingface/hub/models--google--siglip2-so400m-patch16-naflex/snapshots'/manifest['checkpoint']
    processor=AutoImageProcessor.from_pretrained(checkpoint,local_files_only=True)
    model=None;vision=None
    budget=stage['budget'];batch_size=12 if budget==1024 else 36
    specs=records(manifest,stage)
    recipe=dict(stage,checkpoint=checkpoint.name,dtype='bfloat16',batch_size=batch_size,cuda_cap_gib=8,reserve_gib=20,
                worker_sha256=sha(__file__),input_sha256=sha('native-inputs.json'),torch=torch.__version__,transformers=transformers.__version__,batching='Consecutive views across sources')
    if (root/'recipe.json').exists() and read(root/'recipe.json')!=recipe:
        assert not (root/'pilot.json').exists() and not (root/'progress.json').exists() and not list(root.glob('*.npy')),'Resume recipe mismatch'
    dump(root/'recipe.json',recipe)
    maximum_uniform=0.;minimum_available=1000.;timing=dict(preprocess_seconds=0.,vision_seconds=0.,pool_seconds=0.,batches=0,images=0)

    @lru_cache(maxsize=12)
    def originals(image,foreground,label):
        images=[]
        for path,mode in ((image,'RGB'),(foreground,'L'),(label,'L')):
            with Image.open(path) as im:images.append(im.convert(mode))
        assert images[0].size==images[1].size==images[2].size
        return images

    def prepare(spec):
        images=originals(spec['image'],spec['foreground'],spec['label'])
        step=spec.get('resize');scale=min(1.,step['max_size']/max(images[0].size)) if step and not step.get('upscale') else (step['max_size']/max(images[0].size) if step else 1.)
        values=[]
        for pos,image in enumerate(images):
            if spec['in_plane_angle']:image=image.rotate(spec['in_plane_angle'],Image.Resampling.BICUBIC,expand=True,fillcolor=(255,255,255) if pos==0 else 0)
            if scale!=1.:image=image.resize(tuple(max(1,round(v*scale)) for v in image.size),Image.Resampling.LANCZOS)
            values.append(image)
        if stage['margin'] is not None:
            box=values[1].getbbox()
            if box:
                w,h=box[2]-box[0],box[3]-box[1];dx=round(w*stage['margin']);dy=round(h*stage['margin'])
                padded=[]
                for pos,image in enumerate(values):
                    canvas=Image.new(image.mode,(w+2*dx,h+2*dy),(255,255,255) if pos==0 else 0)
                    canvas.paste(image.crop(box),(dx,dy));padded.append(canvas)
                values=padded
        rgb,fg,label=values
        batch=processor(images=[rgb],return_tensors='pt',max_num_patches=budget)
        masks=[]
        for image in (fg,label):
            mask=torch.from_numpy(np.asarray(image,dtype=np.float32).copy()/255)[None]
            processed=processor(images=[mask],return_tensors='pt',max_num_patches=budget,input_data_format='channels_first',do_convert_rgb=False,do_rescale=False,do_normalize=False)
            assert torch.equal(processed['spatial_shapes'],batch['spatial_shapes'])
            assert torch.equal(processed['pixel_attention_mask'],batch['pixel_attention_mask'])
            masks.append(processed['pixel_values'][0].clamp(0,1).numpy())
        rows,cols=batch['spatial_shapes'][0].tolist();count=rows*cols;tokens=batch['pixel_attention_mask'].shape[1]
        exact_fg=masks[0].mean(-1);exact_label=np.minimum(exact_fg,masks[1].mean(-1));occupied=masks[0].max(-1)>0
        if any(manifest['profiles'][key].get('coverage')=='whole' for key in stage['pools']):
            binary=torch.from_numpy((np.asarray(fg)>0).astype(np.float32))[None]
            patches=processor(images=[binary],return_tensors='pt',max_num_patches=budget,input_data_format='channels_first',do_convert_rgb=False,do_rescale=False,do_normalize=False)
            assert torch.equal(patches['spatial_shapes'],batch['spatial_shapes'])
            occupied=patches['pixel_values'][0].amax(-1).numpy()>0
        legacy_fg=np.asarray(fg.resize((cols,rows),Image.Resampling.BOX),np.float32).ravel()/255
        legacy_label=np.minimum(legacy_fg,np.asarray(label.resize((cols,rows),Image.Resampling.BOX),np.float32).ravel()/255)
        weights=np.zeros((len(stage['pools']),tokens),np.float32)
        for index,key in enumerate(stage['pools']):
            profile=manifest['profiles'][key]
            if profile.get('uniform'):w=np.ones(count,np.float32)
            else:
                coverage=profile['coverage'];f,l=(exact_fg[:count],exact_label[:count]) if coverage=='exact' else (legacy_fg,legacy_label)
                powered=np.power(f,profile['gamma'])
                w=np.where(occupied[:count],1.,profile['background']) if coverage=='whole' else profile['background']*(1-powered)+powered
                w=w+(profile['boost']-1)*l
                if w.sum()==0:w=np.ones(count,np.float32)
            weights[index,:count]=w
        assert np.isfinite(weights).all() and (weights>=0).all() and not weights[:,count:].any()
        if transformers.__version__.startswith('5.'):batch['attention_mask']=batch.pop('pixel_attention_mask')
        return batch,weights

    def encode(views,pool):
        nonlocal maximum_uniform,minimum_available
        minimum_available=min(minimum_available,guard()[0]);t=time.perf_counter()
        prepared=list(pool.map(prepare,views));n=len(prepared);prepared.extend([prepared[-1]]*(batch_size-n))
        batch={key:torch.cat([p[0][key] for p in prepared]).to('cuda') for key in prepared[0][0]}
        weights=torch.from_numpy(np.stack([p[1] for p in prepared])).to('cuda')
        torch.cuda.synchronize();timing['preprocess_seconds']+=time.perf_counter()-t;t=time.perf_counter()
        with torch.inference_mode():
            encoded=vision(**batch);hidden=encoded.last_hidden_state
            torch.cuda.synchronize();timing['vision_seconds']+=time.perf_counter()-t;t=time.perf_counter()
            vectors=[]
            for i,key in enumerate(stage['pools']):
                w=weights[:,i].to(hidden);bias=w.clamp_min(torch.finfo(w.dtype).tiny).log().masked_fill(w==0,float('-inf'))
                bias=bias[:,None,:].repeat_interleave(vision.head.num_heads,dim=0)
                probe=vision.head.probe.repeat(len(hidden),1,1)
                pooled=vision.head.attention(probe,hidden,hidden,attn_mask=bias,need_weights=True)[0]
                pooled=(pooled+vision.head.mlp(vision.head.layernorm(pooled)))[:,0]
                vectors.append(normalize(pooled.float().cpu().numpy())[:n])
            output=np.stack(vectors,axis=1)
            uniform=normalize(encoded.pooler_output.float().cpu().numpy())[:n]
        torch.cuda.synchronize();timing['pool_seconds']+=time.perf_counter()-t
        change=float(np.max(np.abs(output[:,stage['pools'].index('u')]-uniform)))
        maximum_uniform=max(maximum_uniform,change);assert change<2e-5,('Uniform head mismatch',change)
        assert np.max(np.abs(np.linalg.norm(output,axis=-1)-1))<1e-4
        timing['images']+=n;timing['batches']+=1
        minimum_available=min(minimum_available,guard()[0])
        return output

    if args.preflight:
        checks=[]
        for record in specs[:3]:
            for view in record['views'][:2]:
                batch,weights=prepare(view)
                mask=batch.get('attention_mask',batch.get('pixel_attention_mask')).numpy().astype(bool)[0]
                assert not weights[:,~mask].any() and (weights.sum(1)>0).all()
                checks.append(dict(id=record['id'],shape=batch['spatial_shapes'][0].tolist(),real_patches=int(mask.sum()),maximum_weight=float(weights.max())))
        dump(root/'preflight.json',dict(passed=True,checks=checks,recipe=recipe,gpu_model_loaded=False))
        print(json.dumps(dict(stage=stage['name'],preflight=True,passed=True)),flush=True);return
    guard(30)
    torch.cuda.set_per_process_memory_fraction(8*2**30/torch.cuda.get_device_properties(0).total_memory,0)
    model=AutoModel.from_pretrained(checkpoint,local_files_only=True,dtype=torch.bfloat16).to('cuda').eval();vision=model.vision_model
    began=time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        if args.pilot:
            old_controls=None
            chosen=specs[:3];checks=[];individual=[]
            if stage['name']=='p512-reference':
                old_controls=np.load(Path('../axial-matrix-20261018/controls.npz'),allow_pickle=False)
                chosen=[r for r in specs if r['id'] in old_controls.files][:3]
                assert len(chosen)==3
            for record in chosen:
                views=record['views'][:min(3,len(record['views']))]
                values=encode(views,pool)
                individual.append(values[0])
                checks.append(dict(id=record['id'],shape=list(values.shape),minimum_norm=float(np.linalg.norm(values,axis=-1).min())))
                if stage['name']=='p512-reference':
                    deltas=[]
                    for index,alias in enumerate(('u','5a','5b','6a','6b','6c','6d')):
                        p=manifest['aliases'][alias];old=old_controls[record['id']][index]
                        change=float(np.max(np.abs(values[0,stage['pools'].index(p)]-old)))
                        assert change<2e-5,('Frozen pooling control changed',record['id'],alias,change)
                        deltas.append(change)
                    checks[-1]['frozen_pool_deltas']=deltas
            mixed=encode([record['views'][0] for record in chosen],pool)
            equivalence=float(np.max(np.abs(mixed-np.stack(individual))))
            assert equivalence<2e-5,('Distinct-source batching changed vectors',equivalence)
            # Fixed, warmed serial model timing. Keep preparation separate.
            serial=prepare(specs[0]['views'][0])[0]
            serial={key:value.to('cuda') for key,value in serial.items()};latency=[]
            with torch.inference_mode():
                vision(**serial);torch.cuda.synchronize()
                for _ in range(5):
                    t=time.perf_counter();vision(**serial);torch.cuda.synchronize();latency.append((time.perf_counter()-t)*1000)
            dump(root/'pilot.json',dict(passed=True,checks=checks,uniform_delta=maximum_uniform,batch_equivalence_max_delta=equivalence,minimum_available_gib=minimum_available,serial_vision_ms=latency,timing=timing,recipe=recipe))
            print(json.dumps(dict(stage=stage['name'],pilot=True,passed=True,seconds=time.monotonic()-began)),flush=True);return
        assert read(root/'pilot.json')['passed']
        rows=[dict(id=r['id'],in_plane_angle=v['in_plane_angle'],axial_angle=v['axial_angle']) for r in specs for v in r['views']]
        dump(root/'rows.json',rows)
        arrays={}
        for key in stage['pools']:
            target=root/(key+'.npy')
            arrays[key]=np.lib.format.open_memmap(target,mode='r+' if target.exists() else 'w+',dtype=np.float32,shape=(len(rows),1152))
        done=read(root/'progress.json').get('completed_sources',0) if (root/'progress.json').exists() else 0
        offset=sum(len(r['views']) for r in specs[:done])
        views=[view for record in specs for view in record['views']]
        priority_only=args.priority_only and stage['kind']=='query'
        limit=manifest['priority_query_sources'] if priority_only else len(views)
        assert offset<=limit
        boundaries=np.cumsum([len(record['views']) for record in specs]);checkpoint_sources=done
        number=done
        for start in range(offset,limit,batch_size):
            values=encode(views[start:min(start+batch_size,limit)],pool)
            for index,key in enumerate(stage['pools']):arrays[key][offset:offset+len(values)]=values[:,index]
            offset+=len(values)
            number=int(np.searchsorted(boundaries,offset,side='right'))
            if number-checkpoint_sources>=10 or offset==limit:
                assert offset==int(boundaries[number-1]),'Checkpoint must end at a source boundary'
                for array in arrays.values():array.flush()
                progress=dict(stage=stage['name'],cohort_scope='my-failed-2' if priority_only else 'all',completed_sources=number,total_sources=limit if priority_only else len(specs),completed_images=offset,total_images=limit if priority_only else len(rows),seconds=time.monotonic()-began,
                              uniform_delta=maximum_uniform,minimum_available_gib=minimum_available,timing=timing)
                dump(root/'progress.json',progress);print(json.dumps(progress),flush=True)
                checkpoint_sources=number
        files={key+'.npy':dict(sha256=sha(root/(key+'.npy')),size=(root/(key+'.npy')).stat().st_size) for key in stage['pools']}
        dump(root/('priority-complete.json' if priority_only else 'complete.json'),dict(passed=True,recipe=recipe,files=files,rows=len(rows),completed_sources=number,cohort_scope='my-failed-2' if priority_only else 'all',seconds=time.monotonic()-began,minimum_available_gib=minimum_available,uniform_delta=maximum_uniform,timing=timing))
        print(json.dumps(dict(stage=stage['name'],complete=True,seconds=time.monotonic()-began)),flush=True)

if __name__=='__main__':main()
