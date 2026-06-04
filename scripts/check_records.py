import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show chapter slugs for General Meetings records
for r in data['bylaws']:
    ch = r.get('chapter', '')
    if 'General' in ch and 'Meeting' in ch:
        print(f'{r["id"]:10s} | bylaw={r.get("official_bylaw_number","")} | chapter_slug={r.get("chapter_slug","")}  ')
print()

# Check a sample record with verbatim_source_verified
for r in data['bylaws']:
    if r['id'] == 'BL_039':
        print('Sample record BL_039 (verbatim_source_verified):')
        for k in ['official_legal_text', 'source_grounded_official_text', 
                   'official_grounding_status', 'official_source_page', 
                   'source_grounding_status', 'verbatim_source_link']:
            print(f'  {k}: {str(r.get(k,""))[:200]}')
        break

print()
# Check a sample fallback record
for r in data['bylaws']:
    if r['id'] == 'BL_028':
        print('Sample record BL_028 (fallback):')
        for k in ['official_legal_text', 'source_grounded_official_text',
                   'official_grounding_status', 'official_source_page',
                   'source_grounding_status', 'verbatim_source_link']:
            print(f'  {k}: {str(r.get(k,""))[:200]}')
        break
