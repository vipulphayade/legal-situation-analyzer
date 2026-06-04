import json
d = json.load(open('dataset/bylaws_dataset.json'))
b = d['bylaws']

# Check specific merged byelaws
targets = ['48', '50', '125', '127', '131']
print("=== MERGED BYLAWS (have section_code='') ===")
for bn in targets:
    recs = [r for r in b if r['bylaw_number'] == bn]
    print(f'\nBylaw {bn}: {len(recs)} records')
    for r in recs:
        sc = r.get('section_code', '') or '(none)'
        lbl = r.get('bylaw_label', '')
        title = r.get('title', '')
        lt = r.get('official_legal_text', '')[:100]
        print(f'  {r["id"]} label={lbl} code={sc} | {title}')
        print(f'    text: {lt}')

# Check 49 (grounds for expulsion) and 50 relationship
print('\n=== BYLAW 49-50 Expulsion ===')
for bn in ['49', '50']:
    recs = [r for r in b if r['bylaw_number'] == bn]
    for r in recs:
        print(f'{r["id"]} {r["bylaw_label"]:>8} code={r.get("section_code","")} | {r["title"]}')

# Check bylaw 174 subsections  
print('\n=== BYLAW 174 Complaints ===')
recs = [r for r in b if r['bylaw_number'] == '174']
for r in recs:
    print(f'{r["id"]} {r["bylaw_label"]:>8} code={r.get("section_code","")} | {r["title"]}')

# Source shows these subsections should exist but parent bylaw may be missing
# 48(a) and 48(b) - check if any record has bylaw_label=48(a) or 48(b)
print('\n=== CHECKING FOR MISSING PARENT RECORDS ===')
# For subsections like 48(a), 48(b) - the parent 48 exists separately
# But some records have label "49(a)" which means parent 49 exists as label "49"?
recs_49a = [r for r in b if r['bylaw_label'].startswith('49')]
print(f'Records with label starting with 49: {len(recs_49a)}')
for r in recs_49a:
    print(f'  {r["id"]} {r["bylaw_label"]} code={r.get("section_code","")} {r["title"][:50]}')

recs_48a = [r for r in b if r['bylaw_label'].startswith('48')]
print(f'Records with label starting with 48: {len(recs_48a)}')
for r in recs_48a:
    print(f'  {r["id"]} {r["bylaw_label"]} code={r.get("section_code","")} {r["title"][:50]}')
