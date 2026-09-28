import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# `scripts/common.py` reads the old configuration of the review tool: `config.yaml` is
# the configuration of the lab server.
os.environ.setdefault("SVOE_VINO_REVIEW_CONFIG", str(ROOT / "config.old.yaml"))
SPEC = importlib.util.spec_from_file_location(
    "review_server_for_atlas_binding_tests", ROOT / "scripts" / "review_server.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)

FIRST_UUID = "6062ada1-5a02-40df-b541-00be133fa36d"
SECOND_UUID = "6b763a31-0575-4bf5-b0f1-81a7cbd58c56"


class DatasetAtlasBindingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "atlas-bindings.jsonl"
        self.matches_path = Path(self.directory.name) / "atlas-matches.jsonl"
        self.old_matches_file = SERVER.ATLAS_MATCHES_FILE
        self.old_file = SERVER.ATLAS_BINDINGS_FILE
        self.old_matches = SERVER._atlas_matches
        self.old_manual = SERVER._atlas_manual_bindings
        self.old_bindings = SERVER._atlas_bindings
        SERVER.ATLAS_MATCHES_FILE = str(self.matches_path)
        SERVER.ATLAS_BINDINGS_FILE = str(self.path)
        SERVER._atlas_matches = {}
        SERVER._atlas_manual_bindings = {}
        SERVER._atlas_bindings = {}
        self.catalog = {
            "wine-a": {"slug": "wine-a"},
            "wine-b": {"slug": "wine-b"},
        }

    def tearDown(self):
        SERVER.ATLAS_MATCHES_FILE = self.old_matches_file
        SERVER.ATLAS_BINDINGS_FILE = self.old_file
        SERVER._atlas_matches = self.old_matches
        SERVER._atlas_manual_bindings = self.old_manual
        SERVER._atlas_bindings = self.old_bindings
        self.directory.cleanup()

    def write_rows(self, rows):
        self.path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        SERVER.reload_atlas_bindings()

    def test_add_normalizes_uuid_and_sorts_rows(self):
        self.write_rows([{"wine_slug": "wine-b", "product_uuid": SECOND_UUID}])

        stored = SERVER.store_dataset_atlas_binding(
            self.catalog, "wine-a", FIRST_UUID.upper())

        self.assertEqual(stored, FIRST_UUID)
        self.assertEqual(SERVER._atlas_bindings, {
            "wine-a": FIRST_UUID, "wine-b": SECOND_UUID,
        })
        rows = [json.loads(line) for line in self.path.read_text().splitlines()]
        self.assertEqual([row["wine_slug"] for row in rows], ["wine-a", "wine-b"])

    def test_replace_preserves_other_record_fields(self):
        self.write_rows([{
            "wine_slug": "wine-a", "product_uuid": FIRST_UUID,
            "note": "keep this field",
        }])

        SERVER.store_dataset_atlas_binding(self.catalog, "wine-a", SECOND_UUID)

        row = json.loads(self.path.read_text())
        self.assertEqual(row["product_uuid"], SECOND_UUID)
        self.assertEqual(row["note"], "keep this field")

    def test_manual_binding_overrides_automatic_match(self):
        self.matches_path.write_text(json.dumps({
            "wine_slug": "wine-a", "product_uuid": FIRST_UUID,
        }) + "\n", encoding="utf-8")
        self.write_rows([])
        automatic_before = self.matches_path.read_bytes()

        SERVER.store_dataset_atlas_binding(self.catalog, "wine-a", SECOND_UUID)

        self.assertEqual(SERVER._atlas_matches["wine-a"], FIRST_UUID)
        self.assertEqual(SERVER._atlas_manual_bindings["wine-a"], SECOND_UUID)
        self.assertEqual(SERVER._atlas_bindings["wine-a"], SECOND_UUID)
        self.assertEqual(self.matches_path.read_bytes(), automatic_before)

    def test_two_slugs_may_bind_to_one_atlas_product(self):
        self.write_rows([{"wine_slug": "wine-a", "product_uuid": FIRST_UUID}])

        SERVER.store_dataset_atlas_binding(self.catalog, "wine-b", FIRST_UUID)

        self.assertEqual(SERVER._atlas_bindings, {
            "wine-a": FIRST_UUID, "wine-b": FIRST_UUID,
        })

    def test_invalid_uuid_and_unknown_slug_are_rejected(self):
        self.write_rows([])

        with self.assertRaisesRegex(ValueError, "not a valid UUID"):
            SERVER.store_dataset_atlas_binding(self.catalog, "wine-a", "not-a-uuid")
        with self.assertRaisesRegex(ValueError, "unknown wine slug"):
            SERVER.store_dataset_atlas_binding(self.catalog, "missing", FIRST_UUID)


if __name__ == "__main__":
    unittest.main()
