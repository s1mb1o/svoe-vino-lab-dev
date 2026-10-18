# MCP research log

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
