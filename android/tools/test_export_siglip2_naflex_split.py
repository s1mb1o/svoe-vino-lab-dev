#!/usr/bin/env python3
"""Tests for the exact SigLIP2 NaFlex model split."""

import importlib.util
from pathlib import Path
import unittest

try:
    import torch
    from transformers import Siglip2VisionConfig, Siglip2VisionModel
except ImportError:
    torch = None
    Siglip2VisionConfig = None
    Siglip2VisionModel = None


@unittest.skipIf(torch is None, "torch and transformers are required")
class NaFlexSplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name("export_siglip2_naflex_split.py")
        spec = importlib.util.spec_from_file_location("naflex_export", path)
        cls.exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.exporter)

    def test_split_matches_original_vision_model(self):
        torch.manual_seed(17)
        config = Siglip2VisionConfig(
            hidden_size=32,
            intermediate_size=64,
            num_hidden_layers=2,
            num_attention_heads=4,
            patch_size=4,
            num_patches=16,
        )
        model = Siglip2VisionModel(config).eval()
        vision = model.vision_model
        patches = torch.randn(1, 16, 3 * 4 * 4)
        mask = torch.ones(1, 16, dtype=torch.int64)
        spatial_shapes = torch.tensor([[2, 8]], dtype=torch.int64)
        table = vision.embeddings.position_embedding.weight.reshape(4, 4, 32)
        positions = vision.embeddings.resize_positional_embeddings(
            table,
            spatial_shapes,
            max_length=16,
        )
        backbone = self.exporter.NaFlexBackbone(vision).eval()
        pooling = self.exporter.NaFlexPooling(vision).eval()
        encoder_mask = self.exporter.backbone_attention_mask(mask)

        with torch.inference_mode():
            expected = model(
                pixel_values=patches,
                pixel_attention_mask=mask,
                spatial_shapes=spatial_shapes,
            ).pooler_output
            actual = pooling(backbone(patches, positions, encoder_mask), mask)

        self.assertTrue(torch.equal(expected, actual))

    def test_foreground_pooling_matches_standard_for_unit_weights(self):
        torch.manual_seed(18)
        config = Siglip2VisionConfig(
            hidden_size=32,
            intermediate_size=64,
            num_hidden_layers=2,
            num_attention_heads=4,
            patch_size=4,
            num_patches=16,
        )
        vision = Siglip2VisionModel(config).eval().vision_model
        tokens = torch.randn(1, 16, 32)
        mask = torch.ones(1, 16, dtype=torch.int64)
        weights = torch.ones(1, 16, dtype=torch.float32)
        standard = self.exporter.NaFlexPooling(vision).eval()
        weighted = self.exporter.NaFlexForegroundPooling(vision).eval()

        with torch.inference_mode():
            expected = standard(tokens, mask)
            actual = weighted(tokens, weights)

        self.assertTrue(torch.equal(expected, actual))

    def test_foreground_pooling_masks_zero_weight_padding(self):
        torch.manual_seed(19)
        config = Siglip2VisionConfig(
            hidden_size=32,
            intermediate_size=64,
            num_hidden_layers=2,
            num_attention_heads=4,
            patch_size=4,
            num_patches=16,
        )
        vision = Siglip2VisionModel(config).eval().vision_model
        tokens = torch.randn(1, 16, 32)
        changed = tokens.clone()
        changed[:, 8:] = 1_000.0
        weights = torch.cat((torch.ones(1, 8), torch.zeros(1, 8)), dim=1)
        weighted = self.exporter.NaFlexForegroundPooling(vision).eval()

        with torch.inference_mode():
            expected = weighted(tokens, weights)
            actual = weighted(changed, weights)

        self.assertTrue(torch.equal(expected, actual))


if __name__ == "__main__":
    unittest.main()
