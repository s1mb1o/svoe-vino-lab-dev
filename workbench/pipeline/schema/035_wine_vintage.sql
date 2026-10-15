-- Same wine across vintages. One undirected link has one row.
-- A wine without a year MAY link to more than one year-specific entry.

CREATE TABLE wine_vintage (
    wine_slug_a TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    wine_slug_b TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at  TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug_a, wine_slug_b),
    CHECK (wine_slug_a < wine_slug_b)
) STRICT;

-- The lookup of the pairs of one wine from the side `b`.
CREATE INDEX wine_vintage_b ON wine_vintage (wine_slug_b);
