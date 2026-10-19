#!/usr/bin/env python3
"""Run original image bytes through the isolated offline Android benchmark app."""

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import threading
import time
import uuid

from run_control import append,percentile,save
from usb_http import UsbHttp

ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'
PACKAGE='com.alolalab.chtozavino.offlinebench'


def require_foreground(health):
    if (health.get('foreground_service') is not True or health.get('wake_lock_held') is not True
        or health.get('process_importance',1000)>125):
        raise RuntimeError('Benchmark foreground-service protection is absent')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--queries',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--mode',choices=['parity','pilot','background-pilot','full'],required=True)
    parser.add_argument('--pack-manifest',type=Path,required=True)
    parser.add_argument('--resume-from',type=Path)
    parser.add_argument('--expected-apk-sha256')
    parser.add_argument('--parity-variant',choices=[str(v) for v in range(1,11)]+['all'],default='10')
    args=parser.parse_args()
    if args.resume_from and (args.mode!='full' or not args.expected_apk_sha256):
        parser.error('Resume requires full mode and --expected-apk-sha256')
    def adb(*parts,check=True,timeout=45):
        result=subprocess.run([ADB,'-s',args.serial,*parts],capture_output=True,text=True,timeout=timeout)
        if check and result.returncode:raise RuntimeError(result.stderr or result.stdout)
        return result.stdout.strip()
    def pid():
        value=adb('shell','pidof',PACKAGE,check=False)
        return int(value.split()[0]) if value else None
    queries=json.loads(args.queries.read_text())
    pack=json.loads(args.pack_manifest.read_text())
    if args.mode!='parity' and pack['development']:raise RuntimeError('Development weights cannot produce benchmark results.')
    assert not pack['reranking'] and not pack['barcode']
    if args.mode in ('pilot','background-pilot'):
        # Freeze evenly spaced source identities. Never select from correctness.
        unique=list({q['image_sha256']:q for q in queries}.values())
        queries=[unique[round(i*(len(unique)-1)/29)] for i in range(30)]
    expected_images={}
    for row in queries:
        digest=hashlib.sha256(Path(row['abs_path']).read_bytes()).hexdigest()
        if digest!=row['image_sha256']:raise RuntimeError('Original image hash mismatch')
        expected_images[digest]=row
    args.out.mkdir(parents=True,exist_ok=False)
    save(args.out/'queries.json',queries)
    metadata=dict(mode=args.mode,complete=False,serial=args.serial,package=PACKAGE,
        started_at=dt.datetime.now(dt.timezone.utc).isoformat(),reranking=False,barcode=False,
        query_file_sha256=hashlib.sha256(args.queries.read_bytes()).hexdigest(),
        pack_manifest_sha256=hashlib.sha256(args.pack_manifest.read_bytes()).hexdigest(),
        pack_version=pack['version'],assignments=len(queries),distinct_images=len(expected_images),
        endpoint='/v1/debug/embedding' if args.mode=='parity' else '/v1/match',
        requests=0,errors=0,hits={str(v):{str(k):0 for k in (1,5,10)} for v in range(1,11)})
    transport=UsbHttp();event_lock=threading.Lock()
    def event(value):
        with event_lock:append(args.out/'transport-attempts.jsonl',dict(
            at=dt.datetime.now(dt.timezone.utc).isoformat(),**value))
    def health():return transport.health(event)
    stop=threading.Event();samples=[];sampler=None;log_process=None;log_stream=None
    created_forward=False;original_power=None;initial_pid=None;carried=0
    start=time.monotonic();timings={str(v):[] for v in range(1,11)}
    try:
        if adb('shell','am','get-current-user')!='0':
            raise RuntimeError('The active Android user changed. Require the original user 0.')
        if 'DEBUGGABLE' not in adb('shell','dumpsys','package',PACKAGE):raise RuntimeError('Require a debuggable isolated package')
        initial_pid=pid()
        if initial_pid is None:raise RuntimeError('The isolated app is not running')
        metadata['initial_pid']=initial_pid
        apk_path=adb('shell','pm','path',PACKAGE).removeprefix('package:')
        apk_sha=adb('shell','sha256sum',apk_path).split()[0]
        if args.expected_apk_sha256 and apk_sha!=args.expected_apk_sha256:
            raise RuntimeError('Installed benchmark APK changed')
        metadata['installed_apk_sha256']=apk_sha
        private_manifest=adb('shell','run-as',PACKAGE,'sha256sum','files/bench/manifest.json').split()[0]
        if private_manifest!=metadata['pack_manifest_sha256']:raise RuntimeError('Private model pack changed')
        forwards=adb('forward','--list').splitlines()
        matching=[r for r in forwards if ' tcp:18088 ' in r]
        if matching and matching!=[f'{args.serial} tcp:18088 tcp:18088']:raise RuntimeError('Host port 18088 is in use')
        if not matching:adb('forward','tcp:18088','tcp:18088');created_forward=True
        initial=health();metadata['health_before']=initial
        require_foreground(initial)
        if not initial['pack_present'] or initial['reranking'] or initial['barcode']:raise RuntimeError('Wrong server state')
        metadata['process_segments']=[dict(start_request=1,pid=initial_pid)]
        if args.resume_from:
            from resume_run import restore_prefix
            carried=restore_prefix(args.resume_from,args.out,queries,metadata)
        save(args.out/'run.json',metadata)
        original_power=adb('shell','settings','get','global','stay_on_while_plugged_in')
        adb('shell','settings','put','global','stay_on_while_plugged_in','15')
        log_stream=(args.out/'logcat.txt').open('w')
        log_process=subprocess.Popen([ADB,'-s',args.serial,'logcat','-v','threadtime','-T','1',
            'OfflineBench:V','AndroidRuntime:V','libc:V','DEBUG:V','LiteRtClGlAccelerator:V','*:S'],
            stdout=log_stream,stderr=subprocess.STDOUT)
        def sample():
            while not stop.is_set():
                try:
                    memory=adb('shell','dumpsys','meminfo',PACKAGE)
                    thermal=adb('shell','dumpsys','thermalservice')
                    battery=adb('shell','dumpsys','battery')
                    pss=re.search(r'TOTAL PSS:\s*(\d+)',memory)
                    state=re.search(r'Thermal Status:\s*(\d+)',thermal)
                    temperature=re.search(r'temperature:\s*(\d+)',battery)
                    row=dict(elapsed_s=time.monotonic()-start,pss_kib=int(pss[1]) if pss else None,
                        thermal_status=int(state[1]) if state else None,
                        battery_celsius=int(temperature[1])/10 if temperature else None)
                    protection=health()
                    row.update({key:protection.get(key) for key in
                        ('foreground_service','wake_lock_held','process_importance','pid','active')})
                    samples.append(row);append(args.out/'telemetry.jsonl',row)
                except Exception as error:append(args.out/'telemetry.jsonl',dict(error=str(error)))
                stop.wait(15)
        sampler=threading.Thread(target=sample,daemon=True);sampler.start()
        def require_idle(retrying):
            deadline=time.monotonic()+600
            while True:
                if adb('shell','am','get-current-user')!='0':raise RuntimeError('Android user changed')
                if pid()!=initial_pid:raise RuntimeError('Application process changed before HTTP attempt')
                state=health();require_foreground(state)
                if state.get('pid')!=initial_pid or not state.get('pack_present'):
                    raise RuntimeError('USB health identity changed')
                if state.get('reranking') is not False or state.get('barcode') is not False:
                    raise RuntimeError('Optional recognition features changed')
                if state.get('pack_version',pack['version'])!=pack['version']:
                    raise RuntimeError('Model pack changed before HTTP attempt')
                if samples and (samples[-1].get('thermal_status') or 0)>=4:
                    raise RuntimeError('Device reached CRITICAL thermal status')
                if not state.get('active'):return
                if time.monotonic()>=deadline:raise RuntimeError('Previous inference did not finish')
                time.sleep(2)
        if args.mode=='parity':
            # Group accelerator checks. Do not recreate a GPU model for each image.
            jobs=[(row,args.parity_variant,accelerator) for accelerator in ('GPU','CPU','GPU') for row in queries]
        elif args.mode=='pilot':jobs=[(row,str(variant),'GPU') for row in queries for variant in range(1,11)]
        else:jobs=[(row,'all','GPU') for row in queries]
        for number,(row,variant,accelerator) in enumerate(jobs):
            if number<carried:continue
            if adb('shell','am','get-current-user')!='0':
                raise RuntimeError('The Android user changed during evaluation. Stop before the next query.')
            if pid()!=initial_pid:raise RuntimeError('Application process changed before a query')
            require_foreground(health())
            if samples and (samples[-1].get('thermal_status') or 0)>=4:raise RuntimeError('Device reached CRITICAL thermal status')
            boundary='----offline-'+uuid.uuid4().hex
            path=Path(row['abs_path'])
            body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
                  'Content-Type: application/octet-stream\r\n\r\n').encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
            endpoint=metadata['endpoint']+f'?variant={variant}&accelerator={accelerator}&k=20'
            before=time.monotonic()
            status,answer,attempts=transport.post(endpoint,body,
                {'Content-Type':f'multipart/form-data; boundary={boundary}'},require_idle,
                lambda value:event(dict(request_number=number+1,query_id=row['query_id'],
                    image_sha256=row['image_sha256'],**value)))
            elapsed=(time.monotonic()-before)*1000
            record=dict(request_number=number+1,query_id=row['query_id'],image_sha256=row['image_sha256'],
                variant=variant,accelerator=accelerator,status=status,client_ms=elapsed,response=answer,
                transport_attempts=attempts)
            append(args.out/'responses.jsonl',record)
            metadata['requests']+=1
            if pid()!=initial_pid:raise RuntimeError('Application process changed during a query')
            if status==200:
                assert answer['image_sha256']==row['image_sha256']
                assert answer['encoder_accelerator']==accelerator and answer['segmenter_accelerator']=='CPU'
                assert not answer['reranking'] and not answer['barcode'] and answer['offline']
                if answer['pack_version']!=pack['version']:raise RuntimeError('Model pack changed')
                variants=answer['variants']
                assert [r['variant'] for r in variants]==(list(range(1,11)) if variant=='all' else [int(variant)])
                for result in variants:
                    key=str(result['variant']);candidates=result['candidates']
                    assert candidates and all(math.isfinite(c['score']) for c in candidates)
                    if args.mode!='parity':
                        expected=set(row['truth'])
                        for k in (1,5,10):metadata['hits'][key][str(k)]+=bool(expected.intersection(c['slug'] for c in candidates[:k]))
                        directory=args.out/f'variant-{key.zfill(2)}';directory.mkdir(exist_ok=True)
                        append(directory/'predictions.jsonl',dict(query_id=row['query_id'],image_path=row['image_path'],
                            image_sha256=row['image_sha256'],predicted_slug=result['slug'],candidates=candidates,
                            timing_mode=result['timing_mode'],client_request_ms=elapsed))
                        if variant!='all':timings[key].append(elapsed)
                if args.mode=='parity':
                    destination=args.out/f'capture-{number+1:02d}'
                    destination.mkdir()
                    archive=args.out/f'capture-{number+1:02d}.tar'
                    with archive.open('wb') as stream:
                        subprocess.run([ADB,'-s',args.serial,'exec-out','run-as',PACKAGE,
                            'tar','-cf','-','-C','files/bench-diagnostics','.'],stdout=stream,check=True,timeout=120)
                    import tarfile
                    with tarfile.open(archive) as packed:packed.extractall(destination,filter='data')
            else:
                metadata['errors']+=1
                if args.mode=='parity':raise RuntimeError(f'Numerical preflight request {number+1} failed: {answer}')
                # Segmentation failures remain in the denominator and in predictions.
                for v in (range(1,11) if variant=='all' else [int(variant)]):
                    directory=args.out/f'variant-{v:02d}';directory.mkdir(exist_ok=True)
                    append(directory/'predictions.jsonl',dict(query_id=row['query_id'],image_path=row['image_path'],
                        image_sha256=row['image_sha256'],predicted_slug=None,candidates=[],error=answer.get('error')))
                expected_detection_errors={'Сегментатор не нашёл бутылку.',
                    'Сегментатор вернул пустую маску бутылки.','Сегментация не нашла объект.'}
                if answer.get('error') not in expected_detection_errors:
                    raise RuntimeError(f'Unexpected device/model error on request {number+1}: {answer}')
            metadata['elapsed_s']=time.monotonic()-start;save(args.out/'run.json',metadata)
            if number==carried or (number+1)%10==0:print(f'{number+1}/{len(jobs)}; errors={metadata["errors"]}; {elapsed:.0f} ms',flush=True)
        metadata['health_after']=health();metadata['complete']=True
    except BaseException as error:
        metadata['failure']=repr(error);print('Stopped:',repr(error),flush=True)
    finally:
        cleanup_errors=[]
        def cleanup(action):
            try:return action()
            except Exception as error:
                cleanup_errors.append(repr(error));return None
        stop.set()
        if sampler:cleanup(lambda:sampler.join(timeout=45))
        if log_process:
            cleanup(log_process.terminate);cleanup(lambda:log_process.wait(timeout=10))
        if log_stream:log_stream.close()
        if original_power is not None:cleanup(lambda:adb('shell','settings','put','global','stay_on_while_plugged_in',original_power))
        if created_forward:
            def remove_forward():
                if f'{args.serial} tcp:18088 tcp:18088' in adb('forward','--list').splitlines():
                    adb('forward','--remove','tcp:18088')
            cleanup(remove_forward)
        metadata.update(finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),elapsed_s=time.monotonic()-start,
            final_pid=cleanup(pid),cleanup_errors=cleanup_errors,
            new_requests=metadata['requests']-carried,
            maximum_thermal_status=max((s.get('thermal_status') or 0 for s in samples),default=0),
            peak_sampled_pss_kib=max((s.get('pss_kib') or 0 for s in samples),default=0),
            maximum_battery_celsius=max((s.get('battery_celsius') or 0 for s in samples),default=0),
            independent_client_ms={v:dict(median=statistics.median(x) if x else None,p95=percentile(x,.95)) for v,x in timings.items()},
            top_k_percent={v:{k:100*n/len(queries) for k,n in hits.items()} for v,hits in metadata['hits'].items()})
        save(args.out/'run.json',metadata)
    print(json.dumps(metadata,ensure_ascii=False,indent=2),flush=True)
    if not metadata['complete']:raise SystemExit(2)


if __name__=='__main__':main()
