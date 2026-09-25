# 11 — GTIN, barcode, and QR URL in the database

Date: 2026-09-25.
Status: specification. The owner approves it before the implementation starts.
The owner message of 2026-09-25T00:52:48+0300 and the answers of 2026-09-25T00:58:25+0300
are in [owner-messages.md](../owner-messages.md).

## Goal

1. The database holds the GTINs, the barcodes, and the QR URLs of each wine.
2. One wine MAY have more than one value of each kind.
3. One value MAY belong to more than one wine.
4. The Dataset page reads and writes these values in the database.

## Terms

| Term | Meaning |
|---|---|
| GTIN | A GS1 product number: 8, 12, 13, or 14 digits with a valid GS1 check digit. The source is an EAN-8, EAN-13, or UPC-A code, or the `(01)` field of a DataMatrix code. |
| barcode | The text of a linear code that is not a GTIN, for example an internal Code 128 code. |
| QR URL | An `http` or `https` URL that a QR code holds. |
| code | One row of `wine_code`: a wine, a kind, and a value. |

The owner chose these meanings on 2026-09-25.

## Present state

- `svoe-vino-matcher/dataset/code-map.json` has 22 records and 23 `barcode` values.
  Each value is 13 digits with a valid GTIN-13 check digit. Three records have a
  `qr_code` value. One `qr_code` value starts with `URL:`.
- Each of the 22 slugs is in `wine_catalog` of `data/lab.sqlite3`, in the state `Active`.
  The check was made on 2026-09-25.
- The Dataset page has the editors `Barcodes` and `QR URLs`. The page calls
  `POST /api/dataset-barcode`, `DELETE /api/dataset-barcode`, `POST /api/dataset-qr-url`,
  and `DELETE /api/dataset-qr-url`. `pipeline/lab_server.py` answers HTTP 503 for each
  of these routes. Plan 07, rule 5, states this.
- The page enables the `+` button only when `DATA.barcode_file` is not empty. The lab
  server sends an empty `barcode_file`.

## Schema 008

File: `pipeline/schema/008_wine_code.sql`.

```sql
CREATE TABLE wine_code (
    wine_slug TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    kind      TEXT NOT NULL CHECK (kind IN ('gtin', 'barcode', 'qr_url')),
    value     TEXT NOT NULL CHECK (value <> ''),
    PRIMARY KEY (wine_slug, kind, value),
    CHECK (kind <> 'gtin'
           OR (length(value) IN (8, 12, 13, 14) AND value NOT GLOB '*[^0-9]*')),
    CHECK (kind <> 'barcode' OR length(value) <= 128),
    CHECK (kind <> 'qr_url'
           OR (length(value) <= 4096
               AND (value GLOB 'http://?*' OR value GLOB 'https://?*')))
) STRICT;

-- The lookup of the wines that have one value.
CREATE INDEX wine_code_value ON wine_code (kind, value);
```

Rules:

1. The primary key allows one value for more than one wine. It refuses the same value
   twice for the same wine.
2. The `rowid` order is the order of the writes. The page shows the values of a wine in
   this order.
3. SQL checks the form alone. Python checks the rest: the GS1 check digit, the white
   space, the control characters, and the URL form. Section "Values" states the checks.
4. The foreign key blocks `DROP TABLE wine_catalog` while `wine_code` holds rows. A later
   schema file that builds `wine_catalog` again MUST handle this table too. Schema 005
   has the same rule for `wine_image`.

## Values

The module `pipeline/codes.py` holds the checks. The seed and the server use the same
module.

| Kind | Normal form | Refused |
|---|---|---|
| `gtin` | The digits alone. White space is removed. See open question O1. | A character that is not a digit. A length that is not 8, 12, 13, or 14. A wrong check digit. |
| `barcode` | White space is removed. | An empty value. More than 128 characters. A control character. A value that is a valid GTIN: the server answers that the value is a GTIN. |
| `qr_url` | The rule of the old editor and of the matcher: remove a `URL:` prefix; lower-case the scheme and the host; convert the host to IDNA; remove a default port; use `/` for an empty path; remove the fragment. | An empty value. More than 4096 characters. White space or a control character. A scheme that is not `http` or `https`. No host. User information in the URL. |

## Seed

File: `pipeline/seed_codes.py`.

```bash
python3 pipeline/seed_codes.py --db data/lab.sqlite3 \
    ../svoe-vino-matcher/dataset/code-map.json
```

Rules:

1. The seed reads the list `wines`. Each record gives `wine_slug`, `barcode`, and
   `qr_code`. `barcode` and `qr_code` are a string, a list, or `null`.
2. A `barcode` value that is a valid GTIN goes to the kind `gtin`. Another `barcode`
   value goes to the kind `barcode`. The 23 present values go to `gtin`.
3. A `qr_code` value goes to the kind `qr_url` in its normal form.
4. The seed checks every value before the first write. A bad value stops the seed. The
   seed then writes nothing and prints the record number and the value.
5. A slug that is not in `wine_catalog` prints `no wine: <slug>`. The seed skips its
   values.
6. The seed adds the missing rows in one transaction. It never removes a row, and it
   never changes a row.
7. The report prints the count of added rows for each kind. A run that adds no row
   prints `result: no change`.
8. The seed does not copy the field `source_note`. One record has it. The field stays in
   `code-map.json`.

## Lab server

File: `pipeline/lab_server.py`.

1. `GET /api/dataset` gives each record the lists `_gtins`, `_barcodes`, and `_qr_urls`.
   The answer gives the row counts `gtins`, `barcodes`, and `qr_urls`.
2. The routes:

   | Route | Body or query | Answer |
   |---|---|---|
   | `POST /api/dataset-gtin` | `{"slug": …, "gtin": …}` | `{ok, slug, gtin, gtins, total}` |
   | `DELETE /api/dataset-gtin` | `?slug=…&gtin=…` | `{ok, slug, removed, gtins, total}` |
   | `POST /api/dataset-barcode` | `{"slug": …, "barcode": …}` | `{ok, slug, barcode, barcodes, total}` |
   | `DELETE /api/dataset-barcode` | `?slug=…&barcode=…` | `{ok, slug, removed, barcodes, total}` |
   | `POST /api/dataset-qr-url` | `{"slug": …, "url": …}` | `{ok, slug, url, qr_urls, total}` |
   | `DELETE /api/dataset-qr-url` | `?slug=…&url=…` | `{ok, slug, removed, qr_urls, total}` |

   The barcode and QR URL routes keep the body and the answer of the old editors.
   `total` is the count of rows of the kind in the database.
3. Status codes: a bad body or a bad value answers 400. An unknown slug answers 404. A
   value that the wine already has answers 409. A DELETE of a value that the wine does
   not have answers 404.
4. A write opens the database read-write and changes one row of `wine_code` alone.
5. A write is allowed for a wine in each state.

## Dataset page

File: `pipeline/pages/dataset.html`.

1. A new editor `GTINs` stands above the editor `Barcodes`. It has the same form: the
   values, a `+` button, an input field, the checkmark icon, and the cross icon.
2. The `+` buttons of the three editors do not depend on `DATA.barcode_file` any more.
   The database is always present when the page has data.
3. The head line shows the count of GTINs next to the counts of barcodes and QR URLs.
4. The text search of the page also searches the GTINs.

## Tests

1. `tests/test_seed_codes.py`: the GTIN and barcode split, the QR URL normal form, a bad
   value that stops the seed with no write, a slug with no wine, and a second run with
   `result: no change`.
2. `tests/test_lab_server.py`: each route, each status code, a value that two wines
   share, and the lists in `/api/dataset`.
3. `tests/test_labdb.py`: the version becomes 8.

## Documents

`COMMANDS.md` (the seed command), `README.md`, `docs/API.md`, `docs/openapi.yaml`,
plan 07 rule 5, `SMOKE_TESTS.md`, and `ChangeLog.md`.

## Order of the work and its effects

1. `pipeline/lab_server.py` compares the schema version with the count of schema files
   on each request. When the file `008_wine_code.sql` is in `pipeline/schema/`, a
   running server answers HTTP 503 until `data/lab.sqlite3` has version 8.
2. `tests/test_labdb.py` asserts version 7. The file `008_wine_code.sql` makes this test
   fail until the test says 8.
3. drink-atlas-workspace-8b lists `pipeline/lab_server.py`, `pipeline/pages/dataset.html`,
   `tests/test_lab_server.py`, `tests/test_labdb.py`, and `data/lab.sqlite3`. Its work
   is not committed. drink-atlas-workspace-9a lists `pipeline/lab_server.py` for its
   work after the commit of plan 09.
4. Because of items 1 to 3, the implementation starts after the commit of plan 09, or
   after an agreement with drink-atlas-workspace-8b.
5. The deploy: the owner stops the lab server. `labdb.py` and `seed_codes.py` run on
   `data/lab.sqlite3`. The owner starts the lab server.

## Consequences

1. `svoe-vino-matcher` still reads `code-map.json`. It does not see the codes that a
   person adds on the Dataset page. The owner did not select an export on 2026-09-25.
2. After the seed, the database is the source of the codes of the lab. `code-map.json`
   is not changed.

## Open questions

### O1. The stored form of a GTIN

A DataMatrix `(01)` field gives 14 digits, for example `04630037251630`. The EAN-13 code
of the same product gives 13 digits: `4630037251630`. Both are the same GTIN.

| # | Option | Effect |
|---|---|---|
| 1 | Store the GTIN-14 form: add leading zeros up to 14 digits. | The same GTIN has one form. The page shows 14 digits, for example `04631168664979` for the printed `4631168664979`. |
| 2 | Store the digits as read. | The page shows the printed number. The same GTIN MAY have two rows for one wine: one of 13 digits and one of 14 digits. A lookup MUST add the zeros to both sides. |

Recommendation: option 1. GS1 practice stores each GTIN as 14 digits. The page MAY show
the value without the leading zeros later.
