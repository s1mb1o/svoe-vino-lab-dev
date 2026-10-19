"""Independent JSON contract projection. No production pairing code is imported.

This establishes deterministic rule compliance and completeness, not taste.
Blind editorial references are scored separately.
"""
from copy import deepcopy


def matches(rule, values):
    if 'all' in rule:return all(matches(x, values) for x in rule['all'])
    if 'any' in rule:return any(matches(x, values) for x in rule['any'])
    value=values.get(rule.get('attribute'))
    if value is None:return False
    return value==rule['value'] if rule['op']=='eq' else value in rule['value']


def expected(data, node_id, attrs):
    nodes={n['id']:n for n in data['nodes']};profiles={p['id']:p for p in data['profiles']}
    node=nodes[node_id];base=node['pairing_rule']['profile_id'];policy=data['suitability_policy']
    values={**policy['profile_context_defaults'].get(base,{}),**node.get('pairing_reference_attributes',{}),**attrs}
    replacements=sorted([r for r in data['modifier_rules'] if 'replace_profile_id' in r['action'] and matches(r['when'],values)],key=lambda r:r['priority'],reverse=True)
    profile=replacements[0]['action']['replace_profile_id'] if replacements else base
    dessert=values.get('is_dessert') is True or 'desserts' in node['hierarchy_path']
    if dessert:
        profile=base if 'desserts' in node['hierarchy_path'] else 'dessert_general'
    elif profile=='sweet_glaze':
        if values.get('poultry_style')=='duck':profile='sweet_glaze_duck'
        elif set(node['hierarchy_path'])&{'meat','game'} or base in {'ribeye','meat_steak','grilled_meat','lamb','venison','game','braised_beef','meat_general'}:profile='sweet_glaze_rich_meat'
    elif profile in {'spicy','spicy_sour'} and values.get('protein_family') in {'meat','game'} and values.get('sauce_sweetness') not in {'medium','high'}:
        profile='spicy_meat'
    elif profile=='white_butter_cream' and values.get('poultry_style')=='duck':
        profile=base
    eligibility=deepcopy(profiles[profile]['eligibility'])
    if dessert:eligibility['sweetness']=['sweet']
    if values.get('heat') in {'medium','high'}:eligibility['max_alcohol_percent']=min(eligibility.get('max_alcohol_percent') or 12.5,12.5)
    if profile=='poultry' and values.get('poultry_style') not in {'duck','grilled_dark_meat'}:eligibility['colors']=[v for v in eligibility['colors'] if v!='red']
    if profile=='game' and values.get('game_type')!='delicate_feathered_game':eligibility['colors']=[v for v in eligibility['colors'] if v!='white']
    if profile=='cheese_general' and values.get('cheese_type')!='blue':eligibility['sweetness']=[v for v in eligibility['sweetness'] if v!='sweet']
    if profile=='dessert_general' and values.get('dessert_base') not in {'cocoa','chocolate','dark_berries'}:eligibility['colors']=[v for v in eligibility['colors'] if v!='red']
    if profile==base:eligibility.update(node['pairing_rule'].get('eligibility_overrides',{}))
    allowed=set(policy['profiles'][profile])
    if profile==base:
        allowed=set(policy['node_family_overrides'].get(node_id,allowed));allowed.update(policy['node_family_extensions'].get(node_id,[]))
    annotations={a['wine_slug']:a for a in policy['wines']}
    guards=policy.get('qualitative_guards');selected=set();body_order={'unknown':0,'light':1,'medium':2,'full':3}
    blocked={e['wine_slug'] for e in node['curated'] if profile==base and not all(matches(c,values) for c in e.get('applicability_conditions',[]))}
    for wine in data['wines']:
        slug=wine['wine_slug'];facts={k:v['value'] for k,v in wine['facts'].items()};a=annotations[slug]
        if (slug in blocked or a['family'] not in allowed or facts['color'] not in eligibility['colors']
            or facts['sweetness'] not in eligibility['sweetness'] or facts['wine_kind'] not in eligibility['wine_kinds']):continue
        maximum=eligibility.get('max_alcohol_percent')
        if maximum is not None and (facts['alcohol_percent'] is None or facts['alcohol_percent']>maximum):continue
        if guards:
            traits=a['qualitative_traits'];q=node['qualitative_pairing_context']
            if values.get('acidity')=='high' and traits['acidity'] not in guards['required_acidity_for_high_acid']:continue
            minimum=guards['minimum_body_by_profile'].get(profile)
            if minimum and body_order[traits['body']]<body_order[minimum]:continue
            if a['family'] in guards['profile_excluded_families'].get(profile,[]):continue
            if profile in guards['creamy_profiles'] and (set(traits['markers'])&set(guards['creamy_excluded_markers']) or a['family'] in guards['creamy_excluded_families'] or traits['body']=='light'):continue
            if profile=='sweet_glaze' and a['family']=='semisweet_white' and values.get('sauce_sweetness')!='high':continue
            if profile=='spicy' and values.get('sauce_sweetness') not in {'medium','high'} and a['family']=='semisweet_white':continue
            if profile=='sweet_glaze_rich_meat':
                if set(traits['markers'])&set(guards['glaze_excluded_markers']):continue
                if values.get('fatty_cream_sauce') and set(traits['markers'])&set(guards['creamy_glaze_excluded_markers']):continue
            if not (values.get('heat') in {'medium','high'} or values.get('sauce_sweetness') in {'medium','high'}):
                if q['mushroom_umami'] and set(traits['markers'])&set(guards['mushroom_excluded_markers']):continue
                if q['raw_shellfish'] and not values.get('fatty_cream_sauce') and (traits['body'] in guards['raw_shellfish_excluded_body'] or set(traits['markers'])&set(guards['raw_shellfish_excluded_markers'])):continue
        selected.add(slug)
    return profile,selected
