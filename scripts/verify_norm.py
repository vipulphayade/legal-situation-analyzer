import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Verify fixes
url_spacing_remaining = 0
slugs_remaining = 0
for r in data['bylaws']:
    for f in ['source_reference', 'primary_source_reference']:
        if '. com/' in r.get(f, ''):
            url_spacing_remaining += 1
    osp = r.get('official_source_page', '')
    if osp and not osp.startswith('http') and osp != 'source_grounded':
        slugs_remaining += 1

print(f'URL spacing remaining: {url_spacing_remaining}')
print(f'Slugs remaining: {slugs_remaining}')
print(f'Total records: {len(data["bylaws"])}')

# Show sample fixed URLs
r = data['bylaws'][0]
print(f'\nFixed source_reference: {r.get("source_reference", "")[:80]}')
print(f'Fixed official_source_page: {r.get("official_source_page", "")}')
