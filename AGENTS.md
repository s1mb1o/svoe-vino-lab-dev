# Context svoe-vino-lab

This file holds the rules of the project `svoe-vino-lab`.
The rules of the workspace are in [../CLAUDE.md](../CLAUDE.md). They apply here too.
`CLAUDE.md` is a symbolic link to this file.

## Messages of the project owner

1. Record each message of the project owner in [docs/owner-messages.md](docs/owner-messages.md).
2. Record the message before you start the work on it.
3. Copy the text verbatim. Do not translate, correct, or shorten it.
4. Add each message at the end of the file. The oldest message stays first.
5. Start each entry with a heading that holds the local date and time in ISO 8601 format,
   for example `## 2026-09-24T21:45:00+0300`.
6. Put the text in a `text` fenced block. If the text holds three backticks, use a fence
   of four backticks.
7. An answer to a question of the agent is a message too. Record the question and the
   selected answer.
8. Do not record a secret. Replace a key, a token, or a password with `<redacted>`.

## Schema changes during development

The owner set these rules on 2026-09-24.

9. The project is in development. A change of the database schema is allowed at any
   time. Do not avoid a feature or a change only because it needs a schema change.
10. Do not ask the owner for a permission only because a change needs a schema change.
11. Until the owner asks for a flatten, put each schema change in a new file
    `pipeline/schema/NNN_<name>.sql` with the next number.
12. At some moment the owner will ask to flatten all schema changes and to create the
    database again from the start. Do the flatten only when the owner asks for it.

## Work of the sessions

The owner set these rules on 2026-09-25. More than one agent session works on this
project at the same time. The file [ACTIVE_WORK.md](ACTIVE_WORK.md) shows the present work
of each session, so that two sessions do not change the same file.

13. Read `ACTIVE_WORK.md` at the start of a task. Read it again before you change a file.
14. Each session has one section in `ACTIVE_WORK.md`. The heading of the section is the
    session name. The first line of the `ListAgents` answer states the name, for example
    `drink-atlas-workspace-20`. A session with no `ListAgents` tool uses a name of its
    own that names the tool, for example `codex-1`.
15. Add your section before you change the first file of a task. The section holds the
    task, its source (a plan or the time of an owner message), the files that you change,
    the state, and the local time of the last update.
16. Put a file in your list before you change it. A glob, for example `pipeline/pages/*`,
    is allowed.
17. Do not change a file that the section of another session lists. Send that session a
    message with `SendMessage`, or ask the owner. Record the agreement in both sections.
18. Change your own section alone. Read the file just before you change it, and make a
    small change, because other sessions write to the same file.
19. Set the state `waiting` when you wait for the owner or for another session. State the
    reason.
20. Remove your section when your work is committed, or when the owner stops the work.
    Record the result in `ChangeLog.md`, not in `ACTIVE_WORK.md`.
21. A section whose session is not in the `ListAgents` answer is stale. Do not remove it.
    Ask the owner.

## The lab server

22. The lab server `pipeline/lab_server.py` of this project listens on port 8168. The
    owner allowed on 2026-09-25 that an agent restarts it when a change needs a restart,
    for example new code of the server or a new schema file.
23. To restart the server, stop the process that listens on port 8168 with SIGTERM. Do
    not use SIGINT: a server that was started in the background ignores SIGINT. Then
    start `python3 pipeline/lab_server.py --no-browser` in the project root, in the
    background, with the log in `work/lab_server.log`. Check that `GET /api/dataset`
    answers HTTP 200. The owner chose SIGTERM on 2026-09-25.
24. Tell the owner about each restart. This permission is for port 8168 alone. Another
    service of the workspace stays a service that the owner restarts.

## Schema numbers between sessions

The owner set these rules on 2026-09-25. They add to rule 11. `pipeline/labdb.py` refuses
a gap in the numbers and applies each schema file one time, by its number. So a number
that two sessions use, or a number that changes after a database applied the file,
breaks the migration of `data/lab.sqlite3`.

25. The number of a new schema file is fixed only when the file enters
    `pipeline/schema/`. Until then, a plan and a section of `ACTIVE_WORK.md` name the
    file `NNN_<name>.sql`.
26. Just before the entry, read `pipeline/schema/` and `ACTIVE_WORK.md`. Send a message
    to each session whose section names schema work. Take the next free number, and
    state it in your section in the same minute.
27. The entry of the file, the migration of `data/lab.sqlite3` with `pipeline/labdb.py`,
    and the restart of the lab server of rules 22 to 24 belong together. A new schema
    file makes the running server answer HTTP 503 until the migration and the restart.
28. Do not renumber, rename, or edit a file that is in `pipeline/schema/`. A change is a
    new file with the next number.
