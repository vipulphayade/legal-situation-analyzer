import json, re

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

# Build bylaw_number -> record lookup (normalized)
bylaw_to_record = {}
for r in data['bylaws']:
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
    if bn:
        key = bn.strip().lower().replace(' ', '').replace('-', '')
        bylaw_to_record[key] = r

def find_record(bylaw_num):
    key = bylaw_num.strip().lower().replace(' ', '').replace('-', '')
    rec = bylaw_to_record.get(key)
    if rec:
        return rec
    # Try parent match: e.g., "22(a)" -> "22(a)" or just "22"
    for k, r in bylaw_to_record.items():
        if k.startswith(key) or key.startswith(k):
            return r
    return None

def extract_references(text):
    """Extract explicit bylaw/section references from legal text."""
    refs = []
    
    # Only match singular "bye-law" (not plural "bye-laws")
    # Pattern 1: "bye-law No. X" / "bye-law no. X" / "bye-law No.X" / "Bye Law No. X"
    for m in re.finditer(r'(?:bye[- ]?law|Bye[- ]?Law|byelaw)\s+No\.?\s*(\d+[A-Za-z]?(?:\([a-z]\))*)', text):
        refs.append(m.group(1))
    
    # Pattern 2: "bye-law X" (without No.) - require word boundary before number
    for m in re.finditer(r'(?:bye[- ]?law|byelaw)\s+(\d+[A-Za-z]?(?:\([a-z]\))*)\b', text, re.I):
        num = m.group(1)
        if num not in refs:
            refs.append(num)
    
    return refs

# Build source-grounded cross-references
refs_created = 0
records_with_refs = 0

for r in data['bylaws']:
    text = r.get('official_legal_text', '')
    if not text:
        continue
    
    raw_refs = extract_references(text)
    if not raw_refs:
        continue
    
    # Deduplicate
    seen = set()
    links = []
    for raw_num in raw_refs:
        target = find_record(raw_num)
        if target and target['id'] != r['id']:
            link_key = target['id']
            if link_key not in seen:
                seen.add(link_key)
                links.append({
                    'related_id': target['id'],
                    'bylaw_label': target.get('official_bylaw_number', target.get('bylaw_label', '')),
                    'title': target.get('title', ''),
                    'source_text': f'bye-law No. {raw_num}',
                    'reference_type': 'explicit_citation',
                })
                refs_created += 1
    
    r['source_cross_references'] = links
    if links:
        records_with_refs += 1

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'Records with source_cross_references: {records_with_refs}')
print(f'Total source-grounded links created: {refs_created}')

# Show examples
shown = 0
for r in data['bylaws']:
    scr = r.get('source_cross_references', [])
    if scr and shown < 5:
        print(f"\n{r['id']} ({r.get('official_bylaw_number','')}) -> {len(scr)} links:")
        for link in scr[:3]:
            print(f"  {link['related_id']} ({link['bylaw_label']}): {link['title'][:50]}")
        shown += 1

# Compare with existing related_bylaws
total_existing = sum(len(r.get('related_bylaws', [])) for r in data['bylaws'])
total_source = sum(len(r.get('source_cross_references', [])) for r in data['bylaws'])
print(f'\nAI-generated related_bylaws entries: {total_existing}')
print(f'Source-grounded cross_references: {total_source}')
print(f'Overlap (records with both): {sum(1 for r in data["bylaws"] if r.get("related_bylaws") and r.get("source_cross_references"))}')
