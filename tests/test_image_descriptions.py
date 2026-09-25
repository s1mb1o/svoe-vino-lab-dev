import sqlite3
import unittest

from image_description_fixture import DescriptionCase

import image_descriptions as DESC

ANSWER = {"package_type": "bottle", "subject_scope": "full_package",
          "package_view": "front", "content_roles": ["front_label"]}


class CheckValueTest(unittest.TestCase):
    def test_the_values_of_each_field(self):
        for field, values in DESC.VALUES.items():
            if field != "content_roles":
                for value in values:
                    self.assertEqual(DESC.check_value(field, value), value)
        self.assertIsNone(DESC.check_value("package_type", None))
        self.assertEqual(DESC.check_value("subject_scope", "multiple_packages"),
                         "multiple_packages")

    def test_the_lists_of_content_roles(self):
        for roles in (["front_label"], ["back_label", "front_label"], ["unknown"]):
            self.assertEqual(DESC.check_value("content_roles", roles), roles)
        for roles in ([], ["unknown", "front_label"], ["front_label", "front_label"],
                      ["side_label"], "front_label", ["front_label", "back_label", "unknown"]):
            with self.subTest(roles=roles):
                with self.assertRaises(DESC.DescriptionError):
                    DESC.check_value("content_roles", roles)

    def test_a_value_out_of_its_set(self):
        for field, value in (("package_type", "carton"), ("subject_scope", "collage"),
                             ("package_view", "side"), ("package_view", ""), ("other", "x")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(DESC.DescriptionError):
                    DESC.check_value(field, value)


class TableTest(DescriptionCase):
    def test_a_manual_value_makes_a_manual_row(self):
        with self.connect() as conn:
            row = DESC.set_values(conn, self.sha["wine-a"], {"package_type": "tetra_pak"},
                                  now="2026-09-25T10:00:00Z")
        self.assertEqual((row["package_type"], row["subject_scope"], row["created_by"]),
                         ("tetra_pak", None, "manual"))
        self.assertEqual((row["created_at"], row["updated_at"], row["vlm_at"]),
                         ("2026-09-25T10:00:00Z", "2026-09-25T10:00:00Z", None))

    def test_a_second_save_changes_only_its_fields(self):
        with self.connect() as conn:
            sha = self.sha["wine-a"]
            DESC.set_values(conn, sha, {"package_type": "can", "package_view": "back"})
            row = DESC.set_values(conn, sha, {"package_view": None,
                                              "content_roles": ["back_label"]},
                                  now="2026-09-25T11:00:00Z")
        self.assertEqual((row["package_type"], row["package_view"], row["content_roles"]),
                         ("can", None, ["back_label"]))
        self.assertEqual(row["updated_at"], "2026-09-25T11:00:00Z")

    def test_the_vlm_fills_only_the_values_that_are_not_set(self):
        sha = self.sha["wine-a"]
        with self.connect() as conn:
            DESC.set_values(conn, sha, {"package_type": "tetra_pak"})
            self.assertTrue(DESC.record_vlm(conn, sha, ANSWER, "vlm-a", "Model-A"))
            row = DESC.description(conn, sha)
        self.assertEqual((row["package_type"], row["subject_scope"], row["package_view"],
                          row["content_roles"]),
                         ("tetra_pak", "full_package", "front", ["front_label"]))
        self.assertEqual((row["created_by"], row["vlm_name"], row["vlm_model"]),
                         ("manual", "vlm-a", "Model-A"))
        self.assertEqual(row["vlm_answer"], ANSWER)
        self.assertIsNotNone(row["vlm_at"])

    def test_a_second_vlm_answer_is_not_taken(self):
        sha = self.sha["wine-b"]
        with self.connect() as conn:
            self.assertTrue(DESC.record_vlm(conn, sha, ANSWER, "vlm-a", "Model-A"))
            other = dict(ANSWER, package_type="can")
            self.assertFalse(DESC.record_vlm(conn, sha, other, "vlm-a", "Model-A"))
            row = DESC.description(conn, sha)
        self.assertEqual((row["package_type"], row["created_by"]), ("bottle", "vlm"))

    def test_the_failures(self):
        sha = self.sha["wine-b"]
        with self.connect() as conn:
            DESC.record_failure(conn, sha, "bad answer")
            DESC.record_failure(conn, sha, "no connection", count=False)
            row = DESC.description(conn, sha)
            self.assertEqual((row["vlm_attempts"], row["vlm_error"], row["created_by"]),
                             (1, "no connection", "vlm"))
            self.assertEqual(DESC.reset_failed(conn), 1)
            DESC.record_vlm(conn, sha, ANSWER, "vlm-a", "Model-A")
            DESC.record_failure(conn, sha, "late")
            row = DESC.description(conn, sha)
        self.assertEqual((row["vlm_attempts"], row["vlm_error"]), (0, None))

    def test_pending_holds_the_linked_images_alone_the_newest_first(self):
        with self.connect() as conn:
            self.assertEqual([r[0] for r in DESC.pending(conn, 3)],
                             [self.sha["wine-b"], self.sha["wine-a"]])
            DESC.set_values(conn, self.sha["wine-b"], {"package_type": "can"})
            self.assertEqual(len(DESC.pending(conn, 3)), 2)
            DESC.record_vlm(conn, self.sha["wine-b"], ANSWER, "vlm-a", "Model-A")
            for _ in range(3):
                DESC.record_failure(conn, self.sha["wine-a"], "bad answer")
            self.assertEqual(DESC.pending(conn, 3), [])
            self.assertEqual([r[0] for r in DESC.pending(conn, 4, limit=1)],
                             [self.sha["wine-a"]])
            self.assertTrue(DESC.is_linked(conn, self.sha["wine-a"]))
            self.assertFalse(DESC.is_linked(conn, self.sha["none"]))

    def test_descriptions_parse_the_json_columns(self):
        with self.connect() as conn:
            DESC.set_values(conn, self.sha["wine-a"], {"content_roles": ["front_label"]})
            DESC.record_vlm(conn, self.sha["wine-b"], ANSWER, "vlm-a", "Model-A")
            rows = DESC.descriptions(conn)
        self.assertEqual(set(rows), {self.sha["wine-a"], self.sha["wine-b"]})
        self.assertEqual(rows[self.sha["wine-a"]]["content_roles"], ["front_label"])
        self.assertEqual(rows[self.sha["wine-b"]]["vlm_answer"], ANSWER)
        self.assertEqual(DESC.preset(rows[self.sha["wine-a"]]),
                         {"content_roles": ["front_label"]})

    def test_the_checks_of_the_table(self):
        sha = self.sha["wine-a"]
        bad = ("INSERT INTO image_description (sha256, package_type, created_by, created_at, "
               "updated_at) VALUES (?, ?, 'manual', '2026-09-25T10:00:00Z', "
               "'2026-09-25T10:00:00Z')")
        with self.connect() as conn:
            for value in ("carton", ""):
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(bad, (sha, value))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO image_description (sha256, created_by, created_at, "
                             "updated_at, vlm_at) VALUES (?, 'vlm', '2026-09-25T10:00:00Z', "
                             "'2026-09-25T10:00:00Z', '2026-09-25T10:00:00Z')", (sha,))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO image_description (sha256, created_by, created_at, "
                             "updated_at) VALUES (?, 'person', '2026-09-25T10:00:00Z', "
                             "'2026-09-25T10:00:00Z')", (sha,))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO image_description (sha256, created_by, created_at, "
                             "updated_at) VALUES (?, 'manual', '2026-09-25T10:00:00Z', "
                             "'2026-09-25T10:00:00Z')", ("f" * 64,))


class WatcherStatusTest(DescriptionCase):
    def status(self):
        with self.connect() as conn:
            return DESC.watcher_status(conn)

    def test_the_counts_of_the_linked_images(self):
        with self.connect() as conn:
            self.assertEqual(DESC.counts(conn, 3),
                             {"linked": 2, "described": 0, "failed": 0, "pending": 2})
            DESC.record_vlm(conn, self.sha["wine-a"], ANSWER, "vlm-a", "Model-A")
            DESC.record_failure(conn, self.sha["wine-b"], "bad answer")
            self.assertEqual(DESC.counts(conn, 1),
                             {"linked": 2, "described": 1, "failed": 1, "pending": 0})
            self.assertEqual(DESC.counts(conn, 3)["pending"], 1)

    def test_no_file_is_stopped(self):
        answer = self.status()
        self.assertEqual((answer["state"], answer["pid"], answer["linked"]), ("stopped", None, 2))

    def test_a_living_watcher_gives_its_state_and_the_slug_of_its_image(self):
        import os
        DESC.write_status({"pid": os.getpid(), "state": "working", "vlm": "vlm-a",
                           "sha256": self.sha["wine-b"], "seconds_per_image": 2.4,
                           "max_attempts": 3, "updated_at": "2026-09-25T10:00:00Z",
                           "error": "old"})
        answer = self.status()
        self.assertEqual((answer["state"], answer["pid"], answer["slug"], answer["vlm"]),
                         ("working", os.getpid(), "wine-b", "vlm-a"))
        self.assertEqual((answer["seconds_per_image"], answer["error"]), (2.4, None))
        DESC.write_status({"pid": os.getpid(), "state": "waiting", "error": "HTTP 503"})
        answer = self.status()
        self.assertEqual((answer["state"], answer["error"], answer["sha256"]),
                         ("waiting", "HTTP 503", None))

    def test_a_process_that_is_gone_is_stopped(self):
        import subprocess
        import sys
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait()
        for status in ({"pid": child.pid, "state": "working"}, {"pid": "x", "state": "idle"},
                       {"state": "working"}):
            DESC.write_status(status)
            self.assertEqual(self.status()["state"], "stopped")
        with open(self.status_path, "w") as fh:
            fh.write("not json")
        self.assertEqual(self.status()["state"], "stopped")


if __name__ == "__main__":
    unittest.main()
