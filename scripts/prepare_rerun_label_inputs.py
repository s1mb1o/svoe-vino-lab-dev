"""Prepare only missing active label inputs of the authorized NaFlex-1024 index.

The default is a read-only dry run. Execution needs --execute --gate FILE --output DIR
and SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3. The parent task MUST complete
all barcode comparisons and GPU checks before it writes the gate. This script does not
perform those checks or build an embedding index.

Gate JSON schema (all fields are required):
  recorded_at: an ISO-8601 time with a timezone, at most 10 minutes old
  embedding: gx10-siglip2-so400m-patch16-naflex-p1024
  database: the absolute database path
  config_sha256: the current configuration file hash
  sam3_endpoint: the exact SAM3_ENDPOINT URL, without a final slash
  comparisons_complete, no_active_measurements, gpu_preflight_passed,
  gpu_task_registered: true
  evidence: a nonempty list of existing absolute paths to parent-recorded evidence

The parent gate attests to benchmark completion, live process reconciliation, fresh
GPU memory checks, the GPU rules, and task registration. The shared measurement lock
also prevents another participating experiment from starting. A gate expires during
execution too. Use a new gate and output directory to continue unfinished sources.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import alternatives
import derive
import embeddings
from benchmark_barcode_crops import measurement_lock
from benchmark_barcode_variants import save_json

EMBEDDING = "gx10-siglip2-so400m-patch16-naflex-p1024"
GATE_MAX_AGE_S = 600
DEFAULT_STAGE1 = ROOT / "docs/reports/2026-09-27_barcode-variants/stage1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def missing_active(conn, db_path, embedding):
    """Return only absent full-photo label inputs of this exact embedding plan."""
    if embedding.name != EMBEDDING:
        raise ValueError("this helper only prepares %s" % EMBEDDING)
    _wines, sources = embeddings.read_inputs(conn, db_path)
    items = embeddings.plan_items(embedding, sources)
    selected = {}
    for (digest, view), item in items.items():
        steps = item["steps"]
        if (view != "label" or item["role"] != "full" or item["cut"] is not None
                or not steps or steps[0].get("step") != "segment"
                or steps[0].get("target") != "label"):
            continue
        # Preserve every existing cut, including manual and old-rule cuts. The raw
        # check also protects a cut whose image row is unexpectedly absent.
        present = conn.execute("SELECT 1 FROM image_derivative WHERE source_sha256 = ? "
                               "AND kind = 'label'", (digest,)).fetchone()
        if (present or alternatives.has_current_cut(conn, digest, "label")
                or alternatives.current_absence(conn, digest)):
            continue
        selected[digest] = {"sha256": digest, "path": sources[digest]["path"],
                            "role": item["role"], "embedding_hash": item["embedding_hash"]}
    return dict(sorted(selected.items()))


def internal_endpoint(value):
    """Restrict this authorized job to the documented internal SAM3 service."""
    if not isinstance(value, str) or not value:
        raise ValueError("--execute requires SAM3_ENDPOINT")
    value = value.rstrip("/")
    parts = urlsplit(value)
    if (parts.scheme not in ("http", "https") or parts.hostname != "192.168.86.14"
            or parts.port != 18081 or parts.path != "/upstream/sam3"
            or parts.username or parts.password or parts.query or parts.fragment):
        raise ValueError("SAM3_ENDPOINT MUST name the documented internal GX10 SAM3 service")
    return value


def check_gate(path, config_path, db_path, endpoint, now=None):
    """Validate the fresh parent-controlled attestation before any client or write."""
    gate = json.loads(Path(path).read_text())
    if not isinstance(gate, dict):
        raise ValueError("parent gate MUST be a JSON object")
    current = now or datetime.datetime.now(datetime.timezone.utc)
    recorded = datetime.datetime.fromisoformat(gate["recorded_at"])
    if recorded.tzinfo is None:
        raise ValueError("gate recorded_at MUST include a timezone")
    age = (current - recorded).total_seconds()
    if age < -5 or age > GATE_MAX_AGE_S:
        raise ValueError("parent preflight gate is stale or in the future")
    expected = {"embedding": EMBEDDING, "database": str(Path(db_path).resolve()),
                "config_sha256": sha256(config_path), "sam3_endpoint": endpoint}
    if any(gate.get(key) != value for key, value in expected.items()):
        raise ValueError("parent gate does not match the configuration, database, embedding or endpoint")
    flags = ("comparisons_complete", "no_active_measurements", "gpu_preflight_passed", "gpu_task_registered")
    if any(gate.get(key) is not True for key in flags):
        raise ValueError("parent gate does not confirm all completion and preflight requirements")
    evidence = gate.get("evidence")
    if (not isinstance(evidence, list) or not evidence
            or any(not isinstance(p, str) or not Path(p).is_absolute() or not Path(p).is_file()
                   for p in evidence)):
        raise ValueError("parent gate MUST reference existing absolute evidence paths")
    return gate


class GuardedSegmenter:
    """Check the parent gate before each detection request, including the fallback."""

    def __init__(self, client, check):
        self.client, self.check = client, check

    def instances(self, *args, **kwargs):
        self.check()
        return self.client.instances(*args, **kwargs)


def process_selected(conn, db_path, embedding, source, segmenter, check=lambda: None):
    """Process outside a transaction. Recheck active eligibility inside the write."""
    digest = source["sha256"]
    if conn.in_transaction:
        raise ValueError("label processing MUST start outside a database transaction")
    check()
    if missing_active(conn, db_path, embedding).get(digest) != source:
        return {"sha256": digest, "state": "skipped_changed", "warnings": []}
    if sha256(source["path"]) != digest:
        return {"sha256": digest, "state": "source_changed", "warnings": []}
    warnings = []
    result = alternatives.process_image(conn, db_path, digest, source["path"], "label",
                                        GuardedSegmenter(segmenter, check), warnings)
    if conn.in_transaction:
        conn.rollback()
        raise ValueError("process_image unexpectedly opened a write transaction")
    record = {"sha256": digest, "warnings": warnings}
    if result.unavailable:
        return dict(record, state="unavailable")
    if result.links or result.not_applicable:
        conn.execute("BEGIN IMMEDIATE")
        try:
            check()
            current = missing_active(conn, db_path, embedding).get(digest)
            if current != source:
                conn.rollback()
                return dict(record, state="skipped_concurrent_change")
            try:
                unchanged = sha256(source["path"]) == digest
            except OSError:
                unchanged = False
            if not unchanged:
                conn.rollback()
                return dict(record, state="source_changed")
            alternatives.write_processed_rows(conn, result)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        return dict(record, state="written" if result.links else "not_applicable",
                    reason=result.not_applicable)
    state = ("present" if result.present else "unreadable" if result.unreadable
             else "error" if result.errors else "no_label")
    return dict(record, state=state)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--execute", action="store_true", help="send SAM3 requests and write still-needed label rows")
    parser.add_argument("--gate", type=Path, help="fresh parent preflight JSON; required with --execute")
    parser.add_argument("--output", type=Path, help="new report directory; required with --execute")
    parser.add_argument("--stage1", type=Path, default=DEFAULT_STAGE1, help="locates the shared measurement.lock")
    args = parser.parse_args(argv)
    try:
        settings = embeddings.load_settings(str(args.config))
        embedding = settings.find(EMBEDDING)
        with contextlib.closing(embeddings.open_database(settings.db_path)) as conn:
            selected = missing_active(conn, settings.db_path, embedding)
        selection = {"embedding": EMBEDDING, "database": settings.db_path,
                     "config_sha256": sha256(args.config), "selected": list(selected.values()),
                     "selected_count": len(selected), "dry_run": not args.execute}
        if not args.execute:
            print(json.dumps(selection, ensure_ascii=False, indent=2))
            return 0
        if not args.gate or not args.output:
            raise ValueError("--execute requires --gate and --output")
        endpoint = internal_endpoint(os.environ.get("SAM3_ENDPOINT"))
        validate = lambda: check_gate(args.gate, args.config, settings.db_path, endpoint)
        gate = validate()  # No client exists before this check.
        output = args.output.resolve()
        protected = (ROOT / "data", ROOT / "runs")
        if any(output == p.resolve() or p.resolve() in output.parents or output in p.resolve().parents for p in protected):
            raise ValueError("report output MUST be outside production data and runs")
        with measurement_lock(args.stage1):
            validate()
            output.mkdir(parents=True, exist_ok=False)
            save_json(output / "selection.json", dict(selection, gate=gate))
            records, started = [], time.perf_counter()
            try:
                with contextlib.ExitStack() as resources:
                    client = derive.Sam3Client(endpoint=endpoint)
                    resources.callback(client.session.close)
                    uri = Path(settings.db_path).resolve().as_uri() + "?mode=rw"
                    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
                    resources.callback(conn.close)
                    conn.execute("PRAGMA foreign_keys = ON")
                    with (output / "results.jsonl").open("w") as stream:
                        for source in selected.values():
                            record = process_selected(conn, settings.db_path, embedding, source, client, validate)
                            records.append(record)
                            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                            stream.flush()
                            os.fsync(stream.fileno())
                            print(json.dumps(record, ensure_ascii=False), flush=True)
                            if record["state"] == "unavailable":
                                break
            finally:
                counts = Counter(r["state"] for r in records)
                save_json(output / "summary.json", {"selected": len(selected), "processed": len(records),
                    "counts": dict(counts), "unresolved_no_label": [r["sha256"] for r in records if r["state"] == "no_label"],
                    "unprocessed": [d for d in selected if d not in {r["sha256"] for r in records}],
                    "elapsed_s": time.perf_counter() - started})
            return 1 if any(r["state"] in ("unavailable", "unreadable", "error", "source_changed") for r in records) else 0
    except (OSError, ValueError, KeyError, sqlite3.Error, embeddings.ConfigError) as exc:
        print("label preparation refused: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
