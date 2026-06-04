import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Verify a sample of cross-references
verify = ['BL_008', 'BL_039', 'BL_052', 'BL_058']
for rid in verify:
    r = next(x for x in data['bylaws'] if x['id'] == rid)
    text = (r.get('official_legal_text', '') or '')
    # Find the exact bylaw reference in text
    scr = r.get('source_cross_references', [])
    print(f'\n=== {rid} ({r.get("official_bylaw_number","")}) ===')
    for link in scr:
        ref_num = link['source_text'].replace('bye-law No. ', '')
        print(f'  Ref to bylaw {ref_num}')
        # Show context around this reference
        import re
        for m in re.finditer(r'.{0,40}' + re.escape(ref_num) + r'.{0,40}', text, re.I):
            print(f'  Context: ...{m.group(0).strip()}...')
