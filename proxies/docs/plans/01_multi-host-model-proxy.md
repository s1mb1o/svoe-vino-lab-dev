# Plan 01: multi-host model proxy

Date: 2026-09-29

Source: the owner messages of 2026-09-29T08:17:32+0300 and the owner answers of
2026-09-29T10:02:42+0300 in
[`../../../workbench/docs/owner-messages.md`](../../../workbench/docs/owner-messages.md).

State: the design is approved. Stage 1 is done (2026-09-29). Stages 2 and 3 wait for an
RTX host.

## Goal

One proxy process runs on the Mac. It accepts the SAM3, Grounding DINO, and SigLIP2
requests of the lab code. It sends each request to one of several work hosts: gx10 and
RTX 4090 hosts. It keeps a cache of the answers.

A client changes only its endpoint variables:

```sh
export SIGLIP2_ENDPOINT=http://127.0.0.1:18092
export GROUNDING_DINO_ENDPOINT=http://127.0.0.1:18092/upstream/grounding-dino-base
export SAM3_ENDPOINT=http://127.0.0.1:18092/upstream/sam3
```

The purpose is a higher throughput of segmentation and SigLIP2 embeddings during long
jobs, for example training.

## Requirements

R1. The proxy MUST accept the paths and the bodies of the gx10 cache
`http://192.168.86.14:18082` for the routes in the section "Pooled routes".

R2. The proxy MUST forward each other request to the passthrough host without a change.
Examples: `GET /v1/models`, `GET /running`, `GET /upstream/sam3/health`.

R3. The proxy MUST send a pooled request only to a host whose configuration lists the
model. For a `bootstrap` host, the model MUST also be in the list `active_models` of its
`GET /health` answer.

R4. The proxy MUST send a pooled request to a host with a free slot. When no eligible host
has a free slot, the request MUST wait in the queue of its model.

R5. The proxy MUST try another host after a connection error, a timeout, or the HTTP
status 429, 502, 503, or 504. One request tries at most `limits.attempts` hosts.

R6. The proxy MUST start one SSH tunnel for each enabled host with an `ssh` entry. It MUST
start the tunnel again after the tunnel stops. It MUST NOT send a request to a host while
the tunnel of the host is down or the health probe of the host fails.

R7. The proxy MUST keep a cache of the answers on the Mac. The rules are in the section
"Cache".

R8. The proxy MUST NOT change the body of a request or of an answer.

R9. The health probe of a `llama-swap` host MUST NOT load a model. The probe uses
`GET /running`. A request to `/upstream/<model>/health` on gx10 loads the model.

R10. The proxy MUST bind `127.0.0.1` by default. It has no authentication.

## Non-goals

- The proxy does not split one SigLIP2 batch into parts for several hosts.
- The proxy does not send Grounding DINO requests to an RTX host. The bootstrap has no
  Grounding DINO service. One configuration line adds such a host later.
- The proxy does not start the bootstrap launcher on an RTX host. The owner starts it.
- The proxy does not import the gx10 cache. The key function is the same as on gx10, so a
  later import stays possible.
- The proxy does not stream a pooled answer. A passthrough answer is streamed.

## Pooled routes

| Method and path | Model | Body | Cache route |
|---|---|---|---|
| `POST /v1/embeddings` | the JSON field `model` | JSON | `visual-embeddings` |
| `POST /upstream/sam3/segment` | `sam3` | multipart | `sam3` |
| `POST /upstream/sam3/segment_multi` | `sam3` | multipart | `sam3` |
| `POST /upstream/sam3/segment_verify` | `sam3` | multipart | `sam3` |
| `POST /upstream/sam3/segment_point` | `sam3` | multipart | `sam3` |
| `POST /upstream/<model>/detect` | `<model>` | multipart | `grounding-dino` |

A route is pooled only when at least one enabled host lists its model. Otherwise the
request is a passthrough request. Example: `POST /v1/embeddings` for
`dinov3-vitb16-pretrain-lvd1689m` goes to gx10 unchanged, and the proxy does not cache it.

## Routes of the proxy

| Method and path | Answer |
|---|---|
| `GET /_proxy/health` | HTTP 200 while the process runs |
| `GET /_proxy/status` | the hosts, the tunnels, the slots, the queues, the counters, and the cache statistics |

## Headers

The answer of a pooled route has these headers:

- `X-Proxy-Cache`: `HIT`, `MISS`, or `BYPASS`.
- `X-Proxy-Host`: the name of the host that made the answer. A hit names the host of the
  stored answer.
- `Age`: the age of a stored answer in seconds, on a hit only.
- An answer from gx10 keeps the gx10 header `X-GX10-Cache`.

A passthrough answer has `X-Proxy-Cache: BYPASS` and `X-Proxy-Host`.

`Cache-Control: no-cache` or `X-GX10-Cache: bypass` in a request skips the cache of the
proxy. The proxy forwards both headers, so the gx10 cache is skipped too. A skipped
request does not store its answer. The gx10 cache has the same rule.

## Errors of the proxy

| Status | `error` | When | `Retry-After` |
|---|---|---|---|
| 400 | `invalid_content_length` | the header `Content-Length` is not a number | — |
| 413 | `request_too_large` | the body is larger than `limits.max_request_size` | — |
| 429 | `queue_full` | the queue of the model holds `limits.queue_limit` requests | 1 |
| 503 | `no_host_available` | no enabled host is up for the model | 5 |
| 503 | `queue_timeout` | the request waited `limits.queue_timeout` seconds | 5 |
| 502 | `upstream_unavailable` | each tried host failed without an HTTP answer | — |

When each tried host gave a retryable HTTP answer, the client gets the last answer as it
came.

## Configuration

One YAML file, by default `config.yaml` in the project directory. An unknown key is an
error.

```yaml
listen:
  host: 127.0.0.1
  port: 18092
passthrough: gx10            # the host for each request that is not pooled
cache:
  path: ~/.cache/svoe-vino-model-proxy/cache.sqlite3
  namespace: svoe-vino-model-proxy-v1
  ttl_days: 30
  max_size: 10GiB
  max_response_size: 256MiB
limits:
  max_request_size: 256MiB
  queue_limit: 128           # waiting requests for each model
  queue_timeout: 300         # seconds
  upstream_timeout: 300      # seconds for the answer of one host
  attempts: 3                # hosts for one request
health:
  interval: 10               # seconds between two probes of one host
  timeout: 5                 # seconds for one probe
hosts:
  - name: gx10
    kind: llama-swap         # probe: GET /running
    url: http://192.168.86.14:18082
    slots: 4                 # parallel requests for each model on this host
    models: [sam3, grounding-dino-base, siglip2-so400m-patch16-naflex, ...]
  - name: kit
    kind: bootstrap          # probe: GET /health, list active_models
    enabled: false
    ssh:
      target: root@178.130.51.88
      local_port: 18191      # the URL of the host is http://127.0.0.1:18191
      remote_port: 18090
    slots: 4
    models: [sam3, siglip2-so400m-patch16-naflex, siglip2-so400m-patch16-512]
```

Rules:

- A host has either `url` or `ssh`. An `ssh` host has the URL
  `http://127.0.0.1:<local_port>`.
- Host names and local ports are unique.
- `passthrough` names an enabled host.
- `slots` is 1 or more. It applies to each model of the host separately, because each
  model is one process on gx10 and on a bootstrap host.

## Dispatch

1. The proxy finds the model of the request.
2. An eligible host is enabled and up, lists the model, has the model active, and was not
   tried for this request.
3. From the eligible hosts with a free slot, the proxy takes the host with the lowest share
   of busy slots. A tie goes to the first host in the configuration.
4. When no eligible host has a free slot, the request waits. A released slot wakes the
   waiting requests in order.
5. A faster host releases its slots sooner, so it takes more requests. No weight is
   necessary.
6. A waiting request checks each second whether its client disconnected. Such a request
   leaves the queue.
7. When no eligible host is up, the request gets HTTP 503 at once.

## Retry

- A connection error marks the host down until its next good probe.
- A timeout, another transport error, or HTTP 429, 502, 503, or 504 does not mark the host
  down. The proxy tries the next eligible host.
- A request never tries one host two times.
- Another HTTP status goes to the client at once, for example HTTP 400 or 422.

## Health

- The proxy probes each enabled host every `health.interval` seconds, and one time at the
  start before it serves.
- While a host is down, the probes come every 2 s (`DOWN_PROBE_INTERVAL`). So a host that
  is back, or a tunnel that opened its forward after the start, is used again soon.
- At the start, the proxy waits at most 3 s until each tunnel process runs. An `ssh`
  process needs about one more second to open its forward. So the first probe of an RTX
  host usually fails, and the probe 2 s later succeeds.
- `llama-swap`: `GET /running`. HTTP 200 with a list `running` means up. Each configured
  model counts as active, because llama-swap loads a model on demand.
- `bootstrap`: `GET /health`. HTTP 200 or 503 with a list `active_models` gives the active
  models. A model in `failures` is not active. A host with no active configured model is
  down.
- A host with a tunnel is down while the tunnel process does not run.

## Tunnels

- One `ssh` process for each enabled `ssh` host:
  `ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15
  -o ServerAliveCountMax=3 -o ConnectTimeout=10
  -L 127.0.0.1:<local_port>:127.0.0.1:<remote_port> <target>`.
- `BatchMode=yes` stops a password prompt. The Mac SSH key MUST have access. The host key
  MUST be in `~/.ssh/known_hosts`.
- After an exit, the proxy waits 1 s, then 2 s, 4 s, and so on up to 60 s. A tunnel that ran
  60 s or more starts the wait again at 1 s.
- The proxy stops each tunnel with SIGTERM when it stops.
- The `ssh` processes are in the process group of the proxy. So Ctrl-C in the terminal
  stops them too. A SIGKILL of the proxy leaves them running.

## Cache

The rules are the rules of the gx10 cache (`/Users/ashmelev/Admin/gx10/docs/inference/vlm-response-cache.md`):

- The key is the SHA-256 of the namespace, the method, the path, the sorted query, and
  the semantic body.
- The semantic body of JSON is the canonical JSON: sorted keys, no spaces.
- The semantic body of multipart is the sorted list of the fields. A file field gives its
  name, its content type, its size, and the SHA-256 of its bytes. The boundary and the file
  name do not change the key.
- Identical requests at the same time are merged. One request goes to a host.
- The proxy stores only an HTTP 200 JSON answer of the expected form: a list `data` for
  embeddings, a list `instances` for SAM3 and Grounding DINO.
- The proxy does not store an answer that is larger than `cache.max_response_size`.
- The TTL is `cache.ttl_days`. The least recently used entries go when the stored size is
  larger than `cache.max_size`.
- The database stores the key and the answer. It does not store the request body or an
  image.

Differences from the gx10 cache:

- Each entry also stores the name of the host that made the answer.
- The store keeps the total size in memory and has an index on the creation time. The gx10
  store computes the total with a scan at each write.
- The TTL cleanup runs at most one time each 60 s. A read of an expired entry is a miss.
- The SQLite calls run in a worker thread, so a large entry does not stop the event loop.
- The database is on the internal disk, not on the T7 disk.
- Starlette 1.7 limits a multipart field without a file name to 1 MiB. A file part has no
  such limit. The clients send each image as a file part. A request with a larger plain
  field goes to a host without the cache (`X-Proxy-Cache: BYPASS`).

## Files

```text
proxies/
  AGENTS.md, CLAUDE.md -> AGENTS.md
  README.md, ChangeLog.md, ResearchLog.md, SMOKE_TESTS.md
  pyproject.toml, config.yaml, .gitignore
  model_proxy/
    __main__.py   the command line
    config.py     the configuration and its checks
    cache.py      the cache key, the SQLite store, the merge of identical requests
    pool.py       the hosts, the slots, the queue, the health probes
    tunnels.py    the SSH tunnels
    app.py        the HTTP routes
  tests/          unit tests with fake hosts
  scripts/smoke.py  a live check through a running proxy
  docs/plans/01_multi-host-model-proxy.md
```

The deployment document is `<workspace>/deploy/mbp2023/model-proxy.md` (workspace rule 27).

## Tests

- The configuration: a good file, each rule of the section "Configuration".
- The cache: canonical JSON and multipart, the same key as gx10, TTL, LRU, the host of an
  entry.
- The pool: a free slot, the wait for a slot, the order, the queue limit, the timeout, no
  host, the active models of a bootstrap host.
- The retry: a connection error, HTTP 429 and 503, the last answer when all hosts fail.
- The app: a miss and a hit for each route kind, the multipart boundary, a bypass, a
  passthrough request, a model that is not pooled, the merge of identical requests, an
  error that is not stored.
- The tunnels: the command line, a restart after an exit, the stop.

## Stages

1. The proxy, the unit tests, and a live test against gx10. For the live test of the pool,
   a scratch configuration has two host entries that both point to gx10 `:18082`. The
   documents and the port registry.
2. When the owner starts an RTX host: start the bootstrap launcher with SAM3 and both
   SigLIP2 models, enable the host, and run the live test again.
3. A comparison of the answers of gx10 and of an RTX host for the same images: SigLIP2
   cosine similarity, SAM3 boxes and scores. The owner then decides whether an index build
   can use answers from mixed hosts.

## Decisions

### D1. Approach (owner answer of 2026-09-29T10:02:42+0300)

- Options: A, a new Python proxy on the Mac based on the gx10 cache code; B, HAProxy or
  Caddy from Homebrew with a copy of the gx10 cache in front of it; C, more hosts behind the
  gx10 cache on port 18082.
- Decision: A.
- Rationale: A keeps the API of 18082 exactly and reuses a tested cache. B needs Lua or one
  port for each model to route `/v1/embeddings` by the JSON field `model`, and has two parts
  to run. C does not run on the Mac and changes a shared gx10 service.

### D2. Tunnels (owner answer of 2026-09-29T10:02:42+0300)

- Options: the proxy runs the SSH tunnels; the owner runs the tunnels; a private network
  without SSH.
- Decision: the proxy runs the SSH tunnels.
- Consequence: one command starts the proxy and all tunnels. The bootstrap stays on
  `127.0.0.1:18090` of each host.

### D3. Grounding DINO (owner answer of 2026-09-29T10:02:42+0300)

- Options: gx10 alone with the cache; a new Grounding DINO service in the bootstrap.
- Decision: gx10 alone with the cache.
- Consequence: no bootstrap change. Grounding DINO gets no speedup from the RTX hosts.

### D4. gx10 port and cache seed (owner answer of 2026-09-29T10:02:42+0300)

- Options: gx10 through `:18082` with an empty Mac cache; an import of the gx10 cache and
  gx10 through `:18081`; gx10 through `:18081` with an empty cache.
- Decision: gx10 through `:18082` with an empty Mac cache.
- Consequence: a request that goes to gx10 can hit the 55,066 gx10 entries of
  2026-09-29. A request that goes to an RTX host cannot hit them.

### D5. Ports

- The proxy listens on `127.0.0.1:18092`. The tunnels use the local ports 18191 to 18199.
- Rationale: on 2026-09-29 no process listened on these ports, and the Mac port registry
  listed none of them. The Mac keeps 28000 to 29999 free for the tunnels of the gx10
  deployments (`deploy/README.md`, port policy).

### D6. Cache location

- Decision: `~/.cache/svoe-vino-model-proxy/cache.sqlite3` on the internal disk.
- Rationale: the T7 disk is often busy with Postgres, enrichment, and match jobs. On
  2026-09-29 the internal disk had 184 GiB free.

## Risks

- Only parallel clients get a speedup. A client that sends one request at a time gains
  nothing, and a cloud host adds network time.
- The upload bandwidth of the home line can limit the RTX hosts. The benchmark of
  2026-09-28 measured 8.84 SAM3 requests per second on one RTX 4090. With a PNG of 2 to 3 MB,
  one host needs about 140 to 210 Mbit/s. The PNG size and the line speed were not measured.
- GB10 and RTX 4090 can give slightly different numbers for the same request, although
  both use SAM3 fp16 and SigLIP2 bf16. Stage 3 measures the difference. A cached answer
  stays the same for all later requests.
- The workbench reads its endpoints from `config.yaml`, not from the variables. The key of
  its cache `data/cache/models/` holds the endpoint URL, so a new URL makes each old record
  a miss. Three workbench scripts refuse a `SAM3_ENDPOINT` that is not the gx10 URL:
  `run_internal_profile_queue.py`, `benchmark_bulk_cache.py`, and
  `prepare_rerun_label_inputs.py`.
- The Mac stops serving while it sleeps. Run `caffeinate -ims -w <pid of the proxy>`
  during a long job.
- The bootstrap launcher stops when its SSH session closes (SIGHUP). Run it in `tmux` on
  the RTX host.
- SAM3 and both SigLIP2 models together on one RTX 4090 with 24 GiB were not measured. The
  gx10 numbers suggest about 9 GB (SAM3 fp16 about 3.8 GB, each SigLIP2 model about 2.5 GB).
