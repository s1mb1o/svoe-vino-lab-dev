# Manual accepted answers

Workbench evaluation accepts the positive wine assignments for one exact image.
The image SHA-256 identifies the exact image.
The accepted assignments MUST belong to the same testset.

To accept two wine slugs for a photo:

1. Assign the exact image to both wine slugs in the testset.
2. Set the label of both assignments to `positive`.
3. Start a new evaluation run.

A copied image with no label does not add an accepted answer.
An assignment with `negative`, `variant`, or `unusable` does not add an accepted answer.
A deleted assignment does not add an accepted answer.
A `Disabled`, `Removed`, or missing catalogue wine does not add an accepted answer.
`No Match` and `Drawer` do not add accepted wine slugs.
An assignment in another testset does not add an accepted answer.

`pipeline/benchmark.py` collects the eligible positive assignments by image SHA-256.
The query `truth` contains the sorted list of accepted wine slugs.
`scripts/match_scoring.py` accepts any wine slug in that list.
The query and result files preserve that list.

Each existing assignment remains a separate query.
The query count and order remain the same.
Metrics count each assignment separately.
Different image bytes do not share accepted answers.
The same file name does not prove that two images are the same image.

The rule does not select a vintage or change matcher ranking.
The rule applies to new Workbench runs.
Historical runs retain their saved truth and verdicts.
`Repeat last failed` does not copy an earlier verdict if its truth differs.
The legacy file runner `scripts/match_run.py` retains its existing rules.

The tests use temporary databases and a fake backend.
The job tests use a temporary HTTP server on localhost.
The tests do not call a model service.
Read the test commands in [COMMANDS.md](../../COMMANDS.md).
