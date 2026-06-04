import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show all chapters
chapters = set()
for r in data['bylaws']:
    ch = r.get('chapter_slug', '') or r.get('chapter', '')
    chapters.add(ch)
print('Chapters:')
for c in sorted(chapters):
    count = sum(1 for r in data['bylaws'] if (r.get('chapter_slug', '') or r.get('chapter', '')) == c)
    print(f'  {c}: {count} records')

print('\n---\n')

# Show records for management-affairs chapter
for r in data['bylaws']:
    ch = r.get('chapter_slug', '') or r.get('chapter', '')
    if 'management' in ch.lower():
        bylaw = r.get('official_bylaw_number', '') or r.get('bylaw_number', '') or ''
        print(f'{r["id"]:10s} | bylaw={bylaw:15s} | grounding={str(r.get("official_grounding_status","")):20s}')

print('\n--- General Meetings ---\n')
for r in data['bylaws']:
    ch = r.get('chapter_slug', '') or r.get('chapter', '')
    if 'general' in ch.lower() or 'first' in ch.lower() or 'annual' in ch.lower() or 'special' in ch.lower():
        bylaw = r.get('official_bylaw_number', '') or r.get('bylaw_number', '') or ''
        print(f'{r["id"]:10s} | bylaw={bylaw:15s} | chapter_slug={r.get("chapter_slug","")} | grounding={str(r.get("official_grounding_status","")):20s}')
