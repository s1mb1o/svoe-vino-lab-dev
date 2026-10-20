"""Replace only DIS graph/metadata in a verified experimental pack."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'base_p224_experiment'))
from profiles import digest
from export_resolution import SOURCE_SHA


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','export','identity','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('Preserve existing packs')
    previous=json.loads((args.previous/'manifest.json').read_text())
    record=json.loads((args.export/'export-record.json').read_text())
    identity=json.loads((args.identity/'export-record.json').read_text())
    size=record['input_size']
    if (previous['format_version']!=4 or size not in (512,768) or record['source_sha256']!=SOURCE_SHA or
        not record['weights_preserved'] or not record['cpu_smoke']['passed'] or
        not record['cpu_smoke']['all_static_shapes_verified'] or identity['identity_cpu_max_error']!=0 or
        identity['source_sha256']!=SOURCE_SHA or identity['input_size']!=1024):raise ValueError('Unverified DIS specialization')
    if digest(args.export/'dis.tflite')!=record['model_sha256']:raise ValueError('Exported graph changed')
    for name,row in previous['files'].items():
        if digest(args.previous/name)!=row['sha256']:raise ValueError('Previous pack changed')
    args.out.mkdir(parents=True);result=copy.deepcopy(previous)
    for name in previous['files']:
        if name in ('dis.tflite','dis.manifest.json'):continue
        shutil.copy2(args.previous/name,args.out/name)
    shutil.copy2(args.export/'dis.tflite',args.out/'dis.tflite')
    metadata=dict(format='chtozavino-mobile-dis',model_file='dis.tflite',model_sha256=record['model_sha256'],
        input_shape=[1,3,size,size],output_shape=[1,1,size,size],precision='float32',
        source_verification=dict(passed=True,scope='Pinned graph specialization; immutable weights; CPU static shapes and identity check',
            source_sha256=SOURCE_SHA,export_record_sha256=digest(args.export/'export-record.json')),
        normalization=f'RGB / 255 - 0.5; NCHW; stretched {size}x{size}',mask_normalization='per-image min-max')
    (args.out/'dis.manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    for name in ('dis.tflite','dis.manifest.json'):
        result['files'][name]=dict(bytes=(args.out/name).stat().st_size,sha256=digest(args.out/name))
    result.update(version=f'20261020-dis{size}-p512-crop-v1',dis_input_size=size,
        source_previous_manifest_sha256=digest(args.previous/'manifest.json'))
    for condition in result['conditions']:
        if condition.get('segmenter_model')=='DIS':
            condition.update(dis_input_size=size,name=f'dis{size}-p512-custom-'+condition['query_frame'])
    (args.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,row in previous['files'].items():
        if name not in ('dis.tflite','dis.manifest.json') and digest(args.out/name)!=row['sha256']:
            raise RuntimeError('Encoder or reference bytes changed')
    print(json.dumps(dict(size=size,manifest_sha256=digest(args.out/'manifest.json'),
        dis_sha256=record['model_sha256'],encoder_and_reference_bytes_unchanged=True)))


if __name__=='__main__':main()
