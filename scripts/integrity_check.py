import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Quick integrity check
errors = []
for i, r in enumerate(data['bylaws']):
    rid = r.get('id', f'index_{i}')
    bid = r.get('bylaw_number', r.get('official_bylaw_number', None))
    
    # Check text is not empty for verbatim_sourced
    if r.get('official_grounding_status') == 'verbatim_sourced':
        text = r.get('official_legal_text', '')
        if not text or len(text) < 20:
            errors.append(f'{rid}: verbatim_sourced but text too short ({len(text)} chars)')
        
        # Check source page is a URL
        sp = r.get('official_source_page', '')
        if not sp.startswith('http'):
            errors.append(f'{rid}: verbatim_sourced but source_page is not URL: {sp}')
    
    # Check grounding_status consistency
    status = r.get('official_grounding_status', '')
    if status not in ('verbatim_sourced', 'verbatim_source_verified', 'source_derived_fallback'):
        errors.append(f'{rid}: unknown grounding status: {status}')

print(f'Total records: {len(data["bylaws"])}')
print(f'Errors: {len(errors)}')
for e in errors[:20]:
    print(f'  {e}')

if not errors:
    print('All checks passed!')

# Show some stats
print('\nRecord counts by grounding status:')
from collections import Counter
status_counts = Counter(r.get('official_grounding_status', '') for r in data['bylaws'])
for s, c in status_counts.most_common():
    print(f'  {s}: {c}')

# Verify a few records have proper verbatim text
print('\nSample updated records:')
for r in data['bylaws']:
    if r['id'] in ('BL_150', 'BL_124', 'BL_135', 'BL_134'):
        bn = r.get('official_bylaw_number', r.get('bylaw_number', ''))
        text = r.get('official_legal_text', '')[:120]
        print(f'  {r["id"]} (bylaw {bn}): {text}...')
