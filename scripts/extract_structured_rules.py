import json, re

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

def extract_field(text, field):
    if not text:
        return []
    results = []
    t = text.lower()
    
    if field == 'time_limits':
        # "within X days/months/years", "X clear days", "within X weeks", "X months", "period of X"
        for m in re.finditer(r'(\d+)\s*(clear\s+)?(day|days|month|months|year|years|week|weeks)(\s+of|\s+before|\s+after|\s+from|\s+of\s+the|\s+prior\s+to)', t):
            results.append({'value': f'{m.group(1)} {m.group(3)}', 'text': m.group(0).strip()[:80]})
        for m in re.finditer(r'within\s+(a\s+)?(period\s+of\s+)?(\d+)\s*(day|days|month|months|year|years|week|weeks)', t):
            results.append({'value': f'{m.group(3)} {m.group(4)}', 'text': m.group(0).strip()[:80]})
        for m in re.finditer(r'(?:not less than|at least|not exceeding|exceeding|within|after|before)\s+(\d+)\s*(day|days|month|months|year|years|week|weeks)', t):
            results.append({'value': f'{m.group(1)} {m.group(2)}', 'text': m.group(0).strip()[:80]})
        for m in re.finditer(r'period\s+of\s+(\d+)\s*(year|years|month|months|day|days)', t):
            val = f'{m.group(1)} {m.group(2)}'
            if not any(r['value'] == val for r in results):
                results.append({'value': val, 'text': m.group(0).strip()[:80]})
                    
    elif field == 'financial_limits':
        for m in re.finditer(r'Rs\.?\s*([\d,]+(?:\.\d+)?)', text):
            results.append({'value': f'Rs. {m.group(1)}', 'text': m.group(0).strip()[:80]})
        for m in re.finditer(r'(?:rupees|rs\.?)\s+([\w\s]+?)(?:\b(?:shall|per|for|and|the|\d|$))', t):
            pass  # complex, skip for now
        # Also capture percentage-based financial rules
        for m in re.finditer(r'(?:rate|interest|penalty|charge)\s+(?:at|of|is)\s+(\d+)\s*%', t):
            results.append({'value': f'{m.group(1)}%', 'text': m.group(0).strip()[:80]})
        for m in re.finditer(r'(\d+)\s*%\s*(?:per\s+)?(?:annum|interest|penalty|p\.a\.)', t):
            results.append({'value': f'{m.group(1)}% per annum', 'text': m.group(0).strip()[:80]})
                    
    elif field == 'voting_thresholds':
        for m in re.finditer(r'(majority|two.?thirds?|2/3rd?s?|three.?fourth|3/4th|simple majority|absolute majority|unanimous|75%\s*|2/3\s*)', t):
            results.append({'value': m.group(1), 'text': m.group(0).strip()[:80]})
                    
    elif field == 'quorum_requirements':
        for m in re.finditer(r'(quorum|2/3rd\s+of\s+the\s+total|majority\s+of\s+members|less\s+than\s+\d+|20\s*,\s*whichever\s+is\s+less)', t):
            val = m.group(1)
            if len(val) > 3:
                results.append({'value': val[:60], 'text': m.group(0).strip()[:80]})
                    
    elif field == 'eligibility_requirements':
        for m in re.finditer(r'(?:no\s+)?(?:person|member|individual|firm|company|body\s+corporate)\s+(?:shall\s+)?(?:be\s+)?(?:eligible|entitled|disqualified|qualified|admitted)\s+[^.]*\.', text, re.I):
            results.append({'value': m.group(0).strip()[:120], 'text': m.group(0).strip()[:120]})
                    
    elif field == 'approval_requirements':
        for m in re.finditer(r'(?:prior\s+)?(?:permission|approval|consent|sanction|authorization|resolution)\s+(?:of|in\s+writing|from|by)\s+(?:the\s+)?(?:Committee|General\s+Body|Registering\s+Authority|Society)[^.]*\.', text, re.I):
            results.append({'value': m.group(0).strip()[:120], 'text': m.group(0).strip()[:120]})
                    
    elif field == 'penalty_conditions':
        for m in re.finditer(r'(?:penalty|forfeit|expelled|expulsion|disqualified|interest\s+at|fine|breach\s+of|liable|shall\s+cease)[^.]*\.', text, re.I):
            results.append({'value': m.group(0).strip()[:120], 'text': m.group(0).strip()[:120]})
                    
    elif field == 'date_references':
        for m in re.finditer(r'(\d+)(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)', text, re.I):
            results.append({'value': m.group(0), 'text': m.group(0).strip()[:80]})
        for m in re.finditer(r'(31st March|30th September|1st April|close\s+of\s+(?:every|each)\s+(?:co-operative|financial)\s+year)', t):
            if not any(r['value'] == m.group(1) for r in results):
                results.append({'value': m.group(1), 'text': m.group(0).strip()[:80]})
                    
    elif field == 'section_rule_references':
        for m in re.finditer(r'(?:Section|Sec\.?|Rule|Bye[-\s]?law\s+No\.?)\s+(\d+[A-Za-z]?(?:\([^)]*\))*(?:\s+(?:of\s+the\s+)?(?:Act|Rules|Bye[-\s]?laws))?)', text, re.I):
            results.append({'value': m.group(0).strip()[:80], 'text': m.group(0).strip()[:80]})
                    
    return results

# Process all records
targets = ['eligibility_requirements','quorum_requirements','voting_thresholds',
           'approval_requirements','time_limits','financial_limits',
           'penalty_conditions','date_references','section_rule_references']

total_updates = 0
for r in data['bylaws']:
    text = r.get('official_legal_text', '')
    if not text:
        continue
    ssd = r.setdefault('structured_specific_data', {})
    changed = False
    for field in targets:
        extracted = extract_field(text, field)
        # Only update if currently empty and extraction found results
        if not ssd.get(field) and extracted:
            ssd[field] = extracted
            changed = True
    if changed:
        total_updates += 1

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'Records improved: {total_updates}')

# Coverage stats
for field in targets:
    filled = sum(1 for r in data['bylaws'] if r.get('structured_specific_data', {}).get(field))
    print(f'{field:30s} {filled}')
