#!/usr/bin/env python3
"""Set only the isolated benchmark HTTP switch through current UI inspection."""

import argparse
import re
import subprocess
import xml.etree.ElementTree as ET

ADB='/Users/ashmelev/Library/Android/sdk/platform-tools/adb'
PACKAGE='com.alolalab.chtozavino.offlinebench'
TEMP='/sdcard/chtozavino-offline-bench-ui.xml'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('state',choices=['on','off'])
    args=parser.parse_args()
    def adb(*parts):
        return subprocess.run([ADB,'-s',args.serial,*parts],capture_output=True,text=True,
                              timeout=30,check=True).stdout
    def inspect():
        adb('shell','uiautomator','dump',TEMP)
        root=ET.fromstring(adb('shell','cat',TEMP))
        switches=[n for n in root.iter('node') if n.get('package')==PACKAGE and
            n.get('class')=='android.widget.Switch' and n.get('text')=='HTTP-сервер для тестов']
        if len(switches)!=1:raise RuntimeError('The benchmark switch is not visible. Unlock the device and open the app.')
        return root,switches[0]
    if adb('shell','am','get-current-user').strip()!='0':
        raise RuntimeError('Require the original Android user 0. Do not change another user profile.')
    adb('shell','am','start','-n',PACKAGE+'/.MainActivity')
    root,switch=inspect();desired=args.state=='on'
    if (switch.get('checked')=='true')!=desired:
        if switch.get('enabled')!='true':raise RuntimeError('The observed switch is disabled')
        x1,y1,x2,y2=map(int,re.findall(r'\d+',switch.get('bounds')))
        adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
        root,switch=inspect()
    if (switch.get('checked')=='true')!=desired:raise RuntimeError('HTTP switch verification failed')
    print('Verified benchmark HTTP:',args.state)
    for n in root.iter('node'):
        text=n.get('text','')
        if n.get('package')==PACKAGE and ('HTTP-сервер' in text or text.startswith('Пакет:')):print(text)


if __name__=='__main__':main()
