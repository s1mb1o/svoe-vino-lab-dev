-- 002: the key column of wine_catalog is `wine_slug`.
--
-- `wine_slug` is the name of the same value in `code-map.json` and in
-- `embedding-ignore.json`. SQLite also renames the column in the CHECK constraint.
-- Read docs/plans/07_sqlite-lab-database.md.

ALTER TABLE wine_catalog RENAME COLUMN slug TO wine_slug;
