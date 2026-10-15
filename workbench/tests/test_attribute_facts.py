"""Exercise shared-image jobs, stale inputs, refresh generations, and durable evidence."""

import tempfile
import unittest
from pathlib import Path

import attribute_facts as facts
import labdb


class FactsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "lab.sqlite3")
        self.conn = labdb.connect(self.db, create=True)
        self.sha = "a" * 64
        with self.conn:
            for slug in ("wine-a", "wine-b"):
                self.conn.execute(
                    "INSERT INTO wine_catalog (wine_slug,name,producer,category,color,region,description,csv_photo_name) "
                    "VALUES (?, 'Muscat 2021', 'Producer', 'Розовое', 'rose', 'Region', 'Reserve', 'a.jpg')",
                    (slug,),
                )
            self.conn.execute(
                "INSERT INTO image VALUES (?, 'main', 'jpg', 100, 300)", (self.sha,)
            )
            for slug in ("wine-a", "wine-b"):
                self.conn.execute(
                    "INSERT INTO wine_image (wine_slug,image_type,sha256,source_name,match_method) VALUES (?,'main',?,'a.jpg','manual')",
                    (slug, self.sha),
                )
            # Simulate inputs present at migration time.
            self.conn.execute(
                "INSERT INTO image_attribute_baseline VALUES (?,?)",
                (self.sha, self.sha),
            )

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def item(self):
        facts.discover(self.conn, force=True)
        return facts.pending(self.conn)[0]

    def complete(self, item=None, source="description"):
        item = item or self.item()
        self.assertTrue(facts.claim(self.conn, item))
        data = facts.empty()
        data["vintage"] = {
            "state": "observed",
            "values": ["2022"],
            "evidence": "Урожай 2022",
        }
        self.assertTrue(facts.finish(self.conn, item, data, source=source))
        return item

    def test_shared_image_has_one_cached_job(self):
        item = self.item()
        self.assertEqual(item["mode"], "cached")
        self.assertEqual(len(facts.targets(self.conn)), 1)
        self.assertEqual(facts.discover(self.conn, force=True), 0)
        self.assertEqual(
            self.conn.execute("SELECT count(*) FROM image_attribute_job").fetchone()[0],
            1,
        )

    def test_new_inputs_are_automatically_image_jobs(self):
        self.conn.execute("DELETE FROM image_attribute_baseline")
        self.assertEqual(self.item()["mode"], "image")

    def test_refresh_retains_old_evidence_and_rejects_stale_generation(self):
        old = self.complete()
        self.assertEqual(facts.enqueue(self.conn, self.sha), 1)
        new = facts.pending(self.conn)[0]
        self.assertGreater(new["generation"], old["generation"])
        self.assertFalse(facts.finish(self.conn, old, facts.empty()))
        self.assertTrue(facts.views(self.conn)[self.sha]["stale"])
        facts.claim(self.conn, new)
        facts.finish(self.conn, new, error="offline", max_attempts=1)
        view = facts.views(self.conn)[self.sha]
        self.assertEqual(view["state"], "failed")
        self.assertEqual(view["facts"]["vintage"]["values"], ["2022"])
        self.assertEqual(
            self.conn.execute("SELECT count(*) FROM image_attribute_facts").fetchone()[
                0
            ],
            1,
        )

    def test_repeated_refresh_does_not_duplicate_active_work(self):
        facts.enqueue(self.conn, self.sha)
        self.assertEqual(facts.enqueue(self.conn, self.sha), 0)
        item = facts.pending(self.conn)[0]
        facts.claim(self.conn, item)
        self.assertFalse(facts.claim(self.conn, item))
        self.assertEqual(facts.enqueue(self.conn, self.sha), 0)

    def test_replaced_input_is_stale_and_old_job_is_not_scheduled(self):
        self.complete()
        new = "b" * 64
        self.conn.execute(
            "INSERT INTO image VALUES (?, 'cropped', 'png', 90, 250)", (new,)
        )
        self.conn.execute(
            "INSERT INTO image_derivative(source_sha256,kind,sha256,method,settings,box_left,box_top,box_right,box_bottom) VALUES (?,'package',?,'crop','{}',0,0,90,250)",
            (self.sha, new),
        )
        facts.discover(self.conn, force=True)
        view = facts.views(self.conn)[self.sha]
        self.assertTrue(view["stale"])
        self.assertEqual(view["input_sha256"], new)
        item = facts.pending(self.conn)[0]
        self.assertEqual((item["input_sha256"], item["mode"]), (new, "image"))

    def test_get_views_does_not_queue_jobs(self):
        self.assertEqual(facts.views(self.conn)[self.sha]["state"], "not_queued")
        self.assertEqual(
            self.conn.execute("SELECT count(*) FROM image_attribute_job").fetchone()[0],
            0,
        )

    def test_lease_recovers_a_dead_worker(self):
        item = self.item()
        facts.claim(self.conn, item)
        self.conn.execute(
            "UPDATE image_attribute_job SET updated_at='2000-01-01T00:00:00Z'"
        )
        self.assertEqual(len(facts.pending(self.conn)), 1)

    def test_validation_rejects_invented_values_without_evidence(self):
        data = facts.empty()
        data["grape"] = {"state": "observed", "values": ["Muscat"], "evidence": ""}
        with self.assertRaises(ValueError):
            facts.validate(data)
        with self.assertRaises(ValueError):
            facts.validate({"vintage": data["vintage"]})

    def test_pause_and_expired_lease_token(self):
        item = self.item()
        facts.claim(self.conn, item)
        self.conn.execute(
            "UPDATE image_attribute_job SET updated_at='2000-01-01T00:00:00Z'"
        )
        next_item = facts.pending(self.conn)[0]
        self.assertGreater(next_item["generation"], item["generation"])
        self.assertFalse(facts.finish(self.conn, item, facts.empty()))
        self.conn.execute("UPDATE image_attribute_settings SET paused=1")
        self.assertEqual(facts.pending(self.conn), [])

    def test_versions_do_not_requeue_existing_observations(self):
        self.complete(source="vlm")
        self.assertEqual(facts.discover(self.conn, "other-version", force=True), 0)
        self.assertEqual(facts.pending(self.conn, version="other-version"), [])
        self.assertTrue(facts.views(self.conn, "other-version")[self.sha]["stale"])
        self.assertEqual(facts.enqueue(self.conn, self.sha, version="other-version"), 1)

    def test_cached_version_is_independent_of_the_model(self):
        self.complete()
        self.assertEqual(facts.discover(self.conn, "other-version", force=True), 0)
        self.assertFalse(facts.views(self.conn, "other-version")[self.sha]["stale"])

    def test_new_image_is_detected_after_in_place_link_update(self):
        new = "b" * 64
        self.conn.execute("INSERT INTO image VALUES (?,'main','jpg',100,300)", (new,))
        self.conn.execute("UPDATE wine_image SET sha256=?", (new,))
        facts.discover(self.conn, force=True)
        self.assertEqual(facts.pending(self.conn)[0]["mode"], "image")

    def test_worker_version_change_keeps_requested_work(self):
        facts.enqueue(self.conn, self.sha)
        facts.heartbeat(self.conn, "worker-v2", force=True)
        item = facts.pending(self.conn)[0]
        self.assertEqual((item["version"], item["mode"]), ("worker-v2", "image"))

    def test_transient_bad_output_has_bounded_retries(self):
        item = self.item()
        for expected in ("pending", "pending", "failed"):
            self.assertTrue(facts.claim(self.conn, item))
            facts.finish(self.conn, item, error="invalid JSON")
            self.assertEqual(facts.views(self.conn)[self.sha]["state"], expected)

    def test_missing_batch_does_not_reanalyse_completed_vlm_unknowns(self):
        self.complete(source="vlm")
        self.assertEqual(facts.enqueue(self.conn, scope="missing"), 0)
        self.assertEqual(facts.enqueue(self.conn, self.sha), 1)
