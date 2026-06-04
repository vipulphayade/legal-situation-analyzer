import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check BL_134
for r in data['bylaws']:
    if r['id'] == 'BL_134':
        print(f'{r["id"]}: bylaw={r.get("official_bylaw_number","")} status={r.get("official_grounding_status","")}')
        print(f'  text={r.get("official_legal_text","")[:200]}')
        print(f'  source_page={r.get("official_source_page","")}')
        break
else:
    print('BL_134 not found')

# Also check first/last updated records
for r in data['bylaws']:
    if r['id'] in ('BL_150', 'BL_124', 'BL_149'):
        print(f'{r["id"]}: bylaw={r.get("official_bylaw_number","")} status={r.get("official_grounding_status","")} source_page={r.get("official_source_page","")[:60]}')
