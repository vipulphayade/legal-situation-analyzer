import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(type(data))
if isinstance(data, dict):
    print(list(data.keys())[:10])
    if 'bylaws' in data:
        items = data['bylaws']
        print(f'bylaws: {type(items)}, len={len(items)}')
        if isinstance(items, list):
            for r in items[:2]:
                print(r.keys())
elif isinstance(data, list):
    print(f'list len={len(data)}')
    for r in data[:2]:
        print(r.keys())
