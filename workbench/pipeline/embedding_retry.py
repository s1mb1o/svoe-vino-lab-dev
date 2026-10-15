"""Repair a missing cut for one failed embedding item.

The build owns its normal index lock. SAM3 runs before the short database write.
An existing cut, including a manual cut, keeps its pixels and settings.
"""
from contextlib import closing

import alternatives
import derive
import embeddings
import labdb


def repair_cut(embedding, db_path, digest, view, log, make_segmenter=None):
    """Retry missing segmentation. A vector failure with a cut needs no SAM3 call."""
    with closing(labdb.connect(db_path)) as conn:
        _wines, sources = embeddings.read_inputs(conn, db_path)
        item = embeddings.plan_items(embedding, sources).get((digest, view))
        if item is None:
            return
        steps = item["steps"]
        if not steps or steps[0]["step"] != "segment" or item["cut"] is not None:
            return
        target = steps[0]["target"]
        kind = "label" if target == "label" else "full"
        log("request", images=1, message="Retry missing %s cut" % target)
        # A previous model answer can contain no label. A refresh asks the model again.
        segmenter = make_segmenter() if make_segmenter else derive.Sam3Client(refresh=True)
        warnings = []
        result = alternatives.process_image(conn, db_path, digest, sources[digest]["path"],
                                            kind, segmenter, warnings)
        for warning in warnings:
            log("warning", message=warning)
        if not (result.links or result.present or getattr(result, "not_applicable", None)
                or getattr(result, "turned_off", False)):
            raise embeddings.ItemError("; ".join(warnings) or embeddings.NO_CUT[target])
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Keep a cut or an owner setting that another operation wrote during SAM3.
            if not alternatives.has_current_cut(conn, digest, kind) and not (
                    kind == "label" and alternatives.label_cut_off(conn, digest)):
                alternatives.write_processed_rows(conn, result)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
