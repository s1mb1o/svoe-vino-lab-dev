"""Freeze seven finite experiment families before new scoring."""
import itertools
from settings import *

def main():
    cohorts = {name: dict(context_sha256=sha(ROOT / folder / "context.json"),
                           queries_sha256=sha(ROOT / (folder + "/queries.json" if name == "my" else "queries.json")))
               for name, folder in FOLDERS.items()}
    families = [
        dict(id="1", name="Independent reference and query pooling", reference_pools=POOLS, query_pools=POOLS,
             query_modes=QUERIES, galleries=list(GALLERIES), axial_union=[False, True],
             conditions=7*7*7*3*2, same_pool_controls=7*7*3*2),
        dict(id="2", name="Nonlinear foreground weights", gamma=[.5, 1., 2.], background=[0., .1],
             label_boost=[1., 2.], coverage=["legacy", "exact"], query_modes=QUERIES,
             galleries=list(GALLERIES), axial_union=[False, True]),
        dict(id="3", name="Label boost", gamma=[1.], background=[0., .1],
             label_boost=[1., 1.25, 1.5, 2., 3.], coverage=["legacy", "exact"],
             query_modes=QUERIES, galleries=list(GALLERIES), axial_union=[False, True]),
        dict(id="4", name="Crop margins and exact NaFlex coverage", reference_margin=[0., .02, .05, .10],
             query_margin=[0., .02, .05, .10], pools=["u", "6b"], query_modes=QUERIES,
             galleries=list(GALLERIES), axial_union=[False], margin_unit="Fraction of the tight foreground width and height on each edge. Add white pixels outside the source canvas.",
             coverage_control="Compare every fractional profile with float masks processed by the same NaFlex resize and patchify steps as RGB."),
        dict(id="5", name="Axial and cardinal Cartesian views", pools=POOLS, query_modes=QUERIES,
             axial_angles=list(range(-30, 31, 5)), in_plane_angles=[0, 90, 180, 270],
             galleries=["cartesian", "rot5-plus-cartesian"],
             note="Reuse existing yaw-zero cardinal views and nonzero-yaw zero-degree views. Build the 36 missing pairs per renderable source. Retain original gallery coverage."),
        dict(id="6", name="NaFlex patch budgets", reference_budget=[256, 512, 1024], query_budget=[256, 512, 1024],
             pools=["u", "6b"], query_modes=QUERIES, galleries=list(GALLERIES), axial_union=[False, True],
             pilot="Require finite normalized vectors, exact mask geometry, padding exclusion, memory limits, and uniform-head agreement at every budget before the full pass.",
             latency="Record preprocessing, vision and pooling time, batch throughput, and serial warmed model latency on fixed pilot inputs."),
        dict(id="7", name="Reference score aggregation", pools=POOLS, query_modes=QUERIES,
             galleries=list(GALLERIES), axial_union=[False, True], aggregation=["max", "top2-mean", "top3-mean"],
             definition="Aggregate vector scores within each wine across the full reference gallery. Use the available vector count when it is below k. Apply lexical wine ties.")]
    # Fixed fusion anchors test the new bottle scores against both known label controls.
    # This is a family comparison. It does not claim a new full Cartesian fusion sweep.
    fusion = dict(labels=["l-7f-rot5", "l-7g-cardinal"],
                  policies=["always-mean50", "always-mean75", "gate-mean50-010", "pin-max-010", "always-rrf"])
    value = dict(version=1, created_at=now(), owner_request="do it all", cohorts=cohorts,
                 checkpoint="cc24074f717b612951c2dead130904ab9b65a81e", model="google/siglip2-so400m-patch16-naflex",
                 baseline="siglip2-p512-rot5-seg", local_reranking=False,
                 families=families, profiles=profiles(), aliases=ALIASES, fixed_fusion_anchors=fusion,
                 source_files_immutable=True, score_full_catalogue=True,
                 scope="Enumerate each stated family. Do not multiply unrelated new axes. Publish every bottle condition and ten fixed label-fusion anchors.",
                 validation="Use a fresh validation cohort only after checking image overlap against saved benchmark inputs. Keep prior-evaluated complements separate.")
    path=HERE / "protocol.json"
    if path.exists():
        old=read(path);value["created_at"]=old["created_at"];assert value==old, "Frozen protocol changed"
    else:
        dump(path,value)
    (HERE / "README.md").write_text("# Retrieval extension\n\nThe owner requested all seven proposed checks on 2026-10-18.\nThe frozen protocol is in `protocol.json`.\nAll tests use the frozen `my` and `my-failed-2` cohorts.\nThe tests use no local re-ranking.\nEach family has a finite grid.\nThe grid does not multiply unrelated new axes.\nEvery bottle condition has ten fixed label-fusion comparisons.\nRepeated conditions reuse the same score result.\nAll scores use the full catalogue before Top-10 selection.\nPending conditions have no published accuracy.\nThe report remains provisional until both scoring and independent audit are complete.\n")
    dump(HERE / "status.json", dict(state="Prepare frozen inputs and cached-vector tests", at=now(), complete=False, families=7))
    print("Frozen seven experiment families;",len(profiles()),"pooling profiles", flush=True)

if __name__=="__main__": main()
