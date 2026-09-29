# Model proxy

The model proxy runs on the Mac. It accepts the SAM3, Grounding DINO, and SigLIP2 requests
of the lab code, and it sends each request to one of several work hosts: gx10 and RTX 4090
hosts. It keeps a cache of the answers on the Mac.

The proxy keeps the API of the gx10 cache `http://192.168.86.14:18082`. A client changes
only its endpoint variables:

```sh
export SIGLIP2_ENDPOINT=http://127.0.0.1:18092
export GROUNDING_DINO_ENDPOINT=http://127.0.0.1:18092/upstream/grounding-dino-base
export SAM3_ENDPOINT=http://127.0.0.1:18092/upstream/sam3
```

The design, the decisions, and the risks are in
[docs/plans/01_multi-host-model-proxy.md](docs/plans/01_multi-host-model-proxy.md). The
deployment on the Mac is in
[`<workspace>/deploy/mbp2023/model-proxy.md`](../../deploy/mbp2023/model-proxy.md).

## Install

Run these commands in this directory. The proxy needs Python 3.12 and `uv`.

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml
```

## Start and stop

```sh
.venv/bin/python -m model_proxy                 # config.yaml of this directory
.venv/bin/python -m model_proxy --verbose       # also one log line for each pooled request
```

The proxy listens on `127.0.0.1:18092`. It probes each enabled host before it serves. It
also starts one SSH tunnel for each enabled host with an `ssh` entry.

Stop the proxy with Ctrl-C or with SIGTERM. The proxy then stops its SSH tunnels too. A
SIGKILL leaves the `ssh` processes running.

The Mac stops serving while it sleeps. During a long job, keep the Mac awake:

```sh
caffeinate -ims -w "$(lsof -bnPw -t -iTCP:18092 -sTCP:LISTEN)"
```

## How the proxy works

- **Pooled routes.** `POST /v1/embeddings` (the model is the JSON field `model`),
  `POST /upstream/sam3/{segment,segment_multi,segment_verify,segment_point}`, and
  `POST /upstream/<model>/detect`. A route is pooled only when an enabled host lists its
  model in `config.yaml`.
- **Passthrough.** Each other request goes to gx10 without a change, for example
  `GET /v1/models`, `GET /running`, and `GET /upstream/sam3/health`. The proxy does not
  cache such a request.
- **Dispatch.** A pooled request goes to an eligible host with a free slot. `slots` of a
  host is the number of parallel requests for each model. When each slot is busy, the
  request waits in the queue of its model. A faster host frees its slots sooner, so it
  takes more requests.
- **Retry.** After a connection error, a timeout, or HTTP 429, 502, 503, or 504, the
  request goes to the next eligible host. One request tries at most `limits.attempts`
  hosts.
- **Health.** gx10 (`kind: llama-swap`): `GET /running`, which loads no model. A bootstrap
  host (`kind: bootstrap`): `GET /health`, whose list `active_models` names the models that
  the host serves now.
- **Cache.** The key and the rules are the rules of the gx10 cache: JSON key order, the
  multipart boundary, and the file name do not change the key. Identical requests at the
  same time go to a host one time. Only an HTTP 200 JSON answer with a list `data` or
  `instances` is stored. The database is
  `~/.cache/svoe-vino-model-proxy/cache.sqlite3`: TTL 30 days, at most 10 GiB.
- **Grounding DINO** goes to gx10 alone, because the bootstrap has no Grounding DINO
  service.

## Headers

| Header | Direction | Meaning |
|---|---|---|
| `X-Proxy-Cache` | answer | `HIT`, `MISS`, or `BYPASS` |
| `X-Proxy-Host` | answer | the host that made the answer; a hit names the host of the stored answer |
| `Age` | answer | the age of a stored answer in seconds, on a hit |
| `X-GX10-Cache` | answer | the state of the gx10 cache, for an answer from gx10 |
| `Cache-Control: no-cache` | request | skip the proxy cache and the gx10 cache; the answer is not stored |
| `X-GX10-Cache: bypass` | request | the same as `Cache-Control: no-cache` |

## Status

```sh
curl -s http://127.0.0.1:18092/_proxy/health
curl -s http://127.0.0.1:18092/_proxy/status | python3 -m json.tool
```

`/_proxy/status` shows each host (up or down, the reason, the tunnel), the slots in use,
the requests, the errors, and the mean time of each model, the queue of each model, and the
cache counters.

## Add an RTX host

1. Start the bootstrap on the host. Read the section "RTX 4090 host" of the deployment
   document.
2. Connect one time with `ssh root@<ip>` from the Mac, so that the host key is in
   `~/.ssh/known_hosts`. The tunnel uses `BatchMode=yes` and cannot ask for a password or
   for a key confirmation.
3. In `config.yaml`, set `enabled: true` for the host, or copy the `kit` entry with a new
   `name`, `ssh.target`, and the next free `ssh.local_port` (18192 to 18199).
4. Run `.venv/bin/python -m model_proxy --check`, then start the proxy again.
5. Check that `/_proxy/status` shows the host up.

## Commands

All commands run in this directory.

Read-only checks:

```sh
# The unit tests. They use fake hosts and send no network request.
.venv/bin/python -m unittest discover -s tests -t .

# Check the configuration and print the hosts.
.venv/bin/python -m model_proxy --check
```

The live check sends real requests to the models through a running proxy. By default it
calls only the models that run on gx10 now. `--load-models` also calls the other models, so
llama-swap loads them. Ask the owner before you use `--load-models`.

```sh
.venv/bin/python scripts/smoke.py --proxy http://127.0.0.1:18092
```

This command changes data: it deletes each cache entry. Stop the proxy first.

```sh
.venv/bin/python -m model_proxy --purge
```

## Files

| Path | Content |
|---|---|
| `config.yaml` | the listen address, the cache, the limits, and the hosts |
| `model_proxy/app.py` | the HTTP routes: pooled, passthrough, and status |
| `model_proxy/pool.py` | the hosts, the slots, the queue, and the health probes |
| `model_proxy/cache.py` | the cache key, the SQLite store, and the merge of identical requests |
| `model_proxy/tunnels.py` | the SSH tunnels |
| `model_proxy/config.py` | the configuration and its checks |
| `scripts/smoke.py` | the live check through a running proxy |
| `tests/` | the unit tests |
