# Model proxy rules

Read the workspace `CLAUDE.md` and the project rules in
[../workbench/AGENTS.md](../workbench/AGENTS.md) before you change this directory. The rules
of the owner messages and of `../workbench/ACTIVE_WORK.md` apply here too.

1. The proxy MUST keep the API of the gx10 cache `http://192.168.86.14:18082` for the pooled
   routes. A client changes only its endpoint variables.
2. The proxy MUST NOT change the body of a request or of an answer.
3. The health probe of a `llama-swap` host MUST use `GET /running`. A request below
   `/upstream/<model>/` on gx10 loads the model, also `GET /upstream/<model>/health`.
4. The cache key function MUST stay equal to the function of the gx10 cache. The test
   `test_key_equals_the_gx10_key` checks it.
5. The proxy MUST bind `127.0.0.1` by default.
6. Do not commit the virtual environment, a cache database, or a log.
7. The deployment document is `<workspace>/deploy/mbp2023/model-proxy.md`. Do not put a
   deployment document into this directory.
8. The owner starts the proxy in a terminal, and long jobs use it. Do not stop a proxy that
   listens on port 18092 without the approval of the owner. For a test, start a second
   proxy with a scratch configuration on another port and with a scratch cache path.
9. A live test sends a real request only to a model that runs on gx10 now. `GET /running`
   shows the models that run. Ask the owner before a request loads a model.

## Tests

Run the unit tests with the virtual environment of this directory:

```sh
.venv/bin/python -m unittest discover -s tests -t .
```

## Gotchas

- `httpx.Response(json=...)` reads its body at once. A test answer of `httpx.MockTransport`
  therefore cannot give `aiter_raw()`: it raises `StreamConsumed`. The passthrough uses
  `aiter_bytes()`, which works with a real host and with a test answer.
- A multipart request of httpx is a stream. In a test, read its body with
  `response.request.read()`, not with `response.request.content`.
- Starlette 1.7 limits a multipart field without a file name to 1 MiB. A file part has no
  such limit. A request with a larger plain field goes to a host without the cache.
- The store opens with the real clock and removes each entry that is older than the TTL.
  A test with fake times MUST use a long TTL, or the entries expire at the open.
