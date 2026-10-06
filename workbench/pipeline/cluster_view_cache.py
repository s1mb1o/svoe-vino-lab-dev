"""Reuse cluster JSON after catalogue, embedding, artifact, note, and rule checks."""

import os

from embedding_view_cache import EmbeddingViewCache
import clusters
import embeddings


class ClusterViewCache(EmbeddingViewCache):
    """Check every source file of one cluster view."""

    def _disk_inputs(self, signature):
        return super()._disk_inputs(signature[0]), signature[1]

    def _inputs(self, settings, name, job, queue):
        base = super()._inputs(settings, name, job, queue)
        names = ([name] if name is not None else
                 [label for label, entry, _ in settings.entries if entry is not None])
        files = []
        for label in names:
            directory = embeddings.entry_dir(settings.db_path, label)
            files.append(tuple(self._optional_file(os.path.join(directory, item))
                               for item in (clusters.CLUSTERS_FILE, clusters.NOTES_FILE,
                                            clusters.RULES_FILE)))
        return base, tuple(files)

    @staticmethod
    def _errors(view):
        return (EmbeddingViewCache._errors(view)
                or (view.get("status") or {}).get("current_error")
                or any(entry.get("status_error") for entry in view.get("embeddings", [])))


def no_job(directory):
    """Cluster responses have no embedding job field."""
    return None


CLUSTER_LIST_CACHE = ClusterViewCache(max_bytes=1024 * 1024, disk_kind="cluster-list-v1")
CLUSTER_DETAIL_CACHE = ClusterViewCache(disk_kind="cluster-detail-v1")
