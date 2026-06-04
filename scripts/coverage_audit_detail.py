import json
d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

problem_chapters = [
    'Appropriation of Profits',
    'Maintenance of Books of Account and Registers',
    'Audit of Accounts of the Society',
    'Redressal of Members Complaints',
    'Redevelopment',
    'Write Off of Irrecoverable Dues',
]
print('=== CHAPTERS WITH UNVERIFIED SOURCE PAGES ===')
for ch in problem_chapters:
    recs = [r for r in b if r['chapter'] == ch]
    verb = sum(1 for r in recs if r.get('source_grounding_status') == 'verbatim_sourced')
    ai = len(recs) - verb
    print(f'{ch}: {len(recs)} recs, verbatim={verb}, ai={ai}')

print('\n=== KEY STRUCTURED DATA ===')
for r in b:
    sd = r.get('structured_specific_data', {})
    flags = []
    for k, v in sd.items():
        if v:
            flags.append(k)
    if flags:
        print(f'{r["id"]} {r["bylaw_label"]:>8}: {flags}')

# Categorize verbatim records
print('\n=== VERBATIM SOURCED RECORDS ===')
for r in b:
    if r.get('source_grounding_status') == 'verbatim_sourced':
        print(f'{r["id"]} {r["bylaw_label"]:>8}: {r["chapter"][:40]} | {r["title"][:50]}')
        print(f'  Legal text: {r["official_legal_text"][:100]}...')

# Benchmark - count unique expected sections
bench = json.load(open('tests/retrieval_benchmark.json'))
print('\n=== BENCHMARK COVERAGE ===')
exp = set()
for q in bench:
    for s in q.get('expected_sections', []):
        exp.add(s)
print(f'Unique expected sections in benchmark: {len(exp)}')
print(f'Sections: {sorted(exp)[:20]}...')
all_bl = set(r['bylaw_label'] for r in b)
missing_in_dataset = exp - all_bl
print(f'Expected sections missing from dataset: {missing_in_dataset}')
