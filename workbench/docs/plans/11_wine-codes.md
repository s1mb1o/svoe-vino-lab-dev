# 11 — GTIN, barcode, and QR URL in the database

Date: 2026-09-25.
Status: approved by the owner on 2026-09-25T07:19:46+0300. Implemented and deployed on
2026-09-25 as schema file `008_wine_code.sql`.
The owner message of 2026-09-25T00:52:48+0300, the answers of 2026-09-25T00:58:25+0300,
and the approval are in [owner-messages.md](../owner-messages.md).
Changed on 2026-09-25: the lab keeps GTINs alone. Read decision O2. The text about the
kind `barcode` below describes the first version.

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

## Schema file

File: `pipeline/schema/NNN_wine_code.sql`. Rules 25 to 28 of `AGENTS.md` apply. `NNN`
is fixed only when the file enters `pipeline/schema/`. Until then the file is
`pipeline/schema_pending/NNN_wine_code.sql`, as the file of plan 12 is.

```sql
CREATE TABLE wine_code (
    wine_slug TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    kind      TEXT NOT NULL CHECK (kind IN ('gtin', 'barcode', 'qr_url')),
    value     TEXT NOT NULL CHECK (value <> ''),
    PRIMARY KEY (wine_slug, kind, value),
    CHECK (kind <> 'gtin'
           OR (length(value) = 14 AND value NOT GLOB '*[^0-9]*')),
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
3. A GTIN is stored in its GTIN-14 form: 14 digits, with leading zeros. The owner chose
   this form on 2026-09-25.
4. SQL checks the form alone. Python checks the rest: the GS1 check digit, the white
   space, the control characters, and the URL form. Section "Values" states the checks.
5. The foreign key blocks `DROP TABLE wine_catalog` while `wine_code` holds rows. A later
   schema file that builds `wine_catalog` again MUST handle this table too. Schema 005
   has the same rule for `wine_image`.

## Values

The module `pipeline/codes.py` holds the checks. The seed and the server use the same
module.

| Kind | Normal form | Refused |
|---|---|---|
| `gtin` | White space is removed. Leading zeros make 14 digits. | A character that is not a digit. A length that is not 8, 12, 13, or 14. A wrong check digit. |
| `barcode` | White space is removed. | An empty value. More than 128 characters. A control character. A value of 8, 12, 13, or 14 digits: it is a GTIN, or a GTIN with a wrong check digit. |
| `qr_url` | The rule of the old editor and of the matcher: remove a `URL:` prefix; lower-case the scheme and the host; convert the host to IDNA; remove a default port; use `/` for an empty path; remove the fragment. | An empty value. More than 4096 characters. White space or a control character. A scheme that is not `http` or `https`. No host. User information in the URL. |

Rules of the check digit. The owner asked on 2026-09-25 to check the checksum of each
input.

1. The GS1 check digit is the last digit. Multiply the other digits by 3 and 1 in turn,
   from the right: the digit next to the check digit gets 3. The check digit is
   `(10 - sum mod 10) mod 10`. Leading zeros do not change the sum, so the check is the
   same for the value as read and for its GTIN-14 form.
2. Each input is checked: a value of the seed, a value of a POST, and a value that a
   person types on the Dataset page.
3. The error of a wrong check digit names the digit that the value has and the digit
   that the other digits give, for example `wrong check digit 5; expected 9`.
4. The Dataset page checks while the person types. A wrong check digit shows the error
   below the input and disables the checkmark icon. The server checks again.

## Seed

File: `pipeline/seed_codes.py`.

```bash
python3 pipeline/seed_codes.py --db data/lab.sqlite3 \
    ../../svoe-vino-matcher/dataset/code-map.json
```

Rules:

1. The seed reads the list `wines`. Each record gives `wine_slug`, `barcode`, and
   `qr_code`. `barcode` and `qr_code` are a string, a list, or `null`.
2. A `barcode` value of 8, 12, 13, or 14 digits goes to the kind `gtin` in its GTIN-14
   form. A wrong check digit of such a value stops the seed. Another `barcode` value
   goes to the kind `barcode`. The 23 present values go to `gtin`.
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
9. The seed refuses a table `wine_code` that already holds rows, unless `--force` is
   given. Read decision O3.

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
6. A DELETE names the value in its stored form, as `/api/dataset` sends it. A GTIN of
   13 digits in a DELETE answers 404.

## Dataset page

File: `pipeline/pages/dataset.html`.

1. A new editor `GTINs` stands above the editor `Barcodes`. It has the same form: the
   values, a `+` button, an input field, the checkmark icon, and the cross icon. The
   editor shows the stored GTIN-14 form.
2. The `+` buttons of the three editors do not depend on `DATA.barcode_file` any more.
   The database is always present when the page has data.
3. The head line shows the count of GTINs next to the counts of barcodes and QR URLs.
4. The text search of the page also searches the GTINs.
5. The GTIN input and the barcode input check the check digit while the person types.
   Section "Values" states the rules.

## Tests

1. `tests/test_codes.py`: the check digit, the GTIN-14 form, the barcode rules, and the
   QR URL normal form. These tests need no database.
2. `tests/test_seed_codes.py`: the GTIN and barcode split, the QR URL normal form, a bad
   value that stops the seed with no write, a slug with no wine, and a second run with
   `result: no change`.
3. `tests/test_lab_server.py`: each route, each status code, a value that two wines
   share, and the lists in `/api/dataset`.
4. `tests/test_labdb.py`: the version becomes `NNN`.

## Documents

`COMMANDS.md` (the seed command), `README.md` (step 6), plan 07 rule 5, `SMOKE_TESTS.md`
(section WC), and `ChangeLog.md`. `docs/API.md` and `docs/openapi.yaml` describe the old
review tool of `scripts/review_server.py`, not the lab server, so they do not change.
This plan and the README describe the routes of the lab server.

## Order of the work and its effects

1. `pipeline/lab_server.py` compares the schema version with the count of schema files
   on each request. When the file `NNN_wine_code.sql` is in `pipeline/schema/`, a
   running server answers HTTP 503 until `data/lab.sqlite3` has version `NNN`.
2. `tests/test_labdb.py` asserts the present version. The file `NNN_wine_code.sql` makes
   this test fail until the test says `NNN`.
3. Plan 09 is committed in `a8e113a`. drink-atlas-workspace-8b released
   `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, `tests/test_lab_server.py`,
   `tests/test_labdb.py`, and `data/lab.sqlite3` on 2026-09-25.
4. By the owner message of 2026-09-25T06:52:00+0300, drink-atlas-workspace-7e changes
   `pipeline/lab_server.py`, the navigation of `pipeline/pages/dataset.html`, and
   `tests/test_lab_server.py` first. The changes of these files for this plan start
   after the commit of 7e.
5. `pipeline/codes.py`, `pipeline/seed_codes.py`, and `tests/test_seed_codes.py` MAY
   start after the approval of this plan. No other session lists them. The tests of the
   seed need the table `wine_code`, so they pass only after the deploy of step 6.
6. The deploy follows rules 22 to 27 of `AGENTS.md`, in one step:
   1. Read `pipeline/schema/` and `ACTIVE_WORK.md`. Send a message to each session
      whose section names schema work. Take the next free number.
   2. Stop the lab server on port 8168 with SIGTERM. Rule 23 names SIGTERM since
      2026-09-25: a server that was started in the background ignores SIGINT.
   3. Put `NNN_wine_code.sql` in `pipeline/schema/`. Run `labdb.py` and `seed_codes.py`
      on `data/lab.sqlite3`.
   4. Start the lab server again. Check that `GET /api/dataset` answers HTTP 200.
   5. Tell the owner about the restart.

## Consequences

1. `svoe-vino-matcher` still reads `code-map.json`. It does not see the codes that a
   person adds on the Dataset page. The owner did not select an export on 2026-09-25.
2. After the seed, the database is the source of the codes of the lab. `code-map.json`
   is not changed.

## Decisions

### O1. The stored form of a GTIN

Answered by the owner on 2026-09-25T07:19:46+0300: store each GTIN padded to 14 digits.

A DataMatrix `(01)` field gives 14 digits, for example `04630037251630`. The EAN-13 code
of the same product gives 13 digits: `4630037251630`. Both are the same GTIN. The
GTIN-14 form gives the same GTIN one row. The page shows 14 digits, for example
`04631168664979` for the printed `4631168664979`.

### O2. GTINs alone, no kind `barcode`

Answered by the owner on 2026-09-25T10:13:54+0300 ("no, keep only GTIN") and in the
answers of 2026-09-25T10:16:07+0300.

1. The lab has no kind `barcode`. `pipeline/codes.py` has the kinds `gtin` and `qr_url`
   alone. `clean_barcode` and `classify_barcode` are removed.
2. No new schema file. Schema 008 still allows `barcode` in its CHECK until the flatten.
   The code never writes it. The one `barcode` row of `data/lab.sqlite3`
   (`golubitskoe-estate-chardonnay`, `343343234233123`) was deleted on 2026-09-25.
3. The lab server has no route `/api/dataset-barcode`. The route answers HTTP 503 as
   each other API route that the lab server does not serve. `GET /api/dataset` sends
   no key `barcodes` and no record key `_barcodes`.
4. The seed stores each `barcode` value of the code map as a GTIN. A value that is not a
   GTIN stops the seed with no write.
5. The Dataset page shows the editor `Barcodes` only when the answer of `/api/dataset`
   holds `barcode_file`, so on the review tool alone. `scripts/review_server.py` is not
   changed. The first version of this change still refused an EAN-13 in the Barcodes
   editor of the review tool and showed the GTIN editor there. The fix of 2026-09-25
   (review `docs/reviews/2026-09-25_unfinished-work.md`, a2 finding 1): the page checks
   a barcode only for an empty value; the GTIN editor and its count show only when the
   answer holds `gtins`; the `+` of `Barcodes` and of `QR URLs` needs a non-empty
   `barcode_file` when the answer holds no `gtins`, as before plan 11.
6. In the same change, each editor of a code redraws its own card with `renderCard`, not
   all 2,103 cards with `render`. A save took about 0.5 s in headless Chromium and a
   couple of seconds in the browser of the owner. It now takes about 60 ms.

### O3. A second run of the seed

Answered by the owner on 2026-09-25T12:28:04+0300 ("Refuse unless --force").

1. A second run of `seed_codes.py` added back each value that a person removed on the
   page, because the seed adds every file row that is not in the table.
2. The seed now refuses a table `wine_code` that already holds rows. The error names the
   count of rows and the option `--force`. With `--force`, the seed adds the missing rows
   as before.
3. `seed_atlas_bindings.py` (plan 15) and `seed_patched.py` use the same rule.
