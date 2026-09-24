# 01 — SQLite for the lab state

Date: 2026-09-24.
Status: accepted by the project owner.
Plan: `docs/plans/07_sqlite-lab-database.md`.

## Context

The lab state is in JSON files: `review-labels.json`, `variant-groups.json`,
`manual-groups.json`, `excluded-slugs.json`, and others. The owner wants more than one
test dataset and a switch between them. A derived dataset such as `vlmrerank-8b-failed`
is a byte copy of photos and labels of `my`: all 179 distinct images of that set are
also in `my`.

## Decision 1 — the store

| Option | For | Against |
|---|---|---|
| JSON files, as now | Git diff of each review. No code change. 1.2 MB of labels is small. | Two writers at the same time: the last write wins. A move changes four files with no transaction. |
| SQLite | Transactions over many tables. Keys and constraints. One store for many datasets. | No git diff of a binary file. Not safe on NFS. Each reader of the JSON files needs a change. |

Decision: SQLite. The owner selected it on 2026-09-24. The tables are in BCNF.

Consequences:

- The database stays on a local disk.
- The history of the data that cannot be rebuilt needs an answer before that data moves
  into the database. See open question 3 of plan 07.

## Decision 2 — the project home

Options: build in `svoe-vino-testset` and rename it later, or build in the new
`svoe-vino-lab`.
Decision: `svoe-vino-lab`. The new code is in `pipeline/`, apart from the stages of
`scripts/`.

## Decision 3 — deliveries per database

| Option | For | Against |
|---|---|---|
| Several deliveries in one database | Old labels keep their reference when a new delivery arrives. | Each catalogue key becomes (release, slug). |
| One delivery per database | The key of `wine_catalog` is `slug` alone. Simple queries. | A new delivery needs a new database, or a migration. |

Decision: one delivery per database.

## Decision 4 — the grape list

| Option | For | Against |
|---|---|---|
| Verbatim text | Equal to the CSV. | A list in one string. A query for one grape needs `LIKE`. Not 1NF. |
| Child table only | 1NF. | The CSV value is not stored. A split rule is needed: `,` and ` и `. |
| Both | Both forms. | The list is stored two times. |

Decision: verbatim text. A child table MAY follow later.

## Decision 5 — outer white space

Options: trim, or keep the bytes. 198 values of the CSV have outer white space.
Decision: trim. `build_catalog.py` uses the same rule, so the database and
`catalog.jsonl` agree. The CSV in `official-2026-09-17/` keeps the exact bytes.
