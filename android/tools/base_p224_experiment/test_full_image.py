"""Verify full-image mask coverage and the new paired comparison contract."""
import unittest

import numpy as np

from profiles import coverage,log_weights
from run_comparison import paired,require_known_replacement
from run_device import parity_queries


class FullImagePoolingTest(unittest.TestCase):
    def test_decoder_parity_includes_all_failed_boundaries(self):
        rows=[dict(query_id=f'q-{i:06d}',image_sha256=f'image-{i}') for i in range(668)]
        for number in (5,6):
            selected=parity_queries(rows,number)
            self.assertEqual([r['query_id'] for r in selected[:4]],
                ['q-000029','q-000171','q-000380','q-000567'])
            self.assertEqual(len({r['image_sha256'] for r in selected}),5)
        self.assertEqual(len(parity_queries(rows,4)),3)
    def test_replacement_requires_exact_isolated_apk(self):
        package='com.alolalab.chtozavino.fullpoolbench';sha='a'*64
        require_known_replacement(package,sha,sha)
        for target,actual,expected in ((package,sha,None),(package,sha,'b'*64),
            ('com.alolalab.chtozavino',sha,sha),(package,'bad','bad')):
            with self.assertRaises(RuntimeError):require_known_replacement(target,actual,expected)
    def test_full_grid_retains_background_patches(self):
        mask=np.zeros((32,64),dtype=np.float32);mask[8:24,24:40]=1
        actual=coverage(mask,2,4)
        np.testing.assert_allclose(actual,[0,.25,.25,0,0,.25,.25,0],atol=1e-7)
        weights=np.exp(log_weights(actual,512,'fractional-bg010')[0,:8])
        np.testing.assert_allclose(weights,[.1,.325,.325,.1,.1,.325,.325,.1],atol=1e-7)
    def test_standard_full_image_remains_zero_bias(self):
        mask=np.zeros((32,64),dtype=np.float32);mask[8:24,24:40]=1
        self.assertTrue(np.all(log_weights(coverage(mask,2,4),512,'standard')==0))
    def test_full_image_pair_reports_gains_and_regressions(self):
        common=dict(query_file_sha256='queries',pack_manifest_sha256='pack')
        left=dict(common,top_k_percent={'1':50},outcomes={'a':{'1':True},'b':{'1':False}})
        right=dict(common,top_k_percent={'1':50},outcomes={'a':{'1':False},'b':{'1':True}})
        result=paired({5:left,6:right})['5-to-6']
        self.assertEqual(result,dict(top1_gain_pp=0,gains=['b'],regressions=['a']))
    def test_full_image_pair_rejects_changed_queries(self):
        left=dict(query_file_sha256='a',pack_manifest_sha256='pack',outcomes={})
        right=dict(query_file_sha256='b',pack_manifest_sha256='pack',outcomes={})
        with self.assertRaises(ValueError):paired({5:left,6:right})


if __name__=='__main__':unittest.main()
