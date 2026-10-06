# Selective OCR testing

The implementation is in the native matcher. The Workbench calls its standard
`/v1/match` route. Read `matcher/docs/selective-ocr.md` at the repository root for
the trigger, backend contracts, deadline, and audit fields.

Run the focused local tests from the Workbench root. Use the project environment.
These tests use generated images, fake services, and temporary catalogs. They send
no image to a LAN or cloud model service.

```sh
PYTHON=/Users/ashmelev/.venvs/svoe-vino-lab/bin/python bash scripts/test_selective_ocr.sh
```

For a live matcher, first set `SIGLIP2_ENDPOINT`, `SAM3_ENDPOINT`, `VLM_ENDPOINT`,
and `QR_SCANNER_ENDPOINT`.
The selected reader needs its documented prerequisite. Tesseract needs the `rus`
and `eng` languages. VLM needs `OCR_VLM_ENDPOINT`. PaddleOCR needs
`PADDLEOCR_ENDPOINT`. The custom reader needs `OCR_HTTP_ENDPOINT`.
The example has all four entries. Only the selected entry resolves its environment.
Live model calls require the normal memory preflight. A live run sends input images
to its configured OCR service. Set file timestamps as required by `internal/AGENTS.md`
before a benchmark sends file copies.

Start an isolated matcher on port 28100 from the Workbench root. This command does
not restart an existing service. Set `matcher.pipeline` in a copy of the example to
select another backend before starting it.

```sh
cd ..
SVOE_VINO_MATCHER_CONFIG=matcher/config.selective-ocr.example.yaml \
  /Users/ashmelev/.venvs/svoe-vino-lab/bin/python -m uvicorn matcher.app:app \
  --host 127.0.0.1 --port 28100
```

`workbench/config.selective-ocr.example.yaml` provides a remote pipeline entry for
this matcher. Add it to a separate Workbench configuration. The shared
`workbench/config.yaml` is unchanged. Preserve frozen benchmark scripts and output.
Use a new output directory for new measurements.
