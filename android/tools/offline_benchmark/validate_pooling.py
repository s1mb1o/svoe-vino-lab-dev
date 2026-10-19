#!/usr/bin/env python3
"""Validate the weighted complete graph before any Android deployment."""

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time

from ai_edge_litert.interpreter import Interpreter
import numpy as np


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def agreement(a, b):
    a, b = a.astype(np.float64).ravel(), b.astype(np.float64).ravel()
    return dict(cosine=float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b))),
                maximum_component_error=float(np.max(np.abs(a-b))))


def invoke(model, values, bias=None):
    for entry in model.get_input_details():
        name = entry['name']
        if name == 'pooling_log_weights':
            value = bias
        else:
            index = next(i for i in range(3) if f'args_{i}' in name)
            value = values[index]
        model.set_tensor(entry['index'], value)
    model.invoke()
    return model.get_tensor(model.get_output_details()[0]['index']).copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Preserve each numerical check.')
    manifest = json.loads((args.fixtures / 'manifest.json').read_text())
    fixtures = []
    for row in manifest['fixtures'][:2]:
        directory = args.fixtures / row['directory']
        tensors = row['tensors']
        def read(key):
            entry = tensors[key]
            path = directory / entry['file']
            if sha(path) != entry['sha256']:
                raise ValueError('Fixture tensor checksum mismatch.')
            return np.fromfile(path, dtype='<f4').reshape(entry['shape'])
        fixtures.append(dict(id=row['id'], values=[read(key) for key in
            ('patch_pixels','position_values','valid_patches')], native=read('image_embedding')))
    source = Interpreter(model_path=str(args.source), num_threads=4)
    source.allocate_tensors()
    for row in fixtures:
        row['baseline'] = invoke(source, row['values'])
    del source
    gc.collect()
    candidate = Interpreter(model_path=str(args.candidate), num_threads=4)
    candidate.allocate_tensors()
    checks = []
    for row in fixtures:
        zeros = np.zeros_like(row['values'][2])
        started = time.monotonic()
        uniform = invoke(candidate, row['values'], zeros)
        pair = agreement(uniform, row['baseline'])
        native = agreement(uniform, row['native'])
        if pair['cosine'] < .999999 or pair['maximum_component_error'] > .00001:
            raise ValueError(f'Zero-bias equivalence failed: {pair}')
        if native['cosine'] < .99999:
            raise ValueError(f'Native source equivalence failed: {native}')
        weights = np.where(np.arange(zeros.shape[1])[None,:] % 3 == 0, .1, 1).astype(np.float32)
        weighted = invoke(candidate, row['values'], np.log(weights))
        if not np.isfinite(weighted).all() or abs(float(np.linalg.norm(weighted))-1) > .001:
            raise ValueError('Weighted output is invalid.')
        perturb_padding = np.where(row['values'][2] == 0, 100, 0).astype(np.float32)
        padding = agreement(invoke(candidate,row['values'],perturb_padding),uniform)
        if padding['cosine'] < .999999 or padding['maximum_component_error'] > .00001:
            raise ValueError('Padding is not excluded from pooling.')
        checks.append(dict(id=row['id'], zero_bias_vs_original=pair, zero_bias_vs_native=native,
                           weighted_vs_uniform=agreement(weighted,uniform),
                           padding_exclusion=padding, elapsed_s=time.monotonic()-started))
        print(checks[-1],flush=True)
    result=dict(passed=True, source_sha256=sha(args.source), candidate_sha256=sha(args.candidate),
                checks=checks, scope='Desktop CPU numerical gate. Android GPU validation is still required.')
    args.out.write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    main()
