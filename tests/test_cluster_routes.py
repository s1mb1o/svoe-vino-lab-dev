import json
import tempfile
import unittest
from types import SimpleNamespace

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from test_clusters import ClusterLab

import cluster_routes  # noqa: E402
import clusters  # noqa: E402
import lab_pages  # noqa: E402


class FakeProcess:
    pid = 4321


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = ClusterLab(self.tmp.name)
        self.server = SimpleNamespace(config_path=self.fixture.lab.config_path)
        # A note write starts the rule rebuild as a process (plan 45); the test records
        # the command and starts nothing.
        self.started = []
        self.old_popen = cluster_routes.subprocess.Popen
        cluster_routes.subprocess.Popen = lambda command, **options: (
            self.started.append((command, options)) or FakeProcess())

    def tearDown(self):
        cluster_routes.subprocess.Popen = self.old_popen
        self.fixture.close()
        self.tmp.cleanup()

    def request(self, path, method="GET", value=None, raw=None):
        body = raw if raw is not None else json.dumps(value or {}).encode("utf-8")
        return cluster_routes.respond(
            self.server, method, path, lambda limit: body if len(body) <= limit else None)

    def test_handles_only_cluster_routes(self):
        for route in ("/clusters", "/api/clusters", "/api/clusters/gw",
                      "/api/clusters/gw/build", "/api/clusters/gw/nothing"):
            self.assertTrue(cluster_routes.handles(route), route)
        for route in ("/cluster", "/dataset", "/api/cluster", "/clusters/x"):
            self.assertFalse(cluster_routes.handles(route), route)

    def test_page_uses_the_shared_theme(self):
        code, body, content_type, cache = self.request("/clusters")
        self.assertEqual((code, body), (200, lab_pages.page("clusters.html")))
        self.assertIn("text/html", content_type)
        self.assertEqual(cache, "no-store")
        self.assertIn('class="on" href="/clusters"', body)
        self.assertNotIn("/* THEME_CSS */", body)

    def test_list_and_detail_before_a_build(self):
        code, body, _, _ = self.request("/api/clusters")
        self.assertEqual(code, 200)
        self.assertEqual(body["embeddings"][0]["name"], "gw")
        self.assertFalse(body["embeddings"][0]["exists"])
        code, body, _, _ = self.request("/api/clusters/gw")
        self.assertEqual(code, 200)
        self.assertIsNone(body["artifact"])
        self.assertFalse(body["status"]["exists"])

    def test_build_detail_and_note(self):
        code, answer, _, _ = self.request("/api/clusters/gw/build", "POST", {})
        self.assertEqual(code, 201)
        self.assertEqual(answer["settings"], {"full_threshold": 0.95, "label_threshold": 0.95,
                                              "min_cluster_size": 2})
        self.assertEqual(answer["embedding"], "gw")
        self.assertGreater(answer["counts"]["combined"]["clusters"], 0)

        code, detail, _, _ = self.request("/api/clusters/gw")
        self.assertEqual(code, 200)
        self.assertFalse(detail["status"]["stale"])
        cluster = detail["artifact"]["spaces"]["full"]["clusters"][0]
        code, answer, _, _ = self.request(
            "/api/clusters/gw/note", "POST",
            {"space": "full", "key": cluster["key"], "text": "Review this pair."})
        self.assertEqual(code, 200)
        self.assertEqual(answer["note"]["text"], "Review this pair.")
        shown = self.request("/api/clusters/gw")[1]
        note = shown["artifact"]["spaces"]["full"]["clusters"][0]["note"]
        self.assertEqual(note["text"], "Review this pair.")

    def test_a_note_write_starts_the_rule_rebuild(self):
        self.request("/api/clusters/gw/build", "POST", {})
        detail = self.request("/api/clusters/gw")[1]
        cluster = detail["artifact"]["spaces"]["combined"]["clusters"][0]
        code, answer, _, _ = self.request(
            "/api/clusters/gw/note", "POST",
            {"space": "combined", "key": cluster["key"], "text": "Look at the ratio."})
        self.assertEqual(code, 200)
        self.assertEqual(answer["rule_rebuild"]["started"], True)
        self.assertEqual(answer["rule_rebuild"]["pid"], 4321)
        self.assertEqual(len(self.started), 1)
        command, options = self.started[0]
        self.assertTrue(command[1].endswith("build_label_rules.py"))
        self.assertEqual(command[2:], ["--config", self.fixture.lab.config_path, "--name", "gw",
                                       "--cluster", cluster["slugs"][0], "--wait"])
        self.assertTrue(options["start_new_session"])
        with open(answer["rule_rebuild"]["log"], encoding="utf-8") as fh:
            self.assertIn("note of %s" % cluster["key"], fh.read())

    def test_a_note_is_kept_when_the_rebuild_cannot_start(self):
        def refuse(command, **options):
            raise OSError("no such interpreter")
        cluster_routes.subprocess.Popen = refuse
        self.request("/api/clusters/gw/build", "POST", {})
        cluster = self.request("/api/clusters/gw")[1]["artifact"]["spaces"]["combined"][
            "clusters"][0]
        code, answer, _, _ = self.request(
            "/api/clusters/gw/note", "POST",
            {"space": "combined", "key": cluster["key"], "text": "Keep me."})
        self.assertEqual(code, 200)
        self.assertEqual(answer["note"]["text"], "Keep me.")
        self.assertEqual(answer["rule_rebuild"],
                         {"started": False, "error": "no such interpreter"})

    def test_methods_unknown_routes_and_bad_bodies(self):
        self.assertEqual(self.request("/clusters", "POST")[0], 405)
        self.assertEqual(self.request("/api/clusters", "POST")[0], 405)
        self.assertEqual(self.request("/api/clusters/gw/build")[0], 405)
        self.assertEqual(self.request("/api/clusters/absent")[0], 404)
        self.assertEqual(self.request("/api/clusters/gw/other")[0], 404)
        self.assertEqual(self.request(
            "/api/clusters/gw/build", "POST", raw=b"[]")[0], 400)
        code, body, _, _ = self.request(
            "/api/clusters/gw/build", "POST", {"full_threshold": 0.95})
        self.assertEqual(code, 400)
        self.assertIn("come from the block `clusters` of config.yaml", body["error"])
        self.fixture.set_clusters({"max_links": 0})
        code, body, _, _ = self.request("/api/clusters/gw/build", "POST", {})
        self.assertEqual(code, 400)
        self.assertIn("clusters.max_links MUST", body["error"])

    def test_note_requires_an_existing_current_cluster(self):
        code, body, _, _ = self.request(
            "/api/clusters/gw/note", "POST",
            {"space": "full", "key": "missing", "text": "x"})
        self.assertEqual(code, 409)
        self.assertIn("build them first", body["error"])
        self.request("/api/clusters/gw/build", "POST")
        self.assertEqual(self.request(
            "/api/clusters/gw/note", "POST",
            {"space": "full", "key": "missing", "text": "x"})[0], 404)
        self.assertEqual(self.request(
            "/api/clusters/gw/note", "POST",
            {"space": "wrong", "key": "missing", "text": "x"})[0], 400)


if __name__ == "__main__":
    unittest.main()
