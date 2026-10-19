"""Source-linked compositional guards; never consume evaluation labels or outputs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# Reviewed qualitative readings of existing catalog descriptions, not measured
# acidity/tannin/body. Unlisted acidity is unknown, never a numeric estimate.
BODY={
 'light':'P2 F2 T1 T2 T3 T4',
 'medium':'R4 R5 P1 P3 P4 P5 G1 G2 G3 O1 O2 O3 O4 O5 K1 K3 F1 F3 F4 F6 F7 B1 B2 B3 H1 H2 H3 H5 D1 D2 D4 D8',
 'full':'R1 R2 R3 G4 K2 F5 H4 D3 D5 D6 D7',
}
ACID={'pronounced':'O4 P2 F1 F5 T1 B2','fresh':'R4 R5 P1 P4 K1 K3 F2 F4 O1 O2 O3 O5 B1 H1 H5 D2 D8',
      'moderate':'F3','soft':'H2'}
MARKERS={'dominant_herbal':'F1','round_ripe_white':'F4','round_structured_red':'R4 R5 G3',
         'forest_or_earth':'P3 G2','vanilla_full_white':'K2', 'savory_smoke':'R5', 'pepper_moderate_tannin':'R3'}


def build():
    base=ROOT/'data/pairing-dataset.v3.json'
    d=json.loads(base.read_bytes());bycode={w['id']:w for w in d['wines']};byslug={w['wine_slug']:w for w in d['wines']}
    d.update(schema_version='4.0.0',taxonomy_version='4.0.0',dataset_id='dinner-lens-200-compositional-sauces-20261019',supersedes='pairing-dataset.v3.json')
    d['$schema']='./pairing-dataset.v4.schema.json'
    traits={code:{'body':'unknown','acidity':'unknown','markers':[]} for code in bycode}
    for key,groups in [('body',BODY),('acidity',ACID)]:
        assigned=set()
        for value,codes in groups.items():
            for code in codes.split():
                assert code not in assigned;assigned.add(code);traits[code][key]=value
        if key=='body':assert assigned==set(bycode)
    for marker,codes in MARKERS.items():
        for code in codes.split():traits[code]['markers'].append(marker)
    policy=d['suitability_policy'];policy['version']='2.0.0'
    policy['profiles']['spicy_meat'].append('delicate_red')
    spicy_meat=next(p for p in d['profiles'] if p['id']=='spicy_meat')
    spicy_meat['curation_pool']=[bycode[c]['wine_slug'] for c in ['H1','H5','P4']]
    next(p for p in d['profiles'] if p['id']=='spicy')['match_rationale_ru']='умеренный алкоголь и подходящая сладость вина помогают сбалансировать жгучесть чили'
    for profile in ['sour_cabbage','seafood_citrus']:
        policy['profile_context_defaults'].setdefault(profile,{})['acidity']='high'
    for annotation in policy['wines']:
        wine=byslug[annotation['wine_slug']];annotation['qualitative_traits']=traits[wine['id']]
    policy['qualitative_guards']={
        'version':'1.0.0',
        'basis':'Reviewed qualitative source descriptions and selected recipe contexts, never measurements, model predictions or evaluation case/wine labels.',
        'acid_conflicts':['moderate','soft'],
        'required_acidity_for_high_acid':['fresh','pronounced'],
        'minimum_body_by_profile':{p:'medium' for p in ['meat_general','grilled_meat','meat_steak','ribeye','lamb','venison','spicy_meat']},
        'profile_excluded_families':{'meat_tomato':['dry_rose']},
        'mushroom_excluded_markers':['dominant_herbal','round_structured_red'],
        'raw_shellfish_excluded_markers':['round_ripe_white','vanilla_full_white'],
        'raw_shellfish_excluded_body':['full'],
        'creamy_profiles':['white_butter_cream','crab_butter'],
        'creamy_excluded_markers':['dominant_herbal'],
        'creamy_excluded_families':[],
        'glaze_excluded_markers':['forest_or_earth','savory_smoke'],
        'creamy_glaze_excluded_markers':['pepper_moderate_tannin'],
        'known_source_conflicts_are_excluded':'Strongly acidic sauces require positive qualitative freshness/acidity evidence. Unknown does not satisfy this style target. No numerical acidity is fabricated.',
    }
    for n in d['nodes']:
        tags=set(n.get('ingredient_tags',[]))
        if n['id'] in {'vinaigrette_salad','gazpacho','greek_salad_feta','tabbouleh','nicoise_tuna',
                       'oysters_lemon','salmon_grilled_lemon','beef_carpaccio_parmesan'}:
            n['pairing_reference_attributes']['acidity']='high'
            n['pairing_reference_acidity_basis']='Reviewed selected recipe reference names a sour dressing, lemon or vinegar. Not an observed image fact; an explicit user acidity correction overrides it.'
        n['qualitative_pairing_context']={
            'mushroom_umami':n['pairing_rule']['profile_id']=='mushrooms',
            'raw_shellfish':'raw_bivalves' in n['hierarchy_path'] or ('oyster' in tags and 'raw' in tags),
        }
    # The new rules narrow editorial choices as well as discovery. Only prune
    # documented conflicting entries; no blind-judge predictions enter this build.
    for n in d['nodes']:
        profile=n['pairing_rule']['profile_id'];q=n['qualitative_pairing_context'];curated=[]
        reference={**policy['profile_context_defaults'].get(profile,{}),**n.get('pairing_reference_attributes',{})}
        if profile=='spicy_meat':
            for entry in n['curated']:
                if entry['wine_slug']==bycode['P2']['wine_slug']:
                    w=bycode['P4'];entry.update(wine_slug=w['wine_slug'],explanation_ru=w['style_summary']['text_ru']+' Свежая кислотность, бархатистые танины и умеренный алкоголь по данным каталога подходят к мясу с чили.',source_facts_used={'color':'red','sweetness':'dry','style_summary':w['style_summary']['text_ru']})
        for e in n['curated']:
            w=byslug[e['wine_slug']];t=traits[w['id']]
            family=next(a['family'] for a in policy['wines'] if a['wine_slug']==e['wine_slug'])
            if profile in policy['qualitative_guards']['minimum_body_by_profile'] and t['body']=='light':continue
            if family in policy['qualitative_guards']['profile_excluded_families'].get(profile,[]):continue
            if q['mushroom_umami'] and set(t['markers'])&set(policy['qualitative_guards']['mushroom_excluded_markers']):continue
            if q['raw_shellfish'] and (t['body']=='full' or set(t['markers'])&set(policy['qualitative_guards']['raw_shellfish_excluded_markers'])):continue
            if profile=='sweet_glaze_rich_meat' and set(t['markers'])&set(policy['qualitative_guards']['glaze_excluded_markers']):continue
            if profile in {'sweet_glaze','spicy'} and family=='semisweet_white':continue
            if reference.get('acidity')=='high' and t['acidity'] not in {'fresh','pronounced'}:continue
            e=deepcopy(e);e['rank']=len(curated)+1;curated.append(e)
            if profile=='spicy':
                e['explanation_ru']=w['style_summary']['text_ru']+' Умеренный алкоголь и подходящая сладость вина помогают сбалансировать жгучесть чили.'
        assert 1<=len(curated)<=5,(n['id'],len(curated));n['curated']=curated
        if len(curated)<3:n['curation_note']='Fewer than three reviewed wines satisfy the default sauce requirements; never fill with unsupported styles.'
    d['scope']['curated_wine_links']=sum(len(n['curated']) for n in d['nodes'])
    d['provenance']['compositional_sauce_revision']={'base_dataset_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'evaluation_reference_used_by_builder':False,'catalog_source_facts_changed':False}
    d['known_data_quality_notes'] += ['V4 guards remove source-described moderate/soft acidity under a strongly acidic sauce, overly light wines under a rich meat profile, and conflicting herbal/round styles with mushroom umami. Qualitative annotations are editorial evidence interpretations, not laboratory measurements.', 'Alcohol ceilings use catalog values; bottle-label precision has not been independently verified. URL slugs never supply numeric facts.']
    d['validation_summary']={'report_file':'pairing-dataset.v4.validation.json','validated_scope':'All320 canonical nodes and all200 dishes x16 sauce additions with full continuation; see separate test report.'}
    target=ROOT/'data/pairing-dataset.v4.json';target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    schema=json.loads((ROOT/'data/pairing-dataset.v3.schema.json').read_bytes());schema['$id']='urn:dinner-lens:pairing-dataset:4.0.0';schema['properties']['schema_version']['const']='4.0.0'
    schema['$defs']['node']['properties']['curated']['minItems']=1
    (ROOT/'data/pairing-dataset.v4.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'dataset':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'curated_links':d['scope']['curated_wine_links']}))

if __name__=='__main__':build()
