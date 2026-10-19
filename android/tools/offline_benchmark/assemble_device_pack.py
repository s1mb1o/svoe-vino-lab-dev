#!/usr/bin/env python3
"""Assemble an isolated device pack. Do not modify any source artifact."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--references',type=Path,required=True)
    parser.add_argument('--encoder-manifest',type=Path,required=True)
    parser.add_argument('--encoder-validation',type=Path,required=True)
    parser.add_argument('--positions',type=Path,required=True)
    parser.add_argument('--segmenter-manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--development',action='store_true')
    args=parser.parse_args()
    reference=json.loads((args.references/'reference-manifest.json').read_text())
    encoder=json.loads(args.encoder_manifest.read_text())
    segmenter=json.loads(args.segmenter_manifest.read_text())
    validation=json.loads(args.encoder_validation.read_text())
    assert validation['passed'] and validation['candidate_sha256']==encoder['model_sha256']
    assert reference['dimension']==1152
    assert encoder['profile']['model_id']==reference['model']
    assert encoder['profile']['model_revision']==reference['revision']
    assert segmenter['numerical_validation']['passed']
    assert segmenter['overlap_mask'] is False
    assert sha(args.positions)=='2596cba5a6a2fa5e523a707a562a5754a4c1d6001f562f025062ad545f0a4df3'
    args.out.mkdir(parents=True,exist_ok=False)
    files={}
    def include(source,name=None,expected=None):
        name=name or source.name
        assert '/' not in name and name not in files
        digest=sha(source)
        if expected is not None:assert digest==expected
        target=args.out/name
        # Immutable generated artifacts can share disk blocks. No file is edited later.
        try:os.link(source,target)
        except OSError:shutil.copyfile(source,target)
        assert sha(target)==digest
        files[name]=dict(bytes=target.stat().st_size,sha256=digest)
    for name,spec in reference['files'].items():
        include(args.references/name,expected=spec['sha256'])
    include(args.references/'reference-manifest.json')
    include(args.encoder_manifest)
    include(args.encoder_manifest.parent/encoder['model_file'],expected=encoder['model_sha256'])
    include(args.encoder_validation)
    include(args.positions)
    include(args.segmenter_manifest)
    include(args.segmenter_manifest.parent/segmenter['model_file'],expected=segmenter['model_sha256'])
    variants=[]
    for item in reference['variants']:
        # Do not include expected answers or desktop measured counts on the device.
        variants.append({k:v for k,v in item.items() if k!='desktop_metrics'})
    manifest=dict(format='chtozavino-offline-device-benchmark',format_version=1,
        version='20261019-offline-'+('development' if args.development else 'frozen'),
        model=reference['model'],revision=reference['revision'],dimension=1152,max_num_patches=512,
        slugs=reference['slugs'],wine_count=reference['wine_count'],indices=reference['indices'],
        variants=variants,files=files,encoder_manifest=args.encoder_manifest.name,
        encoder_validation=args.encoder_validation.name,position_table=args.positions.name,
        segmenter_manifest=args.segmenter_manifest.name,reranking=False,barcode=False,
        query_masks='on-device-mobile-segmenter',development=args.development,
        adaptations=dict(segmentation='catalogue-trained YOLO11n-seg bottle and label',
            segmentation_device='CPU',original_crop_margin_per_edge=.04,
            maximum_prepared_long_edge=1024,resampling='Android Canvas bilinear RGB; float masks',
            geometry_mask_grid='160x160 source-mapped prototypes; core threshold 0.5',
            missing_bottle='request error; no full-image fallback',
            missing_label='bottle-only fusion; no label boost'))
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(pack=str(args.out),bytes=sum(s['bytes'] for s in files.values()),
                          manifest_sha256=sha(args.out/'manifest.json'),development=args.development)))


if __name__=='__main__':main()
