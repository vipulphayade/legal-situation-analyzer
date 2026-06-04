import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show all records grouped by chapter with grounding status
from collections import defaultdict
chapter_records = defaultdict(list)
for r in data['bylaws']:
    ch = r.get('chapter', '').strip()
    chapter_records[ch].append(r)

# For each chapter with >0 fallback records, show all records
for ch in sorted(chapter_records.keys()):
    fallback = [r for r in chapter_records[ch] if r.get('official_grounding_status') == 'source_derived_fallback']
    if fallback:
        total = len(chapter_records[ch])
        print(f'\n=== {ch} ({len(fallback)}/{total} fallback) ===')
        for r in chapter_records[ch]:
            bn = r.get('official_bylaw_number', r.get('bylaw_number', ''))
            status = r.get('official_grounding_status', '')
            if status == 'source_derived_fallback':
                print(f'  {r["id"]:8s} bylaw={bn:15s} FALLBACK')
