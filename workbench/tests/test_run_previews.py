"""Check scoped reads, deferred previews, and current source identities. Use no model service."""
import base64
import io
import json
import os
from pathlib import Path
import types
import threading
import urllib.parse
import urllib.request
from unittest import mock

from PIL import Image

import test_run_steps as TR
import test_embedding_run as TE
import embeddings
import lab_server
import run_routes
import run_steps
from checked_read_cache import CheckedReadCache


class ScopedCardsTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = TE.catalogue_lab(self.root)

    def test_scoped_cards_keep_main_patch_and_derivative_values(self):
        self.lab.image("red", "main_patched", Image.new("RGB", (9, 11), "purple"),
                       folder="patched", derivative=Image.new("RGB", (6, 8), "white"),
                       box=(1, 1, 7, 9))
        all_cards = lab_server.card_images(self.lab.conn)
        queries = []
        self.lab.conn.set_trace_callback(queries.append)
        try:
            selected = lab_server.card_images(self.lab.conn, slugs=["red", "red", "missing"])
        finally:
            self.lab.conn.set_trace_callback(None)
        self.assertEqual(selected, {"red": all_cards["red"]})
        self.assertTrue(selected["red"]["_patch_image_url"].startswith("/images/cropped/"))
        self.assertEqual(len(queries), 1)
        self.assertIn("AND w.wine_slug IN ('missing', 'red')", queries[0])

    def test_an_empty_scope_performs_no_catalogue_query(self):
        queries = []
        self.lab.conn.set_trace_callback(queries.append)
        try:
            self.assertEqual(lab_server.card_images(self.lab.conn, slugs=[]), {})
        finally:
            self.lab.conn.set_trace_callback(None)
        self.assertEqual(queries, [])


class PreviewTest(TR.StepsTest):
    def setUp(self):
        super().setUp()
        run_steps.INDEX_STATES.clear()
        run_steps.THUMBNAILS.clear()
        self.run_dir, rows = self.run_set()
        self.row = rows["green/01.png"]
        self.rows = TR.read_rows(self.run_dir)
        row = next(one for one in self.rows if one["query_id"] == self.row["query_id"])
        record = next(part for part in row["trace"]["steps"]
                      if part["id"] == "search" and part["view"] == "full")
        self.hit = record["out"]["top"][0]
        self.hit["angle"] = 90
        TR.write_rows(self.run_dir, self.rows)
        self.run_id = os.path.basename(self.run_dir)
        self.server = types.SimpleNamespace(db_path=self.lab.db_path, runs_dir=self.runs)
        self.path = Path(embeddings.entry_dir(self.lab.db_path, "gw")) / embeddings.IMAGES / \
            embeddings.image_name(self.hit["sha256"], "full")

    def popup(self):
        query = {"id": [self.run_id], "query": [self.row["query_id"]]}
        scoped = mock.Mock(wraps=lab_server.card_images)
        with mock.patch.object(run_steps.embedding_run, "CachedSam3", TE.FakeSam3), \
                mock.patch.object(embeddings, "image_names", side_effect=AssertionError("directory scan")):
            status, body, _, _ = run_routes.steps_view(
                self.runs, self.lab.db_path, query,
                mock.Mock(side_effect=AssertionError("complete catalogue read")),
                card_images_for_slugs=scoped)
        self.assertEqual(status, 200, body)
        slugs = {item["slug"] for one in body["rounds"] for part in one["steps"]
                 for group in part["lists"] for item in group["items"]}
        self.assertEqual(scoped.call_args.kwargs["slugs"], slugs)
        return body

    def first(self, body):
        part = next(part for part in self.all_steps(body) if part.get("view") == "full"
                    and part["id"] == "search")
        return part["lists"][0]["items"][0]

    def preview(self, url):
        return run_routes.respond(self.server, "GET", url, lab_server.card_images)

    def test_the_popup_checks_required_paths_and_decodes_no_candidate_image(self):
        with mock.patch.object(run_steps.derive, "open_image", wraps=run_steps.derive.open_image) as read, \
                mock.patch.object(embeddings, "read_index", wraps=embeddings.read_index) as index:
            body = self.popup()
            self.assertEqual(self.popup(), body)
            self.assertEqual(index.call_count, 1)
        self.assertNotIn(str(self.path), [str(call.args[0]) for call in read.call_args_list])
        item = self.first(body)
        self.assertTrue(item["image"].startswith("/api/run-preview?"))
        self.assertTrue(item["image_deferred"])
        self.assertEqual(item["image_fallback"], lab_server.card_images(self.lab.conn)[item["slug"]]["main_image_url"])

    def test_preview_bytes_keep_the_previous_rotation_and_reuse_the_thumbnail(self):
        expected = base64.b64decode(run_steps._item_image(
            self.lab.db_path, "gw", self.hit, "full").split(",", 1)[1])
        run_steps.THUMBNAILS.clear()
        url = self.first(self.popup())["image"]
        with mock.patch.object(run_steps.derive, "open_image", wraps=run_steps.derive.open_image) as read:
            status, data, ctype, cache = self.preview(url)
            self.assertEqual(self.preview(url)[1], data)
            self.assertEqual(read.call_count, 1)
        self.assertEqual((status, ctype, cache, data), (200, "image/png", "no-store", expected))
        with Image.open(io.BytesIO(data)) as image, Image.open(self.path) as source:
            self.assertEqual(image.size, (source.height, source.width))

    def test_missing_or_corrupt_prepared_images_have_a_card_fallback(self):
        item = self.first(self.popup())
        self.path.unlink()
        self.assertEqual(self.preview(item["image"])[0], 404)
        current = self.first(self.popup())
        self.assertEqual(current["image"], item["image_fallback"])
        self.assertNotIn("image_deferred", current)
        self.path.write_bytes(b"invalid PNG")
        self.assertEqual(self.preview(item["image"])[0], 404)

    def test_prepared_file_replacement_changes_the_preview_even_with_the_same_mtime(self):
        item = self.first(self.popup())
        first = self.preview(item["image"])[1]
        before = self.path.stat()
        replacement = self.path.with_suffix(".new")
        Image.new("RGB", (20, 40), "purple").save(replacement, "PNG")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.path)
        status, data, _, _ = self.preview(item["image"])
        self.assertEqual(status, 200)
        self.assertNotEqual(data, first)
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (40, 20))

    def test_index_replacement_invalidates_a_preview_and_the_popup_status(self):
        item = self.first(self.popup())
        path = Path(embeddings.entry_dir(self.lab.db_path, "gw")) / embeddings.INDEX
        index = embeddings.read_index(path.parent)
        for record in index["items"]:
            if record["source_sha256"] == self.hit["sha256"] and record["view"] == "full":
                record["embedding_hash"] = "changed"
        before = path.stat()
        replacement = path.with_suffix(".new")
        replacement.write_text(json.dumps(index))
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(path)
        self.assertEqual(self.preview(item["image"])[0], 404)
        current = self.first(self.popup())
        self.assertEqual(current["image"], item["image_fallback"])

    def test_a_changed_record_rejects_the_old_preview_reference(self):
        url = self.first(self.popup())["image"]
        self.hit["angle"] = -5
        TR.write_rows(self.run_dir, self.rows)
        self.assertEqual(self.preview(url)[0], 404)
        changed = self.first(self.popup())["image"]
        self.assertNotEqual(changed, url)
        self.assertEqual(self.preview(changed)[0], 200)

    def test_a_source_change_during_render_is_rejected(self):
        url = self.first(self.popup())["image"]
        original = run_steps._item_image
        def unstable(*args):
            result = original(*args)
            Image.new("RGB", (21, 42), "purple").save(self.path)
            return result
        with mock.patch.object(run_steps, "_item_image", side_effect=unstable):
            self.assertEqual(self.preview(url)[0], 404)

    def test_preview_parameters_cannot_select_an_arbitrary_path_or_unrecorded_hit(self):
        url = self.first(self.popup())["image"]
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parts.query)
        for field, value, status in (("view", "../../outside", 400), ("rank", "0", 400),
                                     ("rank", "99999", 404), ("rank", "-1", 400),
                                     ("token", "0" * 64, 404), ("id", "../../outside", 404),
                                     ("query", "unknown", 404)):
            changed = dict(query, **{field: [value]})
            path = parts.path + "?" + urllib.parse.urlencode(changed, doseq=True)
            self.assertEqual(self.preview(path)[0], status, (field, value))
        self.assertEqual(run_routes.respond(self.server, "POST", url, lab_server.card_images)[0], 405)

    def test_missing_or_corrupt_indexes_do_not_mark_an_unindexed_hit_as_current(self):
        item = self.first(self.popup())
        path = Path(embeddings.entry_dir(self.lab.db_path, "gw")) / embeddings.INDEX
        path.write_text("invalid JSON")
        self.assertEqual(self.preview(item["image"])[0], 404)
        self.assertEqual(self.first(self.popup())["image"], item["image_fallback"])
        path.unlink()
        self.assertEqual(self.preview(item["image"])[0], 404)
        self.assertFalse(run_steps._item_available(self.lab.db_path, "gw",
                         {"sha256": self.hit["sha256"]}, "full", {}))

    def test_index_cache_limits_fall_back_to_live_reads(self):
        small = CheckedReadCache(max_entries=1, max_bytes=1)
        with mock.patch.object(run_steps, "INDEX_STATES", small), \
                mock.patch.object(embeddings, "read_index", wraps=embeddings.read_index) as read:
            first = self.popup()
            self.assertEqual(self.popup(), first)
            self.assertEqual(read.call_count, 2)
        self.assertEqual(small._bytes, 0)

    def test_card_names_and_fallbacks_stay_live(self):
        item = self.first(self.popup())
        with self.lab.conn:
            self.lab.conn.execute("UPDATE wine_catalog SET name_patched='Current name' WHERE wine_slug=?",
                                  (item["slug"],))
        self.lab.image(item["slug"], "main_patched", Image.new("RGB", (6, 8), "purple"), folder="patched")
        updated = self.first(self.popup())
        self.assertEqual(updated["name"], "Current name")
        self.assertNotEqual(updated["image_fallback"], item["image_fallback"])

    def test_the_http_handler_serves_binary_preview_get_and_head(self):
        url = self.first(self.popup())["image"]
        expected = self.preview(url)[1]
        server = lab_server.make_server(self.lab.db_path, port=0)
        server.runs_dir = self.runs
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:%d" % server.server_port
            for method in ("GET", "HEAD"):
                with urllib.request.urlopen(urllib.request.Request(base + url, method=method)) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers["Content-Type"], "image/png")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertEqual(int(response.headers["Content-Length"]), len(expected))
                    self.assertEqual(response.read(), expected if method == "GET" else b"")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
