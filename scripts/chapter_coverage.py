import json
from collections import OrderedDict

d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

chapters = OrderedDict()
for r in b:
    ch = r.get('chapter', 'UNKNOWN')
    if ch not in chapters:
        chapters[ch] = {'total': 0, 'verbatim': 0, 'incomplete': 0, 'fallback': 0, 'ids': []}
    chapters[ch]['total'] += 1
    chapters[ch]['ids'].append(r['id'])
    st = r.get('source_grounding_status', '')
    if st in ('verbatim_sourced', 'verbatim_source_verified'):
        chapters[ch]['verbatim'] += 1
    elif st == 'source_derived_fallback':
        chapters[ch]['fallback'] += 1
    else:
        chapters[ch]['incomplete'] += 1

# Also categorize by specific_data presence
for ch_data in chapters.values():
    ch_data['has_specific'] = sum(
        1 for r in b if r['id'] in ch_data['ids'] and r.get('has_specific_data')
    )

print(f'| Chapter | Total | Verbatim | Incomplete | Fallback | %Grounded | Has Specific Data |')
print(f'|---------|-------|----------|------------|----------|-----------|-------------------|')
total_t = total_v = total_i = total_f = total_sp = 0
for ch, data in chapters.items():
    pct = data['verbatim'] / data['total'] * 100
    total_t += data['total']
    total_v += data['verbatim']
    total_i += data['incomplete']
    total_f += data['fallback']
    total_sp += data['has_specific']
    print(f'| {ch[:45]:45s} | {data["total"]:5d} | {data["verbatim"]:8d} | {data["incomplete"]:10d} | {data["fallback"]:8d} | {pct:9.1f}% | {data["has_specific"]:17d} |')
print(f'|{"-"*45}|{"-"*7}|{"-"*10}|{"-"*12}|{"-"*10}|{"-"*11}|{"-"*19}|')
print(f'| {"TOTAL":45s} | {total_t:5d} | {total_v:8d} | {total_i:10d} | {total_f:8d} | {total_v/total_t*100:9.1f}% | {total_sp:17d} |')

# Recovery priority: chapters with most fallback records, sorted descending
print('\n## Recovery Priority List')
sorted_ch = sorted(chapters.items(), key=lambda x: -x[1]['fallback'])
for i, (ch, data) in enumerate(sorted_ch, 1):
    effort = '6-8 pages' if data['fallback'] > 5 else '1-2 pages'
    print(f'{i}. {ch} ({data["fallback"]} fallback, {data["verbatim"]} grounded) — {effort}')

# List all fallback record IDs for actionable planning
print('\n## All Fallback Records')
for ch, data in sorted_ch:
    if data['fallback'] > 0:
        fb_ids = [r['id'] for r in b if r['id'] in data['ids'] and r.get('source_grounding_status') != 'verbatim_sourced']
        print(f'{ch}: {", ".join(fb_ids)}')
