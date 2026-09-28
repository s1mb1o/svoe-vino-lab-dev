# Decision 014: Use an irreversible server-side censored preview

Date: 2026-09-26

## Context

The administrator needs visual context for a quarantined request.
The administration service must not expose the quarantine source.

## Options

### Option 1: Create a server-side blurred derivative

Advantages:

- The browser receives no quarantine source.
- Browser tools cannot remove the censorship.
- The preview preserves coarse composition.

Disadvantages:

- The system stores one additional derivative.
- The preview can still show coarse colors and shapes.

### Option 2: Apply CSS blur to the source

Advantages:

- The implementation is small.

Disadvantages:

- The browser receives the complete source.
- Browser tools can remove the blur.
- This option violates the quarantine boundary.

### Option 3: Create a pixelated derivative

Advantages:

- Pixelation removes fine detail.

Disadvantages:

- The result is less legible as a composition preview.

## Decision

Use Option 1.
Downsample the longest side to 24 pixels.
Enlarge the result and apply a Gaussian blur with radius 18.
Store the derivative with `exposure = 'censored'`.

## Consequences

The administration service can show coarse visual context for a quarantined request.
The service still does not serve quarantine files.
The exposure check depends on the current moderation result.

## Risks

The preview contains coarse image information.
The administration interface must remain private.
It must use loopback or a TLS proxy and keep its configured network restrictions.
The transformation constants must not become configurable through a web request.
