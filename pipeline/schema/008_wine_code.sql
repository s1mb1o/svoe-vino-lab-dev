-- 008: the GTINs, the barcodes, and the QR URLs of a wine.
--
-- One row links one wine, one kind, and one value. One wine MAY have more than one value
-- of each kind. One value MAY belong to more than one wine. The owner chose one table
-- and shared values on 2026-09-25.
--   gtin     a GS1 product number in its GTIN-14 form: 14 digits, with leading zeros.
--            The source is an EAN-8, EAN-13, or UPC-A code, or the (01) field of a
--            DataMatrix code.
--   barcode  the text of a linear code that is not a GTIN, for example an internal
--            Code 128 code.
--   qr_url   an http or https URL that a QR code holds, in the normal form of
--            pipeline/codes.py.
-- The `rowid` order is the order of the writes.
--
-- SQL checks the form alone. pipeline/codes.py checks the rest: the GS1 check digit,
-- the white space, the control characters, and the URL form.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- pipeline/seed_codes.py fills the table from code-map.json. Read
-- docs/plans/11_wine-codes.md.

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
