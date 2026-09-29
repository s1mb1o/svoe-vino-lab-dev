# Security remediation plan

Date: 2026-09-29

Source: [Security audit](../security-audit-2026-09-29.md)

## Goal

This plan resolves findings `SV-SEC-01` through `SV-SEC-07`.

The plan reduces exposure before it changes application behavior. It then adds
resource limits, data retention, authentication, dependency updates, and browser
security headers.

No production deploy or production restart can occur without owner approval.
Each production image MUST use a committed revision.

## Work rules

1. Create an isolated branch or worktree for this work.
2. Do not mix the existing worktree changes with the security changes.
3. Keep one remediation group in each reviewable commit.
4. Put deployment changes in `<workspace>/deploy/`.
5. Do not put credentials or tokens in Git.
6. Test each control in the development deployment before production.
7. Get owner approval before each production deploy or restart.
8. Record the deployed commit in the applicable deployment document.

## Required owner decisions

The implementation can start before all decisions are complete. Production
activation needs these decisions.

| Decision | Recommended initial value | Reason |
|---|---|---|
| Archive retention | 14 days | This value limits disk growth and keeps recent evidence for diagnosis. |
| Matcher Inspector access | Loopback with an SSH tunnel | This option removes unauthenticated LAN access without a new identity service. |
| Telegram administration access | Loopback with an SSH tunnel | This option prevents HTTP Basic credentials from crossing the LAN. |
| Public single-image rate | Burst 3, then 6 requests per minute per client | This value permits normal retries and limits sustained GPU use. |
| Public shelf rate | Burst 1, then 2 requests per minute per client | Shelf processing costs more than single-image processing. |
| Telegram API identity | One bearer token for each consumer | Separate tokens permit revocation and separate quotas. |
| Bootstrap remote access | Keep the default loopback bind | A remote bind increases the request-memory risk. |

The initial rate values are deployment defaults. The owner can change them after
the first observation period.

## Phase 0: Prepare the change

### Actions

1. Identify every valid client of ports `28001`, `28002`, and `28003`.
2. Record the exact source host for each Telegram recognition API client.
3. Measure the current archive size, archive growth, and free disk space.
4. Record the current request rate, latency, HTTP 429 count, HTTP 503 count, and
   Telegram queue depth.
5. Prepare an SSH tunnel command for Matcher Inspector.
6. Prepare an SSH tunnel command for Telegram administration.
7. Define one rollback command for each deployment change.
8. Install a Java runtime in the test environment, or record Android tests as a
   release exception.

### Exit criteria

- The valid network clients are known.
- The baseline measurements are stored in a report.
- Each production change has a rollback procedure.
- The owner has selected an archive retention period.

## Phase 1: Remove exposed operator interfaces from the LAN

This phase resolves the immediate exposure in `SV-SEC-02` and `SV-SEC-03`.

### Matcher Inspector

1. Change the production host mapping from `0.0.0.0:28001` to
   `127.0.0.1:28001`.
2. Make the same change in the development deployment.
3. Use an SSH tunnel for operator access.
4. Keep the archive mount read-only.
5. Remove the complete request journal and complete bundle manifest from the
   default list view.
6. Add an access log for detail and image requests.
7. Add application authentication if a future requirement permits direct LAN
   access.

### Telegram administration

1. Change the production host mapping from `0.0.0.0:28003` to
   `127.0.0.1:28003`.
2. Make the same change in the development deployment.
3. Use an SSH tunnel for operator access.
4. Rotate the administration password after the new bind is active.

### Deployment files

Update these files when the port mappings change:

- `<workspace>/deploy/gx10/matcher-prod.compose.yaml`
- `<workspace>/deploy/gx10/matcher-inspector.md`
- `<workspace>/deploy/gx10/telegram-bot-prod.compose.yaml`
- `<workspace>/deploy/gx10/telegram-bot-prod.md`
- `<workspace>/deploy/README.md`
- `<workspace>/deploy/ChangeLog.md`

### Acceptance tests

- Another LAN host cannot connect to ports `28001` or `28003`.
- An operator can use each interface through its SSH tunnel.
- Matcher Inspector cannot return an archived image without the operator access
  path.
- Telegram administration still returns HTTP 401 for a missing credential through
  the tunnel.
- The matcher and Telegram health checks remain successful.

### Rollback

Restore the prior Compose mapping only if the operator cannot use the SSH tunnel.
Do not rotate the new password back to the old password.

## Phase 2: Control public recognition cost and archive growth

This phase resolves `SV-SEC-01`.

### Admission control

1. Add a token bucket before the Web UI reads or buffers an upload.
2. Use separate buckets for single-image and shelf routes.
3. Return HTTP 429 with a JSON error body and `Retry-After`.
4. Add a global in-flight limit for expensive public requests.
5. Start with eight single-image requests and two shelf requests in flight.
6. Keep matcher capacity for authenticated and operator traffic.
7. Add a configurable daily global budget as a circuit breaker.
8. Do not forward or archive a request that admission control rejects.

The Web UI MUST derive the client address only through a trusted proxy path.
The reverse proxy MUST replace client-supplied forwarding headers. The Web UI
MUST accept a forwarded client address only when the direct peer is the local
reverse proxy.

An in-process limiter is sufficient for the current single Web UI instance. A
shared limiter is required before the Web UI uses more than one instance.

### Archive limits

1. Add a configurable minimum free-space threshold before archive creation.
2. Reject a new request before inference when free space is below the threshold.
3. Return HTTP 507 or the documented HTTP 503 storage error.
4. Add an idempotent retention tool.
5. Run the tool from a systemd timer on `gx10`.
6. Put the unit and timer files in `<workspace>/deploy/gx10/`.
7. Make dry-run mode the first production run.
8. Remove only completed request directories that are older than the cutoff.
9. Require the expected date path and 32-character request identifier.
10. Do not follow symbolic links.
11. Use a lock to prevent concurrent cleanup runs.
12. Report the directory count and byte count before and after cleanup.
13. Alert at 70%, 85%, and 95% archive filesystem use.
14. Do not copy expired user images to another backup unless the retention policy
    explicitly covers that backup.

The first destructive retention run requires owner approval after review of the
dry-run output.

### Tests

- Test a request below, at, and above each rate limit.
- Test a forged `X-Forwarded-For` header.
- Test simultaneous requests from multiple clients.
- Test the global circuit breaker.
- Test JPEG, PNG, and WebP uploads.
- Test a WebP image at 40,000,000 pixels.
- Test a WebP image above 40,000,000 pixels.
- Confirm that rejected requests create no archive entry.
- Test the free-space guard with a mocked filesystem value.
- Test the retention cutoff boundary.
- Test malformed date paths, malformed request identifiers, and symbolic links.
- Confirm that cleanup does not remove an active request directory.

### Exit criteria

- One client cannot sustain unrestricted GPU work.
- Public overload returns HTTP 429 before upload buffering.
- Matcher overload can still return HTTP 503 without an HTTP 500 response.
- Archive growth has a configured maximum age and a free-space guard.
- WebP behavior remains correct at the pixel boundary.

## Phase 3: Protect the Telegram recognition API

This phase resolves `SV-SEC-04`.

### Authentication and network scope

1. Require an `Authorization: Bearer` token on recognition routes.
2. Store only token hashes or protected environment values.
3. Use a constant-time token comparison.
4. Give each consumer a separate token.
5. Do not write a token to a log, database, URL, error, or request journal.
6. Replace the `192.168.86.0/24` allowlist with the exact consumer addresses.
7. Keep `/healthz` minimal. Do not include configuration or queue details.

### Quotas and queue isolation

1. Apply a per-token token bucket.
2. Apply a separate global quota to HTTP API traffic.
3. Remove the unconditional `rate_limit_exempt` behavior.
4. Reserve queue capacity for Telegram users.
5. Start with a reservation of 20 items in the 100-item queue.
6. Limit HTTP API work to two concurrent requests.
7. Return HTTP 429 for a quota rejection.
8. Return HTTP 503 with `Retry-After` for a queue rejection.
9. Reject requests before creation of database and artifact records.

### Rollout sequence

1. Add tokens to the API consumers.
2. Deploy a transition mode that records missing authentication without accepting
   an unknown source.
3. Confirm that each known consumer sends its token.
4. Enable mandatory authentication.
5. Remove transition mode.

### Acceptance tests

- A missing or invalid token returns HTTP 401.
- A valid token from a disallowed source address returns HTTP 403.
- A per-token limit returns HTTP 429.
- A full API allocation returns HTTP 503 with `Retry-After`.
- Telegram user work continues during an HTTP API flood.
- A rejected request creates no database row and no artifact directory.
- Logs and error bodies contain no token.

## Phase 4: Bound bootstrap service resources

This phase resolves `SV-SEC-05`.

### Gateway controls

1. Add one streaming request-size limit to the gateway.
2. Reject an excessive `Content-Length` before body reading.
3. Stop a chunked request when the byte limit is reached.
4. Add an upload timeout that is shorter than the current 900-second upstream
   timeout.
5. Add per-route concurrency and queue limits.
6. Add a maximum buffered upstream-response size.
7. Keep the default bind at `127.0.0.1`.
8. Require authentication and the same limits before any remote bind is enabled.

### Service controls

1. Define a maximum encoded image size for each service.
2. Define a maximum decoded pixel count for each service.
3. Check image dimensions before a complete decode when the format permits it.
4. Convert Pillow decompression-bomb warnings to a controlled HTTP 413 response.
5. Keep existing batch-item limits.
6. Add byte limits for base64 images, text arrays, noun arrays, and other batch
   fields.
7. Return a stable JSON error for each rejected limit.

Use configuration values that are at least 20% above the largest valid production
request. Do not guess the final values without the Phase 0 measurements.

### Acceptance tests

- Test JPEG, PNG, and WebP images below, at, and above each byte limit.
- Test images below, at, and above each pixel limit.
- Test a small compressed image with excessive decoded dimensions.
- Test an oversized base64 request.
- Test an oversized batch.
- Test a slow upload and a chunked upload.
- Test parallel requests at the concurrency and queue boundaries.
- Confirm that health checks remain responsive during rejected overload.
- Confirm that process memory returns near baseline after each test group.

## Phase 5: Update bootstrap dependencies

This phase resolves `SV-SEC-06`.

### Actions

1. Update `pip` to version 26.2 or later in the environment creation process.
2. Update `setuptools` to version 83 or later.
3. Test `torch` version 2.13 or later.
4. Test `transformers` version 5.10 or later.
5. Pin the tested versions in the bootstrap lock data.
6. Generate a software bill of materials for the release.
7. Add `pip-audit` and the production `npm audit` to continuous integration.
8. Reject untrusted model repositories until the dependency update is complete.
9. Do not call `save_pretrained` on data from an untrusted model repository.

### Compatibility tests

- Load each configured model without network access.
- Compare embedding dimensions and cosine results with the current baseline.
- Compare SAM3 mask output with the current baseline.
- Test each ShieldGemma policy.
- Test QR recognition with the reference set.
- Record startup time, peak memory, and request latency.

If a required model does not work with a fixed version, document a temporary
exception. The exception MUST name the unreachable code path, the source-control
restriction, the owner, and the next review date.

## Phase 6: Add browser security headers

This phase resolves `SV-SEC-07`.

### Actions

1. Add a `Content-Security-Policy-Report-Only` header at the public reverse proxy.
2. Define explicit `script-src`, `style-src`, `img-src`, `font-src`, `connect-src`,
   and `worker-src` values for the portal and its service worker.
3. Add `default-src 'self'`.
4. Add `object-src 'none'`.
5. Add `base-uri 'none'`.
6. Add `frame-ancestors 'none'`.
7. Add `form-action 'self'`.
8. Give the fixed JSON-LD script a nonce or stable hash.
9. Review violations during the observation period.
10. Enforce the policy after valid traffic has no unexplained violation.
11. Add a narrow `Permissions-Policy` that preserves required camera and location
    features.
12. Add `Cross-Origin-Opener-Policy: same-origin` after browser compatibility tests.

### Acceptance tests

- The home page has no unexplained CSP violation.
- Recognition works for JPEG, PNG, and WebP images.
- Camera capture works on each supported browser.
- Location-dependent features work when the user grants permission.
- The service worker installs and updates.
- The progressive web application starts offline where current behavior supports
  it.
- JSON-LD remains present and valid.

## Regression test matrix

Run this matrix after each code phase and before each production deploy.

| Area | Required cases |
|---|---|
| Functional | Valid single image, shelf image, Telegram image, inspector tunnel, administration tunnel |
| Wrong data | Empty body, wrong media type, corrupt JPEG, corrupt PNG, corrupt WebP, invalid JSON, invalid base64, unsupported image |
| Big data | Byte boundary, pixel boundary, batch boundary, archive free-space boundary, retention cutoff |
| Parallel data | Limit minus one, exact limit, limit plus one, sustained sequential traffic, mixed route traffic |
| Authentication | Missing token, invalid token, revoked token, valid token from wrong source, forged forwarding header |
| Failure recovery | Matcher timeout, matcher HTTP 503, client disconnect, service restart, retention lock collision |

The baseline suites MUST continue to pass:

- matcher: 102 tests
- Matcher Inspector: 7 tests
- Telegram bot: 200 tests
- Web UI: 150 tests
- bootstrap: 22 tests

The release MUST also run the Android unit tests after a Java runtime is available.

## Deployment order

Use this production order:

1. Deploy the loopback mappings for Matcher Inspector and Telegram administration.
2. Deploy public admission control and archive free-space protection.
3. Review the retention dry-run output.
4. Enable the retention timer after owner approval.
5. Deploy Telegram API authentication, quotas, and queue reservation.
6. Deploy bootstrap request limits.
7. Deploy tested bootstrap dependency updates.
8. Deploy CSP in report-only mode.
9. Enforce CSP after the observation period.

Each step MUST have a separate owner approval when it restarts a production
service.

## Observation and rollback gates

Observe each production change for at least 30 minutes. Review it again after 24
hours before the next risk-bearing phase.

Monitor these values:

- HTTP 401, 403, 413, 429, 500, 503, and 507 counts
- request latency at the 50th, 95th, and 99th percentiles
- matcher in-flight count and queue depth
- Telegram queue depth and oldest-item age
- archive bytes and filesystem use
- process memory and restart count
- CSP violation count

Roll back the applicable release when it causes an unexplained HTTP 500 increase,
a sustained health-check failure, or loss of a required client. Adjust rate values
without rollback when the code is correct and the initial value blocks valid use.

Do not roll back an exposed interface to a LAN bind as a long-term fix. Use the SSH
tunnel or an approved HTTPS operator path.

## Estimated effort

| Work | Estimate |
|---|---:|
| Preparation and baseline | 0.5 day |
| Operator interface containment | 0.5 day |
| Public admission control and archive controls | 2 days |
| Telegram API controls | 1 day |
| Bootstrap limits | 1.5 days |
| Dependency compatibility work | 1 to 2 days |
| Browser headers | 0.5 to 1 day |
| Total engineering work | 7 to 8.5 days |

The estimate excludes the 24-hour observation gates and owner approval time.

## Completion criteria

The remediation is complete when all conditions are true:

1. Ports `28001` and `28003` are not reachable from another LAN host.
2. Public recognition has per-client and global admission control.
3. Rejected public requests do not create archive data.
4. Archive retention and free-space controls are active.
5. The Telegram recognition API requires identity and enforces quotas.
6. Telegram users have reserved queue capacity.
7. Bootstrap services reject excessive bytes, pixels, batches, and parallel work.
8. Fixed dependency versions pass model compatibility tests.
9. The public site enforces a tested CSP and related headers.
10. The regression matrix passes, including WebP boundary cases.
11. Deployment documents and change logs name the deployed commits and controls.
