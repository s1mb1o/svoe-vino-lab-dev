import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import website_import_routes as ROUTES  # noqa: E402

# A fake `import_website.py`: `--prepare DIR` writes a diff with one conflict and one
# image, `--apply DIR` writes an ok result. The environment variable FAKE_SLEEP makes it
# wait first, and FAKE_FAIL makes the compare fail.
FAKE_SCRIPT = r'''
import json, os, sys, time
args = sys.argv[1:]
mode, directory = args[2], args[3]
time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
print("list: page 1/1, 1 wines", flush=True)
print("images: 1/1", flush=True)
if mode == "--prepare":
    if os.environ.get("FAKE_FAIL"):
        print("error: the compare stops. 1 problems:", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.join(directory, "images"), exist_ok=True)
    with open(os.path.join(directory, "images", "%s.png" % ("a" * 64)), "wb") as fh:
        fh.write(b"PNG")
    diff = {"created_at": "2026-09-25T10:00:00Z", "website": 1, "images": 1,
            "refused": 0, "problems": [], "stale": [], "times": {},
            "conflicts": [{"id": "text:a:name", "slug": "a", "kind": "text",
                           "field": "name", "database": "A", "website": "B"}],
            "changes": [{"id": "new:n", "slug": "n", "kind": "new"}]}
    with open(os.path.join(directory, "diff.json"), "w") as fh:
        json.dump(diff, fh)
else:
    with open(os.path.join(directory, "choices.json")) as fh:
        choices = json.load(fh)
    with open(os.path.join(directory, "result.json"), "w") as fh:
        json.dump({"ok": True, "added": [], "choices": choices}, fh)
'''


class FakeServer:
    def __init__(self, db_path):
        self.db_path = db_path


class WebsiteImportRoutesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        script = self.root / "fake_import.py"
        script.write_text(FAKE_SCRIPT, encoding="utf-8")
        self.saved = ROUTES.WORK, ROUTES.SCRIPT
        ROUTES.WORK, ROUTES.SCRIPT = str(self.root / "work"), str(script)
        self.server = FakeServer(str(self.root / "lab.sqlite3"))
        os.environ.pop("FAKE_SLEEP", None)
        os.environ.pop("FAKE_FAIL", None)

    def tearDown(self):
        for process in list(ROUTES._PROCESSES.values()):
            if process.poll() is None:
                process.kill()
            process.wait()
        ROUTES._PROCESSES.clear()
        ROUTES.WORK, ROUTES.SCRIPT = self.saved
        os.environ.pop("FAKE_SLEEP", None)
        os.environ.pop("FAKE_FAIL", None)
        self.directory.cleanup()

    def call(self, method, path, body=None):
        raw = None if body is None else json.dumps(body).encode("utf-8")
        return ROUTES.respond(self.server, method, path,
                              lambda limit: raw if raw is not None and len(raw) <= limit else None)

    def wait(self, *states):
        for _ in range(200):
            code, answer, _, _ = self.call("GET", ROUTES.API)
            if answer["state"] in states:
                return answer
            time.sleep(0.05)
        self.fail("the job did not reach %s: %s" % (states, answer))

    def test_handles_its_routes_alone(self):
        for route in ("/api/website-import", "/api/website-import/start",
                      "/website-import/20260925T100000/images/x.png", "/website-import.js"):
            self.assertTrue(ROUTES.handles(route), route)
        for route in ("/api/dataset", "/website-importer", "/dataset"):
            self.assertFalse(ROUTES.handles(route), route)

    def test_no_run_gives_the_state_none(self):
        self.assertEqual(self.call("GET", ROUTES.API)[:2], (200, {"state": "none"}))

    def test_a_compare_then_an_apply(self):
        code, answer, _, _ = self.call("POST", ROUTES.API + "/start")
        self.assertEqual((code, answer["state"], answer["phase"]), (202, "running", "prepare"))
        run = answer["run"]
        state = self.wait("prepared")
        self.assertEqual(state["counts"], {"conflicts": 1, "changes": {"new": 1},
                                           "refused": 0, "website": 1})
        self.assertEqual(state["progress"], "images: 1/1")
        code, diff, _, _ = self.call("GET", "%s/%s/diff" % (ROUTES.API, run))
        self.assertEqual((code, diff["run"], len(diff["conflicts"])), (200, run, 1))
        self.assertEqual(diff["renames"], [])
        code, data, ctype, cache = self.call("GET", "/website-import/%s/images/%s.png"
                                             % (run, "a" * 64))
        self.assertEqual((code, data, ctype), (200, b"PNG", "image/png"))
        self.assertIn("immutable", cache)
        self.assertEqual(self.call("GET", "/website-import/%s/images/%s.png"
                                   % (run, "b" * 64))[0], 404)

        code, answer, _, _ = self.call("POST", "%s/%s/apply" % (ROUTES.API, run),
                                       {"conflicts": {"text:a:name": "maybe"}})
        self.assertEqual(code, 400)
        self.assertIn("text:a:name need database or website", answer["error"])
        choices = {"conflicts": {"text:a:name": "website"}, "changes": {"new:n": False}}
        code, answer, _, _ = self.call("POST", "%s/%s/apply" % (ROUTES.API, run), choices)
        self.assertEqual((code, answer["phase"]), (202, "apply"))
        state = self.wait("applied")
        self.assertEqual(state["result"]["choices"], choices)
        saved = json.loads((Path(ROUTES.WORK) / run / "choices.json").read_text())
        self.assertEqual(saved, choices)
        code, answer, _, _ = self.call("POST", "%s/%s/apply" % (ROUTES.API, run), choices)
        self.assertEqual(code, 409)

    def test_one_job_at_a_time_and_stop(self):
        os.environ["FAKE_SLEEP"] = "30"
        self.assertEqual(self.call("POST", ROUTES.API + "/start")[0], 202)
        time.sleep(1.1)
        code, answer, _, _ = self.call("POST", ROUTES.API + "/start")
        self.assertEqual(code, 409)
        self.assertIn("a website import runs", answer["error"])
        self.assertEqual(self.call("GET", ROUTES.API)[1]["state"], "running")
        code, answer, _, _ = self.call("POST", ROUTES.API + "/stop")
        self.assertEqual((code, answer["state"]), (202, "stopping"))
        state = self.wait("failed")
        self.assertEqual(state["phase"], "prepare")
        self.assertEqual(self.call("POST", ROUTES.API + "/stop")[0], 409)

    def test_a_failed_compare_shows_its_error(self):
        os.environ["FAKE_FAIL"] = "1"
        self.call("POST", ROUTES.API + "/start")
        state = self.wait("failed")
        self.assertIn("the compare stops", state["error"])

    def test_the_methods_and_unknown_runs(self):
        self.assertEqual(self.call("POST", ROUTES.API)[0], 405)
        self.assertEqual(self.call("GET", ROUTES.API + "/start")[0], 405)
        self.assertEqual(self.call("GET", ROUTES.API + "/20260101T000000/diff")[0], 404)
        self.assertEqual(self.call("GET", ROUTES.API + "/../diff")[0], 404)
        code, text, ctype, _ = self.call("GET", ROUTES.SCRIPT_ROUTE)
        self.assertEqual((code, ctype), (200, "text/javascript; charset=utf-8"))
        self.assertIn("website-import", text)


if __name__ == "__main__":
    unittest.main()
