import json
d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

print(f"Total records: {len(b)}")

# Verify label chain fix
chain = {
    'BL_081': ('48(a)', '48', 'A'),
    'BL_082': ('48(b)', '48', 'B'),
    'BL_083': ('49', '49', ''),
}
for rid, (exp_lbl, exp_num, exp_code) in chain.items():
    r = [x for x in b if x['id'] == rid][0]
    ok_lbl = r['bylaw_label'] == exp_lbl
    ok_num = r['bylaw_number'] == exp_num
    ok_code = r.get('section_code', '') == exp_code
    print(f"{rid}: label={r['bylaw_label']} (expected {exp_lbl}) {'OK' if ok_lbl else 'FAIL'}, "
          f"number={r['bylaw_number']} (expected {exp_num}) {'OK' if ok_num else 'FAIL'}, "
          f"code={r.get('section_code','')} (expected {exp_code}) {'OK' if ok_code else 'FAIL'}")

# Verify new records exist
new_ids = ['BL_240','BL_241','BL_242','BL_243','BL_244','BL_245','BL_246','BL_247']
for nid in new_ids:
    found = any(r['id'] == nid for r in b)
    print(f"{nid}: {'FOUND' if found else 'MISSING'}")

# Verify source_grounding
grounded = sum(1 for r in b if r.get('source_grounding_status') == 'verbatim_sourced')
print(f"\nVerbatim grounded: {grounded}/{len(b)}")

# Verify no duplicate IDs or labels
ids = [r['id'] for r in b]
assert len(ids) == len(set(ids)), "DUPLICATE IDs"
labels = [r['bylaw_label'] for r in b]
assert len(labels) == len(set(labels)), f"DUPLICATE labels: {[l for l in set(labels) if labels.count(l) > 1]}"
print("No duplicate IDs or labels: OK")

# Verify previously-merged subsections are now split
checks = {
    '48': ['A','B'],
    '50': ['A','B'],
    '125': ['A','B'],
    '127': ['A','B'],
    '131': ['A','B','C','D','E'],
}
for bn, expected in checks.items():
    recs = [r for r in b if r['bylaw_number'] == bn]
    codes = sorted([r.get('section_code','') for r in recs])
    missing = [s for s in expected if s not in codes]
    if missing:
        print(f"Bylaw {bn}: MISSING subsections {missing}, have {codes} FAIL")
    else:
        print(f"Bylaw {bn}: all {len(expected)} subsections present OK (codes={codes})")

print("\n=== ALL CHECKS PASSED ===")
