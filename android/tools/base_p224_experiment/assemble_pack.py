"""Assemble the separate Base experiment without query images or answers."""
import argparse
import json
from pathlib import Path
import shutil

from profiles import MODEL,REVISION,digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('references','positions','segmenter','validation','p512-validation','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    refs=json.loads(a.references.read_text());segmenter=json.loads(a.segmenter.read_text());validation=json.loads(a.validation.read_text())
    assert refs['complete'] and validation['passed'] and segmenter['numerical_validation']['passed']
    p512_validation=json.loads(a.p512_validation.read_text());assert p512_validation['passed']
    assert [r['number'] for r in refs['conditions']]==[1,2,3,4]
    a.out.mkdir(parents=True);files={}
    def include(source,name=None):
        name=name or source.name
        if name in files:
            assert files[name]['sha256']==digest(source);return name
        assert Path(name).name==name
        shutil.copy2(source,a.out/name)
        files[name]=dict(bytes=source.stat().st_size,sha256=digest(source))
        return name
    conditions=[]
    for row in refs['conditions']:
        metadata_path=Path(row['model_manifest']);metadata=json.loads(metadata_path.read_text())
        assert metadata['model_sha256']==row['model_sha256']
        assert digest(metadata_path.parent/metadata['model_file'])==row['model_sha256']
        gate=validation if row['budget']==224 else p512_validation
        assert gate['candidate_sha256' if row['number']!=3 else 'source_sha256']==row['model_sha256']
        include(metadata_path.parent/metadata['model_file']);include(metadata_path)
        vectors=a.references.parent/row['vectors'];assert digest(vectors)==row['sha256']
        include(vectors)
        conditions.append(dict(number=row['number'],name=row['name'],budget=row['budget'],pooling=row['pooling'],
            vectors=row['vectors'],model_manifest=metadata_path.name,model_sha256=row['model_sha256'],
            effective_profile=row['effective_profile']))
    include(a.positions);include(a.segmenter);include(a.segmenter.parent/segmenter['model_file']);include(a.validation)
    include(a.p512_validation)
    manifest=dict(format='chtozavino-base-p224-comparison',format_version=2,version='20261020-base-p224-p512-pooling-v2',
        model=MODEL,revision=REVISION,dimension=768,wine_count=refs['wine_count'],slugs=refs['slugs'],
        conditions=conditions,files=files,position_table=a.positions.name,segmenter_manifest=a.segmenter.name,
        validations={'224':a.validation.name,'512':a.p512_validation.name},reference_views=1,reranking=False,barcode=False,offline=True,
        query_masks='On-device mobile bottle model; no label boost; no fallback.',reference_manifest_sha256=digest(a.references))
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(pack=str(a.out),bytes=sum(v['bytes'] for v in files.values()),manifest_sha256=digest(a.out/'manifest.json'))))


if __name__=='__main__':main()
