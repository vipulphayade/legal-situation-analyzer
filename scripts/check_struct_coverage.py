import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

targets = ['eligibility_requirements','quorum_requirements','voting_thresholds',
           'approval_requirements','time_limits','financial_limits',
           'penalty_conditions','date_references','section_rule_references']

for field in targets:
    filled = sum(1 for r in data['bylaws'] if r.get('structured_specific_data', {}).get(field))
    print(f'{field:30s} {filled}/{len(data["bylaws"])} records non-empty')

miss = [f for f in targets if f not in data['bylaws'][0].get('structured_specific_data', {})]
print(f'\nMissing keys: {miss}')
