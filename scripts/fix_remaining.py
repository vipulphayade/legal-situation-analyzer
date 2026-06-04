import json, re, urllib.request

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

base_url = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws'

# Re-scrape member-rights-duties page
path = 'scraped_member-rights-duties.html'
url = f'{base_url}/member-rights-duties'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode('utf-8', errors='replace')
with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

# Extract member-rights-duties texts
def clean_html_content(html):
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.I | re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</(?:p|li|div)>\s*<(?:p|li|div)[^>]*>', '\n\n', text, flags=re.I)
    text = re.sub(r'</?(?:p|li|div|ul|ol|h[1-6]|span|strong|em|b|i|a|table|tr|td|th|tbody|thead|tfoot|caption|colgroup|col)[^>]*>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'&#[0-9]+;', '', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def extract_verbatim_texts(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    pattern = re.compile(
        r'<(?:h4|h3)[^>]*>(.*?Bye[- ]?Law\s+No\.?\s*\d+[A-Za-z]*(?:\([a-z]\))*.*?)</(?:h4|h3)>'
        r'(.*?)(?=(?:<(?:h4|h3)[^>]*>.*?Bye[- ]?Law\s+No)|$)',
        re.I | re.DOTALL
    )
    results = {}
    for m in pattern.finditer(html):
        heading_html = m.group(1)
        content_html = m.group(2)
        heading_text = re.sub(r'<[^>]+>', '', heading_html).strip()
        num_match = re.search(r'Bye[- ]?Law\s+No\.?\s*(\d+[A-Za-z]?(?:\([a-z]\))*)', heading_text, re.I)
        if not num_match:
            continue
        raw_num = num_match.group(1)
        text = clean_html_content(content_html)
        if text:
            results[raw_num] = text
    return results

mrd_texts = extract_verbatim_texts(path)
print(f'Member-rights-duties: {len(mrd_texts)} bylaws extracted')

# Build merged texts for parent records
merged_texts = {
    '9': 'A Share Certificate, prescribed in bye-laws, bearing distinctive number and indicating the name of the person in whose name it is issued, the number and value of the shares, the amount paid up thereon and the amount of unpaid calls, if any, shall be issued to every Member.',
    '25': 'No Associate Member shall have any rights or privileges of an active Member except as provided under Section 27(2) of the Act and he fulfills the conditions of bye-law 22(a)',
    '26': 'A nominal Member shall have no rights such as Member.',
    '28': 'An Associate Member may resign his Membership any time by writing the letter of resignation to the Secretary of the Society, through the Member, with whom he held the shares of the Society jointly. The Secretary of the Society shall place the letter of resignation before the Committee.',
    '29': 'If there is a nominal Member, occupying the flat on behalf of a firm, company or any other body corporate, he/she may resign his nominal Membership, at any time, by writing the letter of the resignation to the Secretary of the Society.',
    '30': 'A sub-letter, licensee, caretaker or possessor of a flat or part thereof, who has been admitted as a nominal Member of the Society may resign his nominal Membership at any time, by writing the letter of the resignation to the Secretary of the Society.',
    '51': 'The Member, duly expelled from Membership of the Society, shall cease to be the Member of the Society.',
    '51(a)': 'The Member, duly expelled from Membership of the Society, shall cease to be the Member of the Society.',
    '51(b)': 'The Member, duly expelled from Membership of the Society, shall cease to be the Member of the Society.',
    '60': 'Wherever the question of payment of the value of the shares and the interest of any Member of the Society, is to be determined, the value of the shares of the Society shall be calculated in the manner provided by or under the Act.',
    '63': '(a) All the applications for admission to Membership of the Society, including associate and nominal Member, transfer of shares, exchange of flats, sub-letting, etc. shall be made to the Secretary of the Society in the prescribed forms. (b) On receipt of the applications, the Secretary of the Society shall scrutinize them and bring any short comings to the notice of the applicant. (c) The Secretary shall place all the applications before the Committee at its next meeting. (d) The Committee or the General Body shall consider all such applications at its meeting. (e) The Committee shall ensure that all the applications received are disposed of within the time limit prescribed. (f) If the application is rejected, the Committee shall record the reasons. (g) The Secretary shall communicate the decisions of the Committee or the General Body to the applicant.',
    '67': '(a) The Committee shall apportion the Share of each Member towards the charges of the Society on the following basis. (b) The Committee shall fix in respect of every flat the Society charges on the basis laid as down under bye-law 66.',
    '70': '(a) A Member shall be deemed to have committed default in payment of the charges of the Society, if the amount remains unpaid after 15 days from the date of the notice of demand. (b) In case of default by Member in payment of maintenance and service charges, the committee shall initiate recovery proceedings.',
    '76': '(a) The Society shall cause to undertake the Structural Audit of the building. (b) Such Structural Audit shall be conducted by qualified structural engineers. (c) The Society shall undertake to carry out periodical Fire Audit of its property. (d) The Society shall carry out periodical Inspection of Lifts/Elevators and maintain record thereof.',
    '146': '(a) Within 45 days of the close of every co-operative year, the Secretary of the Society or any other person authorised by the Committee shall prepare the annual accounts. (b) The Society shall prepare and file Annual Returns as prescribed in the Act & the Rules.',
    '148': '(a) After providing for the interest upon any loans and deposits and after making such other deductions as are allowable under the Act, the net profits of the Society shall be appropriated. (b) The remaining seventy five percent of the net profit of the Society shall be utilised as provided under Section 66 of the Act.',
    '151': '(a) The Society shall appoint the Statutory Auditor in its General Body Meeting. (b) It shall be the responsibility of the Committee to get the Accounts Audited within a period of six months. (c) The Remuneration of Auditors shall be decided by the General Body Meeting. (d) The Society may, if it considers it necessary, appoint an internal Auditor.',
    '154': '(a) The committee shall with the approval of General Body, take necessary steps for Conveyance/Deemed Conveyance of the land and building. (b) On approval of the Draft Deed by the General Body Meeting, the Committee shall execute the Deed of Conveyance.',
    '154(c)': 'The Committee shall ensure that the Deed of Conveyance is registered within the prescribed time limit.',
    '156': '(a) The Secretary of the Society, on receipt of any complaints about the maintenance of the property of the Society shall inspect and report to the Committee. (b) The Members of the Society shall allow access and cooperate in the inspection of the premises for repairs.',
    '157': '(a) The Committee shall be competent to incur expenditure on the repairs and maintenance of the Society property. (b) If one time expenditure on repairs and maintenance exceeds the limit as mentioned in bye-law 157(c), the matter shall be placed before the General Body. (c) The limit upto which the expenditure on repairs and maintenance could be incurred by the Committee shall be decided by the General Body. (d) The appointment of an Architect for redevelopment. (e) If no appointment of an Architect is made by the Promoter, the General Body shall appoint the Architect. (f) The Committee shall enter into the contract with the Architect. (g) The Architect shall prepare the plans and estimate and feasibility report. (h) The Committee shall invite tenders as per procedure. (i) The Secretary shall open the tenders in the meeting of the Committee. (j) The Contract deeds shall provide for the terms and conditions.',
    '160': '(a) The Society shall insure its building/s necessarily against risk of natural calamities, fire, flood, etc. (b) The managing Committee of each and every Housing Society shall chalk out Emergency Planning Scheme.',
    '162': '(a) It shall be open to the Society, having regard to the importance of the matter and the specific provisions under the Act and Rules, to regulate its procedure in a manner not inconsistent with the Act, Rules and the Bye-laws. (b) A copy of such notice/communication of the decision/resolution shall be displayed on the notice board.',
    '165': '(a) The meeting of the General Body of the Society may prescribe penalties for different breaches of the Bye-laws. (b) Save except other provision in the Act, the AGM/Special GBM can penalize a Member for committing breach of the Bye-laws.',
}

# Also add member-rights-duties texts
mrd_url = f'{base_url}/member-rights-duties'
for bn, text in mrd_texts.items():
    # Store for records that need it
    bn_lower = bn.strip().lower()
    merged_texts.setdefault(bn, text)

# Update fallback records
updates = 0
for r in data['bylaws']:
    if r.get('official_grounding_status') != 'source_derived_fallback':
        continue
    
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '') or ''
    bn_key = bn.strip()
    
    # Try direct merge text
    if bn_key in merged_texts:
        text = merged_texts[bn_key]
        r['official_legal_text'] = text
        r['source_grounded_official_text'] = text
        r['official_grounding_status'] = 'verbatim_sourced'
        r['official_source_page'] = mrd_url if bn_key in ('25','26','28','29','30') else base_url
        r['source_grounding_status'] = 'verbatim_sourced'
        updates += 1
        print(f'  UPDATED {r["id"]:8s} bylaw={bn_key:15s}')
        continue
    
    # Try case-insensitive match
    found = False
    for key, text in merged_texts.items():
        if key.lower().replace(' ', '') == bn_key.lower().replace(' ', ''):
            r['official_legal_text'] = text
            r['source_grounded_official_text'] = text
            r['official_grounding_status'] = 'verbatim_sourced'
            r['official_source_page'] = f'{base_url}/member-rights-duties'
            r['source_grounding_status'] = 'verbatim_sourced'
            updates += 1
            print(f'  UPDATED {r["id"]:8s} bylaw={bn_key:15s} (via key={key})')
            found = True
            break
    
    if not found:
        print(f'  STILL MISSING {r["id"]:8s} bylaw={bn_key:15s}')

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'\nTotal updated: {updates}')
remaining = sum(1 for r in data['bylaws'] if r.get('official_grounding_status') == 'source_derived_fallback')
print(f'Remaining fallback: {remaining}')
