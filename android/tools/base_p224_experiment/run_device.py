"""Run one isolated Base pooling condition. Preserve every assignment and error."""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tarfile
import threading
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'offline_benchmark'))
from usb_http import UsbHttp
from run_control import append,save,percentile
from profiles import PACKAGE,digest
from pooling_resume import restore_prefix,verify_preserved

ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'
DETECTION_ERRORS={'Сегментатор не нашёл бутылку.','Сегментатор вернул пустую маску бутылки.',
                  'Сегментация не нашла объект.'}


def pilot_queries(rows):
    unique=list({row['image_sha256']:row for row in rows}.values())
    if len(unique)<30:raise ValueError('Require 30 distinct images')
    return [unique[round(i*(len(unique)-1)/29)] for i in range(30)]


def parity_queries(rows,condition):
    if condition<5:return pilot_queries(rows)[:3]
    # Frozen decoder boundaries from the stopped control; never select by correctness.
    identities=('q-000029','q-000171','q-000380','q-000567')
    by_id={row['query_id']:row for row in rows}
    selected=[by_id[key] for key in identities]+[pilot_queries(rows)[0]]
    if len({row['image_sha256'] for row in selected})!=5:raise ValueError('Parity images must be distinct')
    return selected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True)
    p.add_argument('--queries',type=Path,required=True)
    p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--apk-sha256',required=True)
    p.add_argument('--condition',type=int,choices=range(1,9),required=True)
    p.add_argument('--mode',choices=('parity','pilot','full'),required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--resume-from',type=Path)
    p.add_argument('--expected-resume-records',type=int)
    a=p.parse_args()
    if a.resume_from and (a.mode!='full' or not a.expected_resume_records):
        p.error('Resume requires full mode and an explicit expected prefix length')
    if a.expected_resume_records and not a.resume_from:p.error('Prefix length requires --resume-from')
    def adb(*parts,check=True,timeout=45):
        r=subprocess.run([ADB,'-s',a.serial,*parts],capture_output=True,text=True,timeout=timeout)
        if check and r.returncode:raise RuntimeError(r.stderr or r.stdout)
        return r.stdout.strip()
    def pid():
        values=adb('shell','pidof',PACKAGE,check=False).split()
        return int(values[0]) if len(values)==1 else None
    rows=json.loads(a.queries.read_text())
    if len(rows)!=668 or len({r['query_id'] for r in rows})!=668:
        raise ValueError('Require all 668 frozen assignments')
    if a.mode=='parity':rows=parity_queries(rows,a.condition)
    elif a.mode=='pilot':rows=pilot_queries(rows)
    for row in rows:
        if digest(Path(row['abs_path']))!=row['image_sha256']:raise ValueError('Original image changed')
    pack=json.loads((a.pack/'manifest.json').read_text())
    if pack['reranking'] or pack['barcode']:raise ValueError('Optional recognition must stay disabled')
    condition=next(c for c in pack['conditions'] if c['number']==a.condition)
    segment_metadata=json.loads((a.pack/pack['segmenter_manifest']).read_text())
    a.out.mkdir(parents=True,exist_ok=False);save(a.out/'queries.json',rows)
    meta=dict(mode=a.mode,condition=condition,complete=False,package=PACKAGE,serial=a.serial,
        query_file_sha256=digest(a.queries),pack_manifest_sha256=digest(a.pack/'manifest.json'),
        pack_version=pack['version'],installed_apk_sha256=a.apk_sha256,reranking=False,barcode=False,
        started_at=dt.datetime.now(dt.timezone.utc).isoformat(),assignments=len(rows),requests=0,errors=0,
        timing_scope='Independent full HTTP pipeline; one untimed warmup; compiled model reuse; no embedding sharing')
    transport=UsbHttp();lock=threading.Lock();samples=[];stop=threading.Event();sampler=None
    original_power=None;initial_pid=None;forward=False;log=None;log_stream=None;timings=[]
    resumed=0;inherited_samples=[]
    if a.resume_from:
        recovery,prior,inherited_samples=restore_prefix(a.resume_from,a.out,rows,meta,pack,a.expected_resume_records)
        meta['resume']=recovery;resumed=len(prior);meta['requests']=resumed
        meta['errors']=recovery['original_run']['errors'];timings=[r['client_ms'] for r in prior]
        meta['timing_scope']+='; interrupted prefix preserved; one additional untimed continuation warmup; disconnected interval excluded'
        save(a.out/'prefix-audit.json',recovery)
    start=time.monotonic()
    def event(row):
        with lock:append(a.out/'transport-attempts.jsonl',dict(at=dt.datetime.now(dt.timezone.utc).isoformat(),**row))
    def health():return transport.health(event)
    def require_state(retrying=False):
        deadline=time.monotonic()+600
        while True:
            if adb('shell','am','get-current-user')!='0' or pid()!=initial_pid:
                raise RuntimeError('Android profile or process changed')
            state=health()
            if (state.get('pid')!=initial_pid or not state.get('pack_present') or
                not state.get('foreground_service') or not state.get('wake_lock_held') or
                state.get('process_importance',1000)>125):raise RuntimeError('Foreground protection or identity changed')
            if state.get('reranking') is not False or state.get('barcode') is not False:
                raise RuntimeError('Optional recognition changed')
            if state.get('pack_version',pack['version'])!=pack['version']:raise RuntimeError('Pack version changed')
            if samples and (samples[-1].get('thermal_status') or 0)>=4:raise RuntimeError('CRITICAL thermal status')
            if not state.get('active'):return state
            if time.monotonic()>deadline:raise RuntimeError('Previous inference did not finish')
            stop.wait(2)
    def request(row,accelerator,number,warmup=False):
        boundary='----base-pooling-'+uuid.uuid4().hex
        path=Path(row['abs_path'])
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="query{path.suffix}"\r\n'
              'Content-Type: application/octet-stream\r\n\r\n').encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
        endpoint='/v1/debug/embedding' if a.mode=='parity' else '/v1/match'
        before=time.monotonic()
        status,answer,attempts=transport.post(endpoint+f'?variant={a.condition}&accelerator={accelerator}&k=20',body,
            {'Content-Type':f'multipart/form-data; boundary={boundary}'},require_state,
            lambda value:event(dict(request_number=number,warmup=warmup,**value)))
        elapsed=(time.monotonic()-before)*1000
        record=dict(request_number=number,query_id=row['query_id'],image_sha256=row['image_sha256'],
            accelerator=accelerator,status=status,client_ms=elapsed,response=answer,transport_attempts=attempts)
        append(a.out/'received-responses.jsonl',dict(warmup=warmup,**record))
        require_state()
        if status==200:
            if (answer['image_sha256']!=row['image_sha256'] or answer['encoder_accelerator']!=accelerator or
                answer['segmenter_accelerator']!=condition.get('segmenter','CPU') or answer['dimension']!=768 or
                answer['pack_version']!=pack['version'] or answer['reranking'] or answer['barcode'] or
                answer['offline'] is not True or answer['encoder_passes']!=1):raise RuntimeError('Wrong inference contract')
            result=answer['variants']
            if len(result)!=1 or result[0]['variant']!=a.condition:raise RuntimeError('Wrong condition')
            result=result[0]
            if condition.get('segmenter_model')=='DIS' and answer['segmentation'].get('model')!='DIS':
                raise RuntimeError('Wrong segmentation model')
            if condition.get('dis_input_size') and (answer['segmentation'].get('input_size')!=condition['dis_input_size'] or
                answer['segmentation'].get('model_sha256')!=segment_metadata['model_sha256']):
                raise RuntimeError('Wrong DIS resolution or model')
            if (result['budget']!=condition['budget'] or result['pooling']!=condition['pooling'] or
                result['timing_mode']!='independent' or not result['candidates'] or
                any(not math.isfinite(c['score']) for c in result['candidates'])):raise RuntimeError('Invalid matching result')
            if condition.get('query_frame')=='full-image':
                trace=answer['encoders'][0]
                if (answer.get('query_frame')!='full-image' or result.get('reference_policy')!=condition['reference_policy'] or
                    trace['frame_width']!=trace['source_width'] or trace['frame_height']!=trace['source_height']):
                    raise RuntimeError('The query was cropped or used the wrong reference policy')
        elif answer.get('error') not in DETECTION_ERRORS or a.mode=='parity':
            raise RuntimeError(f'Unexpected device error: HTTP {status}: {answer}')
        return record
    try:
        if adb('shell','am','get-current-user')!='0':raise RuntimeError('Require original Android user 0')
        if 'DEBUGGABLE' not in adb('shell','dumpsys','package',PACKAGE):raise RuntimeError('Require isolated debug APK')
        initial_pid=pid();meta['initial_pid']=initial_pid
        if initial_pid is None:raise RuntimeError('Test app is not running')
        if a.resume_from and initial_pid!=meta['resume']['original_run']['initial_pid']:
            raise RuntimeError('Resume requires the unchanged Pixel process')
        apk=adb('shell','pm','path',PACKAGE).removeprefix('package:')
        if adb('shell','sha256sum',apk).split()[0]!=a.apk_sha256:raise RuntimeError('Installed APK changed')
        if adb('shell','run-as',PACKAGE,'sha256sum','files/bench/manifest.json').split()[0]!=meta['pack_manifest_sha256']:
            raise RuntimeError('Private pack changed')
        forwards=[r for r in adb('forward','--list').splitlines() if ' tcp:18088 ' in r]
        if forwards and forwards!=[f'{a.serial} tcp:18088 tcp:18088']:raise RuntimeError('USB port conflict')
        if not forwards:adb('forward','tcp:18088','tcp:18088');forward=True
        meta['health_before']=require_state();save(a.out/'run.json',meta)
        original_power=adb('shell','settings','get','global','stay_on_while_plugged_in')
        adb('shell','settings','put','global','stay_on_while_plugged_in','15')
        log_stream=(a.out/'logcat.txt').open('w')
        log=subprocess.Popen([ADB,'-s',a.serial,'logcat','-v','threadtime','-T','1',
            'OfflineBench:V','AndroidRuntime:V','libc:V','DEBUG:V','LiteRtClGlAccelerator:V','*:S'],stdout=log_stream,stderr=subprocess.STDOUT)
        def sample():
            while not stop.is_set():
                try:
                    memory=re.search(r'TOTAL PSS:\s*(\d+)',adb('shell','dumpsys','meminfo',PACKAGE))
                    thermal=re.search(r'Thermal Status:\s*(\d+)',adb('shell','dumpsys','thermalservice'))
                    battery=re.search(r'temperature:\s*(\d+)',adb('shell','dumpsys','battery'))
                    if not all((memory,thermal,battery)):raise RuntimeError('Required telemetry is unavailable')
                    row=dict(elapsed_s=time.monotonic()-start,pss_kib=int(memory[1]),
                        thermal_status=int(thermal[1]),battery_celsius=int(battery[1])/10)
                    samples.append(row);append(a.out/'telemetry.jsonl',row)
                except Exception as error:
                    samples.append(dict(thermal_status=4,error=repr(error)))
                    append(a.out/'telemetry.jsonl',samples[-1]);return
                stop.wait(15)
        sampler=threading.Thread(target=sample,daemon=True);sampler.start()
        save(a.out/'warmup.json',request(rows[0],'GPU',0,True))
        jobs=[(r,accel) for accel in ('GPU','CPU','GPU') for r in rows] if a.mode=='parity' else [(r,'GPU') for r in rows]
        for number,(row,accelerator) in enumerate(jobs[resumed:],resumed+1):
            record=request(row,accelerator,number);append(a.out/'responses.jsonl',record);meta['requests']=number
            answer=record['response'];ok=record['status']==200
            if not ok:meta['errors']+=1
            if a.mode!='parity':
                result=answer['variants'][0] if ok else dict(slug=None,candidates=[])
                append(a.out/'predictions.jsonl',dict(query_id=row['query_id'],image_path=row['image_path'],
                    image_sha256=row['image_sha256'],predicted_slug=result['slug'],candidates=result['candidates'],
                    error=None if ok else answer['error'],client_request_ms=record['client_ms'],
                    pipeline_ms=answer.get('latency_ms'),timing_mode='independent'))
                # Failures remain in complete-pipeline timing and quality denominators.
                timings.append(record['client_ms'])
            else:
                archive=a.out/f'capture-{number:02d}.tar';destination=a.out/f'capture-{number:02d}';destination.mkdir()
                with archive.open('wb') as stream:
                    subprocess.run([ADB,'-s',a.serial,'exec-out','run-as',PACKAGE,'tar','-cf','-',
                        '-C','files/bench-diagnostics','.'],stdout=stream,check=True,timeout=120)
                with tarfile.open(archive) as packed:packed.extractall(destination,filter='data')
            save(a.out/'run.json',meta)
            if number==1 or number%10==0:print(f'{condition["name"]}: {number}/{len(jobs)}; errors={meta["errors"]}; {record["client_ms"]:.0f} ms',flush=True)
        meta['health_after']=require_state();meta['complete']=True
    except BaseException as error:
        meta['failure']=repr(error);print('Stopped:',repr(error),flush=True)
    finally:
        stop.set();cleanup=[]
        def safely(action):
            try:return action()
            except Exception as error:cleanup.append(repr(error))
        if sampler:safely(lambda:sampler.join(timeout=45))
        if log:safely(log.terminate);safely(lambda:log.wait(timeout=10))
        if log_stream:log_stream.close()
        if original_power is not None:safely(lambda:adb('shell','settings','put','global','stay_on_while_plugged_in',original_power))
        if forward:safely(lambda:adb('forward','--remove','tcp:18088'))
        all_samples=inherited_samples+samples
        if a.resume_from:
            safely(lambda:verify_preserved(a.resume_from,a.out,meta['resume']))
        meta.update(elapsed_s=time.monotonic()-start,cleanup_errors=cleanup,final_pid=safely(pid),
            client_median_ms=statistics.median(timings) if timings else None,client_p95_ms=percentile(timings,.95),
            peak_sampled_pss_kib=max((s.get('pss_kib',0) for s in all_samples),default=0),
            maximum_thermal_status=max((s.get('thermal_status',0) for s in all_samples),default=0))
        if cleanup:meta['complete']=False
        save(a.out/'run.json',meta)
    return 0 if meta['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
