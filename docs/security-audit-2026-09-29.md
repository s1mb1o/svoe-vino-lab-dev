# Security audit

Date: 2026-09-29

## Result

The audit found two high-priority flaws, three medium-priority flaws, and two
low-priority weaknesses.

The highest availability risk is the public image-recognition route. It has no
client quota or sustained rate limit. Each accepted request can use the GPU and
create a permanent archive entry.

The highest confidentiality risk is Matcher Inspector. Each host on the trusted
LAN can read archived user images and complete request journals without
authentication.

The audit did not find an authentication bypass on the public Basic-protected
matcher routes. It did not find a path traversal in Matcher Inspector or in the
Android model-pack extractor. It did not find a committed production credential
with the selected secret patterns.

## Scope

The audit covered these components:

- `matcher`
- `matcher-inspector`
- `webui`
- `telegram-bot`
- `bootstrap`
- `android`
- the HTTP-facing parts of `workbench`
- the production deployment configuration in `<workspace>/deploy`

The audit used the current worktree. The worktree already contained unrelated
changes. The audit did not change those files.

The audit also checked the deployed revisions where a deployment document named
the revision:

- matcher: `013ab56`
- Matcher Inspector: `9ba496d`
- Web UI: `11ebfbf181e215b1c0fbdf218bf06c209281105f`
- Telegram bot: `c0d483e`

The production probes were bounded and non-destructive. The probes did not fetch
an archived user image. The probes did not try credentials. The probes did not
run a sustained load test.

## Findings

### SV-SEC-01: The public recognition routes have no sustained client limit

Severity: High

The public portal accepts image requests without authentication. This behavior is
required for the public product. However, the route has no per-client rate limit,
quota, proof-of-work, or other sustained abuse control.

`webui/server/routes/v1/eval/predict.post.ts:3-13` accepts the request and forwards
it to `predict`. `webui/server/utils/prediction.ts:82-120` sends the file to the
matcher. The shelf route uses the same pattern in
`webui/server/routes/v1/group/match.post.ts:4-13`.

The matcher queue limits simultaneous work. It does not limit sustained work by
one client. `matcher/protection.py:45-163` implements only global in-flight and
queue limits.

The matcher archives each accepted image before inference.
`matcher/app.py:223-299` saves the image and the request journal. The production
deployment has no retention job. See
`<workspace>/deploy/gx10/matcher-prod.md:147-156`.

The previous bounded stress test sent 32 concurrent requests. The matcher accepted
16 requests and rejected 16 requests with HTTP 503. The same test added 56 archive
entries and approximately 6.14 MiB of image data. See
`matcher/docs/reports/2026-09-29_production-stress-test.md`.

An internet client can send accepted requests sequentially. The queue will not
stop this pattern. The client can consume GPU time and fill the archive disk.

Recommended controls:

1. Add a per-client token bucket before the Web UI upload routes.
2. Add a global request budget for expensive routes.
3. Add an archive byte limit and a retention job.
4. Reject accepted uploads when free space is below a safe threshold.
5. Consider short-lived anonymous session quotas or an abuse challenge.
6. Apply stricter limits to the shelf route because it is more expensive.

### SV-SEC-02: Matcher Inspector exposes archived user data without authentication

Severity: High

The production service binds to `0.0.0.0:28001`. It has no authentication. See
`<workspace>/deploy/gx10/matcher-inspector.md:24-41`.

The home page lists request identifiers, client addresses, result slugs, and image
sizes. `matcher-inspector/app.py:293-399` renders this data.

The detail page shows the archived image, the original file name, dimensions, the
SHA-256 value, and the complete request journal.
`matcher-inspector/app.py:402-458` renders this data.

The image route returns the original archived input.
`matcher-inspector/app.py:477-510` has no authentication check. The server binds to
all interfaces at `matcher-inspector/app.py:554-570`.

The bounded production probe requested only the home page. It returned HTTP 200
without credentials. The page contained 173 request-detail links. The probe did
not open a detail page or an image route.

Any compromised or untrusted host on the allowed LAN can read user images and
request metadata.

Recommended controls:

1. Bind the host port to `127.0.0.1`.
2. Use an SSH tunnel or a VPN for operator access.
3. If LAN access is necessary, use HTTPS and strong authentication.
4. Put authorization checks on every request and image route.
5. Remove the complete journal and complete bundle manifest from the default view.
6. Record and review access to archived user data.

### SV-SEC-03: The Telegram administration password crosses the LAN in clear text

Severity: Medium

The administration service uses HTTP Basic authentication at
`http://192.168.86.14:28003/`. It binds to all interfaces. See
`<workspace>/deploy/gx10/telegram-bot-prod.md:19-24`.

HTTP Basic sends a replayable credential on each request. HTTP does not encrypt the
credential. A host that can observe LAN traffic can capture the credential and use
the administration functions.

The production probe received HTTP 401 and a Basic authentication challenge. The
probe did not send a credential.

Recommended controls:

1. Bind the administration port to `127.0.0.1` and use an SSH tunnel.
2. Alternatively, put the service behind HTTPS on an operator-only network.
3. Rotate the current password after the transport control is installed.

### SV-SEC-04: The Telegram recognition API bypasses user rate limits

Severity: Medium

The production recognition API binds to `0.0.0.0:28002`. It permits the complete
`192.168.86.0/24` network and does not require a token. See
`<workspace>/deploy/gx10/telegram-bot-prod.md:19-26`.

`telegram-bot/src/chto_za_vino_bot/http_api.py:89-167` checks only the source
network. It then submits the image to the shared Telegram work queue.

The deployed revision creates each API request with `rate_limit_exempt = 1`.
`telegram-bot/src/chto_za_vino_bot/storage.py:516-545` has the same behavior in the
current worktree. `telegram-bot/src/chto_za_vino_bot/app.py:1472-1513` checks only
the global queue capacity before it creates and submits the request.

A LAN host can fill the work queue, delay Telegram users, and create database and
artifact records without a per-client quota.

Recommended controls:

1. Require a bearer token or mutual TLS.
2. Restrict the source network to the exact consumer hosts.
3. Apply a per-client quota and a separate API service quota.
4. Do not mark all HTTP API requests as rate-limit exempt.
5. Keep a small queue reservation for Telegram users.

### SV-SEC-05: Portable model services do not bound request memory or image pixels

Severity: Medium when the gateway is reachable from another host. Low with the
default loopback bind.

The bootstrap launcher binds the gateway to `127.0.0.1` by default. The deployment
guide permits a private-interface bind for trusted-network access.

`bootstrap/gateway.py:45-73` reads the complete request body into memory. It also
buffers the complete upstream response. The timeout is 900 seconds. The gateway
has no body-size middleware and no concurrency limit.

The image services read and decode complete images without a byte or pixel limit:

- `bootstrap/services/siglip2.py:315-324`
- `bootstrap/services/sam3.py:578-582`
- `bootstrap/services/shieldgemma.py:126-146`
- `bootstrap/services/qr_scanner.py:123-165`

The SigLIP service limits the number of batch items. It does not limit the encoded
size or decoded pixel count of each item.

A permitted client can use a large compressed image or a large body to consume
host memory. Multiple requests can multiply the effect.

Recommended controls:

1. Add one shared streaming request limit to the gateway.
2. Add a hard image-byte limit and a hard decoded-pixel limit to each service.
3. Add per-route concurrency and queue limits.
4. Add a smaller upstream-response limit.
5. Keep the default loopback bind unless remote access is necessary.

### SV-SEC-06: The bootstrap environment contains conditional dependency advisories

Severity: Low for the current service paths. Reassess if model sources become
untrusted.

The dependency audit found no known vulnerability in the Web UI production
dependency tree, the matcher environment, or the Telegram bot environment.

The bootstrap environment reported these runtime package advisories:

| Package | Installed | Advisory | Fixed version | Current reachability |
|---|---:|---|---:|---|
| `torch` | 2.11.0 | `CVE-2025-3000` | 2.13.0 | Reported for `torch.jit.script`; the audited service does not call it. |
| `transformers` | 5.3.0 | `CVE-2026-5241` | 5.5.0 | Requires a malicious LightGlue model repository; the configured services do not use LightGlue. |
| `transformers` | 5.3.0 | `CVE-2026-9856` | 5.10.0 | Requires a malicious tokenizer or processor and a later `save_pretrained` call; the audited services do not call it. |

The audit also reported advisories for `pip` and `setuptools` in the local bootstrap
environment. Those packages are build tools, not request handlers. Update them in
the environment creation process.

Update `torch` and `transformers` after a model-compatibility test. Do not accept an
untrusted model repository before the update.

### SV-SEC-07: The public site has no Content Security Policy

Severity: Low

The public response included HSTS, `X-Content-Type-Options`, and
`Referrer-Policy`. It did not include a Content Security Policy,
`Permissions-Policy`, or `Cross-Origin-Opener-Policy`.

The code search found no user-controlled `v-html` use. The only `innerHTML` value is
the fixed JSON-LD value in `webui/nuxt.config.ts:44-71`. The missing policy does not
prove a current cross-site scripting flaw. It reduces protection against a future
injection flaw.

Add a tested Content Security Policy. Add the other headers that match the portal
feature set.

## Production probe results

| Probe | Result |
|---|---:|
| `GET https://chtozavino.ru/` | 200 |
| Unauthenticated `POST https://chtozavino.ru/v1/eval/predict` | 401 |
| Unauthenticated `GET https://api.chtozavino.ru/v1/models` | 401 |
| Tiny invalid body to `POST https://chtozavino.ru/api/predict` | 415 |
| Unauthenticated `GET http://192.168.86.14:28001/` | 200 |
| Encoded traversal-shaped Matcher Inspector path | 404 |
| `GET http://192.168.86.14:28000/healthz` | 200 |
| `GET http://192.168.86.14:28002/healthz` | 200 |
| Unauthenticated `GET http://192.168.86.14:28003/` | 401 |

## Verification

These test suites passed:

- matcher: 102 tests
- Matcher Inspector: 7 tests
- Telegram bot: 200 tests
- Web UI: 150 tests
- bootstrap: 22 tests

The total is 481 passing tests.

The Android unit tests did not run because the host has no Java runtime.

The earlier production stress test confirmed JPEG, PNG, and WebP behavior. It also
confirmed the exact 40,000,000-pixel WebP boundary and the global overload queue.

## Priority order

1. Protect Matcher Inspector immediately.
2. Add public recognition rate limits and archive retention.
3. Protect the Telegram administration transport.
4. Add authentication and quotas to the Telegram recognition API.
5. Add bootstrap request and pixel limits.
6. Update the conditional bootstrap dependencies.
7. Add the public browser security headers.
