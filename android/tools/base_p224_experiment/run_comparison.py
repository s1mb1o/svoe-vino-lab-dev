"""Wait for the existing benchmark, then run a finite gated Base comparison."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time

from profiles import PACKAGE,digest
from run_device import ADB


def prerequisite(after):
    cleanup=after/'coordinator-cleanup.json'
    if not cleanup.exists():return False
    run=json.loads((after/'run.json').read_text());audit=json.loads((after/'independent-audit.json').read_text())
    row=json.loads(cleanup.read_text())
    if (not run['complete'] or not audit['verification_passed'] or not audit['complete'] or
        row['runner_exit_code'] or row['audit_exit_code'] or row.get('switch_exit_code')!=0 or
        row.get('switch_error') or row.get('cleanup_error') or row.get('final_pid')):
        raise RuntimeError('The preceding benchmark did not finish and clean up successfully. Do not use the phone.')
    return True


def paired(results):
    output={}
    for left,right in ((1,2),(3,4),(1,3),(2,4),(1,4),(2,3),(5,6),(5,7),(5,8),(7,8)):
        if left not in results or right not in results:continue
        a,b=results[left],results[right]
        if (a['query_file_sha256']!=b['query_file_sha256'] or a['pack_manifest_sha256']!=b['pack_manifest_sha256'] or
            a['outcomes'].keys()!=b['outcomes'].keys()):raise ValueError('Unpaired comparison')
        wins=[];losses=[]
        for identity in a['outcomes']:
            x,y=a['outcomes'][identity]['1'],b['outcomes'][identity]['1']
            if y and not x:wins.append(identity)
            if x and not y:losses.append(identity)
        output[f'{left}-to-{right}']=dict(top1_gain_pp=b['top_k_percent']['1']-a['top_k_percent']['1'],
            gains=wins,regressions=losses)
    return output


def require_known_replacement(package,actual,expected):
    if (package not in ('com.alolalab.chtozavino.fullpoolbench','com.alolalab.chtozavino.dispoolbench') or
        not expected or not re.fullmatch('[0-9a-f]{64}',expected) or actual!=expected):
        raise RuntimeError('Preserve the installed package: replacement identity is not authorized')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('after','pack','queries','apk','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--serial',required=True)
    p.add_argument('--conditions',nargs='+',type=int,choices=range(1,9),default=[1,2,3,4])
    p.add_argument('--baseline',type=Path)
    p.add_argument('--replace-apk-sha256',help='Require this exact installed isolated APK before an update')
    a=p.parse_args()
    if len(set(a.conditions))!=len(a.conditions):raise ValueError('Duplicate condition')
    if any(n in (6,7,8) for n in a.conditions) and 5 not in a.conditions:
        raise ValueError('Custom conditions require the repeated standard control')
    if 5 in a.conditions and a.baseline is None:raise ValueError('Require the production baseline')
    a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    status=dict(complete=False,state='waiting-for-existing-full-benchmark',
        started_at=dt.datetime.now(dt.timezone.utc).isoformat(),after=str(a.after),
        apk_sha256=digest(a.apk),pack_manifest_sha256=digest(a.pack/'manifest.json'),
        queries_sha256=digest(a.queries),reranking=False,barcode=False,conditions={})
    def save():
        (a.out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    def adb(*parts,check=True,timeout=45):
        r=subprocess.run([ADB,'-s',a.serial,*parts],capture_output=True,text=True,timeout=timeout)
        if check and r.returncode:raise RuntimeError(r.stderr or r.stdout)
        return r.stdout.strip()
    def run(script,*parts):
        return subprocess.run([sys.executable,'-u',str(root/script),*map(str,parts)],check=True)
    def cooling():
        deadline=time.monotonic()+3600
        while True:
            if adb('shell','am','get-current-user')!='0':raise RuntimeError('Android user changed')
            thermal=re.search(r'Thermal Status:\s*(\d+)',adb('shell','dumpsys','thermalservice'))
            battery=re.search(r'temperature:\s*(\d+)',adb('shell','dumpsys','battery'))
            if not thermal or not battery:raise RuntimeError('Cooling telemetry is unavailable')
            status['cooling']=dict(thermal_status=int(thermal[1]),battery_celsius=int(battery[1])/10);save()
            if int(thermal[1])<=2 and int(battery[1])<=400:return
            if time.monotonic()>deadline:raise RuntimeError('Phone did not cool within one hour')
            time.sleep(30)
    def switch(state):run('set_http.py','--serial',a.serial,state)
    def verify_private_pack(pack):
        if adb('shell','run-as',PACKAGE,'sha256sum','files/bench/manifest.json').split()[0]!=status['pack_manifest_sha256']:
            raise RuntimeError('Private pack manifest changed')
        for name,row in pack['files'].items():
            if adb('shell','run-as',PACKAGE,'sha256sum','files/bench/'+name).split()[0]!=row['sha256']:
                raise RuntimeError('Private pack payload changed')
    installed=False;save()
    try:
        # Read local evidence only. Do not use ADB while the preceding run is active.
        deadline=time.monotonic()+12*3600
        while not prerequisite(a.after):
            if time.monotonic()>deadline:raise RuntimeError('Preceding run is still incomplete after twelve hours')
            time.sleep(30)
        if adb('shell','pidof','com.alolalab.chtozavino.offlinebench',check=False):
            raise RuntimeError('The preceding benchmark process is still present')
        if adb('shell','pidof',PACKAGE,check=False):raise RuntimeError('A Base comparison process is already present')
        if any(' tcp:18088 ' in r for r in adb('forward','--list').splitlines()):raise RuntimeError('USB port is still owned')
        if digest(a.apk)!=status['apk_sha256'] or digest(a.pack/'manifest.json')!=status['pack_manifest_sha256']:
            raise RuntimeError('Prepared inputs changed while waiting')
        pack=json.loads((a.pack/'manifest.json').read_text())
        for name,row in pack['files'].items():
            if digest(a.pack/name)!=row['sha256']:raise RuntimeError('Pack payload changed')
        if PACKAGE=='com.alolalab.chtozavino.dispoolbench':
            for other in ('com.alolalab.chtozavino.fullpoolbench','com.alolalab.chtozavino.basepoolbench',
                          'com.alolalab.chtozavino.dualgpu','com.alolalab.chtozavino'):
                if adb('shell','pidof',other,check=False):raise RuntimeError('Another wine application is running: '+other)
        status['state']='cooling-before-install';save();cooling()
        existing=adb('shell','pm','path',PACKAGE,check=False)
        if existing.startswith('package:'):
            old_sha=adb('shell','sha256sum',existing.removeprefix('package:')).split()[0]
            require_known_replacement(PACKAGE,old_sha,a.replace_apk_sha256)
            verify_private_pack(pack)
            status['preserved_previous_apk_sha256']=old_sha;status['reused_private_pack']=True;save()
        elif a.replace_apk_sha256:
            raise RuntimeError('Expected installed isolated APK is absent')
        available=int(adb('shell','df','-k','/data').splitlines()[-1].split()[3])*1024
        required=2*sum(row['bytes'] for row in pack['files'].values())+2*a.apk.stat().st_size+300*1024**2
        if available<required:raise RuntimeError('Insufficient device storage for the isolated pack and safe staging')
        status['state']='installing-isolated-package';save()
        adb('install',*(['-r'] if existing.startswith('package:') else []),str(a.apk),timeout=240);installed=True
        installed_path=adb('shell','pm','path',PACKAGE).removeprefix('package:')
        if adb('shell','sha256sum',installed_path).split()[0]!=status['apk_sha256']:
            raise RuntimeError('Installed APK identity changed')
        # The archive contains only the checked pack. No query image, mask, or answer is sent.
        if not existing.startswith('package:'):
            archive=a.out/'pack.tar'
            with tarfile.open(archive,'w') as tar:
                for path in sorted(a.pack.iterdir()):
                    if not path.is_file():raise ValueError('Unexpected pack directory')
                    tar.add(path,arcname='bench/'+path.name)
            adb('shell','run-as',PACKAGE,'mkdir','-p','files')
            with archive.open('rb') as stream:
                subprocess.run([ADB,'-s',a.serial,'shell','-T','run-as',PACKAGE,'tar','-xf','-','-C','files'],
                    stdin=stream,check=True,timeout=300)
        verify_private_pack(pack)
        # Verify default-off state before explicit enablement.
        run('set_http.py','--serial',a.serial,'--require-current','off');switch('on')
        eligible=[]
        for number in a.conditions:
            status['state']=f'condition-{number}-parity';save();cooling()
            common=['--serial',a.serial,'--queries',a.queries,'--pack',a.pack,'--apk-sha256',status['apk_sha256'],'--condition',number]
            directory=a.out/f'condition-{number}-parity'
            try:
                run('run_device.py',*common,'--mode','parity','--out',directory)
                run('validate_device.py','--run',directory,'--pack',a.pack,
                    *(['--baseline',a.baseline] if a.baseline else []))
            except subprocess.CalledProcessError:
                # A failed gate stops the campaign. Do not hide a possible native failure.
                status['conditions'][str(number)]={'gate':'failed-numerical'};save();raise
            status['state']=f'condition-{number}-pilot';save();cooling()
            directory=a.out/f'condition-{number}-pilot'
            run('run_device.py',*common,'--mode','pilot','--out',directory)
            run('audit_results.py','--run',directory,'--pack',a.pack)
            audit=json.loads((directory/'independent-audit.json').read_text())
            status['conditions'][str(number)]={'gate':'passed' if audit['smoothness_passed'] else 'failed-smoothness'};save()
            if audit['smoothness_passed']:eligible.append(number)
        if any(n>=6 for n in eligible) and 5 in a.conditions and 5 not in eligible:
            raise RuntimeError('Custom full runs require an eligible standard control')
        results={}
        for number in eligible:
            status['state']=f'condition-{number}-full';save();cooling()
            directory=a.out/f'condition-{number}-full'
            run('run_device.py','--serial',a.serial,'--queries',a.queries,'--pack',a.pack,'--apk-sha256',status['apk_sha256'],
                '--condition',number,'--mode','full','--out',directory)
            run('audit_results.py','--run',directory,'--pack',a.pack)
            results[number]=json.loads((directory/'independent-audit.json').read_text())
            if number==5:
                previous={r['query_id']:r for r in map(json.loads,(a.baseline/'predictions.jsonl').read_text().splitlines())}
                actual=list(map(json.loads,(directory/'predictions.jsonl').read_text().splitlines()))
                if len(actual)!=len(previous) or any(previous[r['query_id']]['predicted_slug']!=r['predicted_slug'] for r in actual):
                    raise RuntimeError('The full control does not reproduce every production-control Top-1')
                (directory/'production-control-agreement.json').write_text(json.dumps(dict(
                    passed=True,assignments=len(actual),same_top1=len(actual),
                    baseline_predictions_sha256=digest(a.baseline/'predictions.jsonl')),indent=2)+'\n')
            status['conditions'][str(number)]['full']='complete';save()
        report=dict(complete=True,results={n:{k:v for k,v in r.items() if k!='outcomes'} for n,r in results.items()},
            paired=paired(results),production_default_changed=False,reranking=False,barcode=False)
        (a.out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
        lines=['# Base NaFlex Pixel comparison','',
            'All quality scores use all 668 assignments and accepted alternative slugs.',
            'Segmentation failures remain in the denominator. Re-ranking and barcode stay disabled.',
            'The production default remains unchanged.','',
            '| Condition | Top-1 | Top-5 | Top-10 | Errors | Median, ms | P95, ms |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for number,result in results.items():
            values=result['top_k_percent']
            lines.append(f'| {result["condition"]} | {values["1"]:.2f}% | {values["5"]:.2f}% | {values["10"]:.2f}% | '
                f'{result["errors"]} | {result["client_median_ms"]:.1f} | {result["client_p95_ms"]:.1f} |')
        lines+=['','Read `status.json` for conditions excluded by a pilot gate.',
            'Read `comparison.json` for paired gains and regressions.']
        (a.out/'report.md').write_text('\n'.join(lines)+'\n')
        status.update(complete=True,state='complete',full_conditions=eligible)
    except BaseException as error:
        status.update(state='stopped',failure=repr(error));print('Comparison stopped:',repr(error),flush=True)
    finally:
        if installed:
            cleanup={}
            try:switch('off');cleanup['http_off']=True
            except Exception as error:cleanup['switch_error']=repr(error)
            try:
                adb('shell','am','force-stop','--user','0',PACKAGE)
                cleanup['final_pid']=adb('shell','pidof',PACKAGE,check=False) or None
            except Exception as error:cleanup['stop_error']=repr(error)
            status['cleanup']=cleanup
            if cleanup.get('switch_error') or cleanup.get('stop_error') or cleanup.get('final_pid'):status['complete']=False
        status['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save()
    return 0 if status['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
