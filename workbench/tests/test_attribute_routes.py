"""Check queue method guards, validation, and read-only Dataset responses."""

import json
import test_lab_server as server_tests


class AttributeRouteTest(server_tests.SimilarRouteTest):
    def test_read_requests_do_not_queue_work(self):
        before = self.request("/api/dataset")[2]
        self.assertTrue(json.loads(before)["attribute_comparison"])
        for method in ["GET", "PUT", "DELETE"]:
            self.assertEqual(self.request("/api/dataset-attributes", method)[0], 405)
        import sqlite3

        with sqlite3.connect(self.db) as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM image_attribute_job").fetchone()[0],
                0,
            )

    def test_queue_validates_and_refuses_unlinked_images(self):
        for body, status in [
            ({"sha256": "bad"}, 400),
            ({"scope": "bad"}, 400),
            ({"extra": 1}, 400),
            ({"sha256": "a" * 64}, 404),
        ]:
            self.assertEqual(
                self.request(
                    "/api/dataset-attributes", "POST", json.dumps(body).encode()
                )[0],
                status,
            )
        self.assertEqual(
            self.request("/api/dataset-attributes", "POST", b"not json")[0], 400
        )

    def test_batch_queue_accepts_and_deduplicates(self):
        body = json.dumps({"scope": "missing"}).encode()
        code, _, payload = self.request("/api/dataset-attributes", "POST", body)
        self.assertEqual(code, 202, payload)
        self.assertGreaterEqual(json.loads(payload)["queued"], 0)
        code, _, payload = self.request("/api/dataset-attributes", "POST", body)
        self.assertEqual((code, json.loads(payload)["queued"]), (202, 0))

    def test_posted_job_is_claimed_after_worker_advertises_its_recipe(self):
        from unittest import mock
        import describe_images
        import sqlite3

        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE wine_catalog SET state='Active',removed_by=NULL")
        server_tests.LabServerTest.add_image(self,"wine-a","main",b"attribute-input")

        self.assertEqual(
            self.request(
                "/api/dataset-attributes", "POST", json.dumps({"scope": "all"}).encode()
            )[0],
            202,
        )
        cfg = dict(
            describe_images.DEFAULTS,
            details=False,
            labels=False,
            attributes=True,
            attribute_version="worker-recipe",
        )
        with mock.patch.object(
            describe_images.image_descriptions, "pending", return_value=[]
        ):
            selected = describe_images.next_items(self.db, cfg, 1, set())
        self.assertEqual(selected[0][0], "attributes")
        self.assertEqual(selected[0][1]["version"], "worker-recipe")

    def test_dataset_get_does_not_write_or_parse_attribute_config(self):
        from unittest import mock
        import attribute_extract
        import sqlite3

        with sqlite3.connect(self.db) as conn:
            before = conn.execute("PRAGMA data_version").fetchone()[0]
            with mock.patch.object(
                attribute_extract,
                "configured_version",
                side_effect=AssertionError("No request-time VLM config"),
            ):
                self.assertEqual(self.request("/api/dataset")[0], 200)
            self.assertEqual(conn.execute("PRAGMA data_version").fetchone()[0], before)
