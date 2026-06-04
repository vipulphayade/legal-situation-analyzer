import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

base = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws'

fixes = {'url_spacing': 0, 'slug_to_url': 0}

for r in data['bylaws']:
    # Fix 1: URL spacing in source_reference and primary_source_reference
    for field in ['source_reference', 'primary_source_reference']:
        v = r.get(field, '')
        if v and '. com/' in v:
            r[field] = v.replace('. com/', '.com/')
            fixes['url_spacing'] += 1
    
    # Fix 2: Convert slug official_source_page to full URL
    osp = r.get('official_source_page', '')
    if osp and not osp.startswith('http') and osp != 'source_grounded':
        r['official_source_page'] = f'{base}/{osp}'
        fixes['slug_to_url'] += 1

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

for fix, count in fixes.items():
    print(f'{fix}: {count}')
