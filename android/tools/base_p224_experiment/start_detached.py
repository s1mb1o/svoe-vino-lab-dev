"""Start one finite workflow outside the interactive terminal process group."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);a=p.parse_args()
    config=a.config.resolve();root=config.parent
    values=json.loads(config.read_text())
    if Path(values['full_out']).exists() or Path(values['comparison_out']).exists():
        raise RuntimeError('Refuse to launch over an existing attempt')
    record=root/'detached-launch.json'
    with record.open('x') as stream:
        json.dump(dict(state='starting',started_at=dt.datetime.now(dt.timezone.utc).isoformat()),stream)
    first=os.fork()
    if first:
        _,status=os.waitpid(first,0)
        if status:raise RuntimeError('Detached launch failed')
        print('Started finite detached workflow. Record:',record);return
    os.setsid();signal.signal(signal.SIGHUP,signal.SIG_IGN)
    second=os.fork()
    if second:os._exit(0)
    os.chdir(root)
    with open(os.devnull,'rb') as incoming,(root/'workflow.log').open('ab',buffering=0) as output,(root/'workflow-errors.log').open('ab',buffering=0) as errors:
        os.dup2(incoming.fileno(),0);os.dup2(output.fileno(),1);os.dup2(errors.fileno(),2)
    command=['/usr/bin/caffeinate','-i',sys.executable,'-u',str(root/'resume_workflow.py'),'--config',str(config)]
    record.write_text(json.dumps(dict(state='launched',pid=os.getpid(),started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        launcher='double fork; separate session; SIGHUP ignored; no restart policy',command=command),indent=2)+'\n')
    os.execv(command[0],command)


if __name__=='__main__':main()
