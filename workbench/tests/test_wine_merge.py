"""Manual wine merges keep annotations, related records, and transaction boundaries."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import wine_merge  # noqa: E402

SOURCE = "__source"
TARGET = "target"
STAMP = "2026-09-25T10:00:00Z"


class WineMergeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.conn = labdb.connect(self.db, create=True)
        self.conn.row_factory = sqlite3.Row
        for slug in (SOURCE, TARGET, "neighbor", "other-target"):
            self.conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, "
                              "category, color, region, csv_photo_name) "
                              "VALUES (?, ?, 'p', 'c', 'co', 'r', 'main.jpg')", (slug, slug))
        self.conn.executemany("INSERT INTO test_set (set_name, source_dir) VALUES (?, ?)",
                              [("my", "my"), ("review", "review")])
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.directory.cleanup()

    def image(self, text, folder="testset"):
        data = text.encode()
        digest = hashlib.sha256(data).hexdigest()
        self.conn.execute("INSERT INTO image (sha256, folder, extension) VALUES (?, ?, 'jpg')",
                          (digest, folder))
        path = self.root / "bytes" / (digest + ".jpg")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        return digest

    def photo(self, place, name="01.jpg", *, set_name="my", label="positive", digest=None):
        digest = digest or self.image(set_name + place + name)
        self.conn.execute("INSERT INTO test_photo (set_name, place, file_name, sha256, "
                          "label, marked_delete, ts, proposed, proposed_by, confidence, "
                          "source_url, moved_from, copied_from, prefilled_from, extra, "
                          "box_left, box_top, box_right, box_bottom) "
                          "VALUES (?, ?, ?, ?, ?, 1, '2026-09-25T13:00:00+0300', 'variant', "
                          "'agent', 0.91, 'https://example.test/photo', '__old', '__older', "
                          "?, ?, 1, 2, 30, 40)",
                          (set_name, place, name, digest, label,
                           json.dumps({"wine_slug": SOURCE, "file": "old.jpg"}),
                           json.dumps({"custom": [1, "unchanged"], "history": SOURCE})))
        self.conn.execute("INSERT INTO test_photo_comment (set_name, place, file_name, "
                          "created_at, source, text) VALUES (?, ?, ?, ?, 'user', 'review note')",
                          (set_name, place, name, STAMP))
        return digest

    def snapshot(self):
        return {table: sorted((tuple(row) for row in self.conn.execute(
            'SELECT * FROM "%s"' % table)), key=repr) for table in labdb.tables(self.conn)}

    def assert_no_source_references(self):
        for table in labdb.tables(self.conn):
            for column in self.conn.execute('PRAGMA table_info("%s")' % table):
                if column[1] in ("wine_slug", "wine_slug_a", "wine_slug_b", "place", "reassign_to"):
                    self.assertEqual(self.conn.execute(
                        'SELECT COUNT(*) FROM "%s" WHERE "%s" = ?' % (table, column[1]),
                        (SOURCE,)).fetchone()[0], 0, (table, column[1]))
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_all_testsets_keep_full_annotations_comments_and_image_bytes(self):
        for i, label in enumerate(("positive", "negative", "variant", "unusable", None)):
            digest = self.photo(SOURCE, "%02d.jpg" % i,
                                set_name="my" if i % 2 else "review", label=label)
            self.conn.execute("INSERT INTO image_tag VALUES (?, 'scene_photo', ?)",
                              (digest, STAMP))
        self.conn.commit()
        photos = [dict(row) for row in self.conn.execute("SELECT * FROM test_photo")]
        comments = [dict(row) for row in self.conn.execute("SELECT * FROM test_photo_comment")]
        before = {path: path.read_bytes() for path in (self.root / "bytes").iterdir()}
        tags = [tuple(row) for row in self.conn.execute("SELECT * FROM image_tag")]
        out = wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        self.assertEqual((out["photos"], out["renamed_files"], out["removed"]), (5, 0, True))
        for row in photos:
            row["place"] = TARGET
        for row in comments:
            row["place"] = TARGET
        self.assertEqual([dict(row) for row in self.conn.execute("SELECT * FROM test_photo")], photos)
        self.assertEqual([dict(row) for row in self.conn.execute("SELECT * FROM test_photo_comment")],
                         comments)
        self.assertEqual([tuple(row) for row in self.conn.execute("SELECT * FROM image_tag")], tags)
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertTrue(all(row[0] for row in self.conn.execute("SELECT edited_at FROM test_set")))
        self.assert_no_source_references()

    def test_filename_collisions_keep_both_records_even_for_equal_bytes(self):
        digest = self.photo(TARGET)
        self.photo(TARGET, "01_merged2.jpg")
        self.photo(SOURCE, digest=digest, label="negative")
        self.conn.commit()
        comment_id = self.conn.execute("SELECT id FROM test_photo_comment WHERE place = ?",
                                       (SOURCE,)).fetchone()[0]
        out = wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        self.assertEqual(out["renamed_files"], 1)
        row = self.conn.execute("SELECT * FROM test_photo WHERE place = ? "
                                "AND file_name = '01_merged3.jpg'", (TARGET,)).fetchone()
        self.assertEqual((row["sha256"], row["label"]), (digest, "negative"))
        self.assertEqual(tuple(self.conn.execute("SELECT place, file_name, text FROM "
                                               "test_photo_comment WHERE id = ?",
                                               (comment_id,)).fetchone()),
                         (TARGET, "01_merged3.jpg", "review note"))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM test_photo").fetchone()[0], 3)

    def test_all_catalogue_relations_transfer_and_destination_metadata_wins(self):
        main = self.image("target main", "main")
        for slug, kind, text in ((TARGET, "main", None), (SOURCE, "main", "source main"),
                                 (SOURCE, "main_patched", "source patch"),
                                 (SOURCE, "label_back", "source back")):
            digest = main if text is None else self.image(text, "main")
            self.conn.execute("INSERT INTO wine_image VALUES (?, ?, ?, 'origin.jpg', 'manual')",
                              (slug, kind, digest))
        self.conn.execute("INSERT INTO wine_comment (wine_slug,created_at,source,text) "
                          "VALUES (?, ?, 'user', 'catalogue note')", (SOURCE, STAMP))
        self.conn.execute("INSERT INTO wine_code VALUES (?, 'barcode', '1234', ?)", (SOURCE, STAMP))
        self.conn.execute("INSERT INTO wine_code VALUES (?, 'barcode', '1234', ?)", (TARGET, STAMP))
        self.conn.execute("INSERT INTO wine_favorite VALUES (?, ?)", (SOURCE, STAMP))
        self.conn.execute("INSERT INTO wine_tag VALUES (?, 'manual', ?)", (SOURCE, STAMP))
        self.conn.execute("INSERT INTO wine_beverage_type VALUES (?, '44', ?)", (SOURCE, STAMP))
        self.conn.execute("INSERT INTO wine_beverage_type VALUES (?, '4', ?)", (TARGET, STAMP))
        self.conn.execute("INSERT INTO wine_atlas_binding VALUES (?, 'manual', ?)",
                          (SOURCE, "12345678-1234-1234-1234-123456789abc"))
        self.conn.execute("INSERT INTO wine_similar VALUES (?, 'neighbor', ?)", (SOURCE, STAMP))
        self.conn.execute("INSERT INTO wine_similar VALUES (?, ?, ?)", (SOURCE, TARGET, STAMP))
        self.conn.execute("INSERT INTO wine_similar VALUES ('neighbor', ?, ?)", (TARGET, STAMP))
        self.conn.execute("INSERT INTO website_refusal VALUES (?, 'main', '', NULL, ?)",
                          (SOURCE, STAMP))
        self.conn.commit()
        target = dict(self.conn.execute("SELECT * FROM wine_catalog WHERE wine_slug = ?",
                                       (TARGET,)).fetchone())
        wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        after = dict(self.conn.execute("SELECT * FROM wine_catalog WHERE wine_slug = ?",
                                      (TARGET,)).fetchone())
        after["modified_at"] = target["modified_at"]
        self.assertEqual(after, target)
        self.assertEqual(self.conn.execute("SELECT sha256 FROM wine_image "
                                          "WHERE image_type = 'main'").fetchone()[0], main)
        self.assertEqual([tuple(row) for row in self.conn.execute(
            "SELECT image_type FROM wine_image ORDER BY image_type")],
            [("full_front",), ("full_front",), ("label_back",), ("main",)])
        for table in ("wine_comment", "wine_code", "wine_favorite", "wine_tag", "wine_atlas_binding"):
            self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM "%s" WHERE wine_slug = ?'
                                              % table, (TARGET,)).fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT beverage_type_code FROM wine_beverage_type "
                                          "WHERE wine_slug = ?", (TARGET,)).fetchone()[0], "4")
        self.assertEqual([tuple(row) for row in self.conn.execute("SELECT * FROM wine_similar")],
                         [("neighbor", TARGET, STAMP)])
        self.assert_no_source_references()

    def test_missing_destination_main_inherits_source_main_and_patch(self):
        for kind in ("main", "main_patched"):
            digest = self.image(kind, "main")
            self.conn.execute("INSERT INTO wine_image VALUES (?, ?, ?, 'main.jpg', 'manual')",
                              (SOURCE, kind, digest))
        self.conn.commit()
        wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        self.assertEqual([tuple(row) for row in self.conn.execute(
            "SELECT wine_slug,image_type FROM wine_image ORDER BY image_type")],
            [(TARGET, "main"), (TARGET, "main_patched")])

    def test_variant_groups_and_live_reassignment_follow_the_destination(self):
        self.photo("neighbor")
        self.conn.execute("UPDATE test_photo SET reassign_to = ?", (SOURCE,))
        self.conn.executemany("INSERT INTO test_variant VALUES ('my', ?, ?)",
                              [(SOURCE, 1), ("neighbor", 1), (TARGET, 2), ("other-target", 2)])
        self.conn.execute("INSERT INTO test_variant VALUES ('review', ?, 3)", (SOURCE,))
        self.conn.commit()
        wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        self.assertEqual([tuple(row) for row in self.conn.execute(
            "SELECT wine_slug,group_no FROM test_variant WHERE set_name = 'my' ORDER BY wine_slug")],
            [("neighbor", 2), ("other-target", 2), (TARGET, 2)])
        self.assertEqual(tuple(self.conn.execute("SELECT wine_slug,group_no FROM test_variant "
                                               "WHERE set_name = 'review'").fetchone()), (TARGET, 3))
        self.assertEqual(self.conn.execute("SELECT reassign_to FROM test_photo").fetchone()[0], TARGET)
        self.assert_no_source_references()

    def test_invalid_requests_do_not_change_any_table(self):
        self.photo(SOURCE)
        self.conn.commit()
        before = self.snapshot()
        cases = [(None, 400), ([], 400), ({"slug": TARGET, "to": "neighbor"}, 400),
                 ({"slug": "__null__", "to": TARGET}, 400),
                 ({"slug": "__drawer__", "to": TARGET}, 400),
                 ({"slug": "__missing", "to": TARGET}, 404),
                 ({"slug": SOURCE, "to": SOURCE}, 400), ({"slug": SOURCE}, 400),
                 ({"slug": SOURCE, "to": "missing"}, 404),
                 ({"slug": SOURCE, "to": "__null__"}, 400),
                 ({"slug": SOURCE, "to": [TARGET]}, 400),
                 ({"slug": SOURCE, "to": "\ud800"}, 400)]
        for body, code in cases:
            with self.subTest(body=body):
                with self.assertRaises(wine_merge.MergeError) as error:
                    wine_merge.merge(self.db, body)
                self.assertEqual(error.exception.code, code)
                self.assertEqual(self.snapshot(), before)

    def test_late_database_failure_rolls_back_every_transfer(self):
        self.photo(SOURCE)
        self.conn.execute("INSERT INTO wine_comment (wine_slug,created_at,source,text) "
                          "VALUES (?, ?, 'user', 'source note')", (SOURCE, STAMP))
        self.conn.execute("CREATE TRIGGER reject_source_delete BEFORE DELETE ON wine_catalog "
                          "WHEN OLD.wine_slug = '__source' BEGIN "
                          "SELECT RAISE(ABORT, 'fixture failure'); END")
        self.conn.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "fixture failure"):
            wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        self.assertEqual(self.snapshot(), before)

    def test_preview_and_repeated_merge_are_safe(self):
        self.photo(SOURCE)
        self.conn.commit()
        before = self.snapshot()
        view = wine_merge.preview(self.db, SOURCE)
        self.assertEqual((view["photos"], view["testsets"]), (1, [{"name": "my", "photos": 1}]))
        self.assertNotIn(SOURCE, [row["slug"] for row in view["targets"]])
        self.assertEqual(self.snapshot(), before)
        wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        after = self.snapshot()
        with self.assertRaises(wine_merge.MergeError) as error:
            wine_merge.merge(self.db, {"slug": SOURCE, "to": "neighbor"})
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(self.snapshot(), after)

    def test_competing_merges_transfer_the_source_once(self):
        self.photo(SOURCE)
        self.conn.commit()
        results, errors = [], []
        def run(target):
            try:
                results.append(wine_merge.merge(self.db, {"slug": SOURCE, "to": target}))
            except wine_merge.MergeError as exc:
                errors.append(exc.code)
        threads = [threading.Thread(target=run, args=(slug,)) for slug in (TARGET, "neighbor")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual((len(results), errors), (1, [404]))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM test_photo").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT place FROM test_photo").fetchone()[0],
                         results[0]["to"])
        self.assert_no_source_references()


if __name__ == "__main__":
    unittest.main()
