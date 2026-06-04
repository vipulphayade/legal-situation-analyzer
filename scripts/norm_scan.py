import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Check source URLs for spacing issues
urls = {}
for r in data['bylaws']:
    sp = r.get('official_source_page', '')
    if sp:
        urls.setdefault(sp, []).append(r['id'])

print("=== Source page URLs ===")
for u, ids in sorted(urls.items()):
    print(f'  [{len(ids):2d}] {u}')

# Check for URL spacing issues (e.g., "mysocietyclub. com")
print("\n=== URL spacing issues ===")
for r in data['bylaws']:
    for f in ['official_source_page', 'source_reference', 'primary_source_reference', 'official_excerpt_source']:
        v = r.get(f, '')
        if v and ('. ' in v or '  ' in v):
            print(f'  {r["id"]} {f}={v[:80]}')

# Check chapter title inconsistencies
print("\n=== Chapter titles ===")
chapters = {}
for r in data['bylaws']:
    ch = r.get('chapter', '').strip()
    chapters.setdefault(ch, []).append(r['id'])
for ch, ids in sorted(chapters.items()):
    print(f'  [{len(ids):2d}] {ch}')

# Check title wording differences
print("\n=== Title inconsistencies (same bylaw, different titles) ===")
from collections import defaultdict
bylaw_titles = defaultdict(list)
for r in data['bylaws']:
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
    title = r.get('title', '')
    bylaw_titles[bn].append((r['id'], title))
for bn, entries in bylaw_titles.items():
    titles = set(e[1] for e in entries)
    if len(titles) > 1:
        print(f'  Bylaw {bn}:')
        for eid, t in entries:
            print(f'    {eid}: {t}')
