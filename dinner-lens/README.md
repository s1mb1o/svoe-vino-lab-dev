# Dinner Lens

Food-to-wine backend for issue [#28](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/28). It runs as a separate authenticated FastAPI service and does not load the bottle-recognition models. The web UI and bots are not connected to this service yet.

## Selection pipeline

1. Resolve a user-confirmed dish against complete canonical names and aliases in the current v4 dataset: 200 dishes, 104 intermediate classes, 16 broad fallback classes. The original 75 recipes and their nodes remain verbatim in v2 and in the separately retained v1 file. Unknown names return the 16 categories for manual selection. A substring such as a steak mentioned inside an unknown recipe does not confirm that recipe.
2. For photographs, call local `qwen3.5-9b-nvfp4` on gx10 with English instructions and the taxonomy. Use `qwen3.8-flash` in QwenCloud as fallback for provider failure or invalid output. The model supplies recognition and clarification only; it does not select wine IDs. Exact recipe predictions are conservatively reduced to their parent class until the user confirms the recipe. A hypothesis never counts as confirmation. Recognition can still choose the wrong food family.
3. Derive the pairing profile in code from the selected recipe/style reference and explicit `confirmed_attributes`. User attributes override reference defaults; uncertain model observations never become hard facts. The response reports reference defaults separately from user-confirmed facts.
4. Apply the same admission gate to every candidate: active catalog status, discovery eligibility, profile color/sweetness/wine kind, applicable alcohol limit, and explicit user constraints. A missing required fact fails the check. Conditional editorial picks and their whole conditional styles require confirmation: red for unspecified poultry, white for unspecified game, sweet wine for unspecified cheese, and red for an unspecified dessert. These styles cannot re-enter through discovery until their corresponding recipe attribute is confirmed.
5. Serve eligible editorial picks first. The initial page uses distinct producers where possible. Remaining editorial picks precede all discovery picks. If only one or two producers qualify, the first page can be short. Editorial order can change to provide producer diversity on the initial page.
6. For discovery, compute cosine similarity between a real embedded English pairing rule and the embedded catalog description/facts. The index contains 2,093 wine vectors plus 136 rule vectors (68 profiles, with and without an acidity preference), generated with `qwen3.7-text-embedding`, 1,024 dimensions. Only eligible IDs enter vector search. Discovery order is lexicographic: known fact count, preferred grape matches, cosine similarity, stable slug tie-break. Cosine similarity is ranking evidence, not a calibrated probability or taste score.
7. Continue using a signed cursor. It preserves dish, effective attributes, filters, catalog scope and page size. Cursors expire after one hour and reject changed context, a changed dataset/index/ranking version, or tampering. Pages have no duplicate wine IDs. Exhaustion never silently broadens the dish or relaxes constraints.

The first page can include discovery choices when all eligible editorial picks have been served and there is spare space. Every result identifies `selection_source` as `curated` or `embedding`, provides an explanation, catalog facts, evidence and similarity. The client should send `next_cursor` unchanged for “show more”. To reject a wine or change restrictions, start a new selection with `seen_wine_slugs` / `rejected_wine_slugs` and the updated constraints.

## Catalog limitations

The current dataset includes 1,231 editorial dish/class-to-wine links and 49 reviewed wines from 12 wineries. All 2,093 active wines are indexed, but only 49 currently have a confirmed wine kind; required unknown fields exclude the others from recommendation. Prices, live stock and numerical residual sugar are mostly unknown. A budget, stock or sugar limit can legitimately produce an empty result. A restaurant list limits membership; it does not prove a bottle is in stock. Absolute grape exclusions require a verified complete blend and otherwise fail closed.

Startup also checks that every conditional editorial entry has a corresponding profile-wide gate with the same predicate and wine category. Adding or renaming a conditional style requires an explicit matching policy update. New recipes can narrow an existing profile through validated `pairing_rule.eligibility_overrides`; both curated and discovery stages enforce those restrictions. V3 also requires a reviewed editorial style family compatible with the selected pairing profile. These families are source-linked qualitative judgments, not measured body/tannin/acidity or a taste-probability score. Color and sweetness alone cannot admit every wine to later pages. They apply only while that base profile is effective, so a confirmed chilli or sweet-sauce modifier can select its own profile. New mayonnaise recipes exclude the semi-dry alternative reserved for salted fish; new tomato recipes exclude the white alternative reserved for cheese-based vegetables and substitute a reviewed dry rosé where needed.

Editorial suitability is non-exhaustive. Body, tannin, oak and acidity preferences are descriptive guidance, not measured hard filters. This is a transparent rules-and-retrieval implementation, not a claim of expert sensory validation. Broader useful discovery requires catalog enrichment, then a new index build.

## Run from the source checkout

Python 3.11 or later is required. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

Public service settings are in `config.yaml`. Use `dinner-lens --config /path/to/config.yaml serve`,
or set `DINNER_LENS_CONFIG` to select that file. The selector is the only non-secret application
setting that uses the environment. Relative asset paths resolve from the YAML directory.
`bundle:` paths resolve from the source checkout or the installed wheel reference assets.
A null index path uses `data/index.v4` in a checkout and `~/.cache/svoe-vino-dinner-lens/index.v4`
for a wheel. `DINNER_LENS_DATASET`, `DINNER_LENS_INDEX`, and `XDG_CACHE_HOME` no longer override settings.

The YAML contains the server listener, worker count, logging settings, dataset/index/style paths,
recognition endpoint/model/prompt, generation settings, provider retry/socket limits, image limits,
embedding endpoint/model/dimensions/build workers, request bound, recognition concurrency/queue
wait and cursor lifetime. Changing embedding model or dimensions requires a matching new index.
The existing v4 index remains valid with the default settings. Selection policy and reference data
remain versioned in the dataset. Input schema ceilings remain API contracts; YAML validates operational limits within bounded ranges.
Unknown fields, wrong types, non-finite numbers and credential-bearing endpoint URLs fail startup.
Configuration errors do not echo input values.

Set `DINNER_LENS_API_TOKEN` to a URL-safe token of at least 24 characters. Set an independent
`DINNER_LENS_CURSOR_SECRET` of at least 32 bytes. Both are required by the service factory.
Set `QWENCLOUD_PAYGO_API_KEY` for photo recognition and index building.
The service requires the recognition credential at startup. Secrets are never YAML
values; the `*_env` fields name environment variables. Embedded test callers may still create
an `Engine` with an ephemeral secret. The service uses the persistent secret across workers and restarts.

```sh
.venv/bin/dinner-lens --config config.yaml build-index
.venv/bin/dinner-lens --config config.yaml serve
curl -s http://127.0.0.1:8176/readyz
```

Index building makes paid calls. It uses a resumable verified batch cache. Runtime selection makes
no embedding API calls. Generated index directories are ignored by Git. The manifest pins the dataset,
embedding documents, vectors, model, dimensions and provider receipts. Startup rejects stale or corrupt
artifacts. Frozen v1/v2/v3 indexes and benchmark evidence remain separate. Built wheels include the
reference datasets, schemas, validation reports, English prompts and default public YAML.

`/docs` and all `/v1/` routes require bearer authorization. `/health` and `/readyz` are public.
Readiness confirms successful artifact/configuration loading. It does not call or certify cloud availability.
Responses use `Cache-Control: no-store`. Defaults preserve the previous limits: 8 MiB JSON body,
5 MiB inline JPEG/PNG/HEIC/HEIF/WebP, 20 million pixels, 2,048-pixel long side, four concurrent recognition calls,
one-second capacity wait, 20-second sockets, 50-second provider retry/read budget and 1 MiB responses.
A blocking socket operation can exceed the budget by its socket timeout. Images are oriented,
metadata-stripped and re-encoded as JPEG, or PNG for PNG inputs and images with transparency.
HEIC/HEIF uses the primary image; animated WebP and MPO use the first frame.
The decoder identifies the actual file format rather than trusting a declared MIME type.
Remote image URLs are not fetched. The English image prompt
matches the current inference registry `planning/dinner-lens-eval-20261018/prompt-registry.json`.
Historical recognition runners and results remain unchanged.

## Docker

The Dockerfile uses a pinned Python 3.11 base digest and `requirements.lock` with package hashes.
It runs as UID/GID 1000 with `/readyz` health checks. Build from a committed `dinner-lens/` archive.
Mount `/config/config.yaml` and the verified index under `/data` read-only. Inject secrets from an
environment file outside the image. Compose, installation, checks, rollback and secret locations are
recorded in the private `chtozavino-deploy/gx10/dinner-lens-prod.md` runbook. The API container uses the CPU. It calls the existing gx10 vLLM model through the model gateway;
the model service uses the GPU. QwenCloud performs fallback recognition. The CPU ranks the mounted embedding vectors.

## API

`POST /v1/recommendations` accepts a confirmed dish name or exact `node_id`:

```json
{
  "node_id": "ribeye_grilled",
  "user_constraints": {"exclude_producer": "Фанагория"},
  "confirmed_attributes": {"heat": "high"},
  "limit": 3
}
```

`POST /v1/recognize-and-recommend` accepts `image_base64` (raw base64 or an inline `image/jpeg`, `image/png`, `image/heic`, `image/heif` or `image/webp` data URL), `user_constraints`, `confirmed_attributes`, `limit`. It returns the wine page together with the raw `recognition` and model receipt `llm`. It does not require a model-provider API key in the client request; the service bearer token is required.

`POST /v1/recommendations/more` accepts `{"cursor":"<next_cursor>"}`. Optional `user_constraints` and `confirmed_attributes` must equal the original context; use a new recommendation request to change them.

Supported constraints:

| Field | Accepted value / meaning |
| --- | --- |
| `color` | `red`, `white`, `rose`, `orange` |
| `sweetness` | `dry`, `semi_dry`, `semi_sweet`, `sweet`, `brut`, `extra_brut`, `brut_nature`; exact equality, so `dry` does not mean `brut` |
| `wine_kind` | `still`, `sparkling` |
| `exclude_producer`, `exclude_producers` | One producer name or a list; Unicode-normalized exact matching |
| `seen_wine_slugs`, `rejected_wine_slugs` | Exact catalog IDs to exclude |
| `restaurant_wine_slugs` | Exact allowed IDs; an empty list allows nothing |
| `grapes_include`, `grapes_exclude` | List of reported grape names; all includes must be present, exclusions require a complete verified blend |
| `max_alcohol_percent`, `max_price_rub`, `max_sugar_g_l` | Finite nonnegative numbers; missing values are ineligible |
| `in_stock` | Boolean; `true` requires confirmed stock |

Supported confirmed attributes: `heat`, `acidity`, `sauce_sweetness`, `protein_family`, `poultry_style`, `game_type`, `cheese_type`, `dessert_base`, `is_dessert`, `fatty_cream_sauce`. Enum values are validated in `src/dinner_lens/engine.py`. Unrecognized fields, malformed input and invalid cursors return 422; absent/incorrect authorization returns 401; recognition provider failure returns 503. `no_results` retains the original food context and asks for clarification. `needs_category` returns broad categories without inventing wines.

Each list is limited to 2,500 strings of at most 400 characters; combined canonical UTF-8 filter JSON is limited to 128 KiB. Full selection context is capped at 512 KiB, keeping every generated cursor below the accepted continuation limit. Producer, grape and membership sets are prepared once per page. `applied_modifier_ids` lists only the winning replacement and effective boost/requirement rules.

## Verification

Rebuild the expanded dataset deterministically with `.venv/bin/python scripts/build_dataset_v2.py`. The input `data/expansion.v2.json` explicitly assigns each new recipe and class to an existing reviewed style. The build validates the JSON schema, graph, unchanged v1 nodes/catalog, source IDs, curated eligibility and producer diversity, then exports `data/ground-truth.expanded-text.v2.jsonl`. Run `.venv/bin/python scripts/benchmark_expanded_text.py --output /path/to/results.json` to exercise all 320 canonical names and 28 ambiguous names through authenticated HTTP, checking complete eligibility, curated-first ordering and every continuation page.

The expansion adds 125 recipes and 52 classes. It fills previously empty egg, legume and fruit categories and adds cheese servings, sushi/rolls, poultry preparations, salads, vegetables, soups, pasta, sauce variants and desserts. Group totals are 31 regional, 68 familiar Russian-menu and 101 international recipes. These are editorial coverage choices, not a measured restaurant-market coverage percentage. Text contracts test implementation against editorial rules; they are not independently annotated photo or sensory ground truth. The English VLM prompt remains unchanged, while the reference taxonomy is larger. No new visual-accuracy score is claimed for v2; additional labelled photos are needed to evaluate that coverage.

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/benchmark_e2e.py \
  --ground-truth-root /path/to/dinner-lens-eval-20261018 \
  --output /path/to/a/new-run
```

The benchmark checks frozen ground-truth and image hashes, makes fresh paid photo calls, exercises the authenticated HTTP routes and follows every cursor to exhaustion. It records service, scorer and test hashes, the first full response, all page IDs/sources and raw provider receipts. Expected labels and approved pairing styles are never service inputs. `--replay-records /path/to/a/prior-run/live-api-recognition` explicitly reuses matching live recognition outputs after code-only fixes and labels that run as replay; it refuses a changed recognition request. An explicit `recorded_pipeline_failure` receipt preserves a prior failed inference rather than replacing it with a successful answer.

The 238 fixed cases contain 75 dish names, 20 constraint cases, 68 fallback/class names and 75 photos. Text strict pass checks the unchanged expected wine eligibility and node, availability, explanations and all pages. The complete returned set must equal the frozen eligible set after the independently checked confirmation gates; over-filtering fails too. The scorer does not call production admission/profile code. For an accepted photo node, eligibility and completeness use that exact node's frozen set. A union over ground-truth acceptable nodes is only a diagnostic when recognition is wrong. Photo strict pass additionally requires safe hierarchy, necessary clarification, result availability and pagination. These source style rules are not sensory validation. Photo misclassification remains an end-to-end failure even when the resulting wines obey the wrong class's rules. Reference curated precision measures agreement with the same editorial dataset, not independent quality. ASGI tests exercise the real API implementation but do not constitute deployment/load testing.

English prompts are versioned under `prompts/`. Russian appears only in reference labels/catalog data and response examples. Historical benchmark assets remain unchanged.

The compatibility audit checks every original canonical name and alias. One v1 resolution is intentionally superseded in v2: `шашлык` now asks for the main ingredient instead of assuming red meat, since it can be poultry or fish. The report lists that exact exception and rejects any unapproved change. Generic burgers and unspecified stuffed vegetables use explicitly documented cross-branch broad classes; negative `must_not_resolve_to` references are checked as negative examples, not incorrectly treated as mandatory ancestors. All new ambiguity rules and classes return a clarification question. Named sauces also ask about actual sweetness and heat.

## Sauce and continuation quality (v3)

The selected recipe/style reference contributes pairing-rule defaults, separately from user-confirmed attributes and visible image facts. Defaults preserve an already selected chilli or glaze style when cream is added. Explicit user attributes override reference defaults, and the response keeps `confirmed_attributes` restricted to the actual request. `diagnostics.sauce_rule_context` shows the separate sources. A visual hypothesis never supplies leaf-recipe defaults. Known fish/poultry need not be repeated as another API flag for a cream sauce. Sweet sauce handling does not require a redundant `is_dessert: false`. Desserts keep their selected subprofile and sweetness; confirmed chilli also retains the alcohol cap.

Sweet savoury sauces retain the food's weight: rich red meat uses a ripe, soft-tannin red profile; duck uses a berry-fruited soft red profile; lighter poultry/seafood uses the off-dry profile. These are editorial choices, not a universal claim that dry red is best for every sweet sauce. Chilli on red meat has its own lower-alcohol, delicate-tannin profile. All explicit wine constraints remain hard, and every selected wine passes category, style and final admission checks.

The reviewed style envelope applies to every continuation page and to modifier-profile curated pools. Unsupported or unreviewed styles are excluded rather than used to fill a page. Some hot dishes have only three or four supported wines. Chocolate-only desserts have three compatible reviewed sweet reds from two producers; producer diversity makes the first page shorter. No weaker wine is added merely to reach three cards or a longer list. Embedding results now explain their dish/style fit and active sauce characteristics instead of only repeating a generic catalog description.

Run `.venv/bin/python scripts/build_dataset_v3.py`, rebuild `data/index.v3/`, then run `.venv/bin/python scripts/validate_dataset_v3.py` for the v3 source/category/style contract and all 320 canonical routes with pagination to exhaustion. The separate `benchmark_expanded_text.py` deliberately pins frozen v2 and its 348 text contracts. All v1/v2 JSON, old prompts and historical ground truth remain unchanged.

`scripts/benchmark_pairing_quality.py` captures full wine lists and scores separately frozen blind editorial judgments. The current audit uses 42 dish/sauce contexts and 12 additional prespecified holdout contexts, covering all pages and explicit embeddings. Claude Opus 5.5 assessed all 49 reviewed wine cards for each context without seeing profiles, curated lists, ranks or returned candidates. The policy was frozen before reading the holdout judgments/results. These model opinions diagnose suitability; they are not independent human sensory validation. The main cases informed refinements, so their improvement is diagnostic rather than an unbiased generalization estimate. Marginal disagreements remain, including a moderately acidic Pinot Blanc with a strongly acidic fish soup. No new photo-recognition accuracy is claimed by this wine-selection test.


## Full recipe and sauce coverage (v4)

V4 retains the 200 recipes,104 intermediate classes and16 broad classes. Catalog source facts, original v1/v2/v3 JSON and English prompts are preserved. It adds source-linked qualitative body, acidity and aroma annotations plus compositional admission guards. These are editorial readings of catalog descriptions, never numeric acidity or laboratory body/tannin measurements. Strongly acidic sauces require positive freshness/acidity evidence. Rich meat excludes overly light styles; mushroom umami and delicate raw shellfish exclude conflicting herbal, rounded or overpowering styles. Cream and glaze rules compose with acidity and heat. The same guards apply to curated choices and all embedding pages.

The full test matrix contains all 200 selected dishes and all 16 combinations of cream, pronounced acidity, sweetness and hot chilli additions (3,200 scenarios). Missing dimensions retain the selected recipe reference. Some combinations are intentionally unusual stress cases. This is not a claim to cover every possible sauce or cooking method. The capture records every page's exact node, effective profile and confirmed attributes until exhaustion. An independent JSON projector checks complete eligible-set equality; a separate blind editorial model assesses wine suitability. Its opinions are not human tasting ground truth. Refinement cases are diagnostic, not held-out generalization evidence. Complete returned counts and abstentions must accompany any quality percentage.

A strongly acidic, hot chocolate dessert can have no reviewed wine with the required acidity evidence and alcohol level. The API returns no_results and a clarification instead of filling the list. Some intrinsic spicy-sour recipes have only two supported curated wines. Shorter lists are deliberate evidence limits. Alcohol ceilings use catalog source values, whose physical bottle-label precision has not been independently verified; URL slugs do not provide numeric facts.

Build with `scripts/build_dataset_v4.py`, build the matching `data/index.v4/`, then run `scripts/validate_dataset_v4.py`. `scripts/capture_full_sauce.py` exercises authenticated HTTP and checks that production source and data stayed unchanged throughout the capture. `scripts/score_full_sauce.py` validates the complete 3,200-case source contract and optionally scores a separately frozen blind reference. The actual 2,093 wine and 136 query vectors are unchanged from v3; v4 needs no new embedding-provider calls. The versioned audit directory contains the case matrix, captured lists, editorial reference, comparison, source hashes and actual Claude Opus 5.5 review receipt. No new photo-recognition accuracy is claimed.

Post-review regressions preserve the duck profile when cream is added, retain reviewed intrinsic acidity for sour recipes, and inherit raw-shellfish guards through the raw_bivalves class and photo demotion. The 120 class/fallback routes are additionally tested with all 16 sauce combinations (1,920 scenarios). This tests the recognition-to-class guardrail with fixed recognized IDs; it is not a new vision-model accuracy evaluation. Full-bodied high-acid white is permitted with cream, and a confirmed high-sugar savory glaze can admit a semi-sweet white when other constraints permit it.

## Local recognition and cloud fallback

The public YAML config selects local `qwen3.5-9b-nvfp4` at
`http://192.168.86.14:18081/v1/chat/completions`. The gateway requests this alias, while vLLM
reports `Qwen3.5-9B-NVFP4`. `response_model` pins that exact response ID; a mismatch fails over.
`protocol: vllm` sends `chat_template_kwargs.enable_thinking: false`. The local endpoint uses
`api_key_env: null` and receives no cloud authorization header. Selecting `protocol: vllm`
also defaults the credential reference to null when the field is omitted.

The optional `recognition.fallback` holds one provider configuration, including its endpoint,
model, protocol, credential environment name and limits. The default fallback is Qwen3.8-Flash.
It receives the same sanitized image and English instructions. It is used after a local timeout,
HTTP error, model mismatch, truncated output, invalid JSON or invalid recognition schema.
A valid uncertain or unknown classification stays local and asks for clarification.
There is no model confidence threshold or cloud vote. A plausible wrong local classification
can still yield wines for the wrong food category. Compare the frozen benchmark before deployment.

Local defaults: one attempt, 45-second socket timeout and 50-second read/retry budget.
Cloud fallback defaults: three attempts, 20-second sockets and a 50-second budget.
The budgets are per provider, checked between reads; a blocking socket can extend a budget.
Clients should allow at least 180 seconds for the full chain. Recognition concurrency is per worker.
Startup requires configured provider credentials, including the fallback cloud key.
`/health` reports configured primary/fallback model IDs. It does not call either model.
Each photo result reports the selected/requested/returned model, `fallback_used`, safe failure
codes, provider attempts and total chain latency. Raw provider errors and secrets are not returned.
The default embedded `RecognitionSettings()` remains cloud-only for explicit historical reproduction.
The packaged YAML and gx10 deployment use the local-first configuration.

`scripts/benchmark_recognition.py` performs fresh comparisons on the frozen 75 photos and 163 text/
constraint/fallback cases. Invoke it through the current registry entry point with `--pipeline-eval`.
It checks immutable image/label hashes, uses the current v4 taxonomy, and follows every wine page.
The frozen v4 wine contracts are separate from the original v1 label sets. Constraint cases use
intersection with their frozen original eligibility. Reports distinguish classification accuracy
from wine eligibility for the selected class. These reference labels are not human expert validation.
