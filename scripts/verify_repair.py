import json
d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

total = d['metadata']['total_bylaws']
print(f'Total records: {total}')
assert len(b) == 239, f'Expected 239, got {len(b)}'

b22 = [x for x in b if x['bylaw_number'] == '22']
print(f'\nBylaw 22 records: {len(b22)}')
for r in b22:
    print(f'  {r["id"]}: {r["bylaw_label"]:>6} | {r["title"][:50]}')

b46 = [x for x in b if x['bylaw_number'] == '46']
print(f'\nBylaw 46 records: {len(b46)}')
for r in b46:
    print(f'  {r["id"]:>8}: {r["bylaw_label"]:>6} | {r["title"][:60]}')

b115 = [x for x in b if x['bylaw_number'] == '115']
print(f'\nBylaw 115 records: {len(b115)}')
for r in b115:
    print(f'  {r["id"]:>8}: {r["bylaw_label"]:>6} | {r["title"][:60]}')

ids = [x['id'] for x in b]
assert len(ids) == len(set(ids)), 'DUPLICATE IDs!'
print(f'\nNo duplicate IDs: OK')

new_ids = ['BL_230','BL_231','BL_232','BL_233','BL_234','BL_235','BL_236','BL_237','BL_238','BL_239']
for rec in b:
    if rec['id'] in new_ids:
        assert rec['section_code'], f'{rec["id"]} missing section_code'
        assert rec['source_grounding_status'] == 'verbatim_sourced', f'{rec["id"]} not verbatim_sourced'
print(f'All new records have section_code and verbatim_sourced: OK')

bl38 = [x for x in b if x['id'] == 'BL_038'][0]
assert bl38['bylaw_label'] == '22(A)', f'BL_038 label wrong: {bl38["bylaw_label"]}'
assert '22(A)' in bl38['official_bylaw_number'], f'BL_038 official_bylaw_number wrong'
print(f'\nBL_038 modified: bylaw_label={bl38["bylaw_label"]}, section_code={bl38["section_code"]}')

bl155 = [x for x in b if x['id'] == 'BL_155'][0]
assert bl155['bylaw_label'] == '115(A)', f'BL_155 label wrong: {bl155["bylaw_label"]}'
assert '115(A)' in bl155['official_bylaw_number'], f'BL_155 official_bylaw_number wrong'
print(f'BL_155 modified: bylaw_label={bl155["bylaw_label"]}, section_code={bl155["section_code"]}')

print('\n=== ALL CHECKS PASSED ===')
