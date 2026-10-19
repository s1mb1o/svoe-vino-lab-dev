"""Keep the isolated process cleanup independent from UI availability."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_full_benchmark


class FullBenchmarkTest(unittest.TestCase):
    def test_switch_timeout_still_stops_only_isolated_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'run'
            calls=[]
            def run(command,**kwargs):
                calls.append(command)
                if 'set_http.py' in ' '.join(command):
                    raise subprocess.TimeoutExpired(command,90)
                if 'run_device.py' in ' '.join(command):output.mkdir()
                return subprocess.CompletedProcess(command,0,stdout='',stderr='')
            with patch('sys.argv',['run_full_benchmark.py','--serial','device',
                '--queries','queries.json','--pack-manifest','manifest.json','--out',str(output)]), \
                patch('run_full_benchmark.subprocess.run',side_effect=run):
                with self.assertRaises(SystemExit):run_full_benchmark.main()
            cleanup=json.loads((output/'coordinator-cleanup.json').read_text())
            self.assertIn('TimeoutExpired',cleanup['switch_error'])
            self.assertIsNone(cleanup['final_pid'])
            stop=[command for command in calls if 'force-stop' in command]
            self.assertEqual(stop,[[run_full_benchmark.ADB,'-s','device','shell','am',
                'force-stop','--user','0',run_full_benchmark.PACKAGE]])


if __name__=='__main__':unittest.main()
