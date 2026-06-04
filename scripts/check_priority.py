import json

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Check these priority chapters
chapters = [
    'Management of the Affairs of the Society',
    'Responsibilities and Liabilities of Members',
    'Funds, Their Utilisation and Investment',
]

for ch_name in chapters:
    records = [r for r in data['bylaws'] if r.get('chapter', '').strip() == ch_name]
    fallback = [r for r in records if r.get('official_grounding_status') == 'source_derived_fallback']
    print(f'{ch_name}: {len(records)} total, {len(fallback)} fallback')
    if fallback:
        for r in fallback:
            bn = r.get('official_bylaw_number', r.get('bylaw_number', ''))
            print(f'  {r["id"]} bylaw={bn}')
    else:
        # Sample check text quality
        for r in records[:2]:
            text = (r.get('official_legal_text', '') or '')[:120]
            print(f'  {r["id"]}: {text}...')
    print()
