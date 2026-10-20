"""Run one finite continuation, then the frozen four-condition comparison."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);a=p.parse_args()
    config=json.loads(a.config.read_text());root=a.config.parent
    status=dict(complete=False,state='preflight',started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        full_run=config['full_out'],comparison=config['comparison_out'],reranking=False,barcode=False)
    def save():
        temporary=root/'status.tmp';temporary.write_text(json.dumps(status,indent=2)+'\n');temporary.replace(root/'status.json')
    def adb(*parts):
        return subprocess.check_output([ADB,'-s',config['serial'],*parts],text=True,timeout=45).strip()
    def run(command):
        print('Starting:',command[2],flush=True)
        result=subprocess.run(command)
        if result.returncode:raise RuntimeError(f'Workflow stage exited {result.returncode}: {command[2]}')
    save()
    try:
        for name,expected in config['source_sha256'].items():
            with Path(name).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=expected:raise RuntimeError('Frozen source changed: '+name)
        if adb('shell','am','get-current-user')!='0':raise RuntimeError('Android user changed')
        if adb('shell','pidof','com.alolalab.chtozavino.offlinebench')!='9424':raise RuntimeError('Pixel process changed')
        if Path(config['full_out']).exists() or Path(config['comparison_out']).exists():
            raise RuntimeError('Refuse to overwrite an existing attempt')
        # Transfer the abandoned forward to the new runner. It must own its cleanup.
        expected=f'{config["serial"]} tcp:18088 tcp:18088'
        forwards=[line for line in adb('forward','--list').splitlines() if ' tcp:18088 ' in line]
        if forwards and forwards!=[expected]:raise RuntimeError('USB forward belongs to another target')
        if forwards:adb('forward','--remove','tcp:18088')
        status['state']='resuming-full-from-537';save()
        full=Path(config['full_tools'])/'run_full_benchmark.py'
        run([sys.executable,'-u',str(full),'--serial',config['serial'],'--queries',config['queries'],
            '--pack-manifest',config['pack_manifest'],'--out',config['full_out'],
            '--resume-from',config['recovery'],'--expected-apk-sha256',config['expected_apk_sha256']])
        # The frozen comparison independently checks completion, audit, and cleanup.
        status['state']='four-condition-comparison';save()
        comparison=Path(config['comparison_tools'])/'run_comparison.py'
        run([sys.executable,'-u',str(comparison),'--after',config['full_out'],'--serial',config['serial'],
            '--queries',config['queries'],'--pack',config['comparison_pack'],'--apk',config['comparison_apk'],
            '--out',config['comparison_out']])
        status.update(complete=True,state='complete')
    except BaseException as error:
        status.update(state='stopped',failure=repr(error));print('Workflow stopped:',repr(error),flush=True)
    finally:
        status['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save()
    return 0 if status['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
