"""The views `matcher_wine` and `matcher_wine_image` of schema 031 (plan 75, stage 2).

The matcher reads these two views of a copy of `data/catalog/` alone. The tests compare
them with the rules of `embeddings.read_inputs` and of the bundle builder.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import embedding_lab  # noqa: E402
import embeddings  # noqa: E402
import matcher_bundle  # noqa: E402

WINE_COLUMNS = ["wine_slug", "name", "producer", "category", "region", "color", "grapes",
                "main_source_name", "qr_values"]
IMAGE_COLUMNS = ["wine_slug", "image_type", "sha256", "role"]


class MatcherViewsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.lab = lab = embedding_lab.Lab(directory.name)
        self.addCleanup(lab.close)
        grey = embedding_lab.bottle_on_grey
        lab.wine("wine-a")
        lab.wine("wine-b")
        lab.wine("wine-off", state="Disabled")
        # wine-a: the patch replaces the `main` image.
        self.a_main = lab.image("wine-a", "main", grey((10, 20, 30)))
        self.a_patch = lab.image("wine-a", "main_patched", grey((11, 21, 31)), folder="patched")
        # wine-b: a `main` image and a label close-up. The Disabled wine has the same image.
        self.b_main = lab.image("wine-b", "main", grey((12, 22, 32)))
        self.b_label = lab.image("wine-b", "label_front", grey((13, 23, 33)),
                                 folder="additional")
        lab.link("wine-off", "main", self.b_main)
        lab.conn.executemany("INSERT INTO wine_code (wine_slug, kind, value) VALUES (?, ?, ?)",
                             [("wine-b", "qr_url", "https://b.example/x"),
                              ("wine-b", "qr_url", "http://b.example:80/y"),
                              ("wine-b", "gtin", "04607001234567")])
        lab.conn.commit()

    def rows(self, sql):
        return self.lab.conn.execute(sql).fetchall()

    def test_the_columns_are_the_contract_of_the_matcher(self):
        self.assertEqual([row[1] for row in self.rows("PRAGMA table_info(matcher_wine)")],
                         WINE_COLUMNS)
        self.assertEqual([row[1] for row in self.rows("PRAGMA table_info(matcher_wine_image)")],
                         IMAGE_COLUMNS)

    def test_the_image_view_follows_the_rules_of_read_inputs(self):
        view = sorted(self.rows("SELECT %s FROM matcher_wine_image" % ", ".join(IMAGE_COLUMNS)))
        self.assertEqual(view, sorted([("wine-a", "main_patched", self.a_patch, "full"),
                                       ("wine-b", "main", self.b_main, "full"),
                                       ("wine-b", "label_front", self.b_label, "label")]))
        wines, _ = embeddings.read_inputs(self.lab.conn, self.lab.db_path)
        self.assertEqual(view, sorted((wine["slug"], image_type, digest,
                                       embeddings.ROLES[image_type])
                                      for wine in wines for image_type, digest in wine["columns"]))

    def test_the_wine_view_gives_the_card_fields_of_the_bundle_builder(self):
        view = {row[0]: dict(zip(WINE_COLUMNS, row)) for row in self.rows(
            "SELECT %s FROM matcher_wine" % ", ".join(WINE_COLUMNS))}
        self.assertEqual(sorted(view), ["wine-a", "wine-b"])
        cards = matcher_bundle._card_fields(self.lab.conn)
        for slug, row in view.items():
            card = cards[slug]
            self.assertEqual((row["color"], row["grapes"]), (card["color"], card["grapes"]))
            self.assertEqual(matcher_bundle.IMAGE_URL_PREFIX + row["main_source_name"],
                             card["image_url"])
            self.assertEqual(sorted({matcher_bundle.normalize_qr_url(value)
                                     for value in json.loads(row["qr_values"])}),
                             card["qr_urls"])
        self.assertEqual(json.loads(view["wine-a"]["qr_values"]), [])
        self.assertEqual(sorted(json.loads(view["wine-b"]["qr_values"])),
                         ["http://b.example:80/y", "https://b.example/x"])


if __name__ == "__main__":
    unittest.main()
