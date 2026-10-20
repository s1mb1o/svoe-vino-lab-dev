"""Run finite, isolated DIS 768/512 numerical, pilot, and full device blocks."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tarfile
import time

PACKAGE='com.alolalab.chtozavino.disresbench'
ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def launch(config,values):
    root=config.parent;record=root/'detached-launch.json'
    if Path(values['out']).exists():raise ValueError('Preserve existing attempts')
    with record.open('x') as stream:json.dump(dict(state='starting'),stream)
    first=os.fork()
    if first:
        _,status=os.waitpid(first,0)
        if status:raise RuntimeError('Detached launch failed')
        print(record);return
    os.setsid();signal.signal(signal.SIGHUP,signal.SIG_IGN)
    if os.fork():os._exit(0)
    os.chdir(root)
    with open(os.devnull,'rb') as incoming,(root/'workflow.log').open('ab',buffering=0) as out,(root/'workflow-errors.log').open('ab',buffering=0) as err:
        os.dup2(incoming.fileno(),0);os.dup2(out.fileno(),1);os.dup2(err.fileno(),2)
    command=['/usr/bin/caffeinate','-i',sys.executable,'-u',str(Path(__file__).resolve()),'--config',str(config)]
    save(record,dict(pid=os.getpid(),started_at=dt.datetime.now(dt.timezone.utc).isoformat(),command=command,
        lifecycle='double fork; separate session; SIGHUP ignored; no restart policy'))
    os.execve(command[0],command,dict(os.environ,BASE_POOLING_PACKAGE=PACKAGE,PYTHONDONTWRITEBYTECODE='1'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--launch',action='store_true');args=parser.parse_args()
    config=args.config.resolve();values=json.loads(config.read_text());root=config.parent
    if args.launch:return launch(config,values)
    if os.environ.get('BASE_POOLING_PACKAGE')!=PACKAGE:raise ValueError('Require the isolated resolution package')
    tools=Path(values['tools']);sys.path.insert(0,str(tools))
    from profiles import digest
    from audit_results import audit
    out=Path(values['out']);out.mkdir(parents=True,exist_ok=False)
    status=dict(complete=False,state='preflight',started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        reranking=False,barcode=False,conditions={});installed=False;http=False
    def update():save(out/'status.json',status)
    def adb(*parts,check=True,timeout=45):
        result=subprocess.run([ADB,'-s',values['serial'],*parts],capture_output=True,text=True,timeout=timeout)
        if check and result.returncode:raise RuntimeError(result.stderr or result.stdout)
        return result.stdout.strip()
    def run(script,*parts):
        result=subprocess.run([sys.executable,'-u',str(tools/script),*map(str,parts)])
        if result.returncode:raise RuntimeError(f'{script} exited {result.returncode}')
    def switch(on):
        nonlocal http
        run('set_http.py','--serial',values['serial'],on);http=on=='on'
    def stop_app():
        if http:switch('off')
        adb('shell','am','force-stop','--user','0',PACKAGE)
        if adb('shell','pidof',PACKAGE,check=False):raise RuntimeError('Isolated process did not stop')
    def cooling():
        deadline=time.monotonic()+3600
        while True:
            if adb('shell','am','get-current-user')!='0':raise RuntimeError('Require Android user 0')
            thermal=re.search(r'Thermal Status:\s*(\d+)',adb('shell','dumpsys','thermalservice'))
            battery=re.search(r'temperature:\s*(\d+)',adb('shell','dumpsys','battery'))
            if not thermal or not battery:raise RuntimeError('Telemetry missing')
            status['cooling']=dict(thermal_status=int(thermal[1]),battery_celsius=int(battery[1])/10);update()
            if int(thermal[1])>=4:raise RuntimeError('CRITICAL thermal status')
            if int(thermal[1])<=2 and int(battery[1])<=400:return
            if time.monotonic()>deadline:raise RuntimeError('Cooling timed out')
            time.sleep(30)
    def verify_private(pack):
        manifest=json.loads((pack/'manifest.json').read_text())
        expected={'manifest.json':dict(sha256=digest(pack/'manifest.json')),**manifest['files']}
        for name,row in expected.items():
            if adb('shell','run-as',PACKAGE,'sha256sum','files/bench/'+name).split()[0]!=row['sha256']:
                raise RuntimeError('Private payload changed: '+name)
    update()
    try:
        for path,expected in values['source_sha256'].items():
            if digest(Path(path))!=expected:raise RuntimeError('Frozen source changed: '+path)
        baseline=Path(values['baseline']);baseline_pack=Path(values['baseline_pack'])
        baseline_result=audit(baseline,baseline_pack)
        if baseline_result['assignments']!=668:raise RuntimeError('Incomplete DIS 1024 baseline')
        cleanup=json.loads(Path(values['preceding_status']).read_text())
        if not cleanup['complete'] or cleanup['cleanup']!=dict(http_off=True,final_pid=None):
            raise RuntimeError('Previous DIS workflow did not clean up')
        agreement=json.loads(Path(values['production_agreement']).read_text())
        if not agreement['passed'] or agreement['same_top1']!=668:raise RuntimeError('Production control was not reproduced')
        query_sha=digest(Path(values['queries']))
        if query_sha!=baseline_result['query_file_sha256']:raise RuntimeError('Query assignment file changed')
        previous=json.loads((baseline_pack/'manifest.json').read_text());old_condition=next(c for c in previous['conditions'] if c['number']==8)
        for entry in values['packs']:
            pack=Path(entry['path']);manifest=json.loads((pack/'manifest.json').read_text())
            if digest(pack/'manifest.json')!=entry['sha256']:raise RuntimeError('Pack manifest changed')
            for name,row in manifest['files'].items():
                if digest(pack/name)!=row['sha256']:raise RuntimeError('Prepared pack payload changed')
            condition=next(c for c in manifest['conditions'] if c['number']==8)
            if (manifest['slugs']!=previous['slugs'] or condition['model_sha256']!=old_condition['model_sha256'] or
                condition['effective_profile']!=old_condition['effective_profile'] or
                digest(pack/condition['vectors'])!=digest(baseline_pack/old_condition['vectors']) or
                condition['dis_input_size']!=entry['size'] or manifest['reranking'] or manifest['barcode']):
                raise RuntimeError('Encoder, references, or optional recognition changed')
        if digest(Path(values['apk']))!=values['apk_sha256']:raise RuntimeError('APK changed')
        for other in ('com.alolalab.chtozavino.offlinebench','com.alolalab.chtozavino.basepoolbench',
            'com.alolalab.chtozavino.fullpoolbench','com.alolalab.chtozavino.dispoolbench',PACKAGE,'com.alolalab.chtozavino'):
            if adb('shell','pidof',other,check=False):raise RuntimeError('Another wine application is running: '+other)
        if any(' tcp:18088 ' in line for line in adb('forward','--list').splitlines()):raise RuntimeError('USB forward is owned')
        if adb('shell','pm','path',PACKAGE,check=False).startswith('package:'):raise RuntimeError('Preserve the existing resolution application')
        available=int(adb('shell','df','-k','/data').splitlines()[-1].split()[3])*1024
        if available<4*1024**3:raise RuntimeError('Require at least 4 GiB free storage')
        status['state']='installing-isolated-package';update()
        adb('install',values['apk'],timeout=240);installed=True
        apk_path=adb('shell','pm','path',PACKAGE).removeprefix('package:')
        if adb('shell','sha256sum',apk_path).split()[0]!=values['apk_sha256']:raise RuntimeError('Installed APK changed')
        results={'1024':baseline_result};previous_pack=None
        for entry in values['packs']:
            size=entry['size'];pack=Path(entry['path']);directory=out/f'dis-{size}';directory.mkdir()
            status['conditions'][str(size)]={'gate':'pending'}
            status['state']=f'dis-{size}-staging';update()
            if previous_pack is not None:
                verify_private(previous_pack)
                adb('shell','run-as',PACKAGE,'mv','files/bench',f'files/bench-preserved-dis{previous_size}')
            archive=directory/'pack.tar'
            with tarfile.open(archive,'w') as tar:
                for path in sorted(pack.iterdir()):
                    if not path.is_file():raise ValueError('Unexpected pack directory')
                    tar.add(path,arcname='bench/'+path.name)
            adb('shell','run-as',PACKAGE,'mkdir','-p','files')
            with archive.open('rb') as stream:
                subprocess.run([ADB,'-s',values['serial'],'shell','-T','run-as',PACKAGE,'tar','-xf','-','-C','files'],
                    stdin=stream,check=True,timeout=300)
            verify_private(pack);previous_pack=pack;previous_size=size
            run('set_http.py','--serial',values['serial'],'--require-current','off');switch('on')
            common=['--serial',values['serial'],'--queries',values['queries'],'--pack',pack,
                '--apk-sha256',values['apk_sha256'],'--condition','8']
            status['state']=f'dis-{size}-parity';update();cooling()
            run('run_device.py',*common,'--mode','parity','--out',directory/'parity')
            validation=subprocess.run([sys.executable,'-u',str(tools/'validate_device.py'),
                '--run',str(directory/'parity'),'--pack',str(pack)])
            if validation.returncode:
                report=directory/'parity/numerical-validation.json'
                if not report.exists() or json.loads(report.read_text())['passed']:
                    raise RuntimeError('Numerical validator failed without a completed failed gate')
                status['conditions'][str(size)]={'gate':'failed-numerical'};update();stop_app();continue
            status['state']=f'dis-{size}-pilot';update();cooling()
            run('run_device.py',*common,'--mode','pilot','--out',directory/'pilot')
            pilot=audit(directory/'pilot',pack);save(directory/'pilot/independent-audit.json',pilot)
            if not pilot['smoothness_passed']:
                status['conditions'][str(size)]={'gate':'failed-smoothness'};update();stop_app();continue
            status['conditions'][str(size)]={'gate':'passed'}
            status['state']=f'dis-{size}-full';update();cooling()
            run('run_device.py',*common,'--mode','full','--out',directory/'full')
            result=audit(directory/'full',pack);save(directory/'full/independent-audit.json',result);results[str(size)]=result
            status['conditions'][str(size)]['full']='complete';update();stop_app()
        comparisons={}
        for size,result in results.items():
            if size=='1024':continue
            gains=[q for q in result['outcomes'] if result['outcomes'][q]['1'] and not baseline_result['outcomes'][q]['1']]
            losses=[q for q in result['outcomes'] if baseline_result['outcomes'][q]['1'] and not result['outcomes'][q]['1']]
            comparisons[size]=dict(top1_gain_pp=result['top_k_percent']['1']-baseline_result['top_k_percent']['1'],gains=gains,regressions=losses,
                median_ratio=result['client_median_ms']/baseline_result['client_median_ms'])
        save(out/'comparison.json',dict(complete=True,results=results,versus_1024=comparisons,reranking=False,barcode=False))
        lines=['# DIS input-resolution comparison','',
            'All scores use 668 frozen assignments and accepted alternatives. Re-ranking remains off.','',
            '| DIS input | Top-1 | Top-5 | Top-10 | Median, ms | P95, ms | Errors |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for size,result in results.items():
            quality=result['top_k_percent']
            lines.append(f'| {size} | {quality["1"]:.2f}% | {quality["5"]:.2f}% | {quality["10"]:.2f}% | '
                f'{result["client_median_ms"]:.1f} | {result["client_p95_ms"]:.1f} | {result["errors"]} |')
        lines+=['','Read status.json for pilot exclusions. The 1024 cohort required USB continuation.',
            'The production application and all previous artifacts remain unchanged.']
        (out/'report.md').write_text('\n'.join(lines)+'\n');status.update(complete=True,state='complete')
    except BaseException as error:
        status.update(state='stopped',failure=repr(error));print('Stopped:',repr(error),flush=True)
    finally:
        cleanup={}
        if installed:
            try:
                if http:switch('off')
                cleanup['http_off']=True
            except Exception as error:cleanup['switch_error']=repr(error)
            try:
                adb('shell','am','force-stop','--user','0',PACKAGE)
                cleanup['final_pid']=adb('shell','pidof',PACKAGE,check=False) or None
            except Exception as error:cleanup['stop_error']=repr(error)
        status['cleanup']=cleanup
        if any(k.endswith('_error') for k in cleanup) or cleanup.get('final_pid'):status['complete']=False
        status['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();update()
    return 0 if status['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
