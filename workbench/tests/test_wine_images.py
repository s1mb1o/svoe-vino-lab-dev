"""The static wine images of chtozavino.ru (plan `docs/plans/06_wine-images.md` of the
repository): the release build, the release check, and the check of a published release.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))
import build_wine_images  # noqa: E402
import check_wine_images  # noqa: E402
import embedding_lab  # noqa: E402
import wine_images  # noqa: E402


def png_bytes(image, **options):
    buffer = io.BytesIO()
    image.save(buffer, "PNG", **options)
    return buffer.getvalue()


def two_bottles():
    """RGBA 60 x 100: two opaque bottles (10..20, 40..50) x (10..90), transparent between."""
    image = Image.new("RGBA", (60, 100), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((10, 10, 19, 89), fill=(90, 30, 20, 255))
    ImageDraw.Draw(image).rectangle((40, 10, 49, 89), fill=(90, 30, 20, 255))
    return image


def framed_photo():
    """RGB 100 x 150: a black frame of 5 px around a grey photo with a red bottle. The box
    of the photo is (5, 5, 95, 145)."""
    image = Image.new("RGB", (100, 150), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 94, 144), fill=(128, 128, 128))
    draw.rectangle((30, 30, 69, 119), fill=(200, 20, 20))
    return image


class WineImagesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.lab = lab = embedding_lab.Lab(self.root / "lab")
        self.addCleanup(lab.close)
        grey = embedding_lab.bottle_on_grey
        for slug in ("wine-a", "wine-b", "wine-big", "wine-c", "wine-d", "wine-rot",
                     "wine-twin", "wine-alpha", "wine-cut", "wine-frame"):
            lab.wine(slug)
        lab.wine("wine-off", state="Disabled")
        # wine-a: the patch replaces the `main` image.
        self.a_main = lab.image("wine-a", "main", grey((10, 20, 30)))
        self.a_patch = lab.image("wine-a", "main_patched", grey((11, 21, 31)), folder="patched")
        self.b_main = lab.image("wine-b", "main", grey((12, 22, 32)))
        # wine-twin has the original of wine-b.
        lab.link("wine-twin", "main", self.b_main)
        self.big = lab.image("wine-big", "main", Image.new("RGB", (2000, 3000), (200, 10, 10)))
        self.alpha = lab.image("wine-alpha", "main", two_bottles())
        self.framed = lab.image("wine-frame", "main", framed_photo())
        # wine-cut: a grey original with its SAM3 package cut of plan 09.
        original = grey((14, 24, 34))
        self.cut_source = lab.image("wine-cut", "main", original,
                                    derivative=embedding_lab.seg_derivative(original, (30, 20, 50, 100)),
                                    box=(30, 20, 50, 100))
        self.cut = lab.conn.execute("SELECT sha256 FROM image_derivative WHERE source_sha256 = ?",
                                    (self.cut_source,)).fetchone()[0]
        # wine-can: a tight, fully opaque package cut of a can with a black cap and base.
        can = Image.new("RGBA", (40, 100), (30, 140, 120, 255))
        ImageDraw.Draw(can).rectangle((0, 0, 39, 9), fill=(0, 0, 0, 255))
        ImageDraw.Draw(can).rectangle((0, 90, 39, 99), fill=(0, 0, 0, 255))
        lab.wine("wine-can")
        lab.image("wine-can", "main", embedding_lab.bottle_on_transparent(), derivative=can,
                  box=(10, 0, 50, 100))
        # wine-c has no image. wine-d has a label close-up alone, so it has no image either.
        lab.image("wine-d", "label_front", grey((13, 23, 33)), folder="additional")
        # wine-off is not Active.
        lab.link("wine-off", "main", self.b_main)
        # wine-rot: EXIF orientation 6 turns the 200 x 100 original to 100 x 200.
        exif = Image.Exif()
        exif[0x0112] = 6
        rotated = lab.store_file(png_bytes(Image.new("RGB", (200, 100), (5, 5, 5)), exif=exif),
                                 "main", "png")
        lab.link("wine-rot", "main", rotated)
        # wine-key: an RGB PNG with a colour-key transparency (a tRNS chunk), no alpha channel.
        lab.wine("wine-key")
        keyed = lab.store_file(png_bytes(embedding_lab.bottle_on_grey(), transparency=(128, 128, 128)),
                               "main", "png")
        lab.link("wine-key", "main", keyed)
        self.db = lab.db_path

    def build(self, name="release"):
        out = self.root / name
        result = wine_images.build(self.db, out)
        return out, result, json.loads((out / wine_images.MANIFEST).read_text("utf-8"))

    def test_the_release_holds_the_main_patched_or_main_image_of_each_active_wine(self):
        out, result, manifest = self.build()
        wines = manifest["wines"]
        self.assertEqual(sorted(wines), ["wine-a", "wine-alpha", "wine-b", "wine-big",
                                         "wine-c", "wine-can", "wine-cut", "wine-d",
                                         "wine-frame", "wine-key", "wine-rot", "wine-twin"])
        self.assertEqual((wines["wine-a"]["source"], wines["wine-a"]["source_sha256"]),
                         ("main_patched", self.a_patch))
        self.assertEqual((wines["wine-b"]["source"], wines["wine-b"]["source_sha256"]),
                         ("main", self.b_main))
        self.assertEqual(wines["wine-twin"]["files"], wines["wine-b"]["files"])
        for slug in ("wine-c", "wine-d"):
            self.assertEqual(wines[slug], {"source": None, "source_sha256": None,
                                           "cut_sha256": None, "files": {}})
            self.assertFalse((out / "1600" / ("%s.webp" % slug)).exists())
        self.assertEqual((manifest["format"], manifest["version"], manifest["sizes"]),
                         (wine_images.FORMAT, 2, [1600, 400]))
        self.assertEqual((wines["wine-cut"]["source_sha256"], wines["wine-cut"]["cut_sha256"]),
                         (self.cut_source, self.cut))
        self.assertIsNone(wines["wine-b"]["cut_sha256"])
        self.assertEqual(manifest["catalog"]["active_wines"], 12)
        self.assertEqual(manifest["catalog"]["sha256"], wine_images.sha256_file(self.db))
        self.assertEqual(result["wines"], 12)
        self.assertEqual((result["images"], result["no_image"], result["patched"],
                          result["from_cut"], result["files"]), (10, 2, 1, 2, 20))
        self.assertEqual(oct(out.stat().st_mode & 0o777), "0o755")
        self.assertEqual([p.name for p in out.parent.iterdir() if p.name.startswith(".")], [])

    def test_the_files_keep_the_aspect_ratio_and_are_not_enlarged(self):
        out, _, manifest = self.build()
        big = manifest["wines"]["wine-big"]["files"]
        self.assertEqual((big["1600"]["width"], big["1600"]["height"]), (1067, 1600))
        self.assertEqual((big["400"]["width"], big["400"]["height"]), (267, 400))
        small = manifest["wines"]["wine-b"]["files"]
        self.assertEqual((small["1600"]["width"], small["1600"]["height"]), (80, 120))
        self.assertEqual((small["400"]["width"], small["400"]["height"]), (80, 120))
        # An image that is only black border keeps its whole canvas.
        rotated = manifest["wines"]["wine-rot"]["files"]["400"]
        self.assertEqual((rotated["width"], rotated["height"]), (100, 200))
        # The file of wine-cut is its package cut, not the 80 x 120 grey original.
        cut = manifest["wines"]["wine-cut"]["files"]["400"]
        self.assertEqual((cut["width"], cut["height"]), (20, 80))
        # The opaque can cut keeps its black cap and base (review of 2026-10-19).
        can = manifest["wines"]["wine-can"]["files"]["400"]
        self.assertEqual((can["width"], can["height"]), (40, 100))
        # The black frame of the opaque photo goes.
        framed = manifest["wines"]["wine-frame"]["files"]["400"]
        self.assertEqual((framed["width"], framed["height"]), (90, 140))
        with Image.open(out / "400" / "wine-big.webp") as image:
            self.assertEqual((image.format, image.size), ("WEBP", (267, 400)))
            self.assertNotIn("exif", image.info)
        # The trim keeps the transparency between the two bottles.
        with Image.open(out / "400" / "wine-alpha.webp") as image:
            self.assertEqual((image.mode, image.size), ("RGBA", (40, 80)))
            self.assertEqual((image.getpixel((20, 40))[3], image.getpixel((5, 40))[3]), (0, 255))
        # The tRNS key makes the grey transparent, so the trim keeps the bottle alone. The
        # WebP encoder drops an alpha channel that is fully opaque.
        with Image.open(out / "400" / "wine-key.webp") as image:
            self.assertEqual(image.size, (20, 80))

    def test_the_sums_file_names_each_file(self):
        out, _, manifest = self.build()
        lines = (out / wine_images.SUMS).read_text("ascii").splitlines()
        names = [line.split("  ", 1)[1] for line in lines]
        self.assertEqual(names, sorted(names))
        self.assertIn(wine_images.MANIFEST, names)
        self.assertEqual(len(names), 1 + 20)
        for line in lines:
            digest, name = line.split("  ", 1)
            self.assertEqual(wine_images.sha256_file(out / name), digest)

    def test_a_missing_or_changed_original_stops_the_build(self):
        path = Path(self.lab.db_path).parent / "images" / "main" / ("%s.png" % self.b_main)
        data = path.read_bytes()
        path.write_bytes(data + b"x")
        with self.assertRaisesRegex(wine_images.ImageError, "do not agree"):
            wine_images.build(self.db, self.root / "one")
        path.unlink()
        with self.assertRaisesRegex(wine_images.ImageError, "missing"):
            wine_images.build(self.db, self.root / "two")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["lab"])

    def test_a_changed_or_missing_package_cut_is_found(self):
        out, _, _ = self.build()
        other = self.lab.store_file(png_bytes(Image.new("RGBA", (20, 80), (1, 2, 3, 255))),
                                    "cropped", "png")
        self.lab.conn.execute("UPDATE image_derivative SET sha256 = ? WHERE source_sha256 = ?",
                              (other, self.cut_source))
        self.lab.conn.commit()
        errors, _ = wine_images.check_release(self.db, out)
        self.assertEqual(errors, ["wine-cut: the manifest has the image main %s (cut %s); the "
                                  "database has main %s (cut %s)"
                                  % (self.cut_source, self.cut, self.cut_source, other)])
        (Path(self.lab.db_path).parent / "cuts" / ("%s.png" % other)).unlink()
        with self.assertRaisesRegex(wine_images.ImageError, "package cut .* of wine-cut is missing"):
            wine_images.build(self.db, self.root / "again")

    def test_the_trim_cuts_borders_and_keeps_dark_and_light_bottles_whole(self):
        self.assertEqual(wine_images.trim(framed_photo()).size, (90, 140))
        # A white frame around the same photo goes too.
        white = Image.new("RGB", (110, 160), (255, 255, 255))
        white.paste(framed_photo().crop((5, 5, 95, 145)), (10, 10))
        self.assertEqual(wine_images.trim(white).size, (90, 140))
        # A cut with transparency loses its transparent lines alone: the dark bottom of the
        # bottle stays, and the label row does not stop at a black row.
        cut = Image.new("RGBA", (30, 60), (0, 0, 0, 0))
        ImageDraw.Draw(cut).rectangle((13, 0, 16, 19), fill=(5, 5, 5, 255))
        ImageDraw.Draw(cut).rectangle((10, 20, 19, 59), fill=(5, 5, 5, 255))
        ImageDraw.Draw(cut).rectangle((12, 30, 17, 40), fill=(240, 230, 200, 255))
        self.assertEqual(wine_images.trim(cut).size, (10, 60))
        # A black bottle on a white background: the white goes, the black bottom stays.
        photo = Image.new("RGB", (40, 80), (255, 255, 255))
        ImageDraw.Draw(photo).rectangle((14, 5, 25, 20), fill=(0, 0, 0))
        ImageDraw.Draw(photo).rectangle((10, 21, 29, 69), fill=(0, 0, 0))
        self.assertEqual(wine_images.trim(photo).size, (20, 65))
        # The same bottle touching the bottom edge: the mixed bottom side cuts nothing, also
        # after the white sides go, so its black base stays.
        touching = photo.crop((0, 0, 40, 70))
        self.assertEqual(wine_images.trim(touching).size, (20, 65))
        # A frame with two colours keeps the sides that start mixed: white top and bottom
        # go, the black sides stay (a deliberate limit, review of 2026-10-19).
        mixed = Image.new("RGB", (100, 150), (0, 0, 0))
        ImageDraw.Draw(mixed).rectangle((0, 0, 99, 9), fill=(255, 255, 255))
        ImageDraw.Draw(mixed).rectangle((0, 140, 99, 149), fill=(255, 255, 255))
        ImageDraw.Draw(mixed).rectangle((10, 10, 89, 139), fill=(128, 128, 128))
        self.assertEqual(wine_images.trim(mixed).size, (100, 130))
        # A package cut keeps an opaque frame: it is content.
        self.assertEqual(wine_images.trim(framed_photo(), frames=False).size, (100, 150))
        # A white bottle on a black background stays whole too.
        inverse = Image.eval(photo, lambda value: 255 - value)
        self.assertEqual(wine_images.trim(inverse).size, (20, 65))
        # Only border: the whole canvas stays.
        blank = Image.new("RGBA", (30, 60), (255, 255, 255, 255))
        self.assertEqual(wine_images.trim(blank).size, (30, 60))

    def test_the_build_needs_a_new_directory(self):
        (self.root / "release").mkdir()
        with self.assertRaisesRegex(wine_images.ImageError, "exists"):
            wine_images.build(self.db, self.root / "release")

    def test_a_fresh_release_passes_the_check(self):
        out, _, _ = self.build()
        self.assertEqual(wine_images.check_release(self.db, out), ([], []))

    def test_the_check_finds_a_changed_an_extra_and_a_missing_file(self):
        out, _, _ = self.build()
        (out / "400" / "wine-a.webp").write_bytes(b"not webp")
        (out / "400" / "wine-c.webp").write_bytes(b"x")
        (out / "1600" / "wine-big.webp").unlink()
        errors, _ = wine_images.check_release(self.db, out)
        self.assertIn("400/wine-a.webp: the bytes do not agree with the manifest", errors)
        self.assertIn("400/wine-c.webp: a file that the manifest does not name", errors)
        self.assertIn("1600/wine-big.webp: missing", errors)
        self.assertIn("SHA256SUMS does not agree with the files of the release", errors)

    def test_the_check_finds_a_database_change_after_the_build(self):
        out, _, _ = self.build()
        patch = self.lab.image("wine-b", "main_patched", embedding_lab.bottle_on_grey((1, 2, 3)),
                               folder="patched")
        self.lab.wine("wine-new")
        self.lab.conn.execute("UPDATE wine_catalog SET state = 'Disabled' "
                              "WHERE wine_slug = 'wine-twin'")
        self.lab.conn.commit()
        errors, warnings = wine_images.check_release(self.db, out)
        self.assertEqual(warnings, [])
        self.assertIn("wine-new: an Active wine that the manifest does not hold", errors)
        self.assertIn("wine-twin: in the manifest, but not an Active wine of the database",
                      errors)
        self.assertIn("wine-b: the manifest has the image main %s (cut None); the database has "
                      "main_patched %s (cut None)" % (self.b_main, patch), errors)
        # Before a catalogue update, a wine that the new catalogue made non-Active is a
        # warning alone.
        errors, warnings = wine_images.check_release(self.db, out, catalog_update=True)
        self.assertEqual(warnings,
                         ["wine-twin: in the manifest, but not an Active wine of the database"])
        self.assertEqual(len(errors), 2)

    def test_the_manifest_check_rejects_invalid_records(self):
        _, _, manifest = self.build()
        with contextlib.closing(wine_images.connect(self.db)) as conn:
            wines = wine_images.expected(conn)
        self.assertEqual(wine_images.check_manifest(wines, {"format": "x"})[0],
                         ["the manifest is not a svoe-vino-wine-images manifest of version 2"])
        manifest["wines"]["wine-c"]["files"] = {"400": {}}
        manifest["wines"]["wine-a"]["files"]["400"]["width"] = 401
        manifest["wines"]["wine-b"]["files"].pop("1600")
        errors, _ = wine_images.check_manifest(wines, manifest)
        self.assertEqual(errors, [
            "wine-a: the record of the file of size 400 is not valid",
            "wine-b: the manifest record does not have one file of each size",
            "wine-c: a wine with no image has files"])

    def test_the_check_reads_a_matcher_copy_with_no_image_files(self):
        out, _, _ = self.build()
        copy = self.root / "copy" / "catalog.sqlite3"
        copy.parent.mkdir()
        shutil.copyfile(self.db, copy)
        self.assertEqual(wine_images.check_release(copy, out), ([], []))

    def fetch_from(self, out, overrides=None):
        calls = []

        def fetch(url):
            calls.append(url)
            name = url.removeprefix("https://chtozavino.ru/img/wines/")
            if overrides and name in overrides:
                return overrides[name]
            path = out / name
            return (200, path.read_bytes()) if path.is_file() else (404, b"")
        return fetch, calls

    def test_the_url_check_reads_the_manifest_a_sample_and_the_missing_images(self):
        out, _, _ = self.build()
        fetch, calls = self.fetch_from(out)
        result = wine_images.check_url(self.db, "https://chtozavino.ru/img/wines", sample=3,
                                       fetch=fetch, seed=1)
        self.assertEqual(result, ([], []))
        names = [url.rsplit("/img/wines/", 1)[1] for url in calls]
        self.assertEqual(names[0], "manifest.json")
        self.assertEqual(len(names), 1 + 3 + 4)
        self.assertEqual(names[4:], ["1600/wine-c.webp", "400/wine-c.webp",
                                     "1600/wine-d.webp", "400/wine-d.webp"])

    def test_the_url_check_finds_a_wrong_file_and_an_image_of_a_wine_with_no_image(self):
        out, _, _ = self.build()
        fetch, _ = self.fetch_from(out, {"400/wine-big.webp": (200, b"old"),
                                         "1600/wine-c.webp": (200, b"placeholder")})
        errors, _ = wine_images.check_url(self.db, "https://chtozavino.ru/img/wines/",
                                          sample=100, fetch=fetch)
        self.assertEqual(errors, [
            "400/wine-big.webp: the bytes do not agree with the manifest",
            "1600/wine-c.webp: a wine with no image answered HTTP 200; expected 404"])
        fetch, _ = self.fetch_from(out, {"manifest.json": (401, b"")})
        self.assertEqual(wine_images.check_url(self.db, "https://chtozavino.ru/img/wines/",
                                               fetch=fetch),
                         (["https://chtozavino.ru/img/wines/manifest.json answered HTTP 401"],
                          []))

    def test_the_scripts_return_the_exit_codes_of_the_deploy(self):
        out = self.root / "release"
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(build_wine_images.main(["--db", self.db, "--out", str(out)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["images"], 10)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(check_wine_images.main(["--db", self.db, "--release", str(out)]), 0)
        self.assertEqual(json.loads(stdout.getvalue().splitlines()[-1]),
                         {"differences": 0, "ok": True, "warnings": 0})
        (out / "400" / "wine-a.webp").unlink()
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(check_wine_images.main(["--db", self.db, "--release", str(out)]), 1)
        self.assertIn("difference: 400/wine-a.webp: missing", stdout.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(build_wine_images.main(["--db", self.db, "--out", str(out)]), 2)
            self.assertEqual(check_wine_images.main(
                ["--db", str(self.root / "none.sqlite3"), "--release", str(out)]), 2)


if __name__ == "__main__":
    unittest.main()
