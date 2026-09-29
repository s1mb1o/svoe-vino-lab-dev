# Smoke Tests

Run each test in this directory. A test that sends a model request names the models it
calls. By default, call only a model that runs on gx10 (`GET /running`).

## MP1. Start

1. `.venv/bin/python -m model_proxy --check` prints the hosts and exits with 0.
2. Start `.venv/bin/python -m model_proxy`.
3. The log names each enabled host with `up` or `down` and the reason.
4. `curl -s http://127.0.0.1:18092/_proxy/health` returns `{"status":"ok"}`.

## MP2. One miss and one hit for each model family

1. `.venv/bin/python scripts/smoke.py`.
2. Expected: `PASS` for each family that runs on gx10, `IDLE` for each other family, exit
   code 0. A `PASS` line names the host of the miss and shows a hit of a few milliseconds.

## MP3. Passthrough

1. `curl -s -D - -o /dev/null http://127.0.0.1:18092/v1/models`.
2. Expected: HTTP 200, `x-proxy-cache: BYPASS`, `x-proxy-host: gx10`.
3. `curl -s http://127.0.0.1:18092/running` returns the gx10 list `running`.

## MP4. Bypass

1. Send one SAM3 request two times with `Cache-Control: no-cache`.
2. Expected: `x-proxy-cache: BYPASS` both times, and `x-gx10-cache: BYPASS` from gx10.

## MP5. Two hosts and a real tunnel, without an RTX host

1. Write a scratch configuration with a scratch cache path and another port, for example
   18094. It has two `llama-swap` hosts with `models: [sam3]` and 2 slots each: `gx10` with
   `url: http://192.168.86.14:18082`, and `gx10-ssh` with
   `ssh: {target: ashmelev@192.168.86.14, local_port: 18191, remote_port: 18082}`.
2. Start the proxy with `--config <scratch file>`.
3. Send 8 parallel SAM3 requests with 8 new images, then the same 8 again.
4. Expected: the first pass spreads 4 and 4 over the two hosts, with all `MISS`. The second
   pass gives 8 `HIT`.
5. Stop the proxy with SIGTERM. Expected: the `ssh` process stops, and port 18191 is free.

## MP6. An RTX host

1. Start the bootstrap on the RTX host (deployment document, section "RTX 4090 host").
2. Enable the host in `config.yaml`, then start the proxy.
3. `/_proxy/status` shows the host up, its tunnel `running`, and its active models.
4. Send 16 parallel SAM3 requests with new images. Expected: both gx10 and the RTX host
   answer, and `X-Proxy-Host` names both.
5. Stop the bootstrap on the host, and keep the tunnel. Expected: within 15 s (the probe
   interval and the probe timeout), `/_proxy/status` shows the host down. Until then, a
   request to the host fails at once and goes to gx10.
