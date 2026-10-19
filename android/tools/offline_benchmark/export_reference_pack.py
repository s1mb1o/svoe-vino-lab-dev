#!/usr/bin/env python3
"""Export frozen FP32 galleries for bounded-memory Android reference search."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--exact-source',type=Path,required=True)
    parser.add_argument('--variants',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    extension=args.campaign/'retrieval-extensions-20261018'
    context=json.loads((extension/'context.json').read_text())
    slugs=context['slugs'];assert slugs==sorted(slugs)
    lookup={slug:i for i,slug in enumerate(slugs)}
    meta=json.loads((extension/'cache/reference-meta.json').read_text())
    owners=np.asarray(meta['owners'],dtype='<i4');angles=np.asarray(meta['angles'])
    axial_rows=json.loads((args.campaign/'axial-20261018/axial-rows.json').read_text())
    axial_owners=np.asarray([lookup[r['wine_slug']] for r in axial_rows],dtype='<i4')
    axial_all=np.arange(len(axial_rows))
    files={};indices={}

    def record(path):
        files[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))

    def write_index(name,pieces):
        path=args.out/(name+'.f32');owner_path=args.out/(name+'.i32')
        total=0;covered=set()
        with path.open('wb') as target,owner_path.open('wb') as relation:
            for matrix,picked,owned in pieces:
                assert len(picked)==len(owned)
                for start in range(0,len(picked),2048):
                    chosen=picked[start:start+2048]
                    values=np.ascontiguousarray(matrix[chosen],dtype='<f4')
                    assert values.shape==(len(chosen),1152) and np.isfinite(values).all()
                    assert np.max(np.abs(np.linalg.norm(values,axis=1)-1))<.002
                    group=np.asarray(owned[start:start+2048],dtype='<i4')
                    assert group.min()>=0 and group.max()<len(slugs)
                    target.write(values.tobytes());relation.write(group.tobytes())
                    total+=len(chosen);covered.update(map(int,group))
        record(path);record(owner_path)
        indices[name]=dict(vectors=path.name,owners=owner_path.name,rows=total,dimension=1152,
                           covered_wines=len(covered),precision='float32-le')
        print(name,total,'vectors',path.stat().st_size,'bytes',flush=True)

    for pool,galleries in (('6a',('zero','rot5','cardinal')),('5a',('rot5',)),('u',('zero',))):
        matrix=np.load(extension/'cache'/('reference-'+pool+'.npy'),mmap_mode='r',allow_pickle=False)
        assert matrix.shape==(len(owners),1152)
        extra_path=(args.campaign/'axial-20261018/axial-vectors.npy' if pool=='u' else
                    args.campaign/'axial-matrix-20261018/reference-vectors'/(pool+'.npy'))
        extra=np.load(extra_path,mmap_mode='r',allow_pickle=False)
        assert extra.shape==(len(axial_rows),1152)
        for gallery in galleries:
            selected=np.flatnonzero(np.isin(angles,{'zero':[0],'cardinal':[0,90,180,270],
                                                    'rot5':list(range(0,360,5))}[gallery]))
            pieces=[(matrix,selected,owners[selected])]
            add=pool!='5a'
            if add:pieces.append((extra,axial_all,axial_owners))
            write_index('b-'+pool+'-'+gallery+('-axial' if add else ''),pieces)

    source_owners=json.loads((extension/'reference-owners.json').read_text())
    # Exact-profile physical rows need the same source-to-wine expansion as desktop.
    pieces=[]
    for stage in ('p512-reference','p512-axial'):
        header=json.loads((args.exact_source/(stage+'.json')).read_text())
        path=args.exact_source/(stage+'.f32')
        assert sha(path)==header['sha256']
        matrix=np.memmap(path,mode='r',dtype='<f4',shape=tuple(header['shape']))
        picked=[];owned=[]
        for index,row in enumerate(header['rows']):
            for owner in sorted(source_owners[row['id']]):
                picked.append(index);owned.append(owner)
        pieces.append((matrix,np.asarray(picked),np.asarray(owned,dtype='<i4')))
    write_index('b-g1-bg000-l3-exact-cardinal-axial',pieces)

    ownership=defaultdict(set)
    for wine in json.loads((args.campaign/'catalogue-wines.json').read_text()):
        for _,source in wine['columns']:ownership[source].add(lookup[wine['slug']])
    assert all(ownership[source]==set(group) for source,group in source_owners.items())
    label_root=args.campaign/'labels-20261017/data/catalog/embeddings/exp-my-failed2-label7-iou'
    label_index=json.loads((label_root/'index.json').read_text())
    label_vectors=args.campaign/'matrix-20261017/label-reference-vectors/iou.npy'
    ready=json.loads(label_vectors.with_name('iou-rot5-ready.json').read_text())
    assert sha(label_vectors)==ready['matrix_sha256']
    labels=np.load(label_vectors,mmap_mode='r',allow_pickle=False)
    assert labels.shape==(3440,72,1152)
    labels=labels.reshape(-1,1152)
    picked=[];owned=[]
    for row in label_index['items']:
        for owner in sorted(ownership[row['source_sha256']]):
            for angle in range(72):picked.append(row['row']*72+angle);owned.append(owner)
    write_index('l-7f-rot5',[(labels,np.asarray(picked),np.asarray(owned,dtype='<i4'))])
    frozen=json.loads(args.variants.read_text())
    pool_alias={'g1-bg010-l2-legacy':'6a','g1-bg010-l1-legacy':'5a','u':'u',
                'g1-bg000-l3-exact':'g1-bg000-l3-exact'}
    for variant in frozen['variants']:
        recipe=variant['recipe'];pool=pool_alias[recipe['reference_pool']]
        variant['bottle_index']='b-'+pool+'-'+recipe['gallery']+('-axial' if recipe['axial_union'] else '')
        variant['label_index']='l-7f-rot5' if variant['label_id'] else None
        assert variant['bottle_index'] in indices
    result=dict(format='chtozavino-offline-benchmark-references',format_version=1,
                model=frozen['model'],revision=frozen['revision'],dimension=1152,
                slugs=slugs,wine_count=len(slugs),indices=indices,files=files,
                variants=frozen['variants'],variant_manifest_sha256=sha(args.variants),
                reranking=False,barcode=False,reference_precision='float32',
                query_masks='Mobile bottle/label model. Never frozen evaluation masks.')
    (args.out/'reference-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Reference pack bytes:',sum(r['bytes'] for r in files.values()),flush=True)


if __name__=='__main__':
    main()
