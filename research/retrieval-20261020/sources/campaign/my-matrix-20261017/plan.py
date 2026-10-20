"""Enumerate the finite matrix requested by the owner."""
from pathlib import Path
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
import itertools
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import OUT, dump, sha

POOLS={"u":"Uniform", "5a":"Fractional whitespace 0.1", "5b":"Fractional whitespace 0",
       "6a":"Fractional whitespace 0.1; label 2", "6b":"Fractional whitespace 0; label 2",
       "6c":"Whole empty patch 0.1; label 2", "6d":"Whole empty patch 0; label 2"}
QUERIES={"original":"Original segmented query", "iou":"Maximum-IoU rotation", "min5":"Skip rotations below 5 degrees",
         "card5":"Skip rotations near a cardinal angle", "crop":"Tight crop without rotation",
         "mean-iou":"Normalized mean of original and IoU vectors", "mean-card5":"Normalized mean of original and cardinal-guard vectors"}
ANGLES={"zero":[0],"cardinal":[0,90,180,270],"rot5":list(range(0,360,5))}
LABELS=json.loads((OUT / "labels-20261017/profiles.json").read_text())


def policies():
    result={}
    merges=[("mean25","mean",.25),("mean50","mean",.5),("mean75","mean",.75),("max","max",None),("rrf","rrf",None)]
    def add(key,merge,alpha,mode="always",bt=None,lt=None):
        result[key]={"merge":merge,"bottle_weight":alpha,"mode":mode,"bottle_threshold":bt,"label_threshold":lt}
    for key,merge,alpha in merges:
        add("always-"+key,merge,alpha)
    for threshold,code in ((.005,"005"),(.01,"010"),(.02,"020")):
        for key,merge,alpha in merges:
            add("gate-"+key+"-"+code,merge,alpha,"gate",threshold,threshold)
    for bt,lt in itertools.product((.005,.01,.02),repeat=2):
        if bt==lt:continue
        for key,merge,alpha in (("mean50","mean",.5),("max","max",None)):
            add(f"gate-{key}-b{bt:.3f}-l{lt:.3f}",merge,alpha,"gate",bt,lt)
    for mode in ("conflict","pin"):
        for key,merge,alpha in merges:
            add(mode+"-"+key+"-010",merge,alpha,mode,.01,.01)
    assert len(result)==42
    return result


def definitions():
    bottles={f"b-{p}-{q}-{a}":{"pool":p,"query":q,"angles":a}
             for p,q,a in itertools.product(POOLS,QUERIES,ANGLES)}
    labels={f"l-{g}-{a}":{"geometry":g,"angles":a} for g,a in itertools.product(LABELS,ANGLES)}
    return bottles,labels,policies()


def main():
    bottles,labels,fusions=definitions()
    assert len(bottles)==147 and len(labels)==24
    value={"version":1,"created_at":datetime.now(ZoneInfo("Europe/Moscow")).isoformat(timespec="seconds"),
        "assignments":3409,"distinct_images":3031,"positive_assignments":2970,"negative_assignments":430,"no_match_assignments":9,"query_sha256":sha(HERE / "queries.json"),
        "pooling":POOLS,"query_geometry":QUERIES,"reference_angles":ANGLES,"label_geometry":LABELS,
        "bottles":bottles,"labels":labels,"policies":fusions,
        "counts":{"bottle":147,"label":24,"fusion_policies":42,"pairs":3528,"fusion_variants":148176,"single_space_controls":171,"total_variants":148347},
        "scope":"Cross all listed bottle configurations, standard-pooling label configurations, and the fixed fusion policies. This finite matrix contains every level listed here. Label pooling stays standard as in experiment 7. Bottle pooling varies as in experiment 9.",
        "label_reference_augmentation":"Apply each reference angle after the selected original or IoU label preparation. Include the cached zero-degree vectors. Rotate RGB on white with expanded canvases. Preserve source pixels and close-up resize rules.",
        "query_means":"Normalize the sum of the two unit query vectors within each pooling profile.",
        "wine_score":"Take the maximum cosine across all source images and retained angles for each wine.",
        "mean":"Use the listed bottle weight and its complement for label scores. A candidate absent from one reference space keeps its available score.",
        "max":"Merge unchanged scores. Deduplicate wine_slug and keep its larger original cosine.",
        "rrf":"Sum 1/(60+rank) from both complete wine lists.",
        "confidence":"Use unrounded top-1 minus top-2 wine cosine. A gap at least its space threshold passes. If both pass, compare gap/threshold. A tie uses the bottle space.",
        "conflict":"If both confident spaces have different winners, use the selected merge rule.",
        "pin":"If a space is selected by confidence, place its winner first. Fill positions 2 to 10 from the merged ranking. Store explicit ordinal ranks. Scores can be non-monotonic across the pinned winner and tail.",
        "missing_label":"Use the bottle list. Keep all assignments in the denominator. Label-only controls return no answer.",
        "ties":"Use wine_slug in ascending order.",
        "storage":"Store full metrics and per-case Top-10 wine identities for every variant in compact pair files. Store accepted ranks for all 3409 assignments. Export the leading 100 variants to Workbench Runs at completion.",
        "timing":"Accuracy sweep. Cached matrix operations do not measure end-to-end or parallel inference latency.",
        "reserve":"Keep 20 GiB available on GX10. A new model load needs 28 GiB available. Keep the native worker within an 8 GiB CUDA allocation. Preserve 6c/6d and all resident services.",
        "plan_sha256":sha(Path(__file__))}
    path=HERE / "manifest.json"
    if path.exists():
        previous=json.loads(path.read_text());value["created_at"]=previous["created_at"];assert value==previous,"Do not change the fixed matrix."
    else:dump(path,value)
    with (HERE / "variants.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["variant_id","kind","bottle_id","label_id","policy_id"])
        for b in bottles:w.writerow(["single-"+b,"bottle",b,"",""])
        for l in labels:w.writerow(["single-"+l,"label","",l,""])
        for b,l,p in itertools.product(bottles,labels,fusions):w.writerow([b+"__"+l+"__"+p,"fusion",b,l,p])
    lines=["# Full my combination matrix","", "The cohort has 3409 assignments and 3031 distinct images. It has 2970 positive, 430 negative, and 9 no_match assignments.","",
           "## Bottle factors","", "| Factor | Levels |", "|---|---|",
           "| Pooling | "+"; ".join(k+": "+v for k,v in POOLS.items())+" |",
           "| Query | "+"; ".join(k+": "+v for k,v in QUERIES.items())+" |",
           "| Reference angles | zero; cardinal; rot5 |","", "## Label factors","",
           "Use standard NaFlex p512 pooling for both label query and label reference vectors.",
           "Use all eight geometries from 7a to 7h.","Use zero, cardinal, and rot5 reference angle sets.","",
           "## Fusion policies","", "| Policy | Merge | Bottle weight | Mode | Bottle gap | Label gap |","|---|---|---|---|---|---|"]
    for k,v in fusions.items():lines.append("| "+" | ".join(str(x) for x in (k,v["merge"],v["bottle_weight"],v["mode"],v["bottle_threshold"],v["label_threshold"]))+" |")
    lines += ["", "## Counts", "", "147 bottle configurations × 24 label configurations × 42 fusion policies = 148176 fusion variants.",
              "Add 147 bottle controls and 24 label controls.", "Total: 148347 variants.", "", "Read variants.csv for every variant ID.",
              "Read manifest.json for exact rules and factor definitions."]
    (HERE / "ENUMERATION.md").write_text("\n".join(lines)+"\n")
    print(value["counts"])


if __name__=="__main__":main()
