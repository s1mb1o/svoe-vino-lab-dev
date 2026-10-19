#!/usr/bin/env python3
"""Copy only the frozen exact-pooling reference rows needed by variant ten."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


REMOTE_READER = r'''
from pathlib import Path
import hashlib,json,struct,sys
import numpy as np
stage=sys.argv[1]
assert stage in ('p512-reference','p512-axial')
root=Path('/home/ashmelev/.cache/codex-bench/my-failed2-eight-20261017-01a148d5/retrieval-extensions-20261018/native')/stage
rows=json.loads((root/'rows.json').read_text())
source=root/'g1-bg000-l3-exact.npy'
matrix=np.load(source,mmap_mode='r',allow_pickle=False)
picked=[i for i,row in enumerate(rows) if stage.endswith('axial') or row['in_plane_angle'] in (0,90,180,270)]
values=np.asarray(matrix[picked],dtype='<f4')
assert values.shape==(len(picked),1152) and np.isfinite(values).all()
norm=np.linalg.norm(values,axis=1)
assert np.max(np.abs(norm-1))<.002
data=values.tobytes()
with source.open('rb') as stream:original=hashlib.file_digest(stream,'sha256').hexdigest()
header=dict(stage=stage,source=str(source),source_sha256=original,rows=[rows[i] for i in picked],
            shape=list(values.shape),dtype='float32-le',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
raw=json.dumps(header).encode()
sys.stdout.buffer.write(struct.pack('<Q',len(raw)));sys.stdout.buffer.write(raw);sys.stdout.buffer.write(data)
'''


def read_exact(stream, count):
    parts = []
    while count:
        chunk = stream.read(count)
        if not chunk:
            raise RuntimeError('The SSH data stream stopped before its declared length.')
        parts.append(chunk)
        count -= len(chunk)
    return b''.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for stage in ('p512-reference','p512-axial'):
        command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','ashmelev@192.168.86.14',
                 '/home/ashmelev/comfyui-env/bin/python','-',stage]
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        process.stdin.write(REMOTE_READER.encode());process.stdin.close()
        length=struct.unpack('<Q',read_exact(process.stdout,8))[0]
        if length > 32*1024*1024:
            process.terminate();raise ValueError('Unexpected reference header length.')
        header=json.loads(read_exact(process.stdout,length))
        if header['shape'] != [len(header['rows']),1152] or header['bytes'] != len(header['rows'])*1152*4:
            process.terminate();raise ValueError('Reference stream shape mismatch.')
        path=args.out/(stage+'.f32.partial')
        digest=hashlib.sha256();remaining=header['bytes']
        with path.open('wb') as output:
            while remaining:
                chunk=read_exact(process.stdout,min(8*1024*1024,remaining))
                output.write(chunk);digest.update(chunk);remaining-=len(chunk)
        trailing=process.stdout.read(1)
        code=process.wait(timeout=30)
        if code or trailing or digest.hexdigest()!=header['sha256']:
            raise RuntimeError('Reference transfer integrity check failed.')
        path.rename(path.with_suffix(''))
        (args.out/(stage+'.json')).write_text(json.dumps(header,indent=2)+'\n')
        print(stage,header['shape'],header['bytes'],'bytes; checksum verified',flush=True)


if __name__=='__main__':
    main()
