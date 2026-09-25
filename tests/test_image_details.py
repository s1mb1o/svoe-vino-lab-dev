import sqlite3
import unittest

from image_description_fixture import DescriptionCase

import image_descriptions
import image_details as DET

ANSWER = {"texts": [{"text": "МЫСХАКО", "where": "main label"}], "numbers": [],
          "vintage": None, "colours": ["black"], "design": "a black label",
          "marks": [], "bottle": "dark green"}


class DetailCase(DescriptionCase):
    def pending(self, max_attempts=3):
        with self.connect() as conn:
            return DET.pending(conn, max_attempts)

    def target(self, slug):
        with self.connect() as conn:
            return DET.target(conn, self.sha[slug])

    def detail(self, slug):
        with self.connect() as conn:
            return DET.detail(conn, self.sha[slug])

    def counts(self):
        with self.connect() as conn:
            return DET.counts(conn, 3)

    def answer(self, item):
        conn = self.connect()
        with conn:
            DET.record_answer(conn, item, ANSWER, "gx10-test", "Model-1", now="T1")
        conn.close()

    def fail(self, item, times=1, count=True):
        conn = self.connect()
        with conn:
            for _ in range(times):
                DET.record_failure(conn, item, "bad", count=count, now="T1")
        conn.close()


class EligibleTest(DetailCase):
    def test_only_a_full_package_or_a_label_closeup_with_a_named_type(self):
        self.assertEqual(self.pending(), [])
        self.classify("wine-a", package_type="bottle", subject_scope="full_package")
        self.classify("wine-b", package_type="bottle", subject_scope="multiple_packages")
        self.assertEqual([row[0] for row in self.pending()], [self.sha["wine-a"]])
        for scope, kind in (("label_closeup", "label"), ("unknown", None)):
            with self.subTest(scope=scope):
                self.classify("wine-b", package_type="bottle", subject_scope=scope)
                item = self.target("wine-b")
                self.assertEqual(item[1] if item else None, kind)
        self.classify("wine-b", package_type="other", subject_scope="full_package")
        self.assertIsNone(self.target("wine-b"))
        self.classify("wine-b", package_type=None, subject_scope="full_package")
        self.assertIsNone(self.target("wine-b"))

    def test_an_image_with_no_link_is_not_eligible(self):
        conn = self.connect()
        with conn:
            image_descriptions.set_values(conn, self.sha["none"], {
                "package_type": "bottle", "subject_scope": "full_package"})
        conn.close()
        self.assertIsNone(self.target("none"))
        self.assertEqual(self.pending(), [])

    def test_the_newest_link_comes_first(self):
        for slug in ("wine-a", "wine-b"):
            self.classify(slug, package_type="can", subject_scope="full_package")
        self.assertEqual([row[0] for row in self.pending()],
                         [self.sha["wine-b"], self.sha["wine-a"]])


class InputTest(DetailCase):
    def test_a_full_package_gets_its_package_cut_else_the_original(self):
        self.classify("wine-a", package_type="bottle", subject_scope="full_package")
        self.assertEqual(self.target("wine-a"),
                         (self.sha["wine-a"], "package", "bottle", self.sha["wine-a"],
                          "main", "png"))
        self.add_cut("wine-a", "label", "yellow")
        self.assertEqual(self.target("wine-a")[3], self.sha["wine-a"])
        cut = self.add_cut("wine-a", "package", "white")
        self.assertEqual(self.target("wine-a")[3:], (cut, "cropped", "png"))

    def test_a_label_closeup_gets_its_label_cut_else_its_package_cut(self):
        self.classify("wine-a", package_type="bottle", subject_scope="label_closeup")
        self.assertEqual(self.target("wine-a")[1:4], ("label", "bottle", self.sha["wine-a"]))
        package = self.add_cut("wine-a", "package", "white")
        self.assertEqual(self.target("wine-a")[3], package)
        label = self.add_cut("wine-a", "label", "yellow")
        self.assertEqual(self.target("wine-a")[3], label)


class StaleTest(DetailCase):
    def setUp(self):
        super().setUp()
        self.classify("wine-a", package_type="bottle", subject_scope="full_package")
        self.cut = self.add_cut("wine-a", "package", "white")

    def test_an_answer_makes_the_target_done(self):
        item = self.target("wine-a")
        self.answer(item)
        row = self.detail("wine-a")
        self.assertEqual((row["prompt_kind"], row["package_type"], row["input_sha256"]),
                         ("package", "bottle", self.cut))
        self.assertEqual((row["answer"], row["vlm_at"], row["vlm_name"], row["vlm_model"]),
                         (ANSWER, "T1", "gx10-test", "Model-1"))
        self.assertEqual(self.pending(), [])
        with self.connect() as conn:
            self.assertTrue(DET.is_done(conn, item))
        self.assertEqual(self.counts(), {"details_eligible": 1, "details_done": 1,
                                         "details_failed": 0, "details_pending": 0})

    def test_a_new_package_type_makes_the_row_stale(self):
        self.answer(self.target("wine-a"))
        self.classify("wine-a", package_type="tetra_pak")
        item = self.target("wine-a")
        self.assertEqual(self.pending(), [item])
        with self.connect() as conn:
            self.assertFalse(DET.is_done(conn, item))
        self.assertEqual(self.counts()["details_pending"], 1)
        self.answer(item)
        self.assertEqual(self.detail("wine-a")["package_type"], "tetra_pak")
        self.assertEqual(self.pending(), [])

    def test_a_new_cut_makes_the_row_stale(self):
        self.answer(self.target("wine-a"))
        new = self.add_cut("wine-a", "package", "silver")
        self.assertEqual([row[3] for row in self.pending()], [new])

    def test_three_failures_stop_the_image_until_the_inputs_change(self):
        self.fail(self.target("wine-a"), times=3)
        self.assertEqual(self.pending(), [])
        self.assertEqual(self.counts()["details_failed"], 1)
        self.assertEqual(self.detail("wine-a")["vlm_error"], "bad")
        self.classify("wine-a", subject_scope="label_closeup")
        item = self.target("wine-a")
        self.assertEqual(self.pending(), [item])
        self.fail(item)
        row = self.detail("wine-a")
        self.assertEqual((row["prompt_kind"], row["vlm_attempts"]), ("label", 1))

    def test_a_stale_write_clears_the_old_answer(self):
        self.answer(self.target("wine-a"))
        self.classify("wine-a", package_type="can")
        self.fail(self.target("wine-a"))
        row = self.detail("wine-a")
        self.assertEqual((row["package_type"], row["answer"], row["vlm_at"],
                          row["vlm_attempts"]), ("can", None, None, 1))

    def test_a_failure_of_the_service_is_not_counted_and_a_done_row_stays(self):
        item = self.target("wine-a")
        self.fail(item, count=False)
        self.assertEqual(self.detail("wine-a")["vlm_attempts"], 0)
        self.answer(item)
        self.fail(item)
        row = self.detail("wine-a")
        self.assertEqual((row["vlm_attempts"], row["vlm_error"], row["answer"]),
                         (0, None, ANSWER))

    def test_failed_lists_the_images_that_counts_counts_as_failed(self):
        with self.connect() as conn:
            self.assertEqual(DET.failed(conn, 3), [])
        self.fail(self.target("wine-a"), times=3)
        with self.connect() as conn:
            self.assertEqual(DET.failed(conn, 3), [{
                "sha256": self.sha["wine-a"], "wine_slug": "wine-a",
                "prompt_kind": "package", "package_type": "bottle",
                "input_sha256": self.cut, "input_url": "/images/cropped/%s.png" % self.cut,
                "vlm_attempts": 3, "vlm_error": "bad", "updated_at": "T1"}])
            self.assertEqual(DET.failed(conn, 4), [])
        # New inputs make the row stale: the image waits again and is not failed.
        self.classify("wine-a", package_type="can")
        with self.connect() as conn:
            self.assertEqual(DET.failed(conn, 3), [])

    def test_reset_failed(self):
        self.fail(self.target("wine-a"), times=3)
        with self.connect() as conn:
            self.assertEqual(DET.reset_failed(conn), 1)
        self.assertEqual(len(self.pending()), 1)

    def test_the_checks_of_the_table(self):
        bad = [("prompt_kind", "'full'"), ("answer", "'not json'"), ("vlm_attempts", "-1"),
               ("input_sha256", "'%s'" % ("0" * 64))]
        for column, value in bad:
            with self.subTest(column=column):
                # The connection rolls back the INSERT when the UPDATE fails.
                with self.assertRaises(sqlite3.IntegrityError), self.connect() as conn:
                    conn.execute(
                        "INSERT INTO image_detail (sha256, prompt_kind, package_type, "
                        "input_sha256, created_at, updated_at) VALUES (?, 'package', "
                        "'bottle', ?, 'T', 'T')", (self.sha["wine-b"], self.cut))
                    conn.execute("UPDATE image_detail SET %s = %s WHERE sha256 = ?"
                                 % (column, value), (self.sha["wine-b"],))
        with self.connect() as conn:
            self.assertIsNone(DET.detail(conn, self.sha["wine-b"]))


if __name__ == "__main__":
    unittest.main()
