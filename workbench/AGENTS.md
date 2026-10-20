# Context svoe-vino-lab

This file holds the rules of the project `svoe-vino-lab`.
The rules of the workspace are in [../../CLAUDE.md](../../CLAUDE.md). They apply here too.
`CLAUDE.md` is a symbolic link to this file.

## Schema changes during development

The owner set these rules on 2026-09-24.

9. The project is in development. A change of the database schema is allowed at any
   time. Do not avoid a feature or a change only because it needs a schema change.
10. Do not ask the owner for a permission only because a change needs a schema change.
11. Until the owner asks for a flatten, put each schema change in a new file
    `pipeline/schema/NNN_<name>.sql` with the next number.
12. At some moment the owner will ask to flatten all schema changes and to create the
    database again from the start. Do the flatten only when the owner asks for it.

## The lab server

22. The lab server `pipeline/lab_server.py` of this project listens on port 8168. The
    owner allowed on 2026-09-25 that an agent restarts it when a change needs a restart,
    for example new code of the server or a new schema file.
23. To restart the server, stop the process that listens on port 8168 with SIGTERM. Do
    not use SIGINT: a server that was started in the background ignores SIGINT. Then
    start `python3 pipeline/lab_server.py --no-browser` in the workbench root, in the
    background, with the log in `work/lab_server.log`. Check that `GET /api/dataset`
    answers HTTP 200. The owner chose SIGTERM on 2026-09-25.
24. Tell the owner about each restart. This permission is for port 8168 alone. Another
    service of the workspace stays a service that the owner restarts.

## Schema numbers between sessions

The owner set these rules on 2026-09-25. They add to rule 11. `pipeline/labdb.py` refuses
a gap in the numbers and applies each schema file one time, by its number. So a number
that two sessions use, or a number that changes after a database applied the file,
breaks the migration of `data/catalog/catalog.sqlite3`.

25. The number of a new schema file is fixed only when the file enters
    `pipeline/schema/`. Until then, a plan names the file `NNN_<name>.sql`.
26. Just before the entry, read `pipeline/schema/`. Take the next free number.
27. The entry of the file, the migration of `data/catalog/catalog.sqlite3` with
    `pipeline/labdb.py`, and the restart of the lab server of rules 22 to 24 belong
    together. A new schema file makes the running server answer HTTP 503 until the
    migration and the restart.
28. Do not renumber, rename, or edit a file that is in `pipeline/schema/`. A change is a
    new file with the next number.

## Developer commands

The owner set these rules on 2026-09-28.

29. Store common developer and component-test commands in [COMMANDS.md](COMMANDS.md) at
    the workbench root. Do not put the command catalogue in `README.md`.
30. Group the commands by component and purpose.
31. Make each command executable from the workbench root.
32. State required environment variables and prerequisites immediately before the
    command.
33. Separate read-only tests from commands that change data or call an external service.
34. Use `docs/testing.md` or `docs/testing/<component>.md` for test concepts,
    prerequisites, and troubleshooting that need detailed text.
35. Prefer an executable target in `Makefile`, `justfile`, or `Taskfile.yml` when a
    stable command is shared with CI or is used frequently.
36. Put multi-step shell logic in `scripts/test_<component>.sh`. Keep `COMMANDS.md` as
    the entry point for the script.
37. Record historical test results in `ChangeLog.md`. Do not record them in
    `COMMANDS.md`.
38. If `COMMANDS.md` becomes too large, keep the common commands there and move the
    detailed component instructions to `docs/testing/<component>.md`.

## Known problems

The owner set these rules on 2026-09-29. The owner knows the problems in these files. A
fix of such a problem before the hackathon submission can need a refactor at the last
moment. The owner does not want this risk.

39. These files list the known problems: [FIX_LATER.md](FIX_LATER.md) and each file with
    the name `KNOWN_ISSUES.md` in the project `svoe-vino-lab`, for example
    [../matcher/docs/KNOWN_ISSUES.md](../matcher/docs/KNOWN_ISSUES.md).
40. A problem that one of these files lists is a known problem. Do not report a known
    problem as a new problem in a review, an audit, a test report, or an answer. A report
    MAY name the entry, for example "known: `FIX_LATER.md`, item 1".
41. Fix a known problem only when the owner asks for the fix. Do not start a refactor
    because of a known problem.
42. An effect that the entry does not state is not known. Report this effect as a new
    problem.
