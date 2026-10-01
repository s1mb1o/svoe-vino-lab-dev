"""Tests for the comparable competitor pipeline actions of plan 91."""

import tempfile
import unittest
from pathlib import Path

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)

import competitor_steps
import embeddings
from embeddings import ConfigError
from PIL import Image, ImageDraw


CATALOG = {
    "red-reserve-2020": {
        "slug": "red-reserve-2020", "name": "Reserve 2020", "producer": "Atlas",
        "category": "Красное сухое", "color": "Красное", "grapes": "Каберне",
    },
    "white-riesling-2022": {
        "slug": "white-riesling-2022", "name": "Riesling 2022", "producer": "North",
        "category": "Белое сухое", "color": "Белое", "grapes": "Рислинг",
    },
    "rose-brut": {
        "slug": "rose-brut", "name": "Rose Brut", "producer": "Atlas",
        "category": "Розовое брют", "color": "Розовое", "grapes": "Пино Нуар",
    },
}


def cands():
    return [
        {"slug": "white-riesling-2022", "score": 0.81, "rank": 1,
         "full": 0.81, "label": 0.60},
        {"slug": "red-reserve-2020", "score": 0.80, "rank": 2,
         "full": 0.70, "label": 0.90},
    ]


class OptionsTest(unittest.TestCase):
    def test_atomic_action_is_checked(self):
        value = competitor_steps.check_options({
            "source": "stan", "pool": 30,
            "actions": [{"action": "ocr_rerank", "profile": "stan", "top_k": 10,
                         "alpha": 0.18, "conflict_penalty": 0.08}],
        })
        self.assertEqual(value["source"], "stan")
        self.assertEqual(value["actions"][0]["profile"], "stan")

    def test_bad_options_are_refused(self):
        cases = [
            ({}, "source MUST"),
            ({"source": "stan", "actions": [{"action": "nope"}]}, "unknown action"),
            ({"source": "stan", "actions": [{"action": "reject", "min_score": 2}]},
             "min_score"),
            ({"source": "stan", "actions": [{"action": "ocr_rerank",
                                                "profile": "nope"}]}, "profile"),
            ({"source": "stan", "actions": [{"action": "secondary_union"}]},
             "requires competitor.secondary"),
        ]
        for raw, message in cases:
            with self.subTest(raw=raw), self.assertRaisesRegex(ConfigError, message):
                competitor_steps.check_options(raw)


class ActionTest(unittest.TestCase):
    def test_view_fusion_changes_only_the_order_and_diagnostics(self):
        out = competitor_steps.view_fusion(cands(), {"full": 0.3, "label": 0.7})
        self.assertEqual([row["slug"] for row in out],
                         ["red-reserve-2020", "white-riesling-2022"])
        self.assertEqual(out[0]["visual_score"], 0.80)
        self.assertEqual(out[0]["fusion_score"], 0.84)
        self.assertEqual([row["rank"] for row in out], [1, 2])

    def test_stan_ocr_moves_the_supported_candidate_and_penalizes_a_conflict(self):
        out = competitor_steps.ocr_rerank(
            cands(), "ATLAS RESERVE 2020 RED CABERNET", CATALOG,
            profile="stan", top_k=10, alpha=0.3, conflict_penalty=0.1,
        )
        self.assertEqual(out[0]["slug"], "red-reserve-2020")
        self.assertGreater(out[0]["ocr_score"], out[1]["ocr_score"])
        self.assertGreaterEqual(out[1]["ocr_conflicts"], 1)

    def test_global_ocr_union_adds_a_candidate_outside_the_visual_pool(self):
        visual = [cands()[0]]
        out = competitor_steps.ocr_union(
            visual, "ATLAS RESERVE 2020 CABERNET RED", CATALOG, top_k=1,
        )
        self.assertEqual({row["slug"] for row in out},
                         {"white-riesling-2022", "red-reserve-2020"})
        added = next(row for row in out if row["slug"] == "red-reserve-2020")
        self.assertIsNone(added["visual_score"])
        self.assertEqual(added["candidate_source"], "ocr")

    def test_secondary_union_records_both_scores(self):
        primary = cands()
        secondary = [
            {"slug": "red-reserve-2020", "score": 0.95, "rank": 1},
            {"slug": "rose-brut", "score": 0.80, "rank": 2},
        ]
        out = competitor_steps.secondary_union(primary, secondary, 0.4, 0.6)
        self.assertEqual(out[0]["slug"], "red-reserve-2020")
        self.assertEqual(out[0]["primary_score"], 0.80)
        self.assertEqual(out[0]["secondary_score"], 0.95)
        self.assertIn("rose-brut", {row["slug"] for row in out})

    def test_reject_returns_no_candidate_and_keeps_the_audit(self):
        accepted, audit = competitor_steps.reject(cands(), 0.82, "score")
        self.assertEqual(accepted, [])
        self.assertEqual(audit[0]["slug"], "white-riesling-2022")
        accepted, audit = competitor_steps.reject(cands(), 0.80, "score")
        self.assertEqual(accepted[0]["slug"], "white-riesling-2022")
        self.assertEqual(audit, [])

    def test_sift_records_geometry_for_a_prepared_catalogue_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query = root / "query.png"
            image = Image.new("RGB", (320, 240), "white")
            draw = ImageDraw.Draw(image)
            for x in range(20, 300, 40):
                draw.rectangle((x, 20, x + 18, 220), fill="black")
            draw.ellipse((70, 55, 250, 205), outline="red", width=9)
            draw.text((105, 105), "WINE 2026", fill="blue", stroke_width=1)
            image.save(query)
            images = root / embeddings.IMAGES
            images.mkdir()
            prepared = images / embeddings.image_name("catalogue-sha", "full")
            image.save(prepared)

            reranker = competitor_steps.SiftReranker(root)
            rows = reranker(str(query), [{
                "slug": "red-reserve-2020", "score": 0.8, "rank": 1,
                "items": [{"view": "full", "sha256": "catalogue-sha", "cosine": 0.8}],
            }], top_k=1, weight=0.05)

            self.assertGreater(rows[0]["sift_matches"], 3)
            self.assertGreater(rows[0]["sift_inliers"], 3)
            self.assertGreater(rows[0]["score"], 0.8)


class FakeInner:
    def __init__(self, answer):
        self.answer = answer
        self.id = "base"
        self.catalogue = object()
        self.top_k = 30
        self.spec = {"id": "base", "kind": "embedding", "top_k": 30}

    def ask(self, path, first=None):
        return self.answer


class BackendTest(unittest.TestCase):
    def test_backend_applies_actions_in_order_and_truncates_top_k(self):
        answer = (cands(), 10, 200, None, {"v": 1, "steps": []})
        options = competitor_steps.check_options({
            "source": "stan", "pool": 30,
            "actions": [
                {"action": "ocr_rerank", "profile": "stan", "top_k": 10,
                 "alpha": 0.3, "conflict_penalty": 0.1},
                {"action": "reject", "min_score": 0.1, "score_field": "score"},
            ],
        })
        backend = competitor_steps.CompetitorSteps(
            FakeInner(answer), options, CATALOG, top_k=1,
            ocr=lambda path: "ATLAS RESERVE 2020 RED CABERNET",
        )
        out, latency, status, error, trace = backend.ask("photo.jpg")
        self.assertEqual([row["slug"] for row in out], ["red-reserve-2020"])
        self.assertGreaterEqual(latency, 10)
        self.assertEqual((status, error), (200, None))
        self.assertEqual([step["id"] for step in trace["steps"]],
                         ["competitor-ocr_rerank", "competitor-reject"])
        self.assertEqual(backend.spec["competitor"]["source"], "stan")
        self.assertIs(backend.catalogue, backend.inner.catalogue)

    def test_inner_error_does_not_run_an_action(self):
        backend = competitor_steps.CompetitorSteps(
            FakeInner(([], 5, None, "down", {"v": 1, "steps": []})),
            competitor_steps.check_options({
                "source": "qacen", "actions": [{"action": "reject", "min_score": 0.76}],
            }), CATALOG, top_k=5,
        )
        self.assertEqual(backend.ask("p")[3], "down")
        self.assertEqual(backend.ask("p")[4]["steps"], [])


if __name__ == "__main__":
    unittest.main()
