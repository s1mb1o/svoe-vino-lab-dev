"""Queue image fact extraction. GET requests never create inference work."""

import re
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit

import attribute_facts
import labdb

ROUTE = "/api/dataset-attributes"
JSON = "application/json; charset=utf-8"
MAX_BODY = 4096


def handles(route):
    return route == ROUTE


def respond(server, method, path, body=None):
    if urlsplit(path).path != ROUTE:
        return 404, {"error": "not found"}, JSON, "no-store"
    if method != "POST":
        return 405, {"error": "the attribute queue answers POST only"}, JSON, "no-store"
    if not isinstance(body, dict) or set(body) - {"sha256", "scope", "action"}:
        return 400, {"error": "expected sha256 or scope"}, JSON, "no-store"
    action = body.get("action")
    if action is not None and (
        action not in ("pause", "resume", "cancel") or set(body) != {"action"}
    ):
        return (
            400,
            {"error": "action MUST be pause, resume, or cancel"},
            JSON,
            "no-store",
        )
    sha, scope = body.get("sha256"), body.get("scope", "missing")
    if sha is not None and (
        not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha)
    ):
        return 400, {"error": "sha256 MUST be a lowercase SHA-256"}, JSON, "no-store"
    if scope not in ("missing", "all"):
        return 400, {"error": "scope MUST be missing or all"}, JSON, "no-store"
    try:
        with closing(labdb.connect(server.db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if action in ("pause", "resume"):
                conn.execute(
                    "UPDATE image_attribute_settings SET paused=? WHERE id=1",
                    (int(action == "pause"),),
                )
                queued = 0
            elif action == "cancel":
                conn.execute(
                    "UPDATE image_attribute_job SET state='failed',error='Cancelled',generation=generation+1 WHERE state='pending'"
                )
                queued = 0
            else:
                queued = attribute_facts.enqueue(conn, sha, scope)
            conn.commit()
    except ValueError as exc:
        return 404, {"error": str(exc)}, JSON, "no-store"
    except (labdb.SchemaError, sqlite3.Error) as exc:
        return 503, {"error": str(exc)}, JSON, "no-store"
    return (
        202,
        {
            "queued": queued,
            "message": ("Image fact queue " + action + ". Current calls may finish.")
            if action
            else f"{queued} image(s) queued for background extraction",
        },
        JSON,
        "no-store",
    )
