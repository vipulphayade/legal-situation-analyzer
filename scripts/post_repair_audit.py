import json
from collections import Counter

d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

# Grounding
grounded = sum(1 for r in b if r.get('source_grounding_status') == 'verbatim_sourced')
fallback = sum(1 for r in b if r.get('source_grounding_status') != 'verbatim_sourced')
print(f"Records: {len(b)} | Grounded: {grounded} ({grounded/len(b)*100:.1f}%) | Fallback: {fallback}")

# Chapter coverage
ch_data = {}
for r in b:
    ch = r.get('chapter', 'UNKNOWN')
    if ch not in ch_data:
        ch_data[ch] = {'total': 0, 'grounded': 0, 'fallback': 0, 'subs': 0, 'structured': 0}
    ch_data[ch]['total'] += 1
    if r.get('source_grounding_status') == 'verbatim_sourced':
        ch_data[ch]['grounded'] += 1
    else:
        ch_data[ch]['fallback'] += 1
    if r.get('section_code'):
        ch_data[ch]['subs'] += 1
    if r.get('has_specific_data'):
        ch_data[ch]['structured'] += 1

print(f"\n{'Chapter':45s} {'Tot':>4s} {'Gnd':>4s} {'Fbk':>4s} {'%Gnd':>6s} {'Subs':>4s} {'Struc':>5s}")
print('-'*72)
for ch in sorted(ch_data.keys()):
    d2 = ch_data[ch]
    pct = d2['grounded']/d2['total']*100
    print(f'{ch[:44]:45s} {d2["total"]:4d} {d2["grounded"]:4d} {d2["fallback"]:4d} {pct:5.1f}% {d2["subs"]:4d} {d2["structured"]:5d}')
print('-'*72)
print(f'{"TOTAL":45s} {len(b):4d} {grounded:4d} {fallback:4d} {grounded/len(b)*100:5.1f}%')

# Subsection coverage
subsection_bylaws = {
    '22': 6, '27': 5, '38': 5, '39': 4, '46': 3, '47': 3,
    '48': 3, '50': 2, '75': 5, '78': 2, '88': 2,
    '115': 5, '119': 2, '122': 2, '125': 2, '127': 2, '131': 5,
    '148': 2, '154': 3, '159': 2, '174': 7, '175': 3,
    '12': 2, '13': 4, '14': 4, '17': 3, '19': 3,
    '23': 2, '24': 2, '43': 2, '49': 2, '51': 2,
}
total_expected = sum(subsection_bylaws.values())
total_actual = sum(1 for r in b if r.get('section_code'))
print(f"\nSubsection records: expected {total_expected}, actual {total_actual}")

# Structured data
sd_fields = ['financial_limits','time_limits','member_count_rules','percentage_rules',
             'fraction_rules','notice_requirements','voting_thresholds','quorum_requirements',
             'approval_requirements','eligibility_requirements','penalty_conditions','date_references']
filled = {}
for f in sd_fields:
    filled[f] = sum(1 for r in b if r.get('structured_specific_data',{}).get(f,[]))
print(f"\nStructured data fields filled:")
for f, c in filled.items():
    print(f'  {f:30s} {c:3d}/{len(b)}')

# Benchmark expected sections
bench = json.load(open('tests/retrieval_benchmark.json'))
exp = set()
for q in bench:
    for s in q.get('expected_sections', []):
        exp.add(s)
all_labels = set(r['bylaw_label'] for r in b)
all_nums = set(r['bylaw_number'] for r in b)
# Benchmark refs match on bylaw_number (bare number)
missing_nums = [s for s in exp if s not in all_nums and s not in all_labels]
print(f"\nBenchmark expected sections: {len(exp)}")
print(f"Missing from dataset (by number or label): {sorted(missing_nums) if missing_nums else 'NONE'}")
