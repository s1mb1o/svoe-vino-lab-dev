# Same wine across vintages

Use `Same wine / vintages` on a Dataset card to link entries for the same wine.
An entry without a year MAY link to several year-specific entries.
The card lists direct links. Each link appears on both cards.
A linked slug opens its card, including when the current filter hides the card.
The editor supports add, remove, Enter, Escape, and failed-request recovery.
Names, wine slugs, tags, images, and annotations stay independent.

The database stores each undirected pair once in `wine_vintage`.
The relation is separate from `wine_similar`.
The connected component of these pairs defines a wine family.
The cluster build joins the family's Active entries in all three views.
A family stays connected through an entry outside the build.
That outside entry does not become a cluster member.
Links and cluster signals use `vintage` as their reason.
Existing saved artifacts stay unchanged. Rebuild clusters to apply the changed family.
A catalogue merge transfers the links and removes self-links and duplicate pairs.

The model, HTTP, UI, migration, cluster, and merge tests use temporary databases.
The browser check uses a private copy of the live database.
No live relation or cluster job is created during verification.
Read the commands in [COMMANDS.md](../../COMMANDS.md).
