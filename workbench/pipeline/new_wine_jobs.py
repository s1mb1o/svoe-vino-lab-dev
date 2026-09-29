"""The background index jobs of the new wines of the lab server.

`POST /api/wine` creates the wine and answers at once. A job then runs `update_index` of
`new_wine_workflow.py` in a daemon thread: the incremental build of `new_wine_embedding`
and the verification of the items of the wine. The card of the wine reads the job with
`GET /api/wine-index`; the button `Retry` starts it again with `POST /api/wine-index`.

The jobs stay in memory. A restart of the server removes them. The build process
`build_embeddings.py` has its own session, so it continues after a restart. Two jobs do
not build at the same time: `rebuild_on_run.build` waits for the lock of the build.

Read docs/plans/84_background-new-wine-index.md.
"""
import threading
import time

import new_wine_workflow
import rebuild_on_run

INDEXING = "indexing"
ACTIVE = "active"
FAILED = "failed"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _print(message):
    print(message, flush=True)


class IndexJobs:
    """The index jobs of one server process, by wine slug."""

    def __init__(self, build=rebuild_on_run.build, log=_print):
        self.build = build
        self.log = log
        self._lock = threading.Lock()
        self._jobs = {}

    def get(self, slug):
        """Return a copy of the job of `slug`, or None."""
        with self._lock:
            job = self._jobs.get(slug)
            return dict(job) if job else None

    def states(self):
        """Return {slug: {state, error}} of each job, for `GET /api/dataset`."""
        with self._lock:
            return {slug: {"state": job["state"], "error": job.get("error")}
                    for slug, job in self._jobs.items()}

    def start(self, slug, selected, config_path):
        """Start the job of `slug` with the `selected` index of
        `new_wine_workflow.selected_index`. A job in the state `indexing` stays, and no
        second thread starts. Return a copy of the job."""
        with self._lock:
            job = self._jobs.get(slug)
            if job and job["state"] == INDEXING:
                return dict(job)
            job = {"slug": slug, "name": selected[1], "state": INDEXING, "error": None,
                   "started_at": _now(), "finished_at": None}
            self._jobs[slug] = job
            threading.Thread(target=self._run, args=(slug, selected, config_path),
                             name="wine-index-%s" % slug, daemon=True).start()
            return dict(job)

    def _run(self, slug, selected, config_path):
        started = time.monotonic()
        name = selected[1]

        def log(message):
            self.log("wine index %s: %s" % (slug, message))

        try:
            index, _warning = new_wine_workflow.update_index(
                selected, config_path, slug, build=self.build, log=log)
        except Exception as exc:  # noqa: BLE001 - the card needs an end state for each error
            index = {"name": name, "state": FAILED, "error": "internal error: %s" % exc}
        with self._lock:
            job = self._jobs[slug]
            job.update(index)
            job["finished_at"] = _now()
        log("%s %s in %.1f s%s" % (name, index["state"], time.monotonic() - started,
                                   ": %s" % index["error"] if index.get("error") else ""))
