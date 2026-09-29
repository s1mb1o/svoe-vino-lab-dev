#!/usr/bin/env python3
"""Build aggregate wine-style priors without copying review text."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path


DATASET_URL = "https://www.kaggle.com/datasets/zynicide/wine-reviews"
DATASET_LICENSE = "CC BY-NC-SA 4.0"

VARIETIES = {
    "Aligote": {"Aligoté", "Aligote"},
    "Cabernet Franc": {"Cabernet Franc"},
    "Cabernet Sauvignon": {"Cabernet Sauvignon"},
    "Chardonnay": {"Chardonnay"},
    "Gewurztraminer": {"Gewürztraminer", "Gewurztraminer"},
    "Malbec": {"Malbec"},
    "Merlot": {"Merlot"},
    "Muscat": {"Muscat", "Moscato", "Muscat Canelli", "White Muscat"},
    "Pinot Gris": {"Pinot Gris", "Pinot Grigio"},
    "Pinot Noir": {"Pinot Noir"},
    "Riesling": {"Riesling"},
    "Rkatsiteli": {"Rkatsiteli"},
    "Sangiovese": {"Sangiovese"},
    "Saperavi": {"Saperavi"},
    "Sauvignon Blanc": {"Sauvignon Blanc"},
    "Syrah": {"Syrah", "Shiraz"},
    "Tempranillo": {"Tempranillo", "Tinta de Toro"},
    "Viognier": {"Viognier"},
}

DATASET_TO_CANONICAL = {
    dataset_name: canonical
    for canonical, dataset_names in VARIETIES.items()
    for dataset_name in dataset_names
}

AROMA_PATTERNS = {
    "apple_pear": re.compile(r"\b(?:apple|pear|quince)s?\b"),
    "citrus": re.compile(r"\b(?:citrus|lemon|lime|grapefruit|tangerine|orange peel|citrus peel)s?\b"),
    "cocoa_coffee": re.compile(r"\b(?:cocoa|coffee|chocolate|mocha)\b"),
    "dark_berries": re.compile(r"\b(?:blackberr(?:y|ies)|blueberr(?:y|ies)|black currant|blackcurrant|cassis|black cherr(?:y|ies)|plum)s?\b"),
    "floral": re.compile(r"\b(?:floral|flower|flowers|blossom|violet|rose|honeysuckle|acacia|lavender)s?\b"),
    "herbs_greens": re.compile(r"\b(?:herb|herbal|grass|grassy|mint|eucalyptus|sage|thyme|leafy|green pepper)s?\b"),
    "honey_dried_fruit": re.compile(r"\b(?:honey|honeyed|raisin|fig|date|dried fruit)s?\b"),
    "mineral": re.compile(r"\b(?:mineral|chalk|chalky|flint|flinty|saline|slate|stony|wet stone)s?\b"),
    "oak_vanilla": re.compile(r"\b(?:oak|oaked|barrel|barrique|vanilla|toast|toasted|cedar)s?\b"),
    "red_berries": re.compile(r"\b(?:raspberr(?:y|ies)|strawberr(?:y|ies)|red currant|cranberr(?:y|ies)|red cherr(?:y|ies))\b"),
    "spices": re.compile(r"\b(?:spice|spicy|pepper|peppery|cinnamon|clove|anise|cardamom)s?\b"),
    "stone_fruit": re.compile(r"\b(?:peach|apricot|nectarine)s?\b"),
    "tropical": re.compile(r"\b(?:pineapple|mango|passion fruit|lychee|tropical fruit)s?\b"),
}

STRUCTURE_PATTERNS = {
    "body": [
        (5, re.compile(r"\b(?:massive|monumental|huge)[ -](?:body|bodied)\b")),
        (4, re.compile(r"\b(?:full[ -]bodied|full body|dense|weighty|opulent)\b")),
        (3, re.compile(r"\b(?:medium[ -]bodied|medium body)\b")),
        (2, re.compile(r"\b(?:light[ -]bodied|light body|lean body)\b")),
    ],
    "acidity": [
        (5, re.compile(r"\b(?:searing|razor[ -]sharp|bracing) acidity\b")),
        (4, re.compile(r"\b(?:high|bright|vibrant|lively) acidity\b|\b(?:crisp|racy|zesty)\b")),
        (3, re.compile(r"\b(?:medium|moderate|balanced|fresh) acidity\b")),
        (2, re.compile(r"\b(?:low|soft|mild) acidity\b")),
    ],
    "tannin": [
        (5, re.compile(r"\b(?:massive|huge|powerful) tannins?\b")),
        (4, re.compile(r"\b(?:firm|grippy|chewy|robust|strong|structured) tannins?\b")),
        (3, re.compile(r"\b(?:medium|moderate|fine[ -]grained) tannins?\b")),
        (2, re.compile(r"\b(?:soft|silky|supple|gentle) tannins?\b")),
    ],
}

STRONG_OAK = re.compile(r"\b(?:heavily oaked|strong oak|new oak|oak-driven)\b")
FRUIT_KEYS = {"apple_pear", "citrus", "dark_berries", "red_berries", "stone_fruit", "tropical"}


def first_score(text: str, rules: list[tuple[int, re.Pattern[str]]]) -> int | None:
    for score, pattern in rules:
        if pattern.search(text):
            return score
    return None


def clamp_level(value: float) -> int:
    return max(1, min(5, round(value)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--generated-on", default=date.today().isoformat())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_counts: dict[str, int] = defaultdict(int)
    aroma_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    structure_values: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))

    with args.input_csv.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"description", "variety"}
        if not required.issubset(reader.fieldnames or []):
            raise SystemExit("The CSV must contain description and variety columns.")

        for row in reader:
            canonical = DATASET_TO_CANONICAL.get((row.get("variety") or "").strip())
            description = (row.get("description") or "").strip().lower()
            if not canonical or not description:
                continue
            sample_counts[canonical] += 1
            matched_aromas = {key for key, pattern in AROMA_PATTERNS.items() if pattern.search(description)}
            for key in matched_aromas:
                aroma_counts[canonical][key] += 1
            for dimension, rules in STRUCTURE_PATTERNS.items():
                score = first_score(description, rules)
                if score is not None:
                    structure_values[canonical][dimension].append(score)
            fruit_count = len(matched_aromas & FRUIT_KEYS)
            structure_values[canonical]["fruit"].append(2 if fruit_count == 0 else min(5, fruit_count + 2))
            structure_values[canonical]["oak"].append(4 if STRONG_OAK.search(description) else 3 if "oak_vanilla" in matched_aromas else 1)

    varieties = {}
    for canonical in sorted(VARIETIES):
        sample_count = sample_counts[canonical]
        if not sample_count:
            continue
        aromas = {
            key: round(count / sample_count, 4)
            for key, count in sorted(aroma_counts[canonical].items())
        }
        structure = {}
        for dimension in ("body", "acidity", "tannin", "fruit", "oak"):
            values = structure_values[canonical][dimension]
            if not values:
                continue
            mean = sum(values) / len(values)
            structure[dimension] = {
                "level": clamp_level(mean),
                "mean": round(mean, 3),
                "observationCount": len(values),
            }
        varieties[canonical] = {
            "sampleCount": sample_count,
            "aromas": aromas,
            "structure": structure,
        }

    result = {
        "source": {
            "name": "Wine Reviews, winemag-data-130k-v2.csv",
            "url": DATASET_URL,
            "license": DATASET_LICENSE,
            "generatedOn": args.generated_on,
            "method": "Aggregate descriptor frequencies by grape variety. No review text or critic score is included.",
        },
        "varieties": varieties,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
