# Decision 013: Persist safe pipeline artifacts

Date: 2026-09-26

Status: Updated by Decision 018 for local development and tests. Production still requires
safe moderation before full-fidelity artifact storage.

## Context

The administrator needs to inspect masks, crops, and other recognition inputs.
The current system stores request metadata but does not store visual intermediate results.

## Options

### Option 1: Persist artifacts during processing

Advantages:

- The page shows the exact artifacts from the processing attempt.
- The page does not run GPU work.
- An artifact remains available after a model or configuration change.

Disadvantages:

- The artifact store uses more disk space.
- The pipeline needs advisory artifact generation code.

### Option 2: Recreate artifacts when the page opens

Advantages:

- The system does not store artifacts in advance.

Disadvantages:

- Each page view can use GPU resources.
- The recreated output can differ from the original processing attempt.
- A page failure can depend on an unrelated model outage.

### Option 3: Persist geometry only

Advantages:

- Geometry uses little disk space.

Disadvantages:

- Geometry cannot show the exact model mask.
- A later renderer can produce a different result.

## Decision

Use Option 1.
Persist derived artifacts only after safe moderation or an explicit non-production bypass.
Keep artifact generation advisory.
Serve an artifact only when the current request remains safe or has the explicit bypass state.

## Consequences

The system stores additional derived images.
The administration service can show the exact pipeline output without new GPU work.
A retry replaces the artifact index for the request.
Old unreferenced artifact files can remain until a later retention task removes them.

## Risks

An artifact can contain personal or sensitive visual information from a safe image.
HTTP Basic authentication, network restrictions, and loopback or TLS transport remain mandatory.
The service MUST use `Cache-Control: no-store`.
The service MUST NOT serve quarantine images.
