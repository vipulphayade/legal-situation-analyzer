import json
d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

v = [r for r in b if r.get('source_grounding_status') == 'verbatim_source_verified']
print('verbatim_source_verified count:', len(v))
for r in v[:3]:
    lid = r['id']
    lbl = r['bylaw_label']
    txt = r['official_legal_text'][:80]
    print(f'{lid} {lbl}: {txt}')

f = [r for r in b if r.get('source_grounding_status') == 'source_derived_fallback']
print('\nsource_derived_fallback count:', len(f))
for r in f[:3]:
    lid = r['id']
    lbl = r['bylaw_label']
    txt = r['official_legal_text'][:80]
    print(f'{lid} {lbl}: {txt}')

# Check source_verification on verbatim_source_verified records
print('\nSample verbatim_source_verified metadata:')
for r in v[:2]:
    print(json.dumps(r.get('source_verification', {}), indent=2)[:200])
