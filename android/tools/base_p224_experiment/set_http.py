"""Use the observed UI of only the isolated Base pooling experiment."""
import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from profiles import PACKAGE
from run_device import ADB


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--serial',required=True)
    p.add_argument('--require-current',action='store_true',help='Verify the observed state without changing it.')
    p.add_argument('state',choices=('on','off'));a=p.parse_args()
    temporary='/sdcard/chtozavino-base-pooling-ui.xml'
    def adb(*parts):
        return subprocess.check_output([ADB,'-s',a.serial,*parts],text=True,timeout=45)
    def inspect():
        adb('shell','uiautomator','dump',temporary)
        return ET.fromstring(adb('shell','cat',temporary))
    def click(node):
        if node.get('enabled')!='true':raise RuntimeError('Observed control is disabled')
        x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
        adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
    if adb('shell','am','get-current-user').strip()!='0':raise RuntimeError('Require original Android user 0')
    adb('shell','am','start','-n',PACKAGE+'/com.alolalab.chtozavino.offlinebench.MainActivity')
    desired=a.state=='on'
    for _ in range(8):
        root=inspect()
        switches=[n for n in root.iter('node') if n.get('package')==PACKAGE and
            n.get('class')=='android.widget.Switch' and n.get('text')=='HTTP-сервер для тестов']
        if len(switches)==1:
            switch=switches[0]
            if (switch.get('checked')=='true')==desired:
                print('Verified Base experiment HTTP:',a.state);return
            if a.require_current:raise RuntimeError('Fresh application HTTP state is not the required default')
            click(switch);time.sleep(1);continue
        # Only accept the freshly requested notification permission from the observed dialog.
        buttons=[n for n in root.iter('node') if n.get('package')=='com.google.android.permissioncontroller' and
            n.get('resource-id','').endswith(':id/permission_allow_button') and n.get('clickable')=='true']
        if desired and len(buttons)==1:click(buttons[0]);time.sleep(1);continue
        raise RuntimeError('The Base experiment switch is not visible. Unlock the phone in user 0.')
    raise RuntimeError('HTTP switch did not reach its requested state')


if __name__=='__main__':main()
