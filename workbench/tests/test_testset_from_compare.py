"""Check complete filtered copies, annotation fidelity, and atomic HTTP writes."""

import json
from pathlib import Path
import sqlite3
import sys
import threading
from contextlib import closing
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# The modules of the lab are in `pipeline/`. Another test module adds it too, but this
# module also runs alone (`-p test_testset_from_compare.py`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import benchmark  # noqa: E402
import labdb  # noqa: E402
import lab_server  # noqa: E402
import testset_from_compare as copy  # noqa: E402
from test_run_compare import RunFixture, query  # noqa: E402


class CompareTestsetTest(RunFixture):
    def setUp(self):
        super().setUp()
        self.db = str(self.root / "catalog.sqlite3")
        labdb.connect(self.db, create=True).close()
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO test_set(set_name,source_dir,label_note) VALUES ('my','fixture','source note')"
            )
        self.seed(self.rows)
        config = self.root / "config.yaml"
        config.write_text("pipeline: []\nembeddings: []\n")
        self.server = lab_server.make_server(self.db, port=0, config_path=str(config))
        self.server.runs_dir = str(self.runs)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_address[1])
        self.filters = dict(
            a="a", b="b", group="differences", k="1", common="0", q="", source="b"
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def seed(self, rows, source="my"):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            for row in rows:
                slug = row["slug"]
                if slug != "__null__":
                    conn.execute(
                        "INSERT OR IGNORE INTO wine_catalog(wine_slug,name,producer,category,color,region,description,csv_photo_name) VALUES (?,'n','p','c','co','r','d','x.webp')",
                        (slug,),
                    )
                conn.execute(
                    "INSERT OR IGNORE INTO image(sha256,folder,extension,width,height) VALUES (?,'testset','jpg',100,100)",
                    (row["image_sha256"],),
                )
                place, _, name = row["image_path"].rpartition("/")
                label = (
                    None if row["label"] in ("no_match", "unlabelled") else row["label"]
                )
                conn.execute(
                    "INSERT OR IGNORE INTO test_photo(set_name,place,file_name,sha256,label,ts,source_url,proposed,proposed_by,confidence,extra,box_left,box_top,box_right,box_bottom) VALUES (?,?,?,?,?,'time','https://example.test/photo','positive','mock',.9,'{\"custom\":7}',1,2,30,40)",
                    (source, place, name, row["image_sha256"], label),
                )

    def request(self, filters=None, body=None, method=None):
        url = self.url + "/api/testset-from-compare"
        if filters is not None:
            url += "?" + urlencode(filters, doseq=True)
        req = Request(
            url,
            data=json.dumps(body).encode() if body is not None else None,
            method=method or ("POST" if body is not None else "GET"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req) as response:
                return response.status, json.load(
                    response
                ) if req.method != "HEAD" else {}
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    def preview(self, **changes):
        return self.request({**self.filters, **changes})

    def create(self, name="filtered", **changes):
        params = {**self.filters, **changes}
        status, view = self.request(params)
        self.assertEqual(status, 200, view)
        return self.request(body={**params, "token": view["token"], "name": name})

    def query(self, sql, args=()):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            return conn.execute(sql, args).fetchall()

    def test_default_differences_and_all_annotation_columns(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO test_photo_comment(set_name,place,file_name,created_at,source,text) VALUES ('my','wine-1','photo.jpg','2026-10-01T00:00:00Z','user','keep me')"
            )
            conn.executemany(
                "INSERT INTO test_variant VALUES ('my',?,0)",
                [("wine-1",), ("wine-extra",)],
            )
            conn.execute(
                "INSERT INTO image_tag VALUES (?,'label_front','2026-10-01T00:00:00Z')",
                (self.rows[1]["image_sha256"],),
            )
        before = self.query("SELECT * FROM test_photo ORDER BY place,file_name")
        status, view = self.preview()
        self.assertEqual(
            (status, view["selected"], view["photos"], view["photo_comments"]),
            (200, 2, 2, 1),
        )
        status, out = self.create()
        self.assertEqual(status, 200, out)
        self.assertEqual(out["variant_slugs"], 2)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            cols = copy.testset_from_run._columns(conn, "test_photo")
            columns = ",".join(cols)
            source = conn.execute(
                f"SELECT {columns} FROM test_photo WHERE set_name='my' AND place IN ('wine-1','wine-2') ORDER BY place"
            ).fetchall()
            target = conn.execute(
                f"SELECT {columns} FROM test_photo WHERE set_name='filtered' ORDER BY place"
            ).fetchall()
            self.assertEqual(target, source)
        self.assertEqual(
            before,
            self.query(
                "SELECT * FROM test_photo WHERE set_name='my' ORDER BY place,file_name"
            ),
        )
        self.assertEqual(
            self.query(
                "SELECT text,source,created_at FROM test_photo_comment WHERE set_name='filtered'"
            ),
            [("keep me", "user", "2026-10-01T00:00:00Z")],
        )
        self.assertEqual(len(self.query("SELECT * FROM image_tag")), 1)
        self.assertEqual(self.query("PRAGMA foreign_key_check"), [])
        self.assertIn(
            '"group": "differences"',
            self.query("SELECT label_note FROM test_set WHERE set_name='filtered'")[0][
                0
            ],
        )

    def test_all_pages_are_copied_and_pagination_is_rejected(self):
        rows = [query(i) for i in range(125)]
        self.seed(rows)
        self.write("a", rows, [True] * len(rows))
        self.write("b", rows, [False] * len(rows))
        status, out = self.create()
        self.assertEqual((status, out["photos"]), (200, 125))
        self.assertEqual(self.preview(offset="50")[0], 400)
        self.assertEqual(self.preview(limit="2")[0], 400)

    def test_search_and_each_comparison_group(self):
        for group in ("regressions", "improvements", "both_succeed", "both_fail"):
            status, out = self.create(name=group, group=group)
            self.assertEqual((status, out["photos"]), (200, 1))
        status, out = self.create(name="search", q="wine-2")
        self.assertEqual((status, out["photos"]), (200, 1))
        self.assertEqual(
            self.query("SELECT place FROM test_photo WHERE set_name='search'"),
            [("wine-2",)],
        )

    def test_rank_filter_changes_selection(self):
        self.write("b", self.rows, candidates=[["wrong", r["slug"]] for r in self.rows])
        self.assertEqual(self.preview(k="1")[1]["selected"], 2)
        self.assertEqual(self.preview(k="5")[1]["selected"], 2)
        self.assertEqual(self.preview(group="regressions", k="5")[1]["selected"], 0)

    def test_no_match_and_negative_annotations_are_kept(self):
        rows = [
            query(
                8,
                slug="__null__",
                image_path="__null__/none.jpg",
                label="no_match",
                truth=[],
            ),
            query(9, label="negative", truth=[]),
        ]
        self.seed(rows)
        self.write("a", rows, candidates=[[], []])
        self.write("b", rows, candidates=[["wrong"], []])
        status, out = self.create(group="all")
        self.assertEqual((status, out["photos"]), (200, 2))
        self.assertEqual(
            self.query(
                "SELECT place,label FROM test_photo WHERE set_name='filtered' ORDER BY place"
            ),
            [("__null__", None), ("wine-9", "negative")],
        )

    def test_shared_image_keeps_all_accepted_wine_slugs(self):
        rows = [
            query(20, truth=["wine-20", "wine-21"]),
            query(
                21, image_sha256=query(20)["image_sha256"], truth=["wine-20", "wine-21"]
            ),
        ]
        self.seed(rows)
        self.write("a", rows, [True, True])
        self.write("b", rows, [False, False])
        # Filename search selects one assignment. The other accepted slug is retained.
        rows[0]["image_path"] = "wine-20/special.jpg"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "UPDATE test_photo SET file_name='special.jpg' WHERE place='wine-20'"
            )
        self.write("a", rows, [True, True])
        self.write("b", rows, [False, False])
        status, out = self.create(q="special.jpg")
        self.assertEqual(
            (status, out["selected"], out["photos"], out["support_photos"]),
            (200, 1, 2, 1),
        )
        with closing(sqlite3.connect(self.db)) as conn, conn:
            current, _ = benchmark.build_queries(conn, self.db, "filtered")
        self.assertEqual([r["truth"] for r in current], [["wine-20", "wine-21"]] * 2)

    def test_missing_source_photo_blocks_whole_copy(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("DELETE FROM test_photo WHERE place='wine-1'")
        status, view = self.preview()
        self.assertEqual(
            (status, view["conflicts"], view["can_create"]), (200, 1, False)
        )
        self.assertEqual(self.create()[0], 409)
        self.assertFalse(self.query("SELECT * FROM test_set WHERE set_name='filtered'"))

    def test_source_choice_and_compatibility_guard(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO test_set(set_name,source_dir) VALUES ('other','fixture')"
            )
        self.seed(self.rows, "other")
        changed = [{**self.rows[0], "label": "negative", "truth": []}, *self.rows[1:]]
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "UPDATE test_photo SET label='negative' WHERE set_name='other' AND place='wine-0'"
            )
        self.write(
            "b", changed, candidates=[["wrong"]] * 4, meta={"options": {"set": "other"}}
        )
        self.assertFalse(self.preview()[1]["can_create"])
        self.assertTrue(self.preview(common="1")[1]["can_create"])
        for side, expected in (("a", "positive"), ("b", "negative")):
            status, out = self.create(
                name="source_" + side, group="not_compared", source=side
            )
            self.assertEqual(status, 200, out)
            self.assertEqual(
                self.query(
                    "SELECT label FROM test_photo WHERE set_name=?", ("source_" + side,)
                ),
                [(expected,)],
            )

    def test_absent_side_has_no_silent_fallback(self):
        self.write("b", self.rows[1:], [False, True, False])
        self.assertFalse(
            self.preview(group="not_compared", source="b")[1]["can_create"]
        )
        self.assertTrue(self.preview(group="not_compared", source="a")[1]["can_create"])

    def test_stale_annotations_comments_and_run_files_reject_preview_token(self):
        for mutation in ("label", "box", "comment", "run"):
            status, view = self.preview(group="all")
            self.assertEqual(status, 200)
            with closing(sqlite3.connect(self.db)) as conn, conn:
                if mutation == "label":
                    conn.execute(
                        "UPDATE test_photo SET label='negative' WHERE place='wine-1'"
                    )
                elif mutation == "box":
                    conn.execute(
                        "UPDATE test_photo SET box_left=2 WHERE place='wine-2'"
                    )
                elif mutation == "comment":
                    conn.execute(
                        "INSERT INTO test_photo_comment(set_name,place,file_name,created_at,source,text) VALUES ('my','wine-2','photo.jpg','2026-10-01T00:00:00Z','user','new')"
                    )
                else:
                    (self.runs / "b/run.json").write_text(
                        (self.runs / "b/run.json").read_text() + " "
                    )
            status, out = self.request(
                body={
                    **self.filters,
                    "group": "all",
                    "token": view["token"],
                    "name": "stale",
                }
            )
            self.assertEqual(status, 409, (mutation, out))
            self.assertFalse(
                self.query("SELECT * FROM test_set WHERE set_name='stale'")
            )

    def test_write_failure_rolls_back_new_set_and_photos(self):
        status, view = self.preview()
        # A trigger simulates a failure after the first photo insert.
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "CREATE TRIGGER reject_copy BEFORE INSERT ON test_photo WHEN NEW.set_name='broken' AND NEW.place='wine-2' BEGIN SELECT RAISE(ABORT,'fixture failure'); END"
            )
        status, _ = self.request(
            body={**self.filters, "name": "broken", "token": view["token"]}
        )
        self.assertEqual(status, 503)
        self.assertFalse(self.query("SELECT * FROM test_set WHERE set_name='broken'"))
        self.assertFalse(self.query("SELECT * FROM test_photo WHERE set_name='broken'"))

    def test_names_methods_and_parameter_validation(self):
        self.assertEqual(self.request(self.filters, method="HEAD")[0], 200)
        self.assertEqual(self.request(method="DELETE")[0], 405)
        for changes in (
            {"source": "c"},
            {"q": ["one", "two"]},
            {"k": "3"},
            {"extra": "x"},
        ):
            self.assertEqual(self.preview(**changes)[0], 400)
        self.assertEqual(self.create(name="bad name")[0], 400)
        status, collision = self.create(name="my")
        self.assertEqual(status, 409)
        self.assertEqual(collision["error"], "The testset my already exists.")
        self.assertEqual(self.request(body={**self.filters, "name": "new"})[0], 400)
        self.assertFalse(self.preview(q="not-found")[1]["can_create"])

    def test_run_preparation_does_not_hold_the_database_write_lock(self):
        _, view = self.preview()
        original = copy.prepare

        def inspect_lock(*args):
            with closing(sqlite3.connect(self.db, timeout=0)) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.rollback()
            return original(*args)

        with mock.patch.object(copy, "prepare", side_effect=inspect_lock) as prepare:
            status, out = self.request(
                body={**self.filters, "token": view["token"], "name": "unlocked"}
            )
        self.assertEqual(status, 200, out)
        self.assertEqual(prepare.call_count, 1)

    def test_run_change_after_preparation_is_rejected(self):
        _, view = self.preview()
        original = copy.prepare

        def change_run(*args):
            prepared = original(*args)
            path = self.runs / "b/run.json"
            path.write_text(path.read_text() + " ")
            return prepared

        with mock.patch.object(copy, "prepare", side_effect=change_run):
            status, out = self.request(
                body={**self.filters, "token": view["token"], "name": "changed"}
            )
        self.assertEqual(status, 409, out)
        self.assertFalse(self.query("SELECT * FROM test_set WHERE set_name='changed'"))

    def test_unsupported_historical_labels_have_a_specific_conflict(self):
        rows = [query(9, label="unlabelled", truth=[])]
        self.seed(rows)
        self.write("a", rows, candidates=[[]])
        self.write("b", rows, candidates=[[]])
        status, out = self.preview(group="unscored")
        self.assertEqual(status, 200)
        self.assertFalse(out["can_create"])
        self.assertIn(
            "saved label unlabelled cannot be validated", out["conflict_examples"][0]
        )
