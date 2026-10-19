#!/usr/bin/env python3
"""Train the frozen catalogue-only mobile bottle/label segmenter on local MPS."""

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import torch
from ultralytics import YOLO
import ultralytics


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not torch.backends.mps.is_available():
        raise RuntimeError('MPS is unavailable. Do not silently change the training host.')
    manifest = json.loads((args.dataset.parent / 'manifest.json').read_text())
    if manifest['evaluation_overlap'] or manifest['splits']['val'] < 30:
        raise RuntimeError('The training split failed its evaluation-isolation check.')
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    torch.mps.set_per_process_memory_fraction(.25)
    parameters = dict(data=str(args.dataset), epochs=30, imgsz=640, batch=8, workers=0,
                      device='mps', seed=20261019, deterministic=True, amp=False,
                      optimizer='AdamW', lr0=.001, cos_lr=True, patience=30,
                      degrees=180, flipud=.5, fliplr=.5, mosaic=.7, close_mosaic=5,
                      mixup=0.0, cache=False, plots=False, save_period=5,
                      overlap_mask=False,
                      project=str(args.out), name='bottle-label', exist_ok=False)
    state = dict(pid=os.getpid(), started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                 source_weights=str(args.weights), source_weights_sha256=sha(args.weights),
                 dataset_manifest_sha256=sha(args.dataset.parent / 'manifest.json'),
                 dataset_count=manifest['count'], splits=manifest['splits'],
                 evaluation_overlap=[], parameters=parameters, torch=torch.__version__,
                 ultralytics=ultralytics.__version__, mps_memory_fraction=.25,
                 runner_sha256=sha(Path(__file__)), complete=False)
    save(args.out / 'recipe.json', state)
    model = YOLO(str(args.weights))
    from ultralytics.cfg import get_cfg, get_save_dir
    resolved = get_save_dir(get_cfg(overrides={**parameters, 'model':str(args.weights)})).resolve()
    if not resolved.is_relative_to(args.out.resolve()):
        raise RuntimeError('Ultralytics resolved a run outside the requested artifact directory.')
    started = time.monotonic()

    def progress(trainer):
        row = dict(epoch=trainer.epoch + 1, metrics=trainer.metrics,
                   elapsed_s=time.monotonic() - started,
                   mps_allocated_bytes=torch.mps.current_allocated_memory(),
                   mps_driver_bytes=torch.mps.driver_allocated_memory())
        save(args.out / 'progress.json', row)
        with (args.out / 'epochs.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        print(json.dumps(row),file=sys.__stdout__,flush=True)

    model.add_callback('on_fit_epoch_end', progress)
    try:
        from ultralytics.utils import LOGGER
        with (args.out / 'training.log').open('w') as log:
            for handler in LOGGER.handlers:
                if hasattr(handler,'setStream'):
                    handler.setStream(log)
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                results = model.train(**parameters)
        best = Path(model.trainer.best)
        state.update(complete=True, best=str(best), best_sha256=sha(best),
                     results=results.results_dict, elapsed_s=time.monotonic() - started)
    except BaseException as error:
        state.update(error=repr(error), elapsed_s=time.monotonic() - started)
        raise
    finally:
        save(args.out / 'training.json', state)


if __name__ == '__main__':
    main()
