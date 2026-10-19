#!/usr/bin/env python3
"""Prepare catalogue-only bottle/label polygons without evaluation-image overlap."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def polygon(mask):
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError('empty mask')
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < 64:
        raise ValueError('mask is too small')
    approximation = cv2.approxPolyDP(contour, .001 * cv2.arcLength(contour, True), True)
    if len(approximation) < 3:
        raise ValueError('polygon has fewer than three vertices')
    return approximation[:, 0, :]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue-sources', type=Path, required=True)
    parser.add_argument('--exclude-queries', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    excluded = set()
    for path in args.exclude_queries:
        text = path.read_text()
        rows = json.loads(text) if text.lstrip().startswith('[') else [json.loads(s) for s in text.splitlines() if s]
        excluded.update(row['image_sha256'] for row in rows)
    sources = json.loads(args.catalogue_sources.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    records, omitted = [], []
    for source_sha, source in sorted(sources.items()):
        try:
            if source_sha in excluded:
                raise ValueError('evaluation image hash')
            owners = source.get('main_owners', [])
            if not owners:
                raise ValueError('not a main catalogue reference')
            cuts = source.get('cuts', {})
            if not all(cuts.get(key) for key in ('package', 'label')):
                raise ValueError('missing package or label annotation')
            source_path = Path(source['path'])
            if digest(source_path) != source_sha:
                raise ValueError('source checksum mismatch')
            with Image.open(source_path) as original:
                if original.getexif().get(274, 1) != 1:
                    raise ValueError('non-canonical EXIF orientation')
                image = original.convert('RGB')
            width, height = image.size
            masks, cut_hashes = [], []
            for kind in ('package', 'label'):
                cut = cuts[kind]
                cut_path = Path(cut['path'])
                if digest(cut_path) != cut['sha256']:
                    raise ValueError('cut checksum mismatch')
                with Image.open(cut_path) as opened:
                    if 'A' not in opened.getbands():
                        raise ValueError('cut has no alpha channel')
                    alpha = np.asarray(opened.getchannel('A'))
                left, top, right, bottom = cut['box']
                if not (0 <= left < right <= width and 0 <= top < bottom <= height):
                    raise ValueError('cut box is outside original image')
                if alpha.shape != (bottom - top, right - left):
                    raise ValueError('cut dimensions do not match source-coordinate box')
                mask = np.zeros((height, width), dtype=np.uint8)
                mask[top:bottom, left:right] = alpha >= 128
                masks.append(mask)
                cut_hashes.append(cut['sha256'])
            label_area = int(masks[1].sum())
            if label_area >= .95 * masks[0].sum():
                raise ValueError('label annotation covers nearly the complete object')
            if np.logical_and(masks[0], masks[1]).sum() < .7 * label_area:
                raise ValueError('label annotation is outside the package')
            lines = []
            for class_id, mask in enumerate(masks):
                points = polygon(mask).astype(float)
                points[:, 0] /= width
                points[:, 1] /= height
                lines.append(str(class_id) + ' ' + ' '.join(f'{v:.7f}' for v in points.ravel()))
            group = min(owner['wine_slug'] for owner in owners)
            split = 'val' if int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 10 == 0 else 'train'
            image_dir, label_dir = args.out / 'images' / split, args.out / 'labels' / split
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            target = image_dir / (source_sha + '.jpg')
            image.save(target, quality=95, subsampling=0)
            annotation = label_dir / (source_sha + '.txt')
            annotation.write_text('\n'.join(lines) + '\n')
            records.append(dict(source_sha256=source_sha, source=str(source_path), split=split,
                                wine_group=group, cut_sha256=cut_hashes, size=[width, height],
                                image=str(target.relative_to(args.out)), image_sha256=digest(target),
                                annotation_sha256=digest(annotation)))
        except (OSError, ValueError, KeyError) as error:
            omitted.append(dict(source_sha256=source_sha, reason=str(error)))
    config = dict(path=str(args.out.resolve()), train='images/train', val='images/val',
                  names={0: 'bottle', 1: 'label'})
    # JSON is a valid YAML representation. Keep generated data configuration explicit.
    (args.out / 'dataset.yaml').write_text(json.dumps(config, indent=2) + '\n')
    report = dict(catalogue_sources_sha256=digest(args.catalogue_sources),
                  excluded_evaluation_images=len(excluded), count=len(records),
                  splits=dict(Counter(r['split'] for r in records)),
                  evaluation_overlap=sorted({r['source_sha256'] for r in records} & excluded),
                  records=records, omitted=omitted)
    (args.out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','omitted')}))
    print('Omissions:',dict(Counter(r['reason'] for r in omitted)))
    if not records or report['evaluation_overlap'] or report['splits'].get('val',0) < 30:
        raise RuntimeError('The segmentation dataset does not pass the preparation gate.')


if __name__ == '__main__':
    main()
