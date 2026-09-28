# Split Matcher and Workbench

Date: 2026-09-28

Status: Complete

## Goal

Keep `matcher/` at the repository root.

Move every other visible root path into `workbench/`.

Keep Git metadata and hidden repository configuration at the repository root.

## Changes

1. Stop the lab server on port 8168 before the move.
2. Move all visible root paths except `matcher/` into `workbench/`.
3. Update root ignore rules and CI paths.
4. Update configuration paths that are relative to the workspace root.
5. Update matcher documentation that points to the workbench configuration.
6. Restart the lab server from `workbench/`.

## Verification

1. Confirm that the root contains `matcher/`, `workbench/`, and hidden repository files.
2. Confirm that generated data and run artifacts stay ignored.
3. Run the focused workbench tests.
4. Run the matcher test suite.
5. Confirm that `GET /api/dataset` returns HTTP 200.
6. Check the staged diff before the commit.

This change does not change the database schema.

## Result

The repository root contains `matcher/`, `workbench/`, and hidden repository files.

All generated data and run artifacts stay ignored at their new paths.

The path-sensitive workbench checks pass with 239 tests.

The matcher suite passes with 37 tests.

The lab server runs from `workbench/` on port 8168. `GET /api/dataset` returns HTTP 200.
