import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Verify a few refs with their source text
verify_ids = ['BL_008', 'BL_039', 'BL_031']
for rid in verify_ids:
    r = next(x for x in data['bylaws'] if x['id'] == rid)
    text = (r.get('official_legal_text', '') or '')[:300]
    scr = r.get('source_cross_references', [])
    print(f'\n=== {rid} ({r.get("official_bylaw_number","")}) ===')
    print(f'Source text excerpt: {text}')
    print(f'Extracted references: {[s["related_id"] + " (" + s["bylaw_label"] + ")" for s in scr]}')
