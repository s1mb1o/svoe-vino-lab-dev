# Change Log

## 2026-09-29

- Created the model proxy (plan 01, owner messages of 2026-09-29T08:17:32+0300 and the
  owner answers of 2026-09-29T10:02:42+0300). One process on `127.0.0.1:18092` accepts
  the SAM3, Grounding DINO, and SigLIP2 requests with the API of the gx10 cache
  `http://192.168.86.14:18082`.
- A pooled request goes to an eligible host with a free slot. A waiting request stays in
  the queue of its model. After a connection error, a timeout, or HTTP 429, 502, 503, or
  504, the request goes to the next host.
- The health probe of gx10 is `GET /running`, which loads no model. The probe of a bootstrap
  host reads `active_models` of `GET /health`. A down host is probed every 2 s.
- The proxy starts, restarts, and stops one `ssh -N -L` tunnel for each enabled host with an
  `ssh` entry. The tunnel ends on the Mac use the ports 18191 to 18199.
- The answer cache uses the key function of the gx10 cache. It stores the host of each
  answer, keeps its total size in memory, and runs its SQLite calls in a worker thread.
- Each other request goes to gx10 unchanged and is streamed back.
- `config.yaml`: gx10 through `:18082` with SAM3, three Grounding DINO models, and five
  SigLIP2 models; the RTX 4090 `kit` with SAM3 and the two SigLIP2 models, disabled.
- `scripts/smoke.py`: one miss and one hit for each model family through a running proxy.
  It calls only the models that run on gx10, unless `--load-models` is given.
- Tests: 63 unit tests pass (`.venv/bin/python -m unittest discover -s tests -t .`), five
  runs in a row, 1.6 s for each run. `ruff check --select E,F,W,B --line-length 100` passes.
- Live test with a scratch configuration on port 18093 and a scratch cache:
  `scripts/smoke.py` passed for SAM3 (`segment_multi`, miss 605 ms on gx10, hit 2 ms) and
  for SigLIP2 NaFlex with 512 patches (miss 249 ms, hit 2 ms). Grounding DINO and SigLIP2
  fixed-512 did not run on gx10, so the check did not call them (state `IDLE`).
  `GET /v1/models` (51 models) and `GET /running` passed through to gx10.
- Live test of the pool with a scratch configuration on port 18094: gx10 direct and gx10
  through a real SSH tunnel (`ashmelev@192.168.86.14`, local 18191 to remote 18082), each
  with 2 slots. 8 parallel SAM3 requests went 4 to each host in 4.9 s; the same 8 requests
  again were 8 hits in 0.02 s. The first probe of the tunnel host failed 22 ms after the
  `ssh` start; the probe 2 s later found the host up. SIGTERM stopped the proxy and the
  `ssh` process, and port 18191 was free again.
- No RTX 4090 host was tested: `kit` (178.130.51.88) and `zelda` (111.88.124.23) did not
  answer on port 22 on 2026-09-29.
