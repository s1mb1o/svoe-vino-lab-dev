#!/usr/bin/env python3
"""Run one finite full cohort, audit saved outputs, and stop only its debug app."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from run_device import ADB,PACKAGE
from run_control import save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--queries',type=Path,required=True)
    parser.add_argument('--pack-manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--resume-from',type=Path)
    parser.add_argument('--expected-apk-sha256')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    assert not args.out.exists(),'Use a new output directory'
    command=[sys.executable,'-u',str(root/'run_device.py'),'--serial',args.serial,
        '--queries',str(args.queries),'--pack-manifest',str(args.pack_manifest),
        '--out',str(args.out),'--mode','full']
    if args.resume_from:command+=['--resume-from',str(args.resume_from)]
    if args.expected_apk_sha256:command+=['--expected-apk-sha256',args.expected_apk_sha256]
    result=subprocess.run(command)
    audit=subprocess.run([sys.executable,str(root/'audit_device_run.py'),
        '--run',str(args.out),'--queries',str(args.queries)])
    cleanup=dict(at=dt.datetime.now(dt.timezone.utc).isoformat(),runner_exit_code=result.returncode,
        audit_exit_code=audit.returncode,source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in ('run_device.py','audit_device_run.py','run_full_benchmark.py','usb_http.py','resume_run.py')})
    try:
        switch=subprocess.run([sys.executable,str(root/'set_http.py'),'--serial',args.serial,'off'],
            capture_output=True,text=True,timeout=90)
        cleanup.update(switch_exit_code=switch.returncode,switch_output=switch.stdout,switch_error=switch.stderr)
        if switch.returncode:cleanup['switch_error']='HTTP switch verification failed: '+switch.stderr
    except Exception as error:cleanup['switch_error']=repr(error)
    try:
        # End only this test process. This also covers a locked-screen cleanup failure.
        subprocess.run([ADB,'-s',args.serial,'shell','am','force-stop','--user','0',PACKAGE],check=True,timeout=30)
        own_pid=subprocess.run([ADB,'-s',args.serial,'shell','pidof',PACKAGE],capture_output=True,text=True,timeout=30)
        cleanup['final_pid']=own_pid.stdout.strip() or None
        subprocess.run([ADB,'-s',args.serial,'shell','rm','-f','/sdcard/chtozavino-offline-bench-ui.xml'],check=True,timeout=30)
    except Exception as error:cleanup['cleanup_error']=repr(error)
    save(args.out/'coordinator-cleanup.json',cleanup)
    if (result.returncode or audit.returncode or cleanup.get('switch_error')
        or cleanup.get('cleanup_error') or cleanup.get('final_pid')):
        raise SystemExit(2)


if __name__=='__main__':main()
