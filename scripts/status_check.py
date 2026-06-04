import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

total = len(data['bylaws'])
verbatim_sourced = sum(1 for r in data['bylaws'] if r.get('official_grounding_status') == 'verbatim_sourced')
verbatim_source_verified = sum(1 for r in data['bylaws'] if r.get('official_grounding_status') == 'verbatim_source_verified')
fallback = sum(1 for r in data['bylaws'] if r.get('official_grounding_status') == 'source_derived_fallback')

print(f'Total records: {total}')
print(f'verbatim_sourced: {verbatim_sourced} ({100*verbatim_sourced/total:.1f}%)')
print(f'verbatim_source_verified: {verbatim_source_verified} ({100*verbatim_source_verified/total:.1f}%)')
print(f'grounded total: {verbatim_sourced + verbatim_source_verified} ({(verbatim_sourced+verbatim_source_verified)*100/total:.1f}%)')
print(f'source_derived_fallback: {fallback} ({100*fallback/total:.1f}%)')

# Chapter-level breakdown
from collections import defaultdict
chapter_stats = defaultdict(lambda: {'total': 0, 'grounded': 0})
for r in data['bylaws']:
    ch = r.get('chapter', '').strip() or r.get('chapter_slug', '').strip() or 'UNKNOWN'
    if not ch:
        ch = 'UNKNOWN'
    chapter_stats[ch]['total'] += 1
    if r.get('official_grounding_status') in ('verbatim_sourced', 'verbatim_source_verified'):
        chapter_stats[ch]['grounded'] += 1

print('\nChapter breakdown:')
for ch in sorted(chapter_stats.keys()):
    s = chapter_stats[ch]
    pct = s['grounded'] / s['total'] * 100 if s['total'] > 0 else 0
    print(f'  {ch:60s} {s["grounded"]:3d}/{s["total"]:2d} ({pct:5.1f}%)')
