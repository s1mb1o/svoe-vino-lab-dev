"""Unit tests of plan 61: the key repair, the tables of `pipeline/label_descriptions.py`,
and the routes of `pipeline/label_description_routes.py` on a temporary database. No test
calls a VLM."""
import json
import sqlite3
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing

from image_description_fixture import DescriptionCase

import label_descriptions as LD
import lab_server as LAB

VLM = {"vlm_name": "label-test", "vlm_endpoint": "http://vlm.invalid/v1/chat/completions",
       "vlm_model": "label-model", "vlm_served_model": "Label-Model", "max_tokens": 1500,
       "thinking": False, "input_sha256": "c" * 64,
       "vlm_request": {"input_kind": "package", "describe_side": 2048},
       "vlm_reply": {"finish_reason": "stop", "repairs": []}}
DESCRIPTION = {"texts": [{"text": "МЫСХАКО", "where": "main label"}], "numbers": [],
               "vintage": None, "colours": ["black"], "design": "a black label",
               "marks": [], "bottle": "dark green"}


class RepairTest(unittest.TestCase):
    def test_the_aliases_get_the_keys_of_the_prompt(self):
        texts, numbers = [{"text": "a", "where": "b"}], ["2019"]
        value = {"text": texts, "number": numbers, "vintage_year": 2019, "Colors": ["red"],
                 "design": "d", "mark": [], "bottle": "b"}
        repaired, renames = LD.repair(value)
        self.assertEqual(list(repaired), ["texts", "numbers", "vintage", "colours", "design",
                                          "marks", "bottle"])
        self.assertIs(repaired["texts"], texts)
        self.assertIs(repaired["numbers"], numbers)
        self.assertEqual(renames, [["text", "texts"], ["number", "numbers"],
                                   ["vintage_year", "vintage"], ["Colors", "colours"],
                                   ["mark", "marks"]])

    def test_a_key_of_the_prompt_in_another_letter_case(self):
        self.assertEqual(LD.repair({"Texts": [], "BOTTLE": "b"}),
                         ({"texts": [], "bottle": "b"}, [["Texts", "texts"],
                                                         ["BOTTLE", "bottle"]]))

    def test_a_key_of_the_prompt_is_never_replaced(self):
        value = {"texts": ["a"], "text": ["b"], "colour": "red", "color": "blue"}
        repaired, renames = LD.repair(value)
        self.assertEqual(repaired, {"texts": ["a"], "text": ["b"], "colours": "red",
                                    "color": "blue"})
        self.assertEqual(renames, [["colour", "colours"]])

    def test_the_keys_inside_a_value_do_not_change(self):
        value = {"text": [{"Text": "a", "location": "b"}], "where": "left"}
        self.assertEqual(LD.repair(value), ({"texts": [{"Text": "a", "location": "b"}],
                                             "where": "left"}, [["text", "texts"]]))

    def test_a_value_that_is_not_an_object_stays(self):
        self.assertEqual(LD.repair(["text"]), (["text"], []))
        self.assertEqual(LD.repair(None), (None, []))


class TableTest(DescriptionCase):
    def run_sql(self, work):
        with closing(self.connect()) as conn, conn:
            return work(conn)

    def pending(self, max_attempts=3):
        return self.run_sql(lambda conn: LD.pending(conn, max_attempts))

    def test_each_linked_image_waits_the_newest_link_first(self):
        self.assertEqual(self.pending(), [
            (self.sha["wine-b"], self.sha["wine-b"], "original", "main", "png"),
            (self.sha["wine-a"], self.sha["wine-a"], "original", "main", "png")])
        self.assertEqual(self.run_sql(lambda conn: LD.pending(conn, 3, limit=1)),
                         [self.pending()[0]])
        self.assertIsNone(self.run_sql(lambda conn: LD.target(conn, self.sha["none"])))

    def test_the_package_cut_is_the_input_file(self):
        self.add_cut("wine-b", "label")
        self.assertEqual(self.pending()[0][1:3], (self.sha["wine-b"], "original"))
        cut = self.add_cut("wine-a", "package")
        self.assertEqual(self.pending()[1], (self.sha["wine-a"], cut, "package", "cropped",
                                             "png"))

    def test_an_image_with_a_row_does_not_wait(self):
        row_id = self.run_sql(lambda conn: LD.add_manual(conn, self.sha["wine-a"], {}))
        self.assertEqual([item[0] for item in self.pending()], [self.sha["wine-b"]])
        self.assertEqual(self.run_sql(lambda conn: LD.remove(conn, row_id)), self.sha["wine-a"])
        self.assertEqual(len(self.pending()), 2)

    def test_counted_failures_stop_the_image(self):
        sha = self.sha["wine-b"]
        for count in (True, True, False):
            self.run_sql(lambda conn: LD.record_failure(conn, sha, "bad", count=count))
        self.assertEqual(self.run_sql(lambda conn: LD.failure(conn, sha))["attempts"], 2)
        self.assertEqual(len(self.pending()), 2)
        self.run_sql(lambda conn: LD.record_failure(conn, sha, "the last error"))
        self.assertEqual([item[0] for item in self.pending()], [self.sha["wine-a"]])
        failure = self.run_sql(lambda conn: LD.failure(conn, sha))
        self.assertEqual((failure["attempts"], failure["error"]), (3, "the last error"))
        self.assertEqual(self.run_sql(LD.reset_failed), 1)
        self.assertEqual(len(self.pending()), 2)

    def test_the_watcher_takes_only_an_image_with_no_row(self):
        sha = self.sha["wine-a"]
        manual = self.run_sql(lambda conn: LD.add_manual(conn, sha, {"design": "owner"}))
        self.assertIsNone(self.run_sql(lambda conn: LD.record_vlm(conn, sha, DESCRIPTION, VLM)))
        rows = self.run_sql(lambda conn: LD.rows(conn, sha))
        self.assertEqual([(row["id"], row["created_by"]) for row in rows], [(manual, "manual")])
        self.run_sql(lambda conn: LD.record_failure(conn, sha, "late"))
        self.assertIsNone(self.run_sql(lambda conn: LD.failure(conn, sha)))

    def test_a_vlm_row_keeps_its_settings_and_clears_the_failures(self):
        sha = self.sha["wine-b"]
        self.run_sql(lambda conn: LD.record_failure(conn, sha, "bad"))
        row_id = self.run_sql(lambda conn: LD.record_vlm(conn, sha, DESCRIPTION, VLM,
                                                          now="2026-09-27T10:00:00Z"))
        self.assertIsNone(self.run_sql(lambda conn: LD.failure(conn, sha)))
        row = self.run_sql(lambda conn: LD.latest(conn, sha))
        expected = dict(VLM, id=row_id, sha256=sha, description=DESCRIPTION, created_by="vlm",
                        created_at="2026-09-27T10:00:00Z")
        self.assertEqual(row, expected)
        stored = self.run_sql(lambda conn: conn.execute(
            "SELECT description, thinking FROM image_label_description").fetchone())
        self.assertIn("МЫСХАКО", stored[0])
        self.assertEqual(stored[1], 0)

    def test_the_latest_row_comes_first(self):
        sha = self.sha["wine-a"]
        first = self.run_sql(lambda conn: LD.record_vlm(conn, sha, DESCRIPTION, VLM,
                                                         now="2026-09-27T10:00:00Z"))
        second = self.run_sql(lambda conn: LD.add_manual(conn, sha, {"design": "x"},
                                                          now="2026-09-27T11:00:00Z"))
        third = self.run_sql(lambda conn: LD.add_manual(conn, sha, {"design": "y"},
                                                         now="2026-09-27T11:00:00Z"))
        rows = self.run_sql(lambda conn: LD.rows(conn, sha))
        self.assertEqual([row["id"] for row in rows], [third, second, first])
        self.assertEqual(self.run_sql(lambda conn: LD.latest(conn, sha))["id"], third)
        view = self.run_sql(lambda conn: LD.view(conn, sha, 3))
        self.assertEqual((view["latest_id"], len(view["rows"]), view["failure"],
                          view["max_attempts"]), (third, 3, None, 3))
        self.assertIsNone(rows[0]["vlm_name"])
        self.assertIsNone(rows[0]["thinking"])

    def test_the_removal_of_the_last_row_puts_the_image_back(self):
        sha = self.sha["wine-a"]
        for _ in range(3):
            self.run_sql(lambda conn: LD.record_failure(conn, sha, "bad"))
        one = self.run_sql(lambda conn: LD.add_manual(conn, sha, {}))
        two = self.run_sql(lambda conn: LD.add_manual(conn, sha, {}))
        self.run_sql(lambda conn: LD.remove(conn, two))
        self.assertEqual(self.run_sql(lambda conn: LD.failure(conn, sha))["attempts"], 3)
        self.run_sql(lambda conn: LD.remove(conn, one))
        self.assertIsNone(self.run_sql(lambda conn: LD.failure(conn, sha)))
        self.assertIn(sha, [item[0] for item in self.pending()])
        self.assertIsNone(self.run_sql(lambda conn: LD.remove(conn, one)))

    def test_the_counts(self):
        self.assertEqual(self.run_sql(lambda conn: LD.counts(conn, 3)), {
            "labels_linked": 2, "labels_done": 0, "labels_failed": 0, "labels_pending": 2})
        self.run_sql(lambda conn: LD.add_manual(conn, self.sha["wine-a"], {}))
        self.run_sql(lambda conn: LD.add_manual(conn, self.sha["wine-a"], {}))
        for _ in range(3):
            self.run_sql(lambda conn: LD.record_failure(conn, self.sha["wine-b"], "bad"))
        self.assertEqual(self.run_sql(lambda conn: LD.counts(conn, 3)), {
            "labels_linked": 2, "labels_done": 1, "labels_failed": 1, "labels_pending": 0})
        self.assertEqual(self.run_sql(lambda conn: LD.counts(conn, 4))["labels_pending"], 1)

    def test_the_table_checks_its_rows(self):
        sql = ("INSERT INTO image_label_description (sha256, description, created_by, "
               "created_at, vlm_name) VALUES (?, ?, ?, '2026-09-27T10:00:00Z', ?)")
        for values in ((self.sha["wine-a"], "[]", "manual", None),
                       (self.sha["wine-a"], "{}", "vlm", None),
                       (self.sha["wine-a"], "{}", "manual", "label-test"),
                       ("f" * 64, "{}", "manual", None)):
            with self.subTest(values=values), self.assertRaises(sqlite3.IntegrityError):
                self.run_sql(lambda conn: conn.execute(sql, values))


class RouteTest(DescriptionCase):
    def setUp(self):
        super().setUp()
        self.server = LAB.make_server(self.db, port=0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def request(self, path, method="GET", body=None):
        data = None if body is None else (body if isinstance(body, bytes)
                                          else json.dumps(body).encode("utf-8"))
        req = urllib.request.Request(self.base + path, method=method, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read())

    def rows(self, slug):
        status, view = self.request("/api/image-label-descriptions?sha256=" + self.sha[slug])
        self.assertEqual(status, 200)
        return view["rows"]

    def test_get_sends_the_view_of_a_linked_image(self):
        status, view = self.request("/api/image-label-descriptions?sha256=" + self.sha["wine-a"])
        self.assertEqual(status, 200)
        self.assertEqual(view, {"sha256": self.sha["wine-a"], "rows": [], "latest_id": None,
                                "failure": None, "max_attempts": 3})
        self.assertEqual(self.request("/api/image-label-descriptions?sha256=abc")[0], 400)
        self.assertEqual(self.request("/api/image-label-descriptions?sha256="
                                      + self.sha["none"])[0], 404)
        self.assertEqual(self.request("/api/image-label-description")[0], 405)
        self.assertEqual(self.request("/api/image-label-descriptions", "POST", {})[0], 405)

    def test_post_adds_a_manual_row_that_becomes_the_latest(self):
        status, view = self.request("/api/image-label-description", "POST",
                                    {"sha256": self.sha["wine-a"], "description": DESCRIPTION})
        self.assertEqual(status, 200)
        row = view["rows"][0]
        self.assertEqual((row["created_by"], row["description"], view["latest_id"]),
                         ("manual", DESCRIPTION, row["id"]))
        status, view = self.request("/api/image-label-description", "POST",
                                    {"sha256": self.sha["wine-a"], "description": {}})
        self.assertEqual([r["description"] for r in view["rows"]], [{}, DESCRIPTION])
        self.assertEqual(self.rows("wine-b"), [])

    def test_post_refuses_a_bad_body(self):
        sha = self.sha["wine-a"]
        big = {"design": "x" * (LD.MAX_MANUAL_BYTES + 1)}
        cases = [({"sha256": sha, "description": [1]}, 400),
                 ({"sha256": sha, "description": "text"}, 400),
                 ({"sha256": sha}, 400),
                 ({"sha256": "ABC", "description": {}}, 400),
                 ({"sha256": sha, "description": big}, 400),
                 ({"sha256": self.sha["none"], "description": {}}, 404),
                 (b"not json", 400),
                 ([sha], 400)]
        for body, code in cases:
            with self.subTest(body=str(body)[:60]):
                status, answer = self.request("/api/image-label-description", "POST", body)
                self.assertEqual(status, code)
                self.assertIn("error", answer)
        status, answer = self.request("/api/image-label-description", "POST",
                                      b'{"sha256": "%s", "description": {"a": "\\ud800"}}'
                                      % sha.encode("ascii"))
        self.assertEqual((status, "lone surrogate" in answer["error"]), (400, True))
        self.assertEqual(self.rows("wine-a"), [])

    def test_delete_removes_one_row(self):
        sha = self.sha["wine-a"]
        for description in ({"design": "one"}, {"design": "two"}):
            self.request("/api/image-label-description", "POST",
                         {"sha256": sha, "description": description})
        first, second = [row["id"] for row in reversed(self.rows("wine-a"))]
        status, view = self.request("/api/image-label-description", "DELETE", {"id": second})
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in view["rows"]], [first])
        self.assertEqual(self.request("/api/image-label-description", "DELETE",
                                      {"id": second})[0], 404)
        for body in ({"id": "1"}, {"id": 0}, {"id": True}, {}):
            with self.subTest(body=body):
                self.assertEqual(self.request("/api/image-label-description", "DELETE",
                                              body)[0], 400)
        status, view = self.request("/api/image-label-description", "DELETE", {"id": first})
        self.assertEqual((status, view["rows"], view["latest_id"]), (200, [], None))
        with closing(self.connect()) as conn:
            self.assertIn(sha, [item[0] for item in LD.pending(conn, 3)])


if __name__ == "__main__":
    unittest.main()
