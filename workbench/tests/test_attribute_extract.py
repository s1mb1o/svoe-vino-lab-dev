"""Check background extraction with local fixtures and stubbed inference."""

import json
from types import SimpleNamespace
from unittest import mock

import attribute_extract
import attribute_facts as facts
import describe_images
from test_attribute_facts import FactsTest


class ExtractionTest(FactsTest):
    def setUp(self):
        super().setUp()
        self.entry = SimpleNamespace(protocol="openai", name="test", max_tokens=2000)
        self.cfg = {"detail_max_side": 1024}

    def test_cached_backfill_never_calls_inference(self):
        self.conn.execute(
            "INSERT INTO image_label_description (sha256,description,created_by,created_at,input_sha256,vlm_name) "
            "VALUES (?,?,'vlm','2026-10-15T00:00:00Z',?,'image-only-fixture')",
            (
                self.sha,
                json.dumps(
                    {
                        "texts": [{"text": "Muscat"}, {"text": "Урожай 2022"}],
                        "vintage": 2022,
                    }
                ),
                self.sha,
            ),
        )
        item = self.item()
        self.conn.commit()
        with mock.patch.object(
            describe_images, "ask", side_effect=AssertionError("No inference")
        ):
            self.assertTrue(attribute_extract.one(self.db, self.entry, self.cfg, item))
        view = facts.views(self.conn)[self.sha]
        self.assertEqual(view["facts"]["grape"]["values"], ["Muscat"])
        self.assertEqual(view["source"], "description")

    def test_image_extraction_is_independent_and_persists_quotes(self):
        facts.enqueue(self.conn, self.sha)
        item = facts.pending(self.conn)[0]
        self.conn.commit()
        data = facts.empty()
        data["grape"] = {
            "state": "observed",
            "values": ["Muscat"],
            "evidence": "Muscat",
        }
        self.assertTrue(
            attribute_extract.one(
                self.db, self.entry, self.cfg, item, runner=lambda path: (data, "stub")
            )
        )
        self.assertEqual(facts.views(self.conn)[self.sha]["model"], "stub")

    def test_invalid_quote_is_unknown_and_other_evidence_survives(self):
        facts.enqueue(self.conn, self.sha)
        item = facts.pending(self.conn)[0]
        self.conn.commit()
        data = facts.empty()
        data["grape"] = {
            "state": "observed",
            "values": ["Muscat"],
            "evidence": "Merlot",
        }
        data["vintage"] = {"state": "observed", "values": ["2022"], "evidence": "2022"}
        self.assertTrue(
            attribute_extract.one(
                self.db, self.entry, self.cfg, item, runner=lambda path: (data, "stub")
            )
        )
        view = facts.views(self.conn)[self.sha]
        self.assertEqual(view["state"], "ready")
        self.assertEqual(view["facts"]["grape"]["state"], "unknown")
        self.assertEqual(view["facts"]["vintage"]["values"], ["2022"])

    def test_worker_selects_attribute_stage_when_enabled(self):
        cfg = dict(
            describe_images.DEFAULTS, details=False, labels=False, attributes=True
        )
        # Existing package-class tasks are outside this test's scope.
        with mock.patch.object(
            describe_images.image_descriptions, "pending", return_value=[]
        ):
            self.conn.commit()
            selected = describe_images.next_items(self.db, cfg, 1, set())
        self.assertEqual(selected[0][0], "attributes")

    def test_prompt_excludes_metadata_and_visual_inferences(self):
        self.assertIn("No catalogue metadata is supplied", attribute_extract.PROMPT)
        self.assertIn("barrel illustration", attribute_extract.PROMPT)
        self.assertIn("founding", attribute_extract.PROMPT)

    def test_extraction_key_tracks_model_and_resolution(self):
        from types import SimpleNamespace

        entry = SimpleNamespace(
            model="a",
            endpoint="http://local/v1",
            protocol="openai",
            thinking_field="none",
            max_tokens=2000,
        )
        first = attribute_extract.extractor_key(entry, self.cfg)
        entry.model = "b"
        self.assertNotEqual(first, attribute_extract.extractor_key(entry, self.cfg))
        entry.model = "a"
        self.assertNotEqual(
            first, attribute_extract.extractor_key(entry, {"detail_max_side": 512})
        )

    def test_inconsistent_attribute_does_not_discard_other_fields(self):
        facts.enqueue(self.conn, self.sha)
        item = facts.pending(self.conn)[0]
        self.conn.commit()
        data = facts.empty()
        data["grape"] = {"state": "observed", "values": [], "evidence": ""}
        data["colour"] = {"state": "not_visible", "values": ["Red"], "evidence": ""}
        data["vintage"] = {"state": "observed", "values": ["2022"], "evidence": "2022"}
        self.assertTrue(
            attribute_extract.one(
                self.db, self.entry, self.cfg, item, runner=lambda path: (data, "stub")
            )
        )
        view = facts.views(self.conn)[self.sha]
        self.assertEqual(view["facts"]["grape"]["state"], "unknown")
        self.assertEqual(view["facts"]["colour"]["state"], "unknown")
        self.assertEqual(view["facts"]["vintage"]["values"], ["2022"])

    def test_blank_or_punctuation_value_is_unknown(self):
        for index, text in enumerate(("   ", "—", "%")):
            with self.subTest(value=text):
                year = str(2020 + index)
                facts.enqueue(self.conn, self.sha)
                item = facts.pending(self.conn)[0]
                self.conn.commit()
                data = facts.empty()
                data["grape"] = {
                    "state": "observed",
                    "values": [text],
                    "evidence": "Muscat",
                }
                data["vintage"] = {
                    "state": "observed",
                    "values": [year],
                    "evidence": year,
                }
                self.assertTrue(
                    attribute_extract.one(
                        self.db,
                        self.entry,
                        self.cfg,
                        item,
                        runner=lambda path: (data, "stub"),
                    )
                )
                view = facts.views(self.conn)[self.sha]
                self.assertEqual(
                    view["facts"]["grape"],
                    {"state": "unknown", "values": [], "evidence": ""},
                )
                self.assertEqual(view["facts"]["vintage"]["values"], [year])

    def test_unobserved_commentary_is_reset_without_losing_other_evidence(self):
        facts.enqueue(self.conn, self.sha)
        item = facts.pending(self.conn)[0]
        self.conn.commit()
        data = facts.empty()
        data["grape"] = {
            "state": "not_visible",
            "values": [],
            "evidence": "no grape text visible",
        }
        data["vintage"] = {"state": "observed", "values": ["2024"], "evidence": "2024"}
        self.assertTrue(
            attribute_extract.one(
                self.db, self.entry, self.cfg, item, runner=lambda path: (data, "stub")
            )
        )
        view = facts.views(self.conn)[self.sha]
        self.assertEqual(
            view["facts"]["grape"], {"state": "unknown", "values": [], "evidence": ""}
        )
        self.assertEqual(view["facts"]["vintage"]["values"], ["2024"])
