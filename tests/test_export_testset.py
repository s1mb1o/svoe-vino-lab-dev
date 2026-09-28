"""The export of a test set (plan 24): the import, then the export, gives the files back.
Since plan 51 the export writes the comments of a photo as the list `comments`, and no
`wines` and no `excluded-slugs.json`."""
import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import export_testset as EX  # noqa: E402
import import_testset as IT  # noqa: E402

PHOTOS = {
    "wine-a/01_conf095.jpg": b"a1", "wine-a/02_conf080.jpg": b"a2", "wine-b/01.jpg": b"b1",
    "wine-b/02.jpg": b"b2", "__null__/n1.jpg": b"n1",
}
COMMENTS = [{"created_at": "2026-09-25T07:00:00Z", "source": "script",
             "text": "the same label"},
            {"created_at": "2026-09-26T08:30:00Z", "source": "user", "text": "agreed"}]
LABELS = {
    "wine-a": {
        "01_conf095.jpg": {"label": "positive", "comments": COMMENTS, "ts": "t1",
                           "proposed": "positive", "by": "kimi", "confidence": 0.9,
                           "source_url": "https://example.org/a", "moved_from": "wine-c",
                           "prefilled_from": {"rank": 2, "score": 0.5}},
        "02_conf080.jpg": {"label": "negative", "delete": True, "ts": "t2",
                           "copy_to": "wine-b", "label_2": None},
    },
    "wine-b": {"01.jpg": {"proposed": "variant", "by": "hunter-01", "confidence": 0.4,
                          "ts": "t3", "copied_from": "wine-a"}},
    "__null__": {"n1.jpg": {"label": "unusable", "reassign_to": "wine-a", "ts": "t4"}},
}
WINES = {"wine-a": {"comment": "a note about the wine", "ts": "t5"},
         "wine-b": {"comment": "b", "ts": "t6", "by": "x"}}
EXCLUDED = {"wine-b": {"reason": "wrong bottle photo", "ts": "t7"}}


class ExportTestsetTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        self.set_dir = Path(FX.write_set(self.root, PHOTOS, LABELS, excluded=EXCLUDED))
        (self.set_dir / "review-labels.json").write_text(json.dumps(
            {"version": 2, "note": "the note of the set", "labels": LABELS, "wines": WINES}))
        IT.import_testset(self.db, "my", str(self.set_dir), lambda m: None, self.schema)
        self.out = self.root / "out"

    def tearDown(self):
        self.directory.cleanup()

    def export(self):
        EX.export_testset(self.db, "my", str(self.out), self.schema)
        return json.loads((self.out / EX.LABELS_FILE).read_text(encoding="utf-8"))

    def test_the_export_gives_the_files_back_field_for_field(self):
        labels = self.export()
        self.assertEqual(labels["labels"], LABELS)
        self.assertEqual(labels["note"], "the note of the set")
        self.assertEqual(labels["version"], 2)
        # The old notes of the wines and the old exclusion are wine comments now.
        self.assertNotIn("wines", labels)
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute("SELECT wine_slug, text FROM wine_comment "
                                          "ORDER BY wine_slug, text").fetchall(),
                             [("wine-a", "a note about the wine"),
                              ("wine-b", "Excluded from the benchmark: wrong bottle photo"),
                              ("wine-b", "b")])
        finally:
            conn.close()

    def test_an_old_comment_comes_back_as_a_list(self):
        labels = json.loads(json.dumps(LABELS))
        entry = labels["wine-a"]["01_conf095.jpg"]
        del entry["comments"]
        entry.update(comment="the same label", ts="2026-09-25T10:00:00+0300")
        (self.set_dir / "review-labels.json").write_text(json.dumps({"labels": labels}))
        IT.import_testset(self.db, "my", str(self.set_dir), lambda m: None, self.schema)
        out = self.export()["labels"]["wine-a"]["01_conf095.jpg"]
        self.assertNotIn("comment", out)
        self.assertEqual(out["comments"], [{"created_at": "2026-09-25T07:00:00Z",
                                            "source": "script", "text": "the same label"}])

    def test_the_counts_are_the_counts_of_the_old_tool(self):
        labels = self.export()
        self.assertEqual(labels["counts"], {
            "commented": 1, "copied": 1, "deleting": 1, "labelled": 3, "negative": 1,
            "no_match": 1, "no_match_pending": 0, "positive": 1, "proposed": 1,
            "reassigned": 1, "unusable": 1, "variant": 0})

    def test_a_row_with_no_field_gives_no_entry(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE test_photo SET proposed = NULL, proposed_by = NULL, "
                     "confidence = NULL, copied_from = NULL, ts = NULL WHERE place = 'wine-b'")
        conn.commit()
        conn.close()
        labels = self.export()
        self.assertNotIn("wine-b", labels["labels"])

    def test_a_row_with_comments_alone_gives_an_entry(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE test_photo SET label = NULL, proposed = NULL, proposed_by = NULL, "
                     "confidence = NULL, source_url = NULL, moved_from = NULL, "
                     "prefilled_from = NULL, ts = NULL WHERE file_name = '01_conf095.jpg'")
        conn.commit()
        conn.close()
        self.assertEqual(self.export()["labels"]["wine-a"]["01_conf095.jpg"],
                         {"comments": COMMENTS})

    def test_the_tags_of_the_image_come_back_in_each_entry(self):
        # Plan 66: the import adds the tags, and the export writes them into each photo of
        # the same bytes. A photo with a tag alone gets an entry.
        labels = json.loads(json.dumps(LABELS))
        labels["wine-a"]["01_conf095.jpg"]["tags"] = ["blurry", "back_label"]
        photos = dict(PHOTOS, **{"wine-c/03.jpg": b"a1"})
        set_dir = FX.write_set(self.root, photos, labels, name="tagged")
        IT.import_testset(self.db, "tagged", set_dir, lambda m: None, self.schema)
        EX.export_testset(self.db, "tagged", str(self.out), self.schema)
        exported = json.loads((self.out / EX.LABELS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(exported["labels"]["wine-a"], labels["wine-a"])
        self.assertEqual(exported["labels"]["wine-c"],
                         {"03.jpg": {"tags": ["blurry", "back_label"]}})
        self.assertIn("Field 'tags'", exported["note"])
        # The set "my" holds the same bytes, so its export shows the tags too.
        self.assertEqual(self.export()["labels"]["wine-a"]["01_conf095.jpg"]["tags"],
                         ["blurry", "back_label"])

    def test_the_files_have_the_form_of_the_old_tool(self):
        # An old excluded-slugs.json of the directory stays as it is.
        self.out.mkdir()
        (self.out / "excluded-slugs.json").write_text("old", encoding="utf-8")
        self.export()
        text = (self.out / EX.LABELS_FILE).read_text(encoding="utf-8")
        self.assertTrue(text.endswith("}\n"))
        data = json.loads(text)
        self.assertEqual(text, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
                         + "\n")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         sorted(["excluded-slugs.json", EX.LABELS_FILE]))
        self.assertEqual((self.out / "excluded-slugs.json").read_text(encoding="utf-8"), "old")

    def test_an_unknown_set_is_an_error(self):
        with self.assertRaisesRegex(EX.ExportError, "no test set 'other'"):
            EX.export_testset(self.db, "other", str(self.out), self.schema)

    def test_the_main_command_writes_the_file(self):
        # The schema directory of the fixture holds each file of `pipeline/schema/`.
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            code = EX.main(["--db", self.db, "--set", "my", "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertIn("label entries: 4 in 3 places", printed.getvalue())
        self.assertIn("comments of the photos: 2", printed.getvalue())
        self.assertTrue((self.out / EX.LABELS_FILE).is_file())


if __name__ == "__main__":
    unittest.main()
