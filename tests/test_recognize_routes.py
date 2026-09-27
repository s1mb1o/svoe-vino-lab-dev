"""Tests of the routes of the Recognize page (plan 55): `pipeline/recognize_routes.py`.

The lab, the fake SAM3, and the fake model come from `test_embedding_run.py`. The script
`recognize.py` is replaced by a function that asks the backend in this process. No test
calls gx10.
"""
import hashlib
import os
import re
import sys
import types
from unittest import mock

import test_embedding_run as TE  # noqa: E402  (puts pipeline/ and scripts/ on sys.path)
import embedding_run  # noqa: E402
import recognize_routes  # noqa: E402

STEP_NAMES = ["Input photo", "Package cut", "Label cut", "View full", "View label",
              "Embedding", "Search, space full", "Search, space label", "Score"]
REMOTE = {"name": "r", "backend": "svoe-vino-ru",
          "url": "http://127.0.0.1:9/v1/wines/search-by-photo"}
NO_INDEX = {"name": "other-pipe", "backend": "embedding", "embedding": "other"}


def no_cards(conn):
    return {}


class RoutesTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = TE.catalogue_lab(self.root)
        self.lab.add_entry("other")
        self.embedding = TE.build(self.lab)
        TE.add_pipelines(self.lab, TE.PIPE, REMOTE, NO_INDEX)
        self.uploads = str(self.root / "uploads")
        self.server = types.SimpleNamespace(config_path=self.lab.config_path,
                                            db_path=self.lab.db_path,
                                            recognize_dir=self.uploads)
        self.calls = []

    def fake_run(self, python, config_path, name, photo):
        """Ask the backend of the pipeline in this process, as `recognize.py` does."""
        self.calls.append((name, photo))
        backend = embedding_run.build_backend(self.embedding, self.lab.db_path,
                                              make_model=lambda e: TE.ColourModel(),
                                              segmenter=TE.FakeSam3(), name=name)
        cands, latency, status, error, trace = backend.ask(photo)
        return ({"spec": backend.spec, "candidates": cands, "latency_ms": latency,
                 "http_status": status, "error": error, "trace": trace, "build_ms": 5.0},
                123.4)

    def post(self, query, body):
        with mock.patch.object(embedding_run, "CachedSam3", TE.FakeSam3), \
                mock.patch.object(recognize_routes, "run_script", self.fake_run), \
                mock.patch.object(recognize_routes.run_jobs, "interpreter",
                                  lambda settings, pipeline: sys.executable):
            return recognize_routes.respond(self.server, "POST", "/api/recognize?" + query,
                                            lambda limit: body, no_cards)

    def get(self, path):
        return recognize_routes.respond(self.server, "GET", path, lambda limit: None, no_cards)


class PipelineListTest(RoutesTest):
    def test_the_list_holds_the_embedding_pipelines_alone(self):
        code, body, _, _ = self.get("/api/recognize")
        self.assertEqual(code, 200)
        rows = {row["name"]: row for row in body["pipelines"]}
        self.assertEqual(list(rows), ["gw-pipe", "other-pipe"])
        self.assertEqual((rows["gw-pipe"]["runnable"], rows["gw-pipe"]["embedding"],
                          rows["gw-pipe"]["barcode"]), (True, "gw", False))
        self.assertEqual((rows["other-pipe"]["runnable"], rows["other-pipe"]["reason"]),
                         (False, embedding_run.NO_INDEX))

    def test_the_page_answers_html(self):
        code, body, ctype, _ = self.get("/recognize")
        self.assertEqual((code, ctype), (200, recognize_routes.HTML_TYPE))
        self.assertIn("const Steps = ", body)
        self.assertNotIn("/* STEPS_JS */", body)

    def test_the_page_keeps_the_navigation_of_the_server(self):
        import lab_server  # noqa: E402  (here alone: the NAV of the pages)
        body = self.get("/recognize")[1]
        nav = re.search(r'<nav class="nav">(.*?)</nav>', body, re.S).group(1)
        self.assertEqual(re.findall(r'href="([^"]*)"', nav), [href for href, _ in lab_server.NAV])
        self.assertIn('class="on"\n      href="/recognize"', nav)


class RecognizeTest(RoutesTest):
    def test_a_photo_gives_the_steps_of_the_pipeline(self):
        data = TE.png(TE.query_photo("green"))
        code, body, _, _ = self.post("pipeline=gw-pipe&name=green.png", data)
        self.assertEqual(code, 200, body)
        digest = hashlib.sha256(data).hexdigest()
        path = os.path.join(self.uploads, digest + ".png")
        self.assertEqual(self.calls, [("gw-pipe", path)])
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), data)
        self.assertEqual((body["pipeline"], body["kind"], body["sha256"], body["recorded"]),
                         ("gw-pipe", "embedding", digest, True))
        self.assertEqual((body["process_ms"], body["build_ms"]), (123.4, 5.0))
        self.assertEqual(body["row"]["image_path"], "green.png")
        steps = [part for one in body["rounds"] for part in one["steps"]]
        self.assertEqual([part["name"] for part in steps], STEP_NAMES)
        self.assertEqual([part["n"] for part in steps], list(range(len(STEP_NAMES))))
        self.assertEqual(steps[0]["artifacts"][0]["src"], "/recognize/photo/%s.png" % digest)
        self.assertTrue(all(part["ms"] is not None for part in steps))
        for view in steps[3:5]:
            self.assertEqual(view["artifacts"][0]["check"], "same")
        self.assertEqual(body["answer"][0]["slug"], "green")
        self.assertFalse(any(item["truth"] for part in steps for group in part["lists"]
                             for item in group["items"]))

    def test_a_second_upload_of_the_same_photo_keeps_the_file(self):
        data = TE.png(TE.query_photo("red"))
        self.assertEqual(self.post("pipeline=gw-pipe", data)[0], 200)
        path = os.path.join(self.uploads, hashlib.sha256(data).hexdigest() + ".png")
        before = os.stat(path).st_mtime_ns
        self.assertEqual(self.post("pipeline=gw-pipe", data)[0], 200)
        self.assertEqual(os.stat(path).st_mtime_ns, before)
        self.assertEqual(os.listdir(self.uploads), [os.path.basename(path)])

    def test_a_bad_request_is_refused(self):
        photo = TE.png(TE.query_photo("green"))
        for query, body, text in (
                ("", photo, "the query holds no pipeline"),
                ("pipeline=nope", photo, "config.yaml has no pipeline nope"),
                ("pipeline=r", photo, "has the backend svoe-vino-ru"),
                ("pipeline=other-pipe", photo, embedding_run.NO_INDEX),
                ("pipeline=gw-pipe", None, "the body MUST be an image"),
                ("pipeline=gw-pipe", b"not an image", "not an image that Pillow can read")):
            code, answer, _, _ = self.post(query, body)
            self.assertEqual(code, 400, (query, answer))
            self.assertIn(text, answer["error"])
        self.assertEqual(self.calls, [])
        self.assertFalse(os.path.exists(self.uploads))

    def test_a_script_failure_gives_503(self):
        def failing(python, config_path, name, photo):
            raise recognize_routes.RecognizeError(503, "no index")

        with mock.patch.object(recognize_routes, "run_script", failing), \
                mock.patch.object(recognize_routes.run_jobs, "interpreter",
                                  lambda settings, pipeline: sys.executable):
            code, body, _, _ = recognize_routes.respond(
                self.server, "POST", "/api/recognize?pipeline=gw-pipe",
                lambda limit: TE.png(TE.query_photo("green")), no_cards)
        self.assertEqual((code, body), (503, {"error": "no index"}))

    def test_other_methods_are_refused(self):
        code, _, _, _ = recognize_routes.respond(self.server, "DELETE", "/api/recognize",
                                                 lambda limit: None, no_cards)
        self.assertEqual(code, 405)


class PhotoRouteTest(RoutesTest):
    def test_an_upload_is_served_and_a_bad_name_is_not(self):
        data = TE.png(TE.query_photo("blue"))
        self.assertEqual(self.post("pipeline=gw-pipe", data)[0], 200)
        digest = hashlib.sha256(data).hexdigest()
        code, body, ctype, cache = self.get("/recognize/photo/%s.png" % digest)
        self.assertEqual((code, body, ctype, cache),
                         (200, data, "image/png", recognize_routes.PHOTO_CACHE))
        self.assertEqual(self.get("/recognize/photo/%s.jpg" % digest)[0], 404)
        self.assertEqual(self.get("/recognize/photo/../config.yaml")[0], 404)
        self.assertEqual(self.get("/recognize/photo/%s.png" % ("0" * 64))[0], 404)


class RunScriptTest(TE.Temporary):
    """`run_script` with a small script in place of `recognize.py`."""

    def script(self, text):
        path = self.root / "fake.py"
        path.write_text(text, encoding="utf-8")
        return mock.patch.object(recognize_routes, "SCRIPT", str(path))

    def test_the_last_line_of_stdout_is_the_answer(self):
        with self.script('print("noise")\nprint(\'{"trace": null, "candidates": []}\')\n'):
            answer, ms = recognize_routes.run_script(sys.executable, "c.yaml", "p", "x.png")
        self.assertEqual(answer, {"trace": None, "candidates": []})
        self.assertGreater(ms, 0)

    def test_an_error_answer_or_no_answer_gives_503(self):
        for text, message in (
                ('import sys\nprint(\'{"error": "no index"}\')\nsys.exit(1)\n', "no index"),
                ('import sys\nsys.stderr.write("boom\\n")\nsys.exit(2)\n',
                 "recognize.py wrote no answer (exit status 2): boom")):
            with self.script(text):
                with self.assertRaises(recognize_routes.RecognizeError) as caught:
                    recognize_routes.run_script(sys.executable, "c.yaml", "p", "x.png")
            self.assertEqual((caught.exception.code, str(caught.exception)), (503, message))


class HandlesTest(TE.Temporary):
    def test_the_routes_of_the_page(self):
        for route in ("/recognize", "/api/recognize", "/recognize/photo/x.png"):
            self.assertTrue(recognize_routes.handles(route), route)
        for route in ("/runs", "/api/recognize-other", "/recognizer"):
            self.assertFalse(recognize_routes.handles(route), route)


if __name__ == "__main__":
    import unittest
    unittest.main()
