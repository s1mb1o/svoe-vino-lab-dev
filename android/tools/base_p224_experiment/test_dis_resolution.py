"""Check spatial-only graph contracts and resolution-aware mask projection."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dis_pooling'))
from export_resolution import spatial_shape,specialize
from contracts import dis_foreground


class ResolutionTest(unittest.TestCase):
    def test_nhwc_shape_preserves_channels(self):
        self.assertEqual(spatial_shape([1,512,512,1024],768),[1,384,384,1024])
        self.assertEqual(spatial_shape([1,32,32,512],512),[1,16,16,512])
    def test_nchw_shape_preserves_channels(self):
        self.assertEqual(spatial_shape([1,3,1024,1024],768,True),[1,3,768,768])
    def test_padding_is_not_scaled(self):
        self.assertEqual(spatial_shape([1,1026,1026,3],768,padded=True),[1,770,770,3])
        self.assertEqual(spatial_shape([1,1026,1026,3],512,padded=True),[1,514,514,3])
    def test_unknown_size_and_source_are_rejected(self):
        with self.assertRaises(ValueError):spatial_shape([1,32,32,3],640)
        with self.assertRaises(ValueError):specialize(b'unpinned',512)
    def test_nonintegral_and_unexpected_padding_fail(self):
        with self.assertRaises(ValueError):spatial_shape([1,33,33,3],768)
        with self.assertRaises(ValueError):spatial_shape([1,514,514,3],768,padded=True)
    def test_all_native_mask_grids_preserve_values(self):
        for size in (512,768,1024):
            with self.subTest(size=size):
                mask=np.tile(np.linspace(0,1,size,dtype=np.float32),(size,1))
                np.testing.assert_array_equal(dis_foreground(mask,size,size,'full-image'),mask)
    def test_all_crop_grids_preserve_padding_and_renderer_limit(self):
        for size in (512,768,1024):
            actual=dis_foreground(np.ones((size,size),dtype=np.float32),500,1200,'bottle-crop-white')
            self.assertEqual(actual.max(),1);self.assertEqual(max(actual.shape),1024)
            self.assertTrue(np.all(actual[0,:]==0) and np.all(actual[:,0]==0))
    def test_unsupported_mask_shape_fails(self):
        for shape in ((512,768),(640,640),(0,0)):
            with self.assertRaises(ValueError):dis_foreground(np.ones(shape,dtype=np.float32),500,1200,'full-image')


if __name__=='__main__':unittest.main()
