"""Freeze matching reference cuts. Do not reuse display-image derivatives."""
import argparse
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image

from profiles import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library-dataset',type=Path,required=True)
    parser.add_argument('--catalogue-pack',type=Path,required=True)
    parser.add_argument('--queries',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    assert not args.out.exists(),'Use a new output directory'
    frozen=json.loads(args.library_dataset.read_text())
    with zipfile.ZipFile(args.catalogue_pack) as archive:
        cards=[json.loads(line) for line in archive.read('wines.jsonl').splitlines()]
        pack=json.loads(archive.read('manifest.json'))
    slugs=sorted(row['wine_slug'] for row in cards)
    assert len(slugs)==len(set(slugs))==pack['wine_count']==2093
    original={row['wine_slug']:row for row in frozen['catalogue']}
    selected=[original[slug] for slug in slugs]
    # Verify the entire source set before creating prepared files.
    for row in selected:
        path=Path(row['path'])
        if row['view']!='package' or digest(path)!=row['sha256']:
            raise ValueError('Changed or non-segmented reference: '+row['wine_slug'])
        with Image.open(path) as image:
            if 'A' not in image.getbands() or image.getchannel('A').getextrema()[1]==0:
                raise ValueError('Missing reference bottle mask: '+row['wine_slug'])
    queries=json.loads(args.queries.read_text())
    for row in queries:
        if digest(Path(row['abs_path']))!=row['image_sha256']:raise ValueError('Query checksum mismatch')
    args.out.mkdir(parents=True)
    rows=[]
    for row in selected:
        target=args.out/row['sha256'];target.mkdir(exist_ok=True)
        with Image.open(row['path']) as image:
            image=image.convert('RGBA')
            if max(image.size)>1024:
                scale=1024/max(image.size)
                image=image.resize(tuple(max(1,round(v*scale)) for v in image.size),Image.Resampling.BILINEAR)
            mask=image.getchannel('A');rgb=Image.new('RGB',image.size,'white');rgb.paste(image,mask=mask)
            rgb_path=target/'rgb.png';mask_path=target/'mask.png'
            rgb.save(rgb_path);mask.save(mask_path)
        rows.append(dict(wine_slug=row['wine_slug'],source_path=row['path'],
            source_sha256=row['sha256'],original_sha256=row['original_sha256'],
            rgb=str(rgb_path),rgb_sha256=digest(rgb_path),mask=str(mask_path),mask_sha256=digest(mask_path)))
    shutil.copy2(args.queries,args.out/'queries.json')
    result=dict(format='base-naflex-p224-comparison-inputs',wine_count=len(slugs),slugs=slugs,
        references=rows,queries=len(queries),query_file_sha256=digest(args.queries),
        source_dataset_sha256=digest(args.library_dataset),source_pack_sha256=digest(args.catalogue_pack),
        source_pack_version=pack['version'],reference_views=1,
        reference_preparation='Original alpha cut; maximum long edge 1024; composite on white.',
        query_preparation='Original bytes; mobile bottle segmentation on device.',reranking=False,barcode=False)
    (args.out/'inputs.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(wines=len(rows),queries=len(queries),manifest_sha256=digest(args.out/'inputs.json'))))


if __name__=='__main__':main()
