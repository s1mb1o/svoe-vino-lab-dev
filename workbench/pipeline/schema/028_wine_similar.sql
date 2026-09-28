-- 028: the manual relation `similar` between two wines (plan 62).
--
-- One row is one pair of two wines that a person marked as similar on the Dataset page.
-- The relation has no direction. The smaller slug is always in `wine_slug_a`, so one pair
-- has one row.
--   created_at  the UTC time of the mark, to the second, in ISO 8601 with `Z`, as
--               `wine_favorite.created_at`.
-- A wine of each state MAY have a pair. The cluster build of `pipeline/clusters.py` uses
-- a pair as one more link, but only when both wines are in the build.
--
-- The foreign keys block `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- Read docs/plans/62_similar-wines.md.

CREATE TABLE wine_similar (
    wine_slug_a TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    wine_slug_b TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at  TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug_a, wine_slug_b),
    CHECK (wine_slug_a < wine_slug_b)
) STRICT;

-- The lookup of the pairs of one wine from the side `b`.
CREATE INDEX wine_similar_b ON wine_similar (wine_slug_b);
