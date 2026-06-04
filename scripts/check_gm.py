import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check a few general meeting records for slug
for r in data['bylaws']:
    if r['id'] in ('BL_124', 'BL_134', 'BL_135', 'BL_136'):
        print(f'{r["id"]}: chapter_slug={r.get("chapter_slug","")!r}, chapter={r.get("chapter","")!r}')
        print(f'  official_source_page={r.get("official_source_page","")!r}')
        print(f'  verbatim_source_link={r.get("verbatim_source_link","")!r}')
        print()
