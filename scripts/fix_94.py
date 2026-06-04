import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

merged_text = (
    'The Annual General Body Meeting of the Society shall be held on or before 30th September each year as provided under Section 75(1) of the Act. '
    'In case of default in calling the Annual General Body Meeting as stipulated, shall attract disqualification and action as provided under section 75(5) of the Act.'
)

updates = 0
for r in data['bylaws']:
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
    if str(bn).strip() == '94' and r.get('official_grounding_status') == 'source_derived_fallback':
        r['official_legal_text'] = merged_text
        r['source_grounded_official_text'] = merged_text
        r['official_grounding_status'] = 'verbatim_sourced'
        r['official_source_page'] = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/annual-general-body-meetings'
        r['source_grounding_status'] = 'verbatim_sourced'
        updates += 1
        print(f'Updated {r["id"]} (bylaw 94): verbatim_sourced')

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'Done. {updates} record(s) updated.')
