"""Synchronize safe website changes and publish a checked local matcher catalogue."""

import argparse
from contextlib import closing
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "website-import"
RESULT = "sync-result.json"


class SyncError(ValueError):
    """A synchronization cannot continue safely."""


class Busy(SyncError):
    """Another website operation holds the lock."""


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    temporary.replace(path)


def operation_locked(work=None):
    """Probe the lock without trusting a PID that the OS can reuse."""
    try:
        with (Path(work or WORK) / "operation.lock").open("rb") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
    except FileNotFoundError:
        return False
    return False


class OperationLock:
    """Hold one cross-process lock for CLI, startup, and UI website operations."""

    def __init__(self, work=None):
        self.work = Path(work or WORK)
        self.stream = None

    def __enter__(self):
        self.work.mkdir(parents=True, exist_ok=True)
        self.stream = (self.work / "operation.lock").open("a+")
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Recognize a job that an older server started without this lock.
            job = read_json(self.work / "job.json") or {}
            pid = job.get("pid")
            if job.get("lock") != "flock" and type(pid) is int and pid > 0 and pid != os.getpid():
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise Busy("a website operation runs: PID %s" % pid)
        except (BlockingIOError, Busy, PermissionError) as exc:
            self.stream.close()
            self.stream = None
            raise Busy("a website operation already runs") from exc
        return self

    def fileno(self):
        return self.stream.fileno()

    def __exit__(self, *_):
        # Do not LOCK_UN: a UI child can still hold the inherited descriptor.
        self.stream.close()


def check_config(config):
    raw = config.get("website_sync", {})
    if not isinstance(raw, dict):
        raise SyncError("website_sync MUST be a mapping")
    unknown = set(raw) - {"on_startup", "matcher_embeddings", "matcher_output"}
    if unknown:
        raise SyncError("unknown website_sync option: %s" % sorted(unknown)[0])
    if type(raw.get("on_startup", False)) is not bool:
        raise SyncError("website_sync.on_startup MUST be a boolean")
    names = raw.get("matcher_embeddings", [])
    if (not isinstance(names, list) or any(not isinstance(x, str) or not x.strip() for x in names)
            or len(set(names)) != len(names)):
        raise SyncError("website_sync.matcher_embeddings MUST hold distinct embedding names")
    output = raw.get("matcher_output")
    if output is not None and (not isinstance(output, str) or not output.strip()):
        raise SyncError("website_sync.matcher_output MUST be a path")
    if raw.get("on_startup") and (not names or not output):
        raise SyncError("startup synchronization needs matcher_embeddings and matcher_output")
    return raw


@dataclass
class Options:
    config_path: str
    db_path: str
    python: str
    names: list
    output: Path


def options(config_path):
    import embeddings
    path, config, database = embeddings.read_config(config_path)
    raw = check_config(config)
    if not raw.get("matcher_embeddings") or not raw.get("matcher_output"):
        raise SyncError("configure website_sync.matcher_embeddings and matcher_output first")
    settings = embeddings.load_settings(path)
    for name in raw["matcher_embeddings"]:
        try:
            settings.find(name)
        except KeyError as exc:
            raise SyncError("unknown matcher embedding: %s" % name) from exc
    rootdir = Path(config.get("rootdir") or ROOT.parents[1])
    output = Path(os.path.abspath(rootdir / os.path.expanduser(raw["matcher_output"])))
    output = output.parent.resolve() / output.name
    catalog = Path(database).resolve().parent
    # The publication pointer MUST NOT replace a source path or an ancestor of it.
    if output == catalog or output in catalog.parents or catalog in output.parents:
        raise SyncError("matcher_output MUST be outside the source catalogue")
    if output.exists() and not output.is_symlink():
        raise SyncError("matcher_output exists and is not a publication symlink: %s" % output)
    return Options(path, database, settings.python or sys.executable,
                   raw["matcher_embeddings"], output)


def commands(opts, directory):
    """Return fixed commands. A configuration cannot supply shell command text."""
    shared = ["--config", opts.config_path]
    commands = [[sys.executable, str(ROOT / "pipeline/import_website.py"),
                 "--db", opts.db_path, *shared, "--prepare", str(directory), "--automatic"]]
    for name in opts.names:
        commands.append([opts.python, str(ROOT / "pipeline/build_embeddings.py"),
                         *shared, "--name", name])
    for name in opts.names:
        commands.append([opts.python, str(ROOT / "pipeline/build_clusters.py"),
                         *shared, "--name", name])
    return commands


def complete_indexes(opts, database=None, catalog=None):
    """Require complete vectors for the selected snapshot, including new wines."""
    import embeddings
    settings = embeddings.load_settings(opts.config_path)
    with closing(embeddings.open_database(database or opts.db_path)) as connection:
        _, sources = embeddings.read_inputs(connection, database or opts.db_path)
    report = {}
    for name in opts.names:
        directory = (Path(catalog) / "embeddings" / name if catalog else
                     Path(embeddings.entry_dir(opts.db_path, name)))
        if not catalog and embeddings.running_pid(str(directory)):
            raise SyncError("an embedding build still runs: %s" % name)
        items = embeddings.plan_items(settings.find(name), sources)
        index = embeddings.read_index(str(directory)) or {}
        records = {(x["source_sha256"], x["view"]): x for x in index.get("items", [])}
        if (not items or len(records) != len(index.get("items", [])) or set(records) != set(items)
                or any(records[key].get("embedding_hash") != item["embedding_hash"]
                       for key, item in items.items())):
            raise SyncError("matcher embedding %s is incomplete or stale; keep the previous publication" % name)
        report[name] = len(items)
    return report


def publish(opts, directory):
    """Build an immutable release. Replace the local publication pointer in one step."""
    import catalog_copy
    complete_indexes(opts)
    release = Path(directory) / "matcher-catalog"
    copied = catalog_copy.copy_catalog(opts.config_path, release, opts.names, images=False)
    # Recheck against the frozen database, not the live database that can change.
    complete_indexes(opts, str(release / "catalog.sqlite3"), release)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = opts.output.with_name(".%s.%d" % (opts.output.name, os.getpid()))
    try:
        temporary.symlink_to(release.resolve(), target_is_directory=True)
        if opts.output.exists() and not opts.output.is_symlink():
            raise SyncError("matcher_output is no longer a publication symlink")
        temporary.replace(opts.output)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(copied, published=str(opts.output))


class Runner:
    """Stop the active child before the parent releases its operation lock."""

    def __init__(self, log):
        self.log = log
        self.child = None
        self.stopped = False

    def stop(self, *_):
        # A signal can arrive while Popen creates a child. Check this flag after
        # assignment. Do not raise from a handler and leave that child untracked.
        self.stopped = True

    def check_stopped(self):
        if self.stopped:
            raise InterruptedError("synchronization stopped")

    def wait(self):
        while True:
            if self.stopped:
                if self.child.poll() is None:
                    try:
                        os.killpg(self.child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        self.child.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(self.child.pid, signal.SIGKILL)
                        self.child.wait()
                self.check_stopped()
            try:
                return self.child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass

    def __call__(self, command):
        self.check_stopped()
        self.child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                      stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = self.wait()
            self.check_stopped()
        finally:
            self.child = None
        if code:
            raise SyncError("stage failed with exit status %d; read run.log" % code)


def synchronize(opts, work=None, run_command=None, publish_catalog=None):
    """Keep manual choices in diff.json. A failed stage prevents publication."""
    import import_website
    if not import_website.COMPARE_ENABLED:
        raise SyncError(import_website.COMPARE_DISABLED)
    work = Path(work or WORK)
    with OperationLock(work):
        run = time.strftime("%Y%m%dT%H%M%S")
        directory = work / run
        directory.mkdir()  # Never reuse a report from a previous operation.
        result = {"run": run, "ok": False, "stage": "import", "config": opts.config_path}
        write_json(directory / RESULT, result)
        write_json(work / "job.json", {"run": run, "phase": "sync", "pid": os.getpid(),
                                       "lock": "flock",
                                       "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        with (directory / "run.log").open("a", buffering=1) as log:
            runner = Runner(log)
            saved = {sig: signal.signal(sig, runner.stop) for sig in (signal.SIGTERM, signal.SIGINT)}
            try:
                for command in commands(opts, directory):
                    runner.check_stopped()
                    script = Path(command[1]).stem
                    result["stage"] = script
                    write_json(directory / RESULT, result)
                    print("sync: %s %s" % (script, command[-1]), file=log)
                    print("%s: %s" % (run, script), flush=True)
                    (run_command or runner)(command)
                diff = read_json(directory / "diff.json")
                if not isinstance(diff, dict) or not diff.get("automation_checked_at"):
                    raise SyncError("the safe import did not finish; matcher data stay unchanged")
                result.update(automatic=diff.get("automatic_result", {}),
                              pending_conflicts=len(diff["conflicts"]), pending_changes=len(diff["changes"]),
                              stage="publish")
                write_json(directory / RESULT, result)
                print("sync: validating and publishing matcher data", file=log)
                runner.check_stopped()
                result["matcher"] = (publish_catalog or publish)(opts, directory)
                result.update(ok=True, stage="done")
                print("sync: complete; %d conflicts need a decision" % result["pending_conflicts"], file=log)
            except Exception as exc:
                result["error"] = str(exc)
                print("error: %s" % exc, file=log)
                raise
            finally:
                write_json(directory / RESULT, result)
                for sig, handler in saved.items():
                    signal.signal(sig, handler)
        return result


def start_on_launch(config, config_path):
    """Start a detached job only when the explicit startup option is true."""
    if not check_config(config).get("on_startup", False):
        return None
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK / "startup.log").open("ab") as log:
        process = subprocess.Popen([sys.executable, str(ROOT / "scripts/sync_website.py"),
                                    "--config", os.path.abspath(config_path)], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    threading.Thread(target=process.wait, daemon=True).start()
    return process


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="validate configuration; make no requests or writes")
    args = parser.parse_args(argv)
    try:
        opts = options(args.config)
        if args.dry_run:
            print(json.dumps({"commands": commands(opts, WORK / "<run>"),
                              "matcher_output": str(opts.output), "deploy": False}, indent=1))
            return 0
        result = synchronize(opts)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        print("Review pending choices at http://127.0.0.1:8168/dataset/website-import")
        return 0
    except Busy as exc:
        print("busy: %s" % exc, file=sys.stderr)
        return 3
    except Exception as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
