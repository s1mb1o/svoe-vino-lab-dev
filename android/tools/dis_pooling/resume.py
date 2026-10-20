"""Launch one finite same-process DIS continuation. Never restart automatically."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

PACKAGE='com.alolalab.chtozavino.dispoolbench'
ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def launch(config,values):
    root=config.parent;record=root/'detached-launch.json'
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
    save(record,dict(state='launched',pid=os.getpid(),started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        command=command,launcher='double fork; separate session; SIGHUP ignored; no restart policy'))
    os.execve(command[0],command,dict(os.environ,BASE_POOLING_PACKAGE=PACKAGE))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--launch',action='store_true');args=parser.parse_args()
    config=args.config.resolve();values=json.loads(config.read_text());root=config.parent
    if args.launch:
        if Path(values['out']).exists():raise ValueError('Preserve the existing attempt')
        return launch(config,values)
    if os.environ.get('BASE_POOLING_PACKAGE')!=PACKAGE:raise ValueError('Require the isolated DIS package')
    tools=Path(values['tools']);sys.path.insert(0,str(tools))
    from audit_results import audit
    from run_comparison import paired
    sys.path.insert(0,str(tools.parent/'offline_benchmark'))
    from usb_http import UsbHttp
    state=dict(complete=False,state='preflight',started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        out=values['out'],reranking=False,barcode=False)
    owned=False;forward=False
    def update():save(root/'status.json',state)
    def adb(*parts,check=True):
        result=subprocess.run([ADB,'-s',values['serial'],*parts],capture_output=True,text=True,timeout=45)
        if check and result.returncode:raise RuntimeError(result.stderr or result.stdout)
        return result.stdout.strip()
    def run(command):
        result=subprocess.run([sys.executable,'-u',*map(str,command)])
        if result.returncode:raise RuntimeError('Workflow stage failed: '+str(command))
    update()
    try:
        for path,expected in values['source_sha256'].items():
            with Path(path).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=expected:raise RuntimeError('Frozen source changed: '+path)
        if Path(values['out']).exists():raise ValueError('Preserve the existing attempt')
        if adb('shell','am','get-current-user')!='0':raise RuntimeError('Require Android user 0')
        if adb('shell','pidof',PACKAGE)!=str(values['expected_pid']):raise RuntimeError('Pixel process changed')
        apk=adb('shell','pm','path',PACKAGE).removeprefix('package:')
        if adb('shell','sha256sum',apk).split()[0]!=values['apk_sha256']:raise RuntimeError('Installed APK changed')
        if adb('shell','run-as',PACKAGE,'sha256sum','files/bench/manifest.json').split()[0]!=values['pack_sha256']:
            raise RuntimeError('Private pack changed')
        forwards=[r for r in adb('forward','--list').splitlines() if ' tcp:18088 ' in r]
        if forwards:raise RuntimeError('Require no existing USB forward on 18088')
        adb('forward','tcp:18088','tcp:18088');forward=True;health=UsbHttp().health()
        if (health.get('pid')!=values['expected_pid'] or health.get('active') or not health.get('pack_present') or
            not health.get('foreground_service') or not health.get('wake_lock_held') or
            health.get('process_importance',1000)>125 or health.get('reranking') is not False or
            health.get('barcode') is not False):raise RuntimeError('Invalid protected HTTP state')
        owned=True;state['health_before']=health
        deadline=time.monotonic()+3600;state['state']='cooling';update()
        while True:
            thermal=re.search(r'Thermal Status:\s*(\d+)',adb('shell','dumpsys','thermalservice'))
            battery=re.search(r'temperature:\s*(\d+)',adb('shell','dumpsys','battery'))
            if not thermal or not battery:raise RuntimeError('Missing thermal telemetry')
            state['cooling']=dict(thermal_status=int(thermal[1]),battery_celsius=int(battery[1])/10);update()
            if int(thermal[1])>=4:raise RuntimeError('CRITICAL thermal status')
            if int(thermal[1])<=2 and int(battery[1])<=400:break
            if time.monotonic()>deadline:raise RuntimeError('Cooling timed out')
            time.sleep(30)
        adb('forward','--remove','tcp:18088');forward=False
        state['state']='resuming-condition-8-from-191';update()
        run([tools/'run_device.py','--serial',values['serial'],'--queries',values['queries'],
            '--pack',values['pack'],'--apk-sha256',values['apk_sha256'],'--condition','8','--mode','full',
            '--resume-from',values['resume_from'],'--expected-resume-records','190','--out',values['out']])
        state['state']='independent-audit';update();results={}
        for number,path in ((5,values['control']),(7,values['full_image']),(8,values['out'])):
            result=audit(Path(path),Path(values['pack']));results[number]=result
            if number==8:save(Path(path)/'independent-audit.json',result)
        save(root/'comparison.json',dict(results={str(n):r for n,r in results.items()},paired=paired(results)))
        state.update(complete=True,state='complete')
    except BaseException as error:
        state.update(state='stopped',failure=repr(error));print('Stopped:',repr(error),flush=True)
    finally:
        cleanup={}
        if forward:
            try:adb('forward','--remove','tcp:18088')
            except Exception as error:cleanup['forward_error']=repr(error)
        if owned:
            try:run([tools/'set_http.py','--serial',values['serial'],'off']);cleanup['http_off']=True
            except Exception as error:cleanup['switch_error']=repr(error)
            try:
                adb('shell','am','force-stop','--user','0',PACKAGE);cleanup['final_pid']=adb('shell','pidof',PACKAGE,check=False) or None
            except Exception as error:cleanup['stop_error']=repr(error)
        state['cleanup']=cleanup
        if any(k.endswith('_error') for k in cleanup) or cleanup.get('final_pid'):state['complete']=False
        state['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();update()
    return 0 if state['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
