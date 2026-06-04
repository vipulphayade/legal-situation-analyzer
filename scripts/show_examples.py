import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

targets = ['eligibility_requirements','quorum_requirements','voting_thresholds',
           'approval_requirements','time_limits','financial_limits',
           'penalty_conditions','date_references','section_rule_references']

# Show 2 examples per field
for field in targets:
    shown = 0
    for r in data['bylaws']:
        vals = r.get('structured_specific_data', {}).get(field, [])
        if vals and shown < 2:
            print(f'\n{field} (in {r["id"]} {r.get("official_bylaw_number","")}):')
            for v in vals[:2]:
                print(f'  value={v.get("value","")}')
                print(f'  text={v.get("text","")[:80]}')
            shown += 1

# Summary
total_filled = {}
for field in targets:
    total_filled[field] = sum(1 for r in data['bylaws'] if r.get('structured_specific_data', {}).get(field))
print(f'\n\nCoverage summary:')
for field, count in sorted(total_filled.items(), key=lambda x: -x[1]):
    print(f'  {field:30s} {count:3d}/247 ({count/247*100:5.1f}%)')
print(f'\nTotal records with >=1 structured field: {sum(1 for r in data["bylaws"] if any(r.get("structured_specific_data",{}).get(f) for f in targets))}/247')
