import json
with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)['bylaws']
for fld in ['followup_questions', 'real_world_examples', 'example_queries']:
    present = sum(1 for r in data if fld in r)
    sample = None
    for r in data:
        if r.get(fld):
            sample = r[fld]
            break
    s = str(sample)[:120] if sample else 'N/A'
    print(f'{fld}: in {present}/247, sample: {s}')
