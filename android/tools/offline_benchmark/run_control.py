#!/usr/bin/env python3
"""Measure one frozen test set through the installed Android debug encoder API."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid


ADB = '/Users/ashmelev/Library/Android/sdk/platform-tools/adb'
ORIGIN = 'http://127.0.0.1:18088'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def append(path, value):
    with path.open('a') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] * (hi - position) + ordered[hi] * (position - lo) if hi != lo else ordered[lo]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--queries', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    def adb(*parts, check=True):
        result = subprocess.run([ADB, '-s', args.serial, *parts], capture_output=True,
                                text=True, timeout=30)
        if check and result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return result.stdout.strip()

    def pid():
        value = adb('shell', 'pidof', args.package, check=False)
        return int(value.split()[0]) if value else None

    def health():
        with urllib.request.urlopen(ORIGIN + '/healthz', timeout=15) as response:
            return json.load(response)

    rows = json.loads(args.queries.read_text())
    if not rows or len({row['query_id'] for row in rows}) != len(rows):
        raise ValueError('Require nonempty, unique assignment identities.')
    verified = set()
    for row in rows:
        if row['image_sha256'] not in verified:
            actual = hashlib.sha256(Path(row['abs_path']).read_bytes()).hexdigest()
            if actual != row['image_sha256']:
                raise ValueError('Query source checksum mismatch: ' + row['query_id'])
            verified.add(actual)
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / 'queries.json', rows)
    metadata = dict(started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    package=args.package, serial=args.serial, assignments=len(rows),
                    distinct_images=len(verified), reranking=False, barcode=False,
                    endpoint='/v1/debug/embedding?k=20&aggregation=max',
                    queries_sha256=hashlib.sha256(args.queries.read_bytes()).hexdigest(),
                    complete=False, predictions=0, attempted=0, errors=0)
    original_power = None
    created_forward = False
    log_process = None
    log_stream = None
    stop = threading.Event()
    samples = []
    sampler = None
    timings = []
    hits = {1: 0, 5: 0, 10: 0}
    first_pid = None
    started = time.monotonic()
    try:
        if 'DEBUGGABLE' not in adb('shell', 'dumpsys', 'package', args.package):
            raise RuntimeError('The installed package is not debuggable.')
        forwards = adb('forward', '--list').splitlines()
        matching = [line for line in forwards if ' tcp:18088 ' in line]
        expected = f'{args.serial} tcp:18088 tcp:18088'
        if matching and matching != [expected]:
            raise RuntimeError('Host port 18088 belongs to another ADB forward.')
        if not matching:
            adb('forward', 'tcp:18088', 'tcp:18088')
            created_forward = True
        metadata['health_before'] = initial = health()
        if initial.get('siglip2_runtime') != 'naflex-complete' or initial.get('segmenter') != 'NONE':
            raise RuntimeError('The control requires complete NaFlex without segmentation.')
        first_pid = pid()
        if first_pid is None:
            raise RuntimeError('Application process is not running.')
        metadata['initial_pid'] = first_pid
        metadata['installed_package'] = adb('shell', 'dumpsys', 'package', args.package)
        original_power = adb('shell', 'settings', 'get', 'global', 'stay_on_while_plugged_in')
        adb('shell', 'settings', 'put', 'global', 'stay_on_while_plugged_in', '15')
        log_stream = (args.out / 'logcat.txt').open('w')
        log_process = subprocess.Popen([ADB, '-s', args.serial, 'logcat', '-v', 'threadtime',
                                       '-T', '1', 'ChtoZaVino:V', 'AndroidRuntime:V',
                                       'libc:V', 'DEBUG:V', 'LiteRtClGlAccelerator:V', '*:S'],
                                      stdout=log_stream, stderr=subprocess.STDOUT)

        def sample():
            while not stop.is_set():
                try:
                    memory = adb('shell', 'dumpsys', 'meminfo', args.package)
                    thermal = adb('shell', 'dumpsys', 'thermalservice')
                    pss = re.search(r'TOTAL PSS:\s*(\d+)', memory)
                    status = re.search(r'Thermal Status:\s*(\d+)', thermal)
                    battery = re.search(r'temperature:\s*(\d+)', adb('shell', 'dumpsys', 'battery'))
                    row = dict(elapsed_s=time.monotonic() - started,
                               pss_kib=int(pss[1]) if pss else None,
                               thermal_status=int(status[1]) if status else None,
                               battery_celsius=int(battery[1]) / 10 if battery else None)
                    samples.append(row)
                    append(args.out / 'telemetry.jsonl', row)
                except Exception as error:
                    append(args.out / 'telemetry.jsonl', {'error': str(error)})
                stop.wait(15)

        sampler = threading.Thread(target=sample, daemon=True)
        sampler.start()
        for index, row in enumerate(rows):
            if samples and (samples[-1].get('thermal_status') or 0) >= 4:
                raise RuntimeError('Thermal state reached CRITICAL or higher.')
            boundary = '----android-offline-' + uuid.uuid4().hex
            path = Path(row['abs_path'])
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
                    f'filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
            body += path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
            # Do not send slugs, masks, or reference answers to the application.
            request = urllib.request.Request(ORIGIN + metadata['endpoint'], data=body,
                        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
            call_start = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    status, answer = response.status, json.load(response)
            except urllib.error.HTTPError as error:
                status, answer = error.code, json.loads(error.read())
            latency = (time.monotonic() - call_start) * 1000
            append(args.out / 'responses.jsonl', dict(query_id=row['query_id'], status=status,
                                                     latency_ms=latency, response=answer))
            metadata['attempted'] += 1
            if pid() != first_pid:
                raise RuntimeError('Application PID changed during evaluation.')
            if status == 200:
                raw = base64.b64decode(answer['embedding_base64_f32le'], validate=True)
                dim = answer['embedding_dim']
                vector = struct.unpack('<' + 'f' * dim, raw)
                norm = math.sqrt(sum(value * value for value in vector))
                if dim != initial['vector_dim'] or not math.isfinite(norm) or abs(norm - 1) > .001:
                    raise RuntimeError('Invalid embedding vector.')
                if answer.get('embedding_accelerator') != 'GPU':
                    raise RuntimeError('The GPU control returned a non-GPU embedding.')
                candidates = answer['candidates']
                slugs = [entry['slug'] for entry in candidates]
                expected_slugs = set(row['truth'])
                for k in hits:
                    hits[k] += bool(expected_slugs.intersection(slugs[:k]))
                append(args.out / 'predictions.jsonl', dict(query_id=row['query_id'],
                       image_path=row['image_path'], image_sha256=row['image_sha256'],
                       predicted_slug=slugs[0] if slugs else None, candidates=candidates,
                       latency_ms=latency))
                metadata['predictions'] += 1
                timings.append(latency)
            else:
                metadata['errors'] += 1
            metadata['hits'] = hits
            metadata['elapsed_s'] = time.monotonic() - started
            save(args.out / 'run.json', metadata)
            if index == 0 or (index + 1) % 10 == 0:
                print(f'{index + 1}/{len(rows)}; Top-1 {hits[1]}/{index + 1}; '
                      f'errors {metadata["errors"]}; {latency:.0f} ms', flush=True)
        metadata['health_after'] = health()
        metadata['complete'] = True
    except BaseException as error:
        metadata['failure'] = repr(error)
        print('Stopped:', repr(error), flush=True)
    finally:
        stop.set()
        if sampler:
            sampler.join(timeout=35)
        if log_process:
            log_process.terminate()
            log_process.wait(timeout=10)
        if log_stream:
            log_stream.close()
        if original_power is not None:
            adb('shell', 'settings', 'put', 'global', 'stay_on_while_plugged_in', original_power)
        if created_forward:
            adb('forward', '--remove', 'tcp:18088')
        metadata.update(elapsed_s=time.monotonic() - started, final_pid=pid(),
                        finished_at=dt.datetime.now(dt.timezone.utc).isoformat(), hits=hits,
                        top_k_percent={k: 100 * n / len(rows) for k, n in hits.items()},
                        client_median_ms=statistics.median(timings) if timings else None,
                        client_p95_ms=percentile(timings, .95),
                        peak_sampled_pss_kib=max((s.get('pss_kib') or 0 for s in samples), default=0),
                        maximum_thermal_status=max((s.get('thermal_status') or 0 for s in samples), default=0),
                        forward_removed=created_forward)
        save(args.out / 'run.json', metadata)
    print(json.dumps({k: v for k, v in metadata.items() if k != 'installed_package'}, ensure_ascii=False), flush=True)
    return 0 if metadata['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
