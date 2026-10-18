# MCP research log

## 2026-10-19

### Product-line map integration

Node.js cannot import `webui/shared/product-line-map.ts`.
Its JSON imports have no import attribute. Node.js stops with `ERR_IMPORT_ATTRIBUTE_MISSING`.
The module also has a directory import and an extensionless runtime import.
The Nuxt build needs these imports. Do not change them for the MCP server.
The pure functions now live in `webui/shared/product-line-core.ts` without runtime imports.
Node.js loads this module through native type stripping, like `webui/shared/catalog.ts`.

The 19 maps have 1,046 products. 61 products have no catalog slug.
980 of 2,094 bundle IDs are map nodes: 977 exact slugs and 3 aliases. All aliases are Abrau-Durso IDs.
No bundle ID has a mapped producer without a node.
8 map slugs are absent from the bundle: Abrau-Durso 2, ESSE 1, Fanagoria 1, Zolotaya Balka 4.
The former demo ID `abrau-dyurso-victor-dravigny-bryut` is a verified alias.
The former "other producer" test ID `avtohtonnoe-vino-kryma-beloe-suhoe` is now a node of the Valery Zakharyin map.

Full map files are up to 183 KB. A projection without product descriptions and images is at most about 46 KB.
With the current node and the envelope, the largest response is 49 KiB. The server limit is 128 KiB.
Tier price labels are relative, for example «Базовый ориентир · ₽». No product has a price.
Source conflicts are product badges. One Abrau-Durso source has no URL.

## 2026-10-18

### SDK decision

The official TypeScript SDK publishes the v2 server and client separately.
Use `@modelcontextprotocol/server` 2.3.1 and `@modelcontextprotocol/client` 2.3.1.
The npm metadata was checked before installation.
Zod 4.6.7 provides strict input and structured output schemas.
Use native Node TypeScript imports for the existing shared Web constants.
No TypeScript build pipeline is required for this small JavaScript package.

Primary source: https://github.com/modelcontextprotocol/typescript-sdk.
Inspector source: https://modelcontextprotocol.io/docs/tools/inspector.
Read the installed SDK types for actual transport and result behavior.
Do not implement the wire protocol manually.

### Data decision

The checked-in matcher bundle contains 2,094 exact IDs.
The source export contains additional lab entries.
Join by the matcher IDs. Do not publish every lab row.
One bundle ID is Removed in the export.
Return this state without asserting a public source card.
Use 2,093 Active IDs for discovery.
The default is a reproducible source snapshot. A live production index was not checked.

The bundle checksum is `cdd53eb8be5dbb8ffbeafda7513398551359c4bb9eedcffe82f249bf455abc70`.
The initial combined catalog version is `f9e85e3a0f8b9619d375be482bf6613bd9b729680a88ff11b6e21e0b504ba388`.
Existing Web provenance supplies optional pairings and serving fields for supported records.
Do not extend that limited coverage by generating facts.

### Mock decision

The owner requested the current product-line mock on 18 October.
Import the same `ABRAU_LINE` that the Web demo imports.
Mark its six nodes as demo.
Do not return it as the map of another producer.
Issue 25 contains the replacement checklist.
The verified product-line branch was not merged or copied by this task.

### Test interpretation

The integration test uses a real SDK client and a server subprocess over stdio.
The tests do not call Qwen or another model.
The prompt-like text test checks server data handling and the fixed tool boundary.
It does not prove that every external LLM host resists prompt injection.
Audio tests check approval, identity binding, byte integrity, and path containment.
They do not verify production hosting, decoding, voice quality, or accessibility playback.
These limits remain explicit in the component README.
