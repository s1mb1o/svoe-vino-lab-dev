#!/usr/bin/env python3
"""Stop only this training process after the frozen pilot epoch and save its best checkpoint."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training',type=Path,required=True)
    parser.add_argument('--epochs',type=int,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    recipe=json.loads((args.training/'recipe.json').read_text())
    pid=recipe['pid']
    args.out.mkdir(parents=True,exist_ok=False)
    policy=dict(policy='Best catalogue-validation fitness after fixed pilot epochs',
                pilot_epochs=args.epochs,original_schedule_epochs=recipe['parameters']['epochs'],
                source_recipe_sha256=sha(args.training/'recipe.json'),pid=pid,
                retrieval_results_used=False,complete=False)
    (args.out/'selection.json').write_text(json.dumps(policy,indent=2)+'\n')
    while True:
        progress=json.loads((args.training/'progress.json').read_text())
        if progress['epoch']>=args.epochs:break
        command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
        if 'train_segmenter.py' not in command or str(args.training) not in command:
            raise RuntimeError('The original training process stopped before the pilot target.')
        time.sleep(2)
    if progress['epoch']!=args.epochs:raise RuntimeError('Missed the exact frozen pilot epoch.')
    command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
    if 'train_segmenter.py' not in command or str(args.training) not in command:
        raise RuntimeError('Refuse to signal an unrelated process.')
    os.kill(pid,signal.SIGINT)
    for _ in range(60):
        if not subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout.strip():break
        time.sleep(1)
    else:raise RuntimeError('The training process did not stop after SIGINT.')
    source=args.training/'bottle-label/weights/best.pt'
    digest=sha(source)
    target=args.out/'best-pilot.pt'
    shutil.copyfile(source,target)
    assert sha(source)==sha(target)==digest
    import torch
    checkpoint=torch.load(target,map_location='cpu',weights_only=False)
    policy.update(complete=True,completed_epochs=progress['epoch'],source_checkpoint=str(source),
        checkpoint_sha256=digest,selected_epoch_index=checkpoint['epoch'],
        selected_best_fitness=checkpoint['best_fitness'],stopped_with='SIGINT after epoch checkpoint',
        final_progress=progress)
    shutil.copyfile(args.training/'epochs.jsonl',args.out/'epochs.jsonl')
    shutil.copyfile(args.training/'bottle-label/results.csv',args.out/'results.csv')
    (args.out/'selection.json').write_text(json.dumps(policy,indent=2)+'\n')
    print(json.dumps(policy),flush=True)


if __name__=='__main__':main()
