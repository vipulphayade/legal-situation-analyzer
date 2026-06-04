import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# 1. URL spacing issues
issues = []
for r in data['bylaws']:
    for f in ['source_reference', 'primary_source_reference']:
        v = r.get(f, '')
        if v and '. ' in v:
            issues.append((r['id'], f, v[:80]))

print(f'1. URL spacing issues (mysocietyclub. com): {len(issues)}')
for rid, field, val in issues[:3]:
    print(f'  {rid} {field}: {val}')

# Check official_source_page format
print('\n2. official_source_page formats:')
formats = {}
for r in data['bylaws']:
    v = r.get('official_source_page', '')
    if v.startswith('http'):
        fmt = 'full_url'
    elif v and v != 'source_grounded':
        fmt = 'slug'
    else:
        fmt = v
    formats.setdefault(fmt, 0)
    formats[fmt] += 1
for f, c in sorted(formats.items()):
    print(f'  {f}: {c}')

# Check official_excerpt_source values
print('\n3. official_excerpt_source values:')
vals = {}
for r in data['bylaws']:
    v = r.get('official_excerpt_source', '')
    vals[v] = vals.get(v, 0) + 1
for v, c in sorted(vals.items()):
    print(f'  {v}: {c}')
