import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import benchmark_audit as B
class AuditBenchmarkTest(unittest.TestCase):
    def test_gate_uses_verification_without_catalog_absence(self):
        c=[dict(slug='a',score=.8),dict(slug='b',score=.7)]
        self.assertTrue(B.gate(c,'unsure'));self.assertFalse(B.gate(c,'unsure',True));self.assertTrue(B.gate(c,'supported',True));self.assertFalse(B.gate([], 'untriggered'))
    def test_precision_and_false_acceptance_are_separate_from_membership(self):
        rows=[dict(image_sha256='1',truth=['a'],label='positive',cascade=dict(candidates=[dict(slug='b',score=.8)],evidence='supported',latency_ms=10)),dict(image_sha256='2',truth=[],label='positive',cascade=dict(candidates=[dict(slug='a',score=.8)],evidence='unsure',latency_ms=12))]
        self.assertEqual(B.acceptance(rows)['false_acceptance'],2);self.assertEqual(B.acceptance(rows,True)['false_acceptance'],1)
    def test_one_identity_stays_in_one_split(self):
        a=dict(truth=['wine-a'],image_sha256='0'*64);b=dict(truth=['wine-a'],image_sha256='1'*64);self.assertEqual(B.split_group(a),B.split_group(b))
if __name__=='__main__':unittest.main()
