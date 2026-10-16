"""Exercise fail-closed image update decisions without a model or network."""

import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PIL import Image, ImageDraw

import website_image_review as review


RECORD = {"wine_slug": "muskat-premium", "name": "Мускат Премиум", "producer": "Литавщук",
          "grapes": "Мускат", "category": "Белое", "color": "Соломенный",
          "description": "Белое полусухое вино"}
READING = {"name": "Мускат Премиум", "producer": "Литавщук", "grapes": "Мускат",
           "category": "Белое", "sweetness": "semi_dry", "vintage": ""}


def verdict(**values):
    return {"identity": "match", "fields": {field: "match" for field in review.FIELDS},
            "readability": "better", "sharpness": "better", "artifacts": "none",
            "complete": True, "upscaled": "no", "reason": "The new label has clearer printed text.", **values}


def proof(record, old_sha, new_sha):
    return {"policy": review.POLICY, "binding": review.binding(record, old_sha, new_sha),
            "eligible": True, "reasons": [], "state": "approved", "recognized": dict(READING),
            "enlargement_mean_error": 12.0,
            "required_fields": review.required_fields(record), "verdict": verdict(),
            "crops": {side: {kind: {"size": size, "kind": "wine bottle" if kind == "package" else review.LABEL_NOUN}
                              for kind in ("package", "label")}
                      for side, size in (("old", [100, 200]), ("new", [200, 400]))}}


def png(size=(100, 200), seed=0):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((size[0]//5, 0, 4*size[0]//5, size[1]-1), fill=(50+seed, 50, 50))
    draw.text((size[0]//3, size[1]//2), "MUSCAT " + str(seed), fill="white")
    data = io.BytesIO()
    image.save(data, "PNG")
    return data.getvalue()


class Detector:
    def instances(self, image, texts, masks=False):
        w, h = image.size
        return [{"label": "wine bottle", "box": [w*.2, 0, w*.8, h], "score": .99},
                {"label": review.LABEL_NOUN, "box": [w*.2, h*.4, w*.8, h*.8], "score": .99}], 1


class ImageReviewTest(unittest.TestCase):
    def test_all_gates_and_exact_source_binding_are_required(self):
        p = proof(RECORD, "old", "new")
        self.assertTrue(review.approved(p, RECORD, "old", "new"))
        for field, value in (("identity", "uncertain"), ("readability", "worse"),
                             ("sharpness", "uncertain"), ("complete", False),
                             ("upscaled", "yes"), ("artifacts", "present")):
            changed = copy.deepcopy(p)
            changed["verdict"][field] = value
            self.assertFalse(review.approved(changed, RECORD, "old", "new"), field)
        self.assertFalse(review.approved(p, {**RECORD, "producer": "Other"}, "old", "new"))
        self.assertFalse(review.approved(p, RECORD, "different", "new"))
        p["crops"]["new"]["label"]["size"] = [100, 200]
        self.assertFalse(review.approved(p, RECORD, "old", "new"))

    def test_unknown_independent_field_cannot_be_supplied_by_expected_metadata(self):
        p = proof(RECORD, "old", "new")
        p["recognized"]["grapes"] = ""
        self.assertFalse(review.approved(p, RECORD, "old", "new"))
        p = proof(RECORD, "old", "new")
        p["required_fields"] = ["name"]
        self.assertFalse(review.approved(p, RECORD, "old", "new"))

    def test_independent_contradictions_cannot_be_approved_by_a_model(self):
        conflicts = review.independent_conflicts(RECORD, {**READING, "grapes": "Cabernet Sauvignon"})
        self.assertTrue(any("grape" in reason for reason in conflicts))
        conflicts = review.independent_conflicts({**RECORD, "name": "Мускат Премиум 2020"},
                                                 {**READING, "vintage": "2021"})
        self.assertTrue(any("vintage" in reason for reason in conflicts))

    def test_padding_does_not_count_as_native_resolution(self):
        old = review.native_crops(png(), Detector())
        self.assertEqual(old["package"]["image"].size, (60, 200))
        self.assertEqual(old["label"]["image"].size, (60, 80))
        self.assertFalse(review.larger((60, 200), (60, 200)))
        self.assertFalse(review.larger((100, 200), (105, 201)))
        self.assertTrue(review.larger((100, 200), (150, 300)))

    def test_detector_coordinates_are_mapped_back_to_native_pixels(self):
        detector = Mock()
        detector.instances.return_value = ([
            {"label": "wine bottle", "box": [10, 0, 40, 100], "score": .99},
            {"label": review.LABEL_NOUN, "box": [10, 40, 40, 80], "score": .99}], .5)
        crops = review.native_crops(png(), detector)
        self.assertEqual(crops["package"]["image"].size, (60, 200))
        self.assertEqual(crops["label"]["box"], [20, 80, 80, 160])

    def test_wrong_muskat_example_and_service_failure_are_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = review.ImageReviewer(segmenter=Detector(), recognize=lambda data: {
                **READING, "name": "Wrong wine", "grapes": "Cabernet Sauvignon"},
                judge=lambda *args: verdict(identity="mismatch", reason="Different wine name and grape."))
            result = runtime(RECORD, png(), png((200, 400), 1), directory)
            self.assertFalse(result["eligible"])
            self.assertTrue(any("mismatch" in s for s in result["reasons"]))
            self.assertEqual(result["crops"]["new"]["label"]["size"], [120, 160])
            for side in ("old", "new"):
                for crop in result["crops"][side].values():
                    self.assertTrue((Path(directory) / crop["file"]).is_file())
            runtime.recognize = Mock(side_effect=TimeoutError("VLM unavailable"))
            result = runtime(RECORD, png(), png((200, 400), 1), directory)
            self.assertFalse(result["eligible"])
            self.assertTrue(any("unavailable" in reason for reason in result["reasons"]))

    def test_an_enlargement_cannot_be_an_automatic_improvement(self):
        old = png()
        with Image.open(io.BytesIO(old)) as image:
            image = image.resize((200, 400), Image.Resampling.BICUBIC)
            out = io.BytesIO()
            image.save(out, "PNG")
        runtime = review.ImageReviewer(segmenter=Detector(), recognize=lambda data: READING,
                                       judge=lambda *args: verdict())
        with tempfile.TemporaryDirectory() as directory:
            result = runtime(RECORD, old, out.getvalue(), directory)
        self.assertFalse(result["eligible"])
        self.assertTrue(any("enlarged" in s for s in result["reasons"]))

    def test_invalid_model_output_and_missing_crops_fail_closed(self):
        runtime = review.ImageReviewer(segmenter=Detector(), recognize=lambda data: READING,
                                       judge=lambda *args: {"identity": "match"})
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(runtime(RECORD, png(), png((200, 400), 1), directory)["eligible"])
            detector = Mock()
            detector.instances.return_value = ([], 1)
            runtime.segmenter = detector
            result = runtime(RECORD, png(), png((200, 400), 1), directory)
            self.assertFalse(result["eligible"])
            self.assertTrue(any("crop" in reason for reason in result["reasons"]))


class IndependentIdentityTest(unittest.TestCase):
    def test_wrong_name_or_producer_cannot_be_overruled_by_positive_judge(self):
        for key, value in (('name','Мускат Резерв'),('producer','Другая винодельня')):
            p = proof(RECORD,'old','new')
            p['recognized'][key] = value
            self.assertFalse(review.approved(p,RECORD,'old','new'),key)

    def test_known_translations_and_legal_producer_words_are_supported(self):
        p = proof(RECORD,'old','new')
        p['recognized'].update(name='Muscat Premium',producer='Litavshchuk Vineyards & Winery',grapes='Muscat')
        self.assertTrue(review.approved(p,RECORD,'old','new'))

    def test_mismatch_on_optional_field_still_blocks(self):
        p = proof(RECORD,'old','new')
        p['verdict']['fields']['vintage'] = 'mismatch'
        self.assertFalse(review.approved(p,RECORD,'old','new'))


class ReviewBoundaryTest(unittest.TestCase):
    def test_excessive_native_gain_requires_manual_review_even_with_positive_model(self):
        p = proof(RECORD, "old", "new")
        p["crops"]["new"]["label"]["size"] = [500, 1000]
        self.assertFalse(review.approved(p, RECORD, "old", "new"))

    def test_missing_or_interpolated_pixel_proof_cannot_approve(self):
        for error in (None, 0.2, float("nan"), "12"):
            p = proof(RECORD, "old", "new")
            p["enlargement_mean_error"] = error
            self.assertFalse(review.approved(p, RECORD, "old", "new"))

    def test_malformed_independent_reading_never_escapes(self):
        for value in ([], "bad", 12, None):
            p = proof(RECORD, "old", "new")
            p["recognized"] = value
            self.assertFalse(review.approved(p, RECORD, "old", "new"))

    def test_failed_reuse_keeps_reasons_and_clears_model_context(self):
        runtime = review.ImageReviewer(segmenter=Detector(), recognize=Mock(side_effect=TimeoutError("offline")))
        runtime.model_context = {"review_model": "previous entry"}
        with tempfile.TemporaryDirectory() as directory:
            result = runtime(RECORD, png(), png(), directory)
        self.assertEqual(runtime.model_context, {})
        self.assertTrue(any("not sufficiently larger" in reason for reason in result["reasons"]))
        self.assertTrue(any("offline" in reason for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
