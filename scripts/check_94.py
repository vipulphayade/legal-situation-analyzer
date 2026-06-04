import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check BL_134 (which should be bylaw 94)
for r in data['bylaws']:
    if r['id'] in ('BL_134', 'BL_135'):
        bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
        print(f'{r["id"]}: bylaw_number={bn!r}')
        print(f'  official_bylaw_number={r.get("official_bylaw_number","")!r}')
        print(f'  bylaw_number={r.get("bylaw_number","")!r}')
        print(f'  title={r.get("title","")[:80]}')
        print()
