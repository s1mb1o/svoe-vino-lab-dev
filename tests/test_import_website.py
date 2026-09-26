import contextlib
import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import derive  # noqa: E402
import import_website as IMP  # noqa: E402
import labdb  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def picture(seed):
    """Return the PNG bytes of a small picture with a transparent border, so its
    processing is a crop and needs no SAM3. Each seed gives other bytes."""
    image = Image.new("RGBA", (4, 6), (0, 0, 0, 0))
    image.paste((seed % 256, seed // 256 % 256, 0, 255), (1, 1, 3, 5))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class FakeSam3:
    """A SAM3 client with no network."""

    def segment(self, image):
        raise derive.Sam3Unavailable("the fake service is down")


class FakeClient:
    """The API of the website as a dict of address -> body. A missing address is an
    HTTP error. `hook` runs before each image request."""

    def __init__(self, items, images, cards=None, per_page=2, total=None, times=None):
        self.bodies = {}
        self.hook = None
        times = times or {}
        self.bodies[IMP.SITEMAP_URL] = (
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/'
            'schemas/sitemap/0.9">%s</urlset>' % "".join(
                "<url><loc>https://vino-svoe.ru/wines/%s</loc><lastmod>%s</lastmod></url>"
                % (row["slug"], times.get(row["slug"], LASTMOD)) for row in items))
        pages = [items[i:i + per_page] for i in range(0, len(items), per_page)] or [[]]
        for number, rows in enumerate(pages, 1):
            self.bodies[IMP.LIST_URL % (number, IMP.PER_PAGE)] = json.dumps({
                "currentPage": number, "itemsPerPage": per_page,
                "totalItems": len(items) if total is None else total,
                "totalPages": len(pages) if items else 0, "items": rows})
        for url, data in images.items():
            self.bodies[IMP.file_url(url)] = data
        for slug, card in (cards or {}).items():
            self.bodies[IMP.CARD_URL % slug] = json.dumps(card)
        self.requests = 0
        self.bytes = 0

    def get(self, url, accept="application/json"):
        if accept.startswith("image") and self.hook:
            self.hook()
        if url not in self.bodies:
            raise IMP.FetchError("%s: HTTP Error 404: Not Found" % url)
        body = self.bodies[url]
        body = body.encode("utf-8") if isinstance(body, str) else body
        self.requests += 1
        self.bytes += len(body)
        return body

    def get_json(self, url):
        return json.loads(self.get(url).decode("utf-8"))


LASTMOD = "2026-09-01T10:00:00.000Z"


def item(slug, upload=None, **values):
    """A list item of the API. The values fit `wine()` of the database."""
    row = {"slug": slug, "title": " Вино " + slug, "manufacturer": "Винодельня",
           "category": "Белое сухое", "color": "Соломенный", "region": "Крым",
           "image": {"altText": slug, "url": "/uploads/%s" % (upload or slug + "_0a1b2c3d4e.png")},
           "publicRating": 5}
    row.update(values)
    return row


def card(slug, **values):
    row = {"slug": slug, "description": "Описание %s\n" % slug,
           "grapes": [{"name": "Алиготе"}, {"name": " Кокур Белый"}]}
    row.update(values)
    return row


class WebsiteTestBase(unittest.TestCase):
    """The database and the helpers of the tests. It holds no test."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        labdb.connect(self.db, create=True).close()
        self.log = []

    def tearDown(self):
        self.directory.cleanup()

    def add_wine(self, slug, state="Active", removed_by=None, main=None, **values):
        row = {"name": "Вино " + slug, "producer": "Винодельня", "category": "Белое",
               "color": "Соломенный", "region": "Крым", "grapes": "Алиготе",
               "description": "Описание " + slug, "csv_photo_name": slug + ".png"}
        row.update(values)
        conn = labdb.connect(self.db)
        with conn:
            conn.execute(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, grapes, description, csv_photo_name, state, removed_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (slug, row["name"], row["producer"], row["category"], row["color"],
                 row["region"], row["grapes"], row["description"], row["csv_photo_name"],
                 state, removed_by))
            if main is not None:
                conn.execute("INSERT INTO image (sha256, folder, extension) VALUES "
                             "(?, 'main', 'png') ON CONFLICT DO NOTHING", (sha(main),))
                conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                             "source_name, match_method) VALUES (?, 'main', ?, ?, "
                             "'name-unique')", (slug, sha(main), slug + "_0a1b2c3d4e.png"))
        conn.close()

    def run_import(self, client):
        return IMP.import_website(self.db, client, FakeSam3(), self.log.append)

    def query(self, sql, args=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def states(self):
        return {slug: (state, removed_by) for slug, state, removed_by in self.query(
            "SELECT wine_slug, state, removed_by FROM wine_catalog")}

    def notes(self):
        return {(slug, source, text) for slug, source, text in self.query(
            "SELECT wine_slug, source, text FROM wine_comment")}

    def snapshot(self):
        return [self.query("SELECT * FROM %s ORDER BY 1" % table) for table in
                ("wine_catalog", "image", "wine_image", "image_derivative", "wine_comment")]

    def store_files(self):
        store = self.root / "images"
        return sorted(p.name for p in store.rglob("*") if p.is_file()) if store.exists() else []

    def site(self, slugs, pictures, cards=None, **options):
        items = [item(slug) for slug in slugs]
        images = {"/uploads/%s_0a1b2c3d4e.png" % slug: pictures[slug] for slug in slugs}
        return FakeClient(items, images, cards, **options)


class ImportWebsiteTest(WebsiteTestBase):
    def test_new_missing_back_and_main(self):
        pics = {slug: picture(n) for n, slug in enumerate("acefgn", 1)}
        self.add_wine("a", main=pics["a"])
        self.add_wine("b", state="Disabled", main=picture(20))
        self.add_wine("c", state="Removed", removed_by="person", main=pics["c"])
        self.add_wine("d", state="Removed", removed_by="import")
        self.add_wine("e")
        self.add_wine("f", state="Disabled", main=pics["f"])
        self.add_wine("g", state="Removed", removed_by="import", main=pics["g"])
        self.add_wine("h")
        client = self.site("acefgn", pics, {"n": card("n")})

        report = self.run_import(client)

        self.assertEqual(report.added, ["n"])
        self.assertEqual(report.restored, ["c", "g"])
        self.assertEqual(report.removed, ["b", "h"])
        self.assertEqual(report.mains, ["e"])
        self.assertEqual(report.unchanged, 2)
        self.assertEqual(report.images, 6)
        self.assertEqual(self.states(), {
            "a": ("Active", None), "b": ("Removed", "import"), "c": ("Active", None),
            "d": ("Removed", "import"), "e": ("Active", None), "f": ("Disabled", None),
            "g": ("Active", None), "h": ("Removed", "import"), "n": ("Active", None)})
        self.assertEqual(self.notes(), {
            ("n", "script", IMP.COMMENT_NEW), ("c", "script", IMP.COMMENT_BACK),
            ("g", "script", IMP.COMMENT_BACK), ("b", "script", IMP.COMMENT_MISSING),
            ("h", "script", IMP.COMMENT_MISSING), ("e", "script", IMP.COMMENT_MAIN)})
        self.assertEqual(self.query(
            "SELECT name, producer, category, color, region, grapes, description, "
            "csv_photo_name FROM wine_catalog WHERE wine_slug = 'n'"),
            [("Вино n", "Винодельня", "Белое", "Соломенный", "Крым", "Алиготе, Кокур Белый",
              "Описание n", "n_0a1b2c3d4e.png")])
        self.assertEqual(sorted(self.query(
            "SELECT wine_slug, sha256, source_name, match_method FROM wine_image "
            "WHERE match_method = 'website'")),
            [("e", sha(pics["e"]), "e_0a1b2c3d4e.png", "website"),
             ("n", sha(pics["n"]), "n_0a1b2c3d4e.png", "website")])
        self.assertEqual(self.query("SELECT folder, extension, width, height FROM image "
                                    "WHERE sha256 = ?", (sha(pics["n"]),)),
                         [("main", "png", 4, 6)])
        self.assertTrue((self.root / "images" / "main" / (sha(pics["n"]) + ".png")).exists())
        self.assertEqual(report.derivatives.methods["crop"], 2)
        self.assertEqual(len(self.query("SELECT * FROM image_derivative")), 2)

    def test_a_returned_wine_with_no_main_gets_both_comments(self):
        self.add_wine("a", main=picture(1))
        self.add_wine("c", state="Removed", removed_by="import")
        report = self.run_import(self.site("ac", {"a": picture(1), "c": picture(2)}))
        self.assertEqual((report.restored, report.mains, report.unchanged), (["c"], ["c"], 1))
        self.assertEqual(self.notes(), {("c", "script", IMP.COMMENT_BACK),
                                        ("c", "script", IMP.COMMENT_MAIN)})

    def test_a_manual_wine_is_never_removed(self):
        self.add_wine("a", main=picture(1))
        self.add_wine("__hand", main=picture(2))
        self.add_wine("__gone", state="Disabled")
        report = self.run_import(self.site("a", {"a": picture(1)}))
        self.assertEqual(report.removed, [])
        self.assertEqual(self.states(), {"a": ("Active", None), "__hand": ("Active", None),
                                         "__gone": ("Disabled", None)})
        self.assertEqual(self.notes(), set())

    def test_a_website_slug_with_the_manual_prefix_stops(self):
        self.add_wine("a", main=picture(1))
        self.add_wine("h")
        before = self.snapshot()
        client = self.site(["a", "__x"], {"a": picture(1), "__x": picture(2)},
                           {"__x": card("__x")})
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("__x: a website slug starts with '__'", str(caught.exception))
        self.assertEqual(self.snapshot(), before)

    def test_second_run_changes_nothing(self):
        pics = {"a": picture(1), "n": picture(2)}
        self.add_wine("a")
        self.add_wine("h")
        self.run_import(self.site("an", pics, {"n": card("n")}))
        before = self.snapshot()

        report = self.run_import(self.site("an", pics, {"n": card("n")}))

        self.assertTrue(report.empty())
        self.assertEqual(report.unchanged, 2)
        self.assertEqual(self.snapshot(), before)

    def test_a_removed_wine_that_stays_missing_gets_no_second_comment(self):
        self.add_wine("a", main=picture(1))
        self.add_wine("h")
        self.run_import(self.site("a", {"a": picture(1)}))
        self.run_import(self.site("a", {"a": picture(1)}))
        self.assertEqual(self.notes(), {("h", "script", IMP.COMMENT_MISSING)})

    def test_changed_text_stops_and_changes_nothing(self):
        pics = {"a": picture(1), "n": picture(2)}
        self.add_wine("a", main=pics["a"])
        self.add_wine("h")
        client = self.site("an", pics, {"n": card("n")})
        list_url = IMP.LIST_URL % (1, IMP.PER_PAGE)
        page = json.loads(client.bodies[list_url])
        page["items"][0]["title"] = "Вино а."
        page["items"][0]["category"] = "Розовое брют"
        client.bodies[list_url] = json.dumps(page)
        before = self.snapshot()

        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)

        message = str(caught.exception)
        self.assertIn("a (Active): the text changed", message)
        self.assertIn("name 'Вино a' -> 'Вино а.'", message)
        self.assertIn("category 'Белое' -> 'Розовое'", message)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.store_files(), [])

    def test_changed_image_stops(self):
        self.add_wine("a", main=picture(1))
        before = self.snapshot()
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(self.site("a", {"a": picture(9)}))
        self.assertIn("a: the main image changed: stored a_0a1b2c3d4e.png (sha256 %s), "
                      "website a_0a1b2c3d4e.png (sha256 %s)" % (sha(picture(1)), sha(picture(9))),
                      str(caught.exception))
        self.assertEqual(self.snapshot(), before)

    def test_same_bytes_under_a_new_upload_name_are_no_change(self):
        self.add_wine("a", main=picture(1))
        client = FakeClient([item("a", upload="other_ffffffffff.png")],
                            {"/uploads/other_ffffffffff.png": picture(1)})
        report = self.run_import(client)
        self.assertEqual((report.replaced, report.mains, report.times), ([], [], 1))
        self.assertEqual(self.notes(), set())

    def test_all_problems_are_reported_together(self):
        self.add_wine("a", main=picture(1))
        self.add_wine("b", main=picture(2))
        client = self.site("ab", {"a": picture(1), "b": picture(3)})
        page = json.loads(client.bodies[IMP.LIST_URL % (1, IMP.PER_PAGE)])
        page["items"][0]["region"] = "Кубань"
        client.bodies[IMP.LIST_URL % (1, IMP.PER_PAGE)] = json.dumps(page)
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("2 problems", str(caught.exception))
        self.assertIn("a (Active): the text changed: region", str(caught.exception))
        self.assertIn("b: the main image changed", str(caught.exception))

    def test_a_new_wine_with_no_description_stops(self):
        client = self.site("n", {"n": picture(1)}, {"n": card("n", description=" ")})
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("n: the new wine has no description", str(caught.exception))
        self.assertEqual(self.query("SELECT * FROM wine_catalog"), [])

    def test_a_new_wine_with_no_grapes_gets_null(self):
        self.run_import(self.site("n", {"n": picture(1)}, {"n": card("n", grapes=[])}))
        self.assertEqual(self.query("SELECT grapes FROM wine_catalog"), [(None,)])

    def test_a_website_wine_with_no_image_stops(self):
        self.add_wine("a", main=picture(1))
        client = FakeClient([item("a", image=None)], {})
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("a: the website shows no image", str(caught.exception))

    def test_duplicate_slug_with_other_data_stops(self):
        self.add_wine("a", main=picture(1))
        client = FakeClient([item("a"), item("a", color="Золотистый")],
                            {"/uploads/a_0a1b2c3d4e.png": picture(1)}, total=1)
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("a: the list holds two different items", str(caught.exception))

    def test_count_that_differs_from_total_items_stops(self):
        self.add_wine("a", main=picture(1))
        client = self.site("a", {"a": picture(1)}, total=2)
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("1 distinct slugs, and totalItems is 2", str(caught.exception))

    def test_an_empty_list_stops(self):
        self.add_wine("a", main=picture(1))
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(FakeClient([], {}))
        self.assertIn("holds no wine", str(caught.exception))
        self.assertEqual(self.states(), {"a": ("Active", None)})

    def test_a_fetch_error_stops(self):
        self.add_wine("a", main=picture(1))
        with self.assertRaises(IMP.FetchError):
            self.run_import(FakeClient([item("a")], {}))
        self.assertEqual(self.states(), {"a": ("Active", None)})

    def test_a_database_change_during_the_run_stops(self):
        self.add_wine("a", main=picture(1))
        self.add_wine("h")
        client = self.site("a", {"a": picture(1)})

        def person_disables():
            conn = sqlite3.connect(self.db)
            with conn:
                conn.execute("UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'a'")
            conn.close()
            client.hook = None

        client.hook = person_disables
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(client)
        self.assertIn("the database changed during the import", str(caught.exception))
        self.assertEqual(self.states(), {"a": ("Disabled", None), "h": ("Active", None)})
        self.assertEqual(self.notes(), set())

    def test_list_values_map_the_api_fields(self):
        self.assertEqual(IMP.list_values(item("x", title="  Вино  x ", category="Красное полусладкое")),
                         {"name": "Вино  x", "producer": "Винодельня", "category": "Красное",
                          "color": "Соломенный", "region": "Крым"})
        self.assertEqual(IMP.file_url("/uploads/Вино 1.webp"), IMP.FILE_URL
                         + "/uploads/%D0%92%D0%B8%D0%BD%D0%BE%201.webp")

    def test_main_prints_the_report(self):
        self.add_wine("a", main=picture(1))
        client = self.site("an", {"a": picture(1), "n": picture(2)}, {"n": card("n")})
        real_client, real_sam3 = IMP.Client, derive.Sam3Client
        IMP.Client, derive.Sam3Client = (lambda: client), FakeSam3
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = IMP.main(["--db", self.db])
                again = IMP.main(["--db", self.db])
                missing = IMP.main(["--db", str(self.root / "none.sqlite3")])
        finally:
            IMP.Client, derive.Sam3Client = real_client, real_sam3
        self.assertEqual((status, again, missing), (0, 0, 1))
        text = out.getvalue()
        self.assertIn("added: 1: n\n", text)
        self.assertIn("comments added: 1\n", text)
        self.assertIn("result: imported\n", text)
        self.assertIn("result: no change\n", text)
        self.assertIn("error: no database at", err.getvalue())


if __name__ == "__main__":
    unittest.main()


class UiModeTest(WebsiteTestBase):
    """Plan 21: `--prepare`, `--apply`, the refusals, the times, and the connection."""

    def setUp(self):
        super().setUp()
        self.run_dir = self.root / "run"
        # a: its name changed; b: its image changed; e: no main image; h: missing; n: new.
        self.pics = {"a": picture(1), "b": picture(2), "old_b": picture(3), "e": picture(4),
                     "n": picture(5)}
        self.add_wine("a", main=self.pics["a"])
        self.add_wine("b", main=self.pics["old_b"])
        self.add_wine("e")
        self.add_wine("h", main=picture(6))

    def client(self, **changes):
        items = [item("a", title="Вино a новое"), item("b"), item("e"), item("n")]
        images = {"/uploads/%s_0a1b2c3d4e.png" % slug: self.pics[slug] for slug in "aben"}
        for slug, data in changes.items():
            images["/uploads/%s_0a1b2c3d4e.png" % slug] = data
        return FakeClient(items, images, {"n": card("n")},
                          times={"n": "2026-09-22T15:36:48.000Z"})

    def prepare(self, client=None):
        return IMP.prepare(self.db, str(self.run_dir), client or self.client(), self.log.append)

    def apply(self, conflicts, changes=None):
        IMP.write_json(str(self.run_dir / IMP.CHOICES_FILE),
                       {"conflicts": conflicts, "changes": changes or {}})
        return IMP.apply_directory(self.db, str(self.run_dir), FakeSam3(), self.log.append)

    def refusals(self):
        return set(self.query("SELECT wine_slug, kind, field, website_value FROM website_refusal"))

    def test_prepare_writes_the_diff_and_changes_nothing(self):
        before = self.snapshot()
        diff = self.prepare()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(sorted(entry["id"] for entry in diff["conflicts"]),
                         ["image:b", "text:a:name"])
        self.assertEqual(sorted(entry["id"] for entry in diff["changes"]),
                         ["main:e", "missing:h", "new:n"])
        saved = json.loads((self.run_dir / IMP.DIFF_FILE).read_text(encoding="utf-8"))
        self.assertEqual(saved["snapshot"], diff["snapshot"])
        self.assertEqual(saved["database"], os.path.abspath(self.db))
        files = sorted(p.name for p in (self.run_dir / IMP.IMAGES_DIR).iterdir())
        self.assertEqual(files, sorted(sha(self.pics[s]) + ".png" for s in "ben"))
        image = next(entry for entry in diff["conflicts"] if entry["kind"] == "image")
        self.assertEqual(image["database"]["url"], "/images/main/%s.png" % sha(self.pics["old_b"]))

    def test_apply_writes_each_choice_and_its_comment(self):
        self.prepare()
        report = self.apply({"text:a:name": "website", "image:b": "database"},
                            {"new:n": False, "main:e": False})
        self.assertEqual(report.texts, ["a name"])
        self.assertEqual(report.removed, ["h"])
        self.assertEqual((report.added, report.mains, report.replaced), ([], [], []))
        self.assertEqual(self.query("SELECT name FROM wine_catalog WHERE wine_slug = 'a'"),
                         [("Вино a новое",)])
        self.assertEqual(self.query("SELECT sha256 FROM wine_image WHERE wine_slug = 'b'"),
                         [(sha(self.pics["old_b"]),)])
        self.assertEqual(self.states()["h"], ("Removed", "import"))
        self.assertNotIn("n", self.states())
        self.assertEqual(self.refusals(), {("b", "image", "", sha(self.pics["b"])),
                                           ("n", "new", "", None),
                                           ("e", "main", "", sha(self.pics["e"]))})
        self.assertEqual(self.notes(), {
            ("a", "script", "name from vino-svoe.ru; was 'Вино a'."),
            ("b", "script", "kept main image; vino-svoe.ru has b_0a1b2c3d4e.png."),
            ("e", "script", "main image of vino-svoe.ru not taken."),
            ("h", "script", IMP.COMMENT_MISSING)})
        result = IMP.main(["--db", self.db, "--apply", str(self.run_dir)])
        self.assertEqual(result, 1)  # the database changed after the compare
        self.assertFalse(json.loads((self.run_dir / IMP.RESULT_FILE).read_text())["ok"])

    def test_a_refusal_holds_in_the_cli_while_the_website_stays(self):
        self.prepare()
        self.apply({"text:a:name": "database", "image:b": "database"},
                   {"new:n": False, "main:e": False, "missing:h": False})
        self.assertEqual(self.notes() & {("h", "script", "kept Active; missing on vino-svoe.ru."),
                                         ("a", "script", "kept name; vino-svoe.ru has 'Вино a новое'.")},
                         {("h", "script", "kept Active; missing on vino-svoe.ru."),
                          ("a", "script", "kept name; vino-svoe.ru has 'Вино a новое'.")})
        before = self.snapshot()
        report = self.run_import(self.client())
        self.assertEqual(report.refused, 5)
        self.assertTrue(report.empty())
        self.assertEqual(self.snapshot(), before)

    def test_a_new_website_value_ends_the_refusal(self):
        self.prepare()
        self.apply({"text:a:name": "website", "image:b": "database"})
        diff = IMP.prepare(self.db, str(self.root / "run2"), self.client(b=picture(7)),
                           self.log.append)
        self.assertEqual([entry["id"] for entry in diff["conflicts"]], ["image:b"])
        self.assertEqual(diff["stale"], [["b", "image", ""]])
        IMP.write_json(str(self.root / "run2" / IMP.CHOICES_FILE),
                       {"conflicts": {"image:b": "website"}})
        report = IMP.apply_directory(self.db, str(self.root / "run2"), FakeSam3(), self.log.append)
        self.assertEqual((report.replaced, report.stale), (["b"], 1))
        self.assertEqual(self.refusals(), set())
        self.assertEqual(self.query("SELECT sha256, source_name, match_method FROM wine_image "
                                    "WHERE wine_slug = 'b' AND image_type = 'main'"),
                         [(sha(picture(7)), "b_0a1b2c3d4e.png", "website")])
        self.assertIn(("b", "script", "main image from vino-svoe.ru; was b_0a1b2c3d4e.png."),
                      self.notes())
        self.assertEqual(len(self.query("SELECT * FROM image WHERE sha256 = ?",
                                        (sha(self.pics["old_b"]),))), 1)

    def test_the_cli_still_stops_on_a_conflict(self):
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.run_import(self.client())
        self.assertIn("a (Active): the text changed: name", str(caught.exception))
        self.assertIn("b: the main image changed", str(caught.exception))

    def test_apply_skips_a_conflict_with_no_choice(self):
        self.prepare()
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.apply({"text:a:name": "website", "image:b": "maybe"})
        self.assertIn("image:b need database or website", str(caught.exception))
        report = self.apply({"text:a:name": "website"}, {"new:n": False, "main:e": False})
        self.assertEqual((report.texts, report.replaced), (["a name"], []))
        self.assertEqual(report.unresolved, ["image:b"])
        self.assertEqual(self.query("SELECT sha256 FROM wine_image WHERE wine_slug = 'b'"),
                         [(sha(self.pics["old_b"]),)])
        self.assertFalse(any(row[0] == "b" for row in self.refusals()))
        self.assertFalse(any(row[0] == "b" for row in self.notes()))
        diff = IMP.prepare(self.db, str(self.root / "run2"), self.client(), self.log.append)
        self.assertEqual([entry["id"] for entry in diff["conflicts"]], ["image:b"])

    def test_apply_after_a_database_change_stops(self):
        self.prepare()
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'e'")
        conn.close()
        before = self.snapshot()
        with self.assertRaises(IMP.WebsiteError) as caught:
            self.apply({"text:a:name": "website", "image:b": "website"})
        self.assertEqual(str(caught.exception), IMP.CHANGED)
        self.assertEqual(self.snapshot(), before)

    def test_the_times_of_a_wine(self):
        self.prepare()
        self.apply({"text:a:name": "database", "image:b": "database"})
        times = dict(self.query("SELECT wine_slug, website_modified_at FROM wine_catalog"))
        self.assertEqual(times, {"a": LASTMOD, "b": LASTMOD, "e": LASTMOD, "h": None,
                                 "n": "2026-09-22T15:36:48.000Z"})
        changed = dict(self.query("SELECT wine_slug, modified_at FROM wine_catalog"))
        self.assertRegex(changed["n"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")  # the insert
        self.assertIsNotNone(changed["h"])                                   # the state
        self.assertIsNotNone(changed["a"])   # the insert of the fixture set the time
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("UPDATE wine_catalog SET modified_at = NULL")
            conn.execute("UPDATE wine_catalog SET website_modified_at = 'x', name = name")
        self.assertEqual(self.query("SELECT count(modified_at) FROM wine_catalog"), [(0,)])
        with conn:
            conn.execute("UPDATE wine_catalog SET region = 'Кубань' WHERE wine_slug = 'a'")
        conn.close()
        self.assertEqual(self.query("SELECT wine_slug FROM wine_catalog "
                                    "WHERE modified_at IS NOT NULL"), [("a",)])

    def test_main_prepare_and_apply(self):
        real_client, real_sam3 = IMP.Client, derive.Sam3Client
        IMP.Client, derive.Sam3Client = self.client, FakeSam3
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                prepared = IMP.main(["--db", self.db, "--prepare", str(self.run_dir)])
                IMP.write_json(str(self.run_dir / IMP.CHOICES_FILE),
                               {"conflicts": {"text:a:name": "website", "image:b": "website"}})
                applied = IMP.main(["--db", self.db, "--apply", str(self.run_dir)])
        finally:
            IMP.Client, derive.Sam3Client = real_client, real_sam3
        self.assertEqual((prepared, applied), (0, 0))
        self.assertIn("prepared: 2 conflicts, 3 changes", out.getvalue())
        result = json.loads((self.run_dir / IMP.RESULT_FILE).read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual((result["added"], result["replaced"]), (["n"], ["b"]))


class FakeResponse:
    def __init__(self, status, body, close=False):
        self.status, self.reason, self._body, self.will_close = status, "OK", body, close

    def read(self):
        return self._body


class FakeConnection:
    made = []
    answers = []

    def __init__(self, host, timeout=None):
        self.host, self.closed, self.targets = host, False, []
        FakeConnection.made.append(self)

    def request(self, method, target, headers=None):
        self.targets.append(target)

    def getresponse(self):
        return FakeConnection.answers.pop(0)

    def close(self):
        self.closed = True


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.real = IMP.http.client.HTTPSConnection
        IMP.http.client.HTTPSConnection = FakeConnection
        FakeConnection.made, FakeConnection.answers = [], []

    def tearDown(self):
        IMP.http.client.HTTPSConnection = self.real

    def test_one_connection_is_reused_until_the_server_closes_it(self):
        FakeConnection.answers = [FakeResponse(200, b"1"), FakeResponse(200, b"2", close=True),
                                  FakeResponse(200, b"3")]
        client = IMP.Client(delay=0)
        bodies = [client.get("https://api.vino-svoe.ru/v1/x?page=%d" % n) for n in range(3)]
        self.assertEqual(bodies, [b"1", b"2", b"3"])
        self.assertEqual(len(FakeConnection.made), 2)
        self.assertEqual(FakeConnection.made[0].targets, ["/v1/x?page=0", "/v1/x?page=1"])
        self.assertTrue(FakeConnection.made[0].closed)

    def test_a_retry_code_is_retried_and_a_404_is_not(self):
        FakeConnection.answers = [FakeResponse(503, b""), FakeResponse(200, b"ok"),
                                  FakeResponse(404, b"")]
        client = IMP.Client(delay=0, retries=1)
        real_sleep, IMP.time.sleep = IMP.time.sleep, lambda seconds: None
        try:
            self.assertEqual(client.get("https://api.vino-svoe.ru/a"), b"ok")
            with self.assertRaises(IMP.FetchError) as caught:
                client.get("https://api.vino-svoe.ru/b")
        finally:
            IMP.time.sleep = real_sleep
        self.assertIn("HTTP 404", str(caught.exception))
        self.assertEqual(client.requests, 3)
