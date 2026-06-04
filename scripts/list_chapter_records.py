import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chapter = 'member-rights-duties'
count = 0
for r in data['bylaws']:
    ch = r.get('chapter_slug', '') or r.get('chapter', '')
    if 'member' in ch.lower() and 'right' in ch.lower():
        count += 1
        vl = r.get('official_source_page', '') or r.get('verbatim_source_link', '') or ''
        bylaw = r.get('official_bylaw_number', '') or r.get('bylaw_number', '') or ''
        print(f'{r["id"]:12s} | bylaw={str(bylaw):20s} | grounding={str(r.get("official_grounding_status","")):20s} | page={vl[:60]}')
print(f'\nTotal: {count}')
