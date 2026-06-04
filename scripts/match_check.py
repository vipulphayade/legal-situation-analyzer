import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('extracted_all.json', 'r', encoding='utf-8') as f:
    extracted = json.load(f)

# Build lookup from bylaw_number -> records (case-insensitive)
record_lookup = {}
for r in data['bylaws']:
    bn = (r.get('official_bylaw_number', '') or r.get('bylaw_number', '')).strip().lower()
    if bn:
        record_lookup.setdefault(bn, []).append(r)

# Build lookup from bylaw_number -> text
extracted_texts = {}
for page, bylaws in extracted.items():
    for bn, text in bylaws.items():
        key = bn.strip().lower()
        extracted_texts.setdefault(key, []).append((page, text))

# Find matches and mismatches
print("=== EXTRACTED BYLAWS WITH NO MATCHING RECORD ===")
for key, texts in sorted(extracted_texts.items()):
    if key not in record_lookup:
        print(f'  {key} -> NO RECORD (page: {texts[0][0]})')

print("\n=== FALLBACK RECORDS WITH NO EXTRACTED TEXT ===")
for r in data['bylaws']:
    if r.get('official_grounding_status') == 'source_derived_fallback':
        bn = (r.get('official_bylaw_number', '') or r.get('bylaw_number', '')).strip().lower()
        if bn not in extracted_texts:
            # Try partial match
            found = False
            for ekey in extracted_texts:
                if ekey.startswith(bn) or bn.startswith(ekey):
                    found = True
                    break
            if not found:
                print(f'  {r["id"]:8s} bylaw={bn:15s} ({r.get("chapter","")})')
