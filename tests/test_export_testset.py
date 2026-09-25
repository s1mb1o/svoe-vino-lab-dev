"""The export of a test set (plan 24): the import, then the export, gives the files back."""
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
LABELS = {
    "wine-a": {
        "01_conf095.jpg": {"label": "positive", "comment": "the same label", "ts": "t1",
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
        return (json.loads((self.out / EX.LABELS_FILE).read_text(encoding="utf-8")),
                json.loads((self.out / EX.EXCLUDED_FILE).read_text(encoding="utf-8")))

    def test_the_export_gives_the_files_back_field_for_field(self):
        labels, excluded = self.export()
        self.assertEqual(labels["labels"], LABELS)
        self.assertEqual(labels["wines"], WINES)
        self.assertEqual(labels["note"], "the note of the set")
        self.assertEqual(labels["version"], 2)
        self.assertEqual(excluded["excluded"], EXCLUDED)
        self.assertEqual((excluded["version"], excluded["count"]), (1, 1))

    def test_the_counts_are_the_counts_of_the_old_tool(self):
        labels, _ = self.export()
        self.assertEqual(labels["counts"], {
            "commented": 1, "copied": 1, "deleting": 1, "labelled": 3, "negative": 1,
            "no_match": 1, "no_match_pending": 0, "positive": 1, "proposed": 1,
            "reassigned": 1, "unusable": 1, "variant": 0, "wine_notes": 2})

    def test_a_row_with_no_field_gives_no_entry(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE test_photo SET proposed = NULL, proposed_by = NULL, "
                     "confidence = NULL, copied_from = NULL, ts = NULL WHERE place = 'wine-b'")
        conn.commit()
        conn.close()
        labels, _ = self.export()
        self.assertNotIn("wine-b", labels["labels"])

    def test_the_files_have_the_form_of_the_old_tool(self):
        self.export()
        text = (self.out / EX.LABELS_FILE).read_text(encoding="utf-8")
        self.assertTrue(text.endswith("}\n"))
        data = json.loads(text)
        self.assertEqual(text, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
                         + "\n")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         sorted([EX.EXCLUDED_FILE, EX.LABELS_FILE]))

    def test_an_unknown_set_is_an_error(self):
        with self.assertRaisesRegex(EX.ExportError, "no test set 'other'"):
            EX.export_testset(self.db, "other", str(self.out), self.schema)

    def test_the_main_command_writes_the_two_files(self):
        # The schema directory of the fixture holds each file of `pipeline/schema/`.
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            code = EX.main(["--db", self.db, "--set", "my", "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertIn("label entries: 4 in 3 places", printed.getvalue())
        self.assertTrue((self.out / EX.LABELS_FILE).is_file())


if __name__ == "__main__":
    unittest.main()
