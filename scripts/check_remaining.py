import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

remaining = [r for r in data['bylaws'] if r.get('official_grounding_status') == 'source_derived_fallback']
print(f'Remaining fallback: {len(remaining)}')
for r in remaining:
    bn = r.get('official_bylaw_number', r.get('bylaw_number', ''))
    ch = r.get('chapter', '').strip()
    print(f'  {r["id"]:8s} bylaw={bn:15s} chapter={ch}')
