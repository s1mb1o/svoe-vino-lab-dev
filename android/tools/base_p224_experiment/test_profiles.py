import unittest

import numpy as np

from profiles import CONDITIONS,coverage,effective_profile,log_weights


class PoolingProfileTest(unittest.TestCase):
    def test_fractional_whitespace_and_bottle(self):
        actual=log_weights([0,.5,1],224,'fractional-bg010')
        np.testing.assert_allclose(np.exp(actual[0,:3]),[.1,.55,1],atol=1e-7)
        self.assertTrue(np.all(actual[0,3:]==0))

    def test_standard_is_zero_bias(self):
        self.assertTrue(np.all(log_weights([0,.5,1],224,'standard')==0))

    def test_coverage_uses_spatial_mask_not_rgb(self):
        # An entirely white bottle label still has foreground coverage one.
        np.testing.assert_array_equal(coverage(np.ones((32,16)),2,1),[1,1])
        np.testing.assert_array_equal(coverage(np.zeros((32,16)),2,1),[0,0])

    def test_partial_patch_coverage(self):
        alpha=np.zeros((16,16),dtype=np.float32);alpha[:8]=1
        np.testing.assert_allclose(coverage(alpha,1,1),[.5],atol=1e-7)

    def test_invalid_masks_are_rejected(self):
        for value in ([],[float('nan')],[-.01],[1.01],list(np.ones(225))):
            with self.assertRaises(ValueError):log_weights(value,224,'fractional-bg010')

    def test_effective_profiles_cannot_share_an_index_identity(self):
        manifest=dict(profile=dict(max_num_patches=224))
        self.assertNotEqual(effective_profile(manifest,'standard')['sha256'],
            effective_profile(manifest,'fractional-bg010')['sha256'])

    def test_each_budget_has_standard_and_custom_pooling(self):
        self.assertEqual({(c['budget'],c['pooling']) for c in CONDITIONS},
            {(budget,pooling) for budget in (224,512) for pooling in ('standard','fractional-bg010')})
        self.assertEqual([c['number'] for c in CONDITIONS],[1,2,3,4])

    def test_p512_fractional_weights_keep_padding_excluded(self):
        actual=log_weights(np.tile([0,.5,1],170),512,'fractional-bg010')
        self.assertEqual(actual.shape,(1,512))
        np.testing.assert_allclose(np.exp(actual[0,:3]),[.1,.55,1],atol=1e-7)
        np.testing.assert_array_equal(actual[0,510:],[0,0])


if __name__=='__main__':unittest.main()
