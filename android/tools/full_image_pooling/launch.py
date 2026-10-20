"""Launch one finite, immutable full-image experiment without an automatic restart."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    a=p.parse_args();config=a.config.resolve();values=json.loads(config.read_text());root=config.parent
    package=values.get('package','com.alolalab.chtozavino.fullpoolbench')
    conditions=values.get('conditions',[5,6])
    if (package,conditions) not in [('com.alolalab.chtozavino.fullpoolbench',[5,6]),
        ('com.alolalab.chtozavino.dispoolbench',[5,7,8])]:raise ValueError('Unknown isolated campaign')
    if Path(values['out']).exists():raise ValueError('Preserve the existing attempt')
    record=root/'detached-launch.json'
    with record.open('x') as stream:json.dump(dict(state='starting'),stream)
    first=os.fork()
    if first:
        _,status=os.waitpid(first,0)
        if status:raise RuntimeError('Detached launch failed')
        print('Launched finite full-image comparison:',record);return
    os.setsid();signal.signal(signal.SIGHUP,signal.SIG_IGN)
    if os.fork():os._exit(0)
    os.chdir(root)
    with open(os.devnull,'rb') as incoming,(root/'workflow.log').open('ab',buffering=0) as out,(root/'workflow-errors.log').open('ab',buffering=0) as err:
        os.dup2(incoming.fileno(),0);os.dup2(out.fileno(),1);os.dup2(err.fileno(),2)
    command=['/usr/bin/caffeinate','-i',sys.executable,'-u',values['script']]
    for key in ('after','serial','pack','queries','apk','out','baseline'):command+=['--'+key,values[key]]
    if values.get('replace_apk_sha256'):command+=['--replace-apk-sha256',values['replace_apk_sha256']]
    command+=['--conditions',*map(str,conditions)]
    record.write_text(json.dumps(dict(state='launched',pid=os.getpid(),started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        command=command,launcher='double fork; separate session; SIGHUP ignored; no restart policy'),indent=2)+'\n')
    environment=dict(os.environ,BASE_POOLING_PACKAGE=package)
    os.execve(command[0],command,environment)


if __name__=='__main__':main()
