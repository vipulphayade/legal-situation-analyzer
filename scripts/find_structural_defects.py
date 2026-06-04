import json

d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

# 1. Find records where source has sub-subsections (like 27(a)(b)(c)...) 
#    that are merged in the dataset
# Check: records where the source page has sub-subsections but dataset has one record
print("=== SUBSECTIONS THAT MAY BE MERGED ===")
# Source has sub-subsections for: 27(a)-(e), 38(a)-(e), 39(a)-(d), 47(a)-(c), 48(a)-(b)
# 50(a)-(b), 75(a)-(e), 78(a)-(b), 88(a)-(b), 119(a)-(b), 122(a)-(b), 125(a)-(b)
# 127(a)-(b), 131(a)-(e), 148(a)-(b), 154(a)-(c), 159(a)-(b), 174(a)-(g)
# Check if dataset has records for all of these

source_subs = {
    '27': ['a','b','c','d','e'],
    '38': ['a','b','c','d','e'],
    '39': ['a','b','c','d'],
    '47': ['a','b','c'],
    '48': ['a','b'],
    '50': ['a','b'],
    '75': ['a','b','c','d','e'],
    '78': ['a','b'],
    '88': ['a','b'],
    '119': ['a','b'],
    '122': ['a','b'],
    '125': ['a','b'],
    '127': ['a','b'],
    '131': ['a','b','c','d','e'],
    '148': ['a','b'],
    '154': ['a','b','c'],
    '159': ['a','b'],
    '174': ['a','b','c','d','e','f','g'],
}

for bylaw_num, expected_subs in sorted(source_subs.items()):
    # Find dataset records for this bylaw
    recs = [r for r in b if r['bylaw_number'] == bylaw_num]
    actual_subs = set()
    for r in recs:
        sc = r.get('section_code', '').lower()
        if sc:
            actual_subs.add(sc)
    missing = [s for s in expected_subs if s not in actual_subs and s.upper() not in actual_subs]
    if missing:
        print(f"Bylaw {bylaw_num}: expected subsections {expected_subs}, have {sorted(actual_subs)}, missing {missing}")
    else:
        print(f"Bylaw {bylaw_num}: all {len(expected_subs)} subsections present OK")

# 2. Check records that have section_code but bylaw_label doesn't match pattern
print("\n=== LABEL MISMATCHES ===")
for r in b:
    lbl = r.get('bylaw_label', '')
    sc = r.get('section_code', '')
    bn = r.get('bylaw_number', '')
    if sc and lbl:
        # label should be like "46(b)" or "115(A)"
        expected = f"{bn}({sc})"
        if lbl.upper() != expected.upper():
            print(f"  {r['id']}: label={lbl}, number={bn}, code={sc}, expected={expected}")

# 3. Check chapter assignments - any record in wrong chapter?
print("\n=== UNUSUAL CHAPTER ASSIGNMENTS ===")
# Compare chapter naming vs source. Source uses different chapter names in some cases
# e.g., "VII. MEMBERS, THEIR RIGHTS, RESPONSIBILITY AND LIABILITIES" (source) vs 
# "Members, Their Rights, Responsibilities and Liabilities" (dataset) - close enough
# Check for truly wrong chapter assignments
for r in b:
    lbl = r.get('bylaw_label', '')
    bn = r.get('bylaw_number', '')
    ch = r.get('chapter', '')
    # Spot-check: bylaw 110-140 should be in Management of Affairs
    # bylaw 1-2 should be in Preliminary
    # etc.
    n = bn.lstrip('0')
    try:
        num = int(n)
    except:
        continue
    if 1 <= num <= 2 and ch != 'Preliminary':
        print(f"  {r['id']} {lbl}: chapter={ch}, expected Preliminary")
    if num == 3 and ch != 'Interpretations':
        print(f"  {r['id']} {lbl}: chapter={ch}, expected Interpretations")
    if num == 4 and ch != 'Area of Operation':
        print(f"  {r['id']} {lbl}: chapter={ch}, expected Area of Operation")
    if num == 5 and ch != 'Objects':
        print(f"  {r['id']} {lbl}: chapter={ch}, expected Objects")

# 4. Check for duplicate bylaw_label values  
print("\n=== DUPLICATE BYLAW_LABELS ===")
from collections import Counter
labels = [r.get('bylaw_label','') for r in b]
dupes = {k:v for k,v in Counter(labels).items() if v > 1}
if dupes:
    for lbl, cnt in sorted(dupes.items()):
        recs = [r['id'] for r in b if r.get('bylaw_label','') == lbl]
        print(f"  {lbl}: {cnt}x ({', '.join(recs)})")
else:
    print("  None found")

# 5. Check records with section_code but no subsection in title
print("\n=== RECORDS WITH SECTION CODE BUT GENERIC TITLE ===")
for r in b:
    sc = r.get('section_code', '')
    if sc:
        print(f"  {r['id']} {r['bylaw_label']}: {r['title'][:60]}")
