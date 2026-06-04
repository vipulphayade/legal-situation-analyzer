import json
from collections import Counter

d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']
bench = json.load(open('tests/retrieval_benchmark.json'))

# Source page URLs by chapter (from TOC analysis)
chapter_source_pages = {
    "Preliminary": "preliminary",
    "Interpretations": "interpretation",
    "Area of Operation": "area-of-operation",
    "Objects": "objects",
    "Affiliation": "affiliation",
    "Funds, Their Utilisation and Investment": "raising-funds share-capital limit-of-liabilities constitution-of-reserve-fund society-other-fund-creation society-fund-utilisation society-fund-investment",
    "Members, Their Rights, Responsibilities and Liabilities": "membership member-rights-duties",
    "Responsibilities and Liabilities of Members": "maintenance-flat-members member-explusion membership-cessation flat-restriction-holding-more-than-one-flat member-liabilities other-matters",
    "Levy of Charges of the Society": "levy-of-charges-of-society",
    "Incorporation of Duties and Powers of the Society": "incorporation-duties-powers-of-society",
    "General Meetings": "first-general-meeting annual-general-meeting special-general-meeting",
    "Management of the Affairs of the Society": "management-affairs",
    "Maintenance of Books of Account and Registers": "UNKNOWN_404",
    "Appropriation of Profits": "UNKNOWN_404",
    "Write Off of Irrecoverable Dues": "UNKNOWN_404",
    "Audit of Accounts of the Society": "UNKNOWN_404",
    "Conveyance, Repairs and Maintenance of Property": "conveyance-repairs-maintenance",
    "Other Miscellaneous Matters": "other-miscellaneous-matters",
    "Redressal of Members Complaints": "UNKNOWN_404",
    "Redevelopment": "UNKNOWN_404",
}

# Query frequency from benchmark
query_chapters = Counter()
for q in bench:
    for s in q.get('expected_sections', []):
        query_chapters[s] += 1

# Map bylaw numbers to chapters
bylaw_to_chapter = {}
for r in b:
    bn = r.get('bylaw_number', '')
    if bn:
        bylaw_to_chapter[bn] = r.get('chapter', '')

# Count benchmark queries per chapter
chapter_query_count = Counter()
for bn, count in query_chapters.items():
    ch = bylaw_to_chapter.get(bn, 'UNKNOWN')
    chapter_query_count[ch] += count

print(f"{'Priority':>8s} | {'Chapter':45s} | {'Fallback':>7s} | {'Benchmark Q':>10s} | {'Source Pages':>11s} | {'Effort':>6s}")
print('-' * 100)

# Build priority list
priority_data = []
for ch, recs_data in sorted(chapter_source_pages.items()):
    fallback = sum(1 for r in b if r.get('chapter') == ch and r.get('source_grounding_status') != 'verbatim_sourced')
    grounded = sum(1 for r in b if r.get('chapter') == ch and r.get('source_grounding_status') == 'verbatim_sourced')
    total = fallback + grounded
    if total == 0:
        continue
    bq = chapter_query_count.get(ch, 0)
    src = chapter_source_pages.get(ch, 'UNKNOWN')
    status = "VERIFIED" if "UNKNOWN" not in src else "404"
    effort = f"{len(src.split())} pg"
    priority_data.append((fallback, bq, total, ch, status, effort, grounded))

priority_data.sort(key=lambda x: (-x[0], -x[1]))

for i, (fb, bq, total, ch, status, effort, gnd) in enumerate(priority_data, 1):
    print(f'{i:>8d} | {ch[:44]:45s} | {fb:7d} | {bq:10d} | {status:11s} | {effort:6s}')

total_fb = sum(p[0] for p in priority_data)
total_bq = sum(p[1] for p in priority_data)
total_recs = sum(p[2] for p in priority_data)
print('-' * 100)
print(f'{"TOTAL":>8s} | {"":45s} | {total_fb:7d} | {total_bq:10d} |')

# Ease of recovery
print(f'\n=== EASE OF RECOVERY ===')
print(f'Verified pages (fetchable):')
for fb, bq, total, ch, status, effort, gnd in priority_data:
    if status == "VERIFIED" and fb > 0:
        print(f'  {ch[:40]:40s} {fb:3d} fallback, {effort}')

print(f'\n404 pages (need investigation):')
for fb, bq, total, ch, status, effort, gnd in priority_data:
    if status == "404":
        print(f'  {ch[:40]:40s} {fb:3d} fallback')
