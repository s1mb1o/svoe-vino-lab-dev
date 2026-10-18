# Change log

The change log of the repository. A project folder can have its own `ChangeLog.md`, for example
`telegram-bot/`, `max-bot/`, and `im-core/`.

## 2026-10-19

- Merged the producer product-line maps into `webui/` (branch `product-line-map`): 19 producers and 1,046 products.
  Read `webui/ChangeLog.md`.
- Replaced the six-node Abrau demo of the MCP tool `get_producer_line` with these maps (#25).
  Read `mcp/ChangeLog.md` and `docs/plans/03_mcp-producer-line-maps.md`.
- Updated F-24 and F-48 in `ASSESSMENT.md` for these changes. The other entries and the header still describe
  the check at `0621952`.
- Updated `ASSESSMENT.md` to `main` at `0621952`. Added F-13 shelf pipeline with label
  evidence (port of the production matcher), F-48 read-only catalogue MCP server (#25), and
  F-86 HEIF (HEIC) photos (#24). Highlight 10 now covers WebMCP (F-77) and the MCP server
  (F-48). Added `mcp/` to the test commands and the component layout. Removed the
  `feature/mcp` row: the branch is merged into `main` and deleted.

## 2026-10-18

- Added `ASSESSMENT.md`: an index of the features on `main` for the hackathon organizers and the
  jury. It is not development documentation. Each feature has its status, entry point, proofs,
  and a verify step. `README.md` links to it (#42).
- Ported the Yandex.Metrika counter `113460637` of the production web UI to `webui/` (#40).
  The source is the lab repository `svoe-vino-lab`, branch `codex/metrika-release`, commits
  `10632011` and `af36345e`. Read `webui/ChangeLog.md`.

## 2026-10-02

- Added the evaluation results: `predictions.jsonl` with 100 predictions (`aca12e6d`) and their
  summary in `README.md` (`d935c652`, `20a9903e`).

## 2026-09-29

- Froze the repository for the hackathon submission (`e8787cf4`).
