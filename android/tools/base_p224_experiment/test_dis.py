"""DIS normalization, mask projection, and paired-condition regression tests."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dis_pooling'))
from contracts import normalized_dis,dis_foreground
from run_comparison import paired,require_known_replacement
from run_device import parity_queries


class DisTest(unittest.TestCase):
    def test_normalization_uses_image_min_max(self):
        np.testing.assert_array_equal(normalized_dis([2.,3.,4.]),[0.,.5,1.])
    def test_invalid_or_constant_masks_fail(self):
        for raw in ([],[0.,0.],[float('nan'),1.],[float('inf'),1.]):
            with self.assertRaises(ValueError):normalized_dis(raw)
    def test_native_grid_preserves_mask(self):
        mask=np.tile(np.linspace(0,1,1024,dtype=np.float32),(1024,1))
        np.testing.assert_array_equal(dis_foreground(mask,1024,1024,'full-image'),mask)
    def test_cropped_mask_keeps_outside_padding_zero(self):
        mask=np.ones((1024,1024),dtype=np.float32)
        actual=dis_foreground(mask,500,1000,'bottle-crop-white')
        self.assertEqual(actual.max(),1)
        self.assertTrue(np.all(actual[0,:]==0) and np.all(actual[:,0]==0))
        self.assertEqual(max(actual.shape),1024)
    def test_both_dis_conditions_use_five_decoder_inputs(self):
        rows=[dict(query_id=f'q-{i:06d}',image_sha256=f'image-{i}') for i in range(668)]
        for n in (7,8):self.assertEqual(len(parity_queries(rows,n)),5)
    def test_all_dis_pairs_are_reported(self):
        common=dict(query_file_sha256='queries',pack_manifest_sha256='pack',top_k_percent={'1':50},
            outcomes={'a':{'1':True}})
        self.assertEqual(set(paired({n:dict(common) for n in (5,7,8)})),{'5-to-7','5-to-8','7-to-8'})
    def test_dis_update_must_have_exact_known_hash(self):
        require_known_replacement('com.alolalab.chtozavino.dispoolbench','a'*64,'a'*64)
        with self.assertRaises(RuntimeError):require_known_replacement('com.alolalab.chtozavino.dispoolbench','a'*64,'b'*64)


if __name__=='__main__':unittest.main()
