import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix old verbatim_sourced records that have 'source_grounded' as page
# Map bylaw numbers to correct source URLs
bylaw_chapter_map = {
    '22(A)': 'member-rights-duties', '22(B)': 'member-rights-duties', '22(C)': 'member-rights-duties',
    '22(D)': 'member-rights-duties', '22(E)': 'member-rights-duties', '22(F)': 'member-rights-duties',
    '46(C)': 'maintenance-flat-members',
    '50(a)': 'member-explusion', '50(b)': 'member-explusion',
    '115(A)': 'management-affairs', '115(B)': 'management-affairs', '115(C)': 'management-affairs',
    '115(D)': 'management-affairs', '115(E)': 'management-affairs',
    '125(a)': 'management-affairs', '125(b)': 'management-affairs',
    '127(a)': 'management-affairs', '127(b)': 'management-affairs',
    '131(a)': 'management-affairs', '131(b)': 'management-affairs', '131(c)': 'management-affairs',
    '131(d)': 'management-affairs', '131(e)': 'management-affairs',
}

base_url = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws'

fixes = 0
for r in data['bylaws']:
    if r.get('official_source_page') == 'source_grounded' and r.get('official_grounding_status') == 'verbatim_sourced':
        bn = r.get('official_bylaw_number', r.get('bylaw_number', ''))
        # Try exact match first
        slug = bylaw_chapter_map.get(bn)
        if not slug:
            # Try without case
            for key, val in bylaw_chapter_map.items():
                if key.lower() == bn.lower().replace(' ',''):
                    slug = val
                    break
        if not slug:
            print(f'  No slug found for {r["id"]} ({bn})')
            continue
        r['official_source_page'] = f'{base_url}/{slug}'
        fixes += 1
        print(f'  Fixed {r["id"]} ({bn}): {slug}')

# Also fix the original 22A-F records that may have been set differently
for r in data['bylaws']:
    if r['id'] in ('BL_038',):
        r['official_source_page'] = f'{base_url}/member-rights-duties'
        fixes += 1

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'\nFixed {fixes} record(s).')
