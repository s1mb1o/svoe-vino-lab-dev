# Fix later

This file lists known problems that wait until after the hackathon.
`HACKATHON_TODO.md` lists the work before the submission.
`ChangeLog.md` records the work that is done.
Rules 39 to 42 of [AGENTS.md](AGENTS.md) apply to each problem of this file. Do not report
such a problem as a new problem. Do not fix it until the owner asks for the fix.

Rules:

1. Add one section for each problem. Add a new section at the end of the file.
2. Each section states the problem, the risk until the fix, the planned fix, the
   evidence, and the source.
3. Do not renumber a section.
4. When the fix is done, remove the section. Record the fix in `ChangeLog.md`.

## 1. A shared cache for the prepared PNG files of the embeddings

- Added: 2026-09-29.
- Source: owner messages of 2026-09-29T07:44:57+0300, 07:50:13, and 07:54:44.
- Plan: stage 3 of [plan 75](docs/plans/75_data-layout.md).
- Evidence: the `ResearchLog.md` entry "Storage of `data/catalog/embeddings/` and use of
  the prepared images" of 2026-09-29.

Problem:

- Each gx10 and local index keeps its own copy of the prepared PNG files in
  `data/catalog/embeddings/<name>/images/`.
- The 12 indexes hold the same files. The 12 copies use 17.8 GB. One copy uses about
  1.5 GB.
- The prepared PNG files are cache data, not catalogue data. The build makes them from
  `catalog/images/`, `catalog/cuts/`, and the steps in `index.json`. The matcher does not
  read them.

Risk until the fix:

- `embeddings.item_status` gives the state `current` only when the PNG file exists.
- Do not delete a directory `images/`. If it is deleted, the lab has no catalogue vector
  for that index. The next build then sends each item of the index to the model again.

Planned fix:

1. Make a shared store `data/cache/prepared/` with one file for each distinct PNG. The key
   of a file MUST NOT include the model.
2. Make the status of an item independent of its PNG file.
3. Make the Embeddings page, the cluster pages, the step popup of `/runs`, and the
   rotation scripts read the shared store.
4. Keep one copy of each file in the shared store. Then remove the 12 directories
   `images/`.

Special case: the index `android-siglip2-base-224-dis-white` runs the DIS model in the
step `segment_dis`. No other file stores the DIS result. The migration MUST keep these
PNG files, or the owner MUST accept a new DIS run. The last full build of this index took
3,833 s for 2,271 items. That time includes DIS and the embedding.

Optional step before the fix: replace the duplicate files with APFS clones. This step
needs no code change. Do it only when no build runs. A later build writes full copies
again.
