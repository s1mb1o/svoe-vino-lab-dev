#!/usr/bin/env python3
"""A rotation test with several reference vectors of one catalogue image.

Owner messages of 2026-09-29T01:34:10+0300 and 01:34:20. `rotation_similarity.py` compares
a rotated image with one vector: the indexed `full` vector. This script gives the
reference side one vector for each angle from 0° to `--ref-max` in steps of `--ref-step`:
the index image on white, rotated counter-clockwise with the method of
`rotation_similarity.py`. The query side is the same as in `rotation_similarity.py`: 0° to
355° in steps of `--step`, on white and on black. The score of a query is the maximum
cosine over the reference vectors. The script also writes the cosine to the one indexed
vector.

The script saves all vectors in `<out>/vectors/<entry>.npz` and the images in
`<out>/reference/` and `<out>/images/`. It does not change the catalogue index.

The rank is optimistic. The other wines of the index keep their indexed `full` vectors
only, and only this wine gets the rotated reference vectors.

    python3 scripts/rotation_multiref.py --out docs/reports/rotation-similarity-2026-09-29/multiref
    python3 scripts/rotation_multiref.py --out docs/reports/rotation-similarity-2026-09-29/multiref --plots-only
"""

import argparse
import collections
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotation_similarity as rs  # noqa: E402  (it adds pipeline/ to sys.path)
import rotation_similarity_plots as plots  # noqa: E402
from rotation_similarity import build_embeddings, embeddings  # noqa: E402


def best_by_wine(scores, inverse, count):
    """Return the best score of each wine: `inverse` maps each item to its wine."""
    best = np.full(count, -2.0)
    np.maximum.at(best, inverse, scores)
    return best


def embed_all(backend, pngs, batch):
    """Embed in requests of `batch` images. No request holds one image alone: NaFlex p256
    gives another vector for a request of one image (report of 2026-09-29)."""
    got = []
    for start in range(0, len(pngs), batch):
        chunk = pngs[start:start + batch]
        if len(chunk) == 1 and start:
            got.append(backend.embed([pngs[start - 1], chunk[0]])[1])
        else:
            got.extend(backend.embed(chunk))
    return got


def run(args):
    for name in ("vectors", "reference", "images"):
        os.makedirs(os.path.join(args.out, name), exist_ok=True)
    settings = embeddings.load_settings()
    loaded = {name: rs.load_entry(settings, name) for name in args.entries}
    conn = embeddings.open_database(settings.db_path)
    wines, sources = embeddings.read_inputs(conn, settings.db_path)
    conn.close()
    wine, digest = rs.pick_wine(wines, sources, loaded, args.slug)
    sha_to_slug = {}
    for other in wines:
        for _, sha in other["columns"]:
            if sources.get(sha, {}).get("role") == "full":
                sha_to_slug.setdefault(sha, other["slug"])
    print("wine %s (%s), main image %s" % (wine["slug"], wine["name"], digest), flush=True)

    steps = rs.full_steps(loaded[args.entries[0]][0])
    bases, resize_step = rs.base_images(sources[digest], steps)
    scale = rs.scale_of(bases["white"].size, resize_step)
    white = rs.BACKGROUNDS["white"]
    ref_angles = list(range(0, args.ref_max + 1, args.ref_step))
    query_angles = list(range(0, 360, args.step))
    pngs = []
    for angle in ref_angles:
        picture = rs.rotated(bases["white"], angle, white, scale)
        picture.save(os.path.join(args.out, "reference", "white_%03d.png" % angle))
        pngs.append(embeddings.png_bytes(picture))
    for background, color in rs.BACKGROUNDS.items():
        for angle in query_angles:
            picture = rs.rotated(bases[background], angle, color, scale)
            picture.save(os.path.join(args.out, "images", "%s_%03d.png" % (background, angle)))
            pngs.append(embeddings.png_bytes(picture))

    rows = []
    for name, (embedding, directory, index, vectors) in loaded.items():
        backend = build_embeddings.OpenAIBackend(embedding)
        got = rs.normalise(embed_all(backend, pngs, args.batch))
        reference = got[:len(ref_angles)]
        queries, offset = {}, len(ref_angles)
        for background in rs.BACKGROUNDS:
            queries[background] = got[offset:offset + len(query_angles)]
            offset += len(query_angles)
        stored = rs.normalise(vectors[rs.row_of(index, digest)["row"]])
        np.savez(os.path.join(args.out, "vectors", name + ".npz"),
                 reference_angles=np.asarray(ref_angles),
                 reference=reference.astype(np.float32),
                 query_angles=np.asarray(query_angles),
                 query_white=queries["white"].astype(np.float32),
                 query_black=queries["black"].astype(np.float32),
                 stored=stored.astype(np.float32))
        print("%s: the 0° reference vector against the indexed vector, cosine %.6f"
              % (name, reference[0] @ stored), flush=True)

        slugs, item_rows = rs.wine_rows(index, sha_to_slug)
        catalogue = rs.normalise(vectors[item_rows])
        own = slugs == wine["slug"]
        other_slugs, inverse = np.unique(slugs[~own], return_inverse=True)
        for background in rs.BACKGROUNDS:
            query = queries[background]
            multi = query @ reference.T
            single = query @ stored
            own_best = (query @ catalogue[own].T).max(axis=1)
            other_scores = query @ catalogue[~own].T
            for i, angle in enumerate(query_angles):
                best = best_by_wine(other_scores[i], inverse, len(other_slugs))
                top = int(best.argmax())
                own_multi = max(own_best[i], multi[i].max())
                rows.append({
                    "entry": name, "background": background, "angle": angle,
                    "cosine_single": round(float(single[i]), 6),
                    "cosine_multi": round(float(multi[i].max()), 6),
                    "best_reference_angle": ref_angles[int(multi[i].argmax())],
                    "rank_single": int((best > own_best[i]).sum()) + 1,
                    "rank_multi": int((best > own_multi).sum()) + 1,
                    "best_other_cosine": round(float(best[top]), 6),
                    "best_other_slug": str(other_slugs[top])})
        print("%s: %d reference and %d query images" % (name, len(ref_angles),
                                                         2 * len(query_angles)), flush=True)

    with open(os.path.join(args.out, "results.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    meta = {"wine": {key: wine[key] for key in ("slug", "name", "producer", "category")},
            "main_sha256": digest, "reference_angles": ref_angles,
            "reference_background": "white", "query_angles": query_angles, "scale": scale,
            "score": "the maximum cosine over the reference vectors",
            "rank": "optimistic: the other wines keep their indexed full vectors only",
            "vectors": "vectors/<entry>.npz: reference_angles, reference, query_angles, "
                       "query_white, query_black, stored (all L2-normalised float32)",
            "entries": {name: loaded[name][0].base_url for name in args.entries}}
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("wrote %s" % os.path.join(args.out, "results.csv"), flush=True)


def draw(directory):
    """Draw the charts of the maximum cosine, apart from the charts of one vector."""
    with open(os.path.join(directory, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    data = collections.defaultdict(lambda: collections.defaultdict(dict))
    with open(os.path.join(directory, "results.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            entry = row["entry"].replace(plots.PREFIX, "")
            data[entry][row["background"]][int(row["angle"])] = (
                float(row["cosine_multi"]), int(row["rank_multi"]))
    angles = meta["query_angles"]
    band = (meta["reference_angles"][0], meta["reference_angles"][-1])
    count = len(meta["reference_angles"])
    step = meta["reference_angles"][1] - meta["reference_angles"][0]
    text = ("Вино: «%s». Опорные векторы: белый фон, поворот %d°–%d°, шаг %d° (%d шт.). "
            "Сходство — максимум по ним." % (meta["wine"]["name"], band[0], band[1], step,
                                             count))
    footer = " Белый фон, %d°–%d°: запрос = опорное изображение (1.000)." % band
    ylabel = "максимум косинуса по %d опорным векторам" % count
    plt = plots.plt
    plt.rcParams.update({"font.size": 9.5, "text.color": plots.INK,
                         "axes.labelcolor": plots.INK2})
    images = {background: plots.load_images(directory, background, angles)
              for background in plots.BG_NAMES}
    plots.chart_by_model(data, meta, directory, images["white"],
                         title="{family}: сходство повёрнутой бутылки с %d опорными "
                               "векторами (%d°–%d°)" % ((count,) + band),
                         text=text, ylabel=ylabel, rank=False, band=band, footer=footer)
    for background in plots.BG_NAMES:
        plots.chart_models(data, meta, directory, background, images[background],
                           title="{family}: %d опорных векторов (%d°–%d°), бутылка на "
                                 "{background}" % ((count,) + band),
                           text=text, ylabel=ylabel, band=band,
                           footer=footer if background == "white" else "")
    print("wrote the charts to %s" % directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the output directory")
    parser.add_argument("--slug", help="the wine; default: the first wine that fits")
    parser.add_argument("--ref-max", type=int, default=45, help="the last reference angle")
    parser.add_argument("--ref-step", type=int, default=5, help="the reference angle step")
    parser.add_argument("--step", type=int, default=5, help="the query angle step")
    parser.add_argument("--batch", type=int, default=8, help="images per request")
    parser.add_argument("--entries", nargs="*", default=list(rs.ENTRIES))
    parser.add_argument("--plots-only", action="store_true",
                        help="draw the charts from an earlier run; send no request")
    args = parser.parse_args(argv)
    if not args.plots_only:
        run(args)
    draw(args.out)


if __name__ == "__main__":
    main()
