from __future__ import annotations

import io
import tarfile
import unittest

from scripts.install_model_bundles import select_entries, validate_members


class BundleSafetyTest(unittest.TestCase):
    def archive(self, name: str, *, symbolic: bool = False) -> tarfile.TarFile:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as output:
            member = tarfile.TarInfo(name)
            if symbolic:
                member.type = tarfile.SYMTYPE
                member.linkname = "/tmp/target"
                output.addfile(member)
            else:
                payload = b"model"
                member.size = len(payload)
                output.addfile(member, io.BytesIO(payload))
        buffer.seek(0)
        return tarfile.open(fileobj=buffer, mode="r")

    def test_accepts_regular_model_file(self) -> None:
        with self.archive("facebook--sam3/config.json") as archive:
            validate_members(archive, "facebook--sam3")

    def test_rejects_parent_path(self) -> None:
        with self.archive("facebook--sam3/../escape") as archive:
            with self.assertRaises(ValueError):
                validate_members(archive, "facebook--sam3")

    def test_rejects_symbolic_link(self) -> None:
        with self.archive("facebook--sam3/model", symbolic=True) as archive:
            with self.assertRaises(ValueError):
                validate_members(archive, "facebook--sam3")

    def test_empty_selection_installs_all_manifest_entries(self) -> None:
        manifest = {
            "bundles": [
                {"model_id": "facebook/sam3"},
                {"model_id": "google/shieldgemma-2-4b-it"},
            ]
        }
        self.assertEqual(select_entries(manifest, None), manifest["bundles"])

    def test_unknown_selection_is_rejected(self) -> None:
        manifest = {"bundles": [{"model_id": "facebook/sam3"}]}
        with self.assertRaisesRegex(ValueError, "missing/model"):
            select_entries(manifest, ["missing/model"])


if __name__ == "__main__":
    unittest.main()
