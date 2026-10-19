#!/usr/bin/env python3
"""Export a frozen bottle/label checkpoint and verify raw LiteRT CPU outputs."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--ultralytics-site',type=Path)
    parser.add_argument('--selection',type=Path)
    args=parser.parse_args()
    if args.ultralytics_site:sys.path.append(str(args.ultralytics_site))
    import numpy as np
    import torch
    from PIL import Image
    from ai_edge_litert.interpreter import Interpreter
    import litert_torch
    import ultralytics
    torch.set_num_threads(4)
    args.out.mkdir(parents=True,exist_ok=False)
    original=sha(args.checkpoint)
    selection=json.loads(args.selection.read_text()) if args.selection else None
    if selection is not None:
        assert selection['complete'] and selection['checkpoint_sha256']==original
        assert selection['retrieval_results_used'] is False
    snapshot=args.out/'source-checkpoint.pt'
    shutil.copyfile(args.checkpoint,snapshot)
    if sha(snapshot)!=original or sha(args.checkpoint)!=original:
        raise RuntimeError('The source checkpoint changed during the snapshot.')
    checkpoint=torch.load(snapshot,map_location='cpu',weights_only=False)
    if checkpoint.get('train_args',{}).get('overlap_mask') is not False:
        raise ValueError('Nested bottle and label masks require overlap_mask=False.')
    model=checkpoint['ema'] if checkpoint.get('ema') is not None else checkpoint['model']
    assert model.names=={0:'bottle',1:'label'}
    model=model.float().eval()
    model.fuse(verbose=False)
    head=model.model[-1]
    head.export=True;head.format='onnx';head.dynamic=False
    dummy=torch.zeros(1,3,640,640)
    with torch.inference_mode():outputs=model(dummy)
    assert [list(t.shape) for t in outputs]==[[1,38,8400],[1,32,160,160]]
    path=args.out/'bottle-label-fp32.tflite'
    print('Convert the frozen two-class graph',flush=True)
    with torch.no_grad():converted=litert_torch.convert(model,(dummy,))
    converted.export(str(path))
    interpreter=Interpreter(model_path=str(path),num_threads=4)
    interpreter.allocate_tensors()
    input_spec=interpreter.get_input_details()[0]
    assert input_spec['shape'].tolist()==[1,3,640,640]
    checks=[]
    for image_path in sorted((args.dataset/'images/val').glob('*.jpg'))[:3]:
        with Image.open(image_path) as opened:image=opened.convert('RGB')
        scale=min(640/image.width,640/image.height)
        size=(round(image.width*scale),round(image.height*scale))
        resized=image.resize(size,Image.Resampling.BILINEAR)
        canvas=Image.new('RGB',(640,640),(114,114,114))
        canvas.paste(resized,((640-size[0])//2,(640-size[1])//2))
        values=np.asarray(canvas,dtype=np.float32).transpose(2,0,1)[None]/255
        with torch.inference_mode():expected=[t.numpy() for t in model(torch.from_numpy(values))]
        interpreter.set_tensor(input_spec['index'],values)
        interpreter.invoke()
        actual={tuple(spec['shape']):interpreter.get_tensor(spec['index'])
                for spec in interpreter.get_output_details()}
        detections=actual[(1,38,8400)];prototype=actual[(1,32,160,160)]
        assert np.isfinite(detections).all() and np.isfinite(prototype).all()
        box_error=float(np.max(np.abs(detections[:,:4]-expected[0][:,:4])))
        other_error=float(np.max(np.abs(detections[:,4:]-expected[0][:,4:])))
        proto_error=float(np.max(np.abs(prototype-expected[1])))
        if box_error>.05 or other_error>.001 or proto_error>.001:
            raise ValueError(f'LiteRT raw-output parity failed: {box_error,other_error,proto_error}')
        checks.append(dict(image=image_path.name,image_sha256=sha(image_path),
                           box_maximum_error=box_error,score_coefficients_maximum_error=other_error,
                           prototype_maximum_error=proto_error))
        print(checks[-1],flush=True)
    metadata=dict(format='chtozavino-mobile-bottle-label',model_file=path.name,
                  model_sha256=sha(path),model_bytes=path.stat().st_size,
                  source_checkpoint_sha256=original,source_epoch_index=checkpoint['epoch'],
                  classes=['bottle','label'],input_shape=[1,3,640,640],input_layout='NCHW',
                  coordinate_units='pixels',normalization='0..1',letterbox_rgb=114,
                  detection_shape=[1,38,8400],prototype_shape=[1,32,160,160],
                  prototype_layout='NCHW',threshold=.25,mask_threshold=.5,
                  overlap_mask=False,precision='float32',numerical_validation=dict(passed=True,checks=checks),
                  torch=torch.__version__,ultralytics=ultralytics.__version__,
                  dataset_manifest_sha256=sha(args.dataset/'manifest.json'),
                  export_runner_sha256=sha(Path(__file__)),
                  original_schedule_epochs=checkpoint['train_args']['epochs'])
    if selection is not None:
        metadata.update(pilot_selection_sha256=sha(args.selection),
            completed_training_epochs=selection['completed_epochs'],
            selected_best_fitness=selection['selected_best_fitness'],
            retrieval_results_used_for_selection=False)
    (args.out/'bottle-label.manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('Segmenter CPU export gate passed:',path,flush=True)


if __name__=='__main__':
    main()
