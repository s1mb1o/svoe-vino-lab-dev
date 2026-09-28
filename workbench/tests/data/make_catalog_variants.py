"""Write the fake variants of the official catalogue CSV into this directory.

The variants test `pipeline/import_catalog.py` on the full catalogue. Each variant is
the official file with a few wines removed, a few fake wines added, or one field
changed. Read `README.md` of this directory for the expected import results.

Usage:
    python3 tests/data/make_catalog_variants.py

The script reads the official file and never writes to it. A row that the script does
not change keeps its exact bytes, so `diff` against the official file shows only the
changes.
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SOURCE = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "svoe-wino-hackaton", "dataset",
                      "official-2026-09-17", "strapi_output0709.csv")
PREFIX = "strapi_output0709"

# v2 removes three wines: two with two identical rows, and one with a single row.
REMOVED_V2 = [
    "ivan-ksenia-kruz-argonne-syrah-sira-krasnoe-suhoe-124",
    "vinodelnya-myshako-quintessence-blaufrankish-rozovoe-bryut-115",
    "silvaner-pet-nat-2022",
]
# v3 brings back the first wine of v2 and removes two more wines.
RESTORED_V3 = REMOVED_V2[:1]
REMOVED_V3 = [
    "donskoe-vinodelcheskoe-hozyaystvo-elbuzd-merlo-krasnoe-suhoe-13",
    "novyy-svet-dom-shampanskih-vin-rossiyskoe-shampanskoe-kollektsionnoe-ekstra-bryut-beloe-novyy-svet-shardone-125",
]
# v4 is v3 with one changed field of one wine, in each of its rows.
CHANGED_V4 = ("shato-pino-shary-kolduna-glyu-glyu-vione-krasnoe-suhoe-10", "Регион", "Крым")
# The template of a fake wine. A fake wine copies the other fields of this row.
TEMPLATE = "vinodelnya-vedernikov-gubernatorskiy-rezerv-beloe-risling-suhoe-12"
# fake slug -> number of identical rows. The official file holds most wines twice.
FAKES_V2 = {"fake-added-wine-1": 1, "fake-added-wine-2": 2}
FAKES_V3 = {**FAKES_V2, "fake-added-wine-3": 2}


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def to_text(header, rows):
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\n").writerows([header] + rows)
    return out.getvalue()


def fake_rows(header, rows, fakes):
    """Return the rows of the fake wines. Each one copies the template row."""
    slug = header.index("Slug")
    template = next(row for row in rows if row[slug] == TEMPLATE)
    out = []
    for number, (fake, copies) in enumerate(fakes.items(), 1):
        row = list(template)
        row[slug] = fake
        row[header.index("Название вина")] = "FAKE тестовое вино %d" % number
        row[header.index("Винодельня")] = "FAKE тестовая винодельня"
        row[header.index("Описание")] = ("FAKE: a test variant of the catalogue adds "
                                         "this wine. It is not a real wine.")
        row[header.index("Название фото")] = fake + ".webp"
        out.extend([row] * copies)
    return out


def without(header, rows, slugs):
    slug = header.index("Slug")
    missing = set(slugs) - {row[slug] for row in rows}
    if missing:
        sys.exit("error: the source holds no slug %s" % ", ".join(sorted(missing)))
    return [row for row in rows if row[slug] not in set(slugs)]


def changed(header, rows, change):
    wine, column, value = change
    slug, index = header.index("Slug"), header.index(column)
    out, hits = [], 0
    for row in rows:
        if row[slug] == wine:
            if row[index] == value:
                sys.exit("error: %s of %s is already %r" % (column, wine, value))
            row = list(row)
            row[index] = value
            hits += 1
        out.append(row)
    if not hits:
        sys.exit("error: the source holds no slug %s" % wine)
    return out


def main():
    with open(SOURCE, encoding="utf-8", newline="") as fh:
        original = fh.read()
    header, rows = read_rows(SOURCE)
    if to_text(header, rows) != original:
        sys.exit("error: the CSV writer does not reproduce %s byte for byte" % SOURCE)

    v2 = without(header, rows, REMOVED_V2) + fake_rows(header, rows, FAKES_V2)
    gone_v3 = [s for s in REMOVED_V2 if s not in RESTORED_V3] + REMOVED_V3
    v3 = without(header, rows, gone_v3) + fake_rows(header, rows, FAKES_V3)
    v4 = changed(header, v3, CHANGED_V4)

    for name, variant in (("v2-add-remove", v2), ("v3-add-remove", v3),
                          ("v4-changed-field", v4)):
        path = os.path.join(HERE, "%s.%s.csv" % (PREFIX, name))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(to_text(header, variant))
        print("%s: %d rows" % (os.path.relpath(path, ROOT), len(variant)))


if __name__ == "__main__":
    main()
