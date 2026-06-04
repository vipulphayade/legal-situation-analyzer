import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for r in data['bylaws']:
    if r['id'] in ('BL_235', 'BL_240', 'BL_241', 'BL_245', 'BL_246', 'BL_247'):
        bn = r.get('official_bylaw_number', r.get('bylaw_number', ''))
        sp = r.get('official_source_page', '')
        print(f'{r["id"]:8s} bylaw={bn:10s} status={r["official_grounding_status"]:25s} page={sp[:60]}')
