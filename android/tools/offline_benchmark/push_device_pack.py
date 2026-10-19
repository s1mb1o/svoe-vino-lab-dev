#!/usr/bin/env python3
"""Send the verified pack to app-private storage through debuggable run-as."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'
PACKAGE='com.alolalab.chtozavino.offlinebench'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--pack',type=Path,required=True)
    parser.add_argument('--changed-only',action='store_true',help='Skip files with unchanged metadata in the existing private manifest.')
    args=parser.parse_args()
    current=subprocess.run([ADB,'-s',args.serial,'shell','am','get-current-user'],
        capture_output=True,text=True,check=True).stdout.strip()
    if current!='0':raise RuntimeError('Require the original Android user 0 before pack transfer.')
    manifest=json.loads((args.pack/'manifest.json').read_text())
    names=['manifest.json',*manifest['files']]
    for name in names:
        path=(args.pack/name).resolve()
        if not path.is_relative_to(args.pack.resolve()) or not path.is_file():raise RuntimeError('Unsafe pack path')
        if name!='manifest.json':
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if digest!=manifest['files'][name]['sha256']:raise RuntimeError('Pack hash mismatch')
    if args.changed_only:
        result=subprocess.run([ADB,'-s',args.serial,'exec-out','run-as',PACKAGE,'cat','files/bench/manifest.json'],
            capture_output=True,text=True,check=True)
        previous=json.loads(result.stdout)
        names=[name for name in names if name=='manifest.json' or
               previous.get('files',{}).get(name)!=manifest['files'][name]]
        print('Changed files:',names,flush=True)
    subprocess.run([ADB,'-s',args.serial,'shell','run-as',PACKAGE,'mkdir','-p','files/bench'],check=True)
    process=subprocess.Popen([ADB,'-s',args.serial,'exec-in','run-as',PACKAGE,'tar','-xf','-','-C','files/bench'],stdin=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdin,mode='w|',dereference=True) as stream:
            for name in names:
                # Write independent file entries. Do not send host uid, gid, or broad modes.
                path=args.pack/name
                info=tarfile.TarInfo(name);info.size=path.stat().st_size;info.mode=0o600
                with path.open('rb') as source:stream.addfile(info,source)
                print('Transferred',name,info.size,flush=True)
        process.stdin.close()
        if process.wait(timeout=120):raise RuntimeError('App-private extraction failed')
    finally:
        if process.poll() is None:process.terminate()
    print('The app will verify every file checksum before model creation.',flush=True)


if __name__=='__main__':main()
