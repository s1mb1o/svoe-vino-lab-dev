"""Check vintage-link HTTP validation and independent Dataset fields."""
import json
import sqlite3
import urllib.parse
import unittest
import test_lab_server as LS
class VintageRouteTest(unittest.TestCase):
    """The manual pairs of two vintage wines: plan 62."""

    setUp = LS.LabServerTest.setUp
    tearDown = LS.LabServerTest.tearDown
    request = LS.LabServerTest.request

    def post_vintage(self, slug, other):
        status, _, body = self.request("/api/dataset-vintage", "POST", json.dumps(
            {"slug": slug, "other": other}).encode())
        return status, json.loads(body)

    def delete_vintage(self, slug, other):
        query = urllib.parse.urlencode({"slug": slug, "other": other})
        status, _, body = self.request("/api/dataset-vintage?" + query, "DELETE")
        return status, json.loads(body)

    def dataset(self):
        return json.loads(self.request("/api/dataset")[2])

    def test_a_pair_shows_on_both_wines(self):
        data = self.dataset()
        self.assertEqual((data["vintage_editor"], data["vintage_pairs"]), (True, 0))
        self.assertEqual([r["_vintages"] for r in data["records"]], [[], []])
        # wine-a is Removed. A pair MAY hold a wine of each state.
        status, body = self.post_vintage("wine-b", "wine-a")
        self.assertEqual((status, body), (200, {
            "ok": True, "slug": "wine-b", "other": "wine-a", "added": ["wine-a", "wine-b"],
            "vintages": ["wine-a"], "other_vintages": ["wine-b"], "total": 1}))
        data = self.dataset()
        self.assertEqual(data["vintage_pairs"], 1)
        self.assertEqual({r["slug"]: r["_vintages"] for r in data["records"]},
                         {"wine-b": ["wine-a"], "wine-a": ["wine-b"]})
        # The pair has no direction: the other order is the same pair.
        self.assertEqual(self.post_vintage("wine-a", "wine-b")[0], 409)
        status, body = self.delete_vintage("wine-a", "wine-b")
        self.assertEqual((status, body["removed"], body["vintages"], body["other_vintages"],
                          body["total"]), (200, ["wine-a", "wine-b"], [], [], 0))
        self.assertEqual([r["_vintages"] for r in self.dataset()["records"]], [[], []])

    def test_vintage_errors(self):
        cases = ((self.post_vintage("", "wine-a"), 400, "two wine slugs"),
                 (self.post_vintage("wine-a", None), 400, "two wine slugs"),
                 (self.post_vintage("wine-a", "wine-a"), 400, "itself"),
                 (self.post_vintage("wine-none", "wine-a"), 404, "no wine with the slug wine-none"),
                 (self.post_vintage("wine-a", "wine-none"), 404, "no wine with the slug wine-none"),
                 (self.delete_vintage("wine-a", "wine-b"), 404, "have no vintage link"))
        for (status, body), code, text in cases:
            with self.subTest(text=text):
                self.assertEqual(status, code)
                self.assertIn(text, body["error"])
        self.assertEqual(self.request("/api/dataset-vintage", "POST", b"not json")[0], 400)
        self.assertEqual(self.request("/api/dataset-vintage", "PUT")[0], 405)
        self.assertEqual(self.dataset()["vintage_pairs"], 0)


    def test_the_relation_does_not_add_hard_cases_or_tags(self):
        status, body = self.post_vintage("wine-a", "wine-b")
        self.assertEqual(status, 200, body)
        data = self.dataset()
        self.assertEqual(data["similar_pairs"], 0)
        for record in data["records"]:
            self.assertEqual(record["_similar"], [])
            self.assertEqual(record["_tags"], [])

    def test_invalid_types_and_surrogates_return_400(self):
        for value in [True, [], {}, "\ud800"]:
            with self.subTest(value=value):
                self.assertEqual(self.post_vintage("wine-a", value)[0], 400)
        self.assertEqual(self.request("/api/dataset-vintage")[0], 405)
        self.assertEqual(self.dataset()["vintage_pairs"], 0)

    def test_a_failed_write_rolls_back_the_link(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TRIGGER reject_vintage AFTER INSERT ON wine_vintage "
                         "BEGIN SELECT RAISE(ABORT, 'private test'); END")
        self.assertEqual(self.post_vintage("wine-a", "wine-b")[0], 503)
        self.assertEqual(self.dataset()["vintage_pairs"], 0)


if __name__ == '__main__':
    unittest.main()
