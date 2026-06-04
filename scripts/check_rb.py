import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Check existing related_bylaws structure
rec = data['bylaws'][0]
rb = rec.get('related_bylaws', [])
print('Existing related_bylaws sample:')
print(json.dumps(rb[:2], indent=2))
print(f'Type: {type(rb).__name__}')
if rb:
    print(f'Keys in first item: {list(rb[0].keys())}')

# Count records with non-empty related_bylaws
has_rb = sum(1 for r in data['bylaws'] if r.get('related_bylaws'))
print(f'\nRecords with related_bylaws: {has_rb}/{len(data["bylaws"])}')
print(f'Total related_bylaws entries: {sum(len(r.get("related_bylaws",[])) for r in data["bylaws"])}')
