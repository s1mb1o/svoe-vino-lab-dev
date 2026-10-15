# Post-VLM vintage matching

The Workbench OpenAI VLM path reads the actual printed vintage.
A vintage answer is a four-digit year string or null.
The prompt does not give candidate years as choices.
Other questions keep their option-score contract.

The post-VLM code prefers the same vintage inside the triggered wine cluster.
If the retrieved rerank window has no exact vintage, the code prefers a confirmed
undated variant. A null or conflicting vintage is neutral. Candidates with the same
preference keep their previous order. Other wines keep their positions.

Candidate facts use the existing resolver in `label_rules.vintage_facts`.
Name or slug years take priority over tags. Tags take priority over saved label
descriptions. A missing or unreadable description does not prove an undated variant.

The trace holds `raw_vintage_years` and `vintage_match`.
Vintage preference is separate from option-score confidence.
Laya keeps its supported numeric-score contract.
This change applies to Workbench. It does not change the native matcher service.

The local tests use fake VLM responses and temporary databases.
They call no model service. Use the vintage matching test commands in
[COMMANDS.md](../../COMMANDS.md) from the Workbench root.

The first suite covers post-VLM selection and the actual runtime integration.
The second suite preserves existing option scoring, retries and triggers.
The earlier prepared patch and controlled replay are in
`internal/vintage-match-20261011` at the repository root.
