# Messages of the project owner

The agents of this project record each message of the project owner in this file.
The rules are in [CLAUDE.md](../CLAUDE.md), section "Messages of the project owner".
The oldest message is first. The log starts on 2026-09-24.

## 2026-09-24T21:42:47+0300

```text
I removed from config.yaml all references to json files. Now sqlite is single oracle. 

temporary disable Clusters, Embeddings, Testset and Runs pages. Let's have only "Dataset" page working. Ensure that server capable to start and display contents of database. Do not remove anything in UI, we will add data later
```

## 2026-09-24T21:48:09+0300

```text
Question: How should the server read the database?
Answer: New lab server

Question: Port 8154 is registered to svoe-vino-testset, which runs a copy of the same server. Both cannot run at once. Which port should the lab server use?
Answer: Keep 8154 for now (Recommended)
```

## 2026-09-24T21:55:37+0300

```text
run lab_server on other port
```

## 2026-09-24T22:01:04+0300

```text
try to launch lab_server.py
```

## 2026-09-24T22:02:43+0300

```text
Question: config.yaml says `database_file: data/lab.sqlite3`. What should a relative path in config.yaml be relative to?
Answer: rootdir, as now

Question: You moved the database from data/catalog-2026-09-17/lab.sqlite3 to data/lab.sqlite3. Plan 07 rule 2 says one directory per delivery. Which layout is the rule now?
Answer: data/lab.sqlite3 (flat)
```

## 2026-09-24T22:03:07+0300

```text
git commit
```

## 2026-09-24T22:04:20+0300

```text
Question: Which of your own pending files should go into the commit? My changes go in anyway.
Answer: config.yaml
```
