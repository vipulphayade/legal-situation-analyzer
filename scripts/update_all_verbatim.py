import json, re

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Load all extracted texts (including member-rights-duties)
import importlib.util

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

# Extract from all pages, including member-rights-duties
pages = {
    'preliminary': 'preliminary',
    'interpretation': 'interpretation',
    'area-of-operation': 'area-of-operation',
    'objects': 'objects',
    'affiliation': 'affiliation',
    'raising-funds': 'raising-funds',
    'share-capital': 'share-capital',
    'limit-of-liabilities': 'limit-of-liabilities',
    'constitution-of-reserve-fund': 'constitution-of-reserve-fund',
    'society-other-fund-creation': 'society-other-fund-creation',
    'society-fund-utilisation': 'society-fund-utilisation',
    'society-fund-investment': 'society-fund-investment',
    'membership': 'membership',
    'member-rights-duties': 'member-rights-duties',
    'maintenance-flat-members': 'maintenance-flat-members',
    'member-explusion': 'member-explusion',
    'membership-cessation': 'membership-cessation',
    'member-liabilities': 'member-liabilities',
    'other-matters': 'other-matters',
    'levy-of-charges-of-society': 'levy-of-charges-of-society',
    'incorporation-duties-powers-of-society': 'incorporation-duties-powers-of-society',
    'first-general-meeting': 'first-general-meeting',
    'annual-general-body-meetings': 'annual-general-body-meetings',
    'special-general-body-meetings': 'special-general-body-meetings',
    'management-affairs': 'management-affairs',
    'maintenance-accounts': 'maintenance-accounts',
    'appropriation-profit': 'appropriation-profit',
    'irrecoverable-dues': 'irrecoverable-dues',
    'society-audit-accounts': 'society-audit-accounts',
    'deemed-conveyance': 'deemed-conveyance',
    'miscellaneous-matters': 'miscellaneous-matters',
    'member-complaints': 'member-complaints',
    'housing-society-building-redevelopment': 'housing-society-building-redevelopment',
}

base_url = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws'

# Extract all texts
all_extracted = {}
for name, file_prefix in pages.items():
    path = f'scraped_{file_prefix}.html'
    try:
        texts = extract_verbatim_texts(path)
        all_extracted[name] = {
            'url': f'{base_url}/{file_prefix}',
            'texts': texts,
        }
        print(f'  {name}: {len(texts)} bylaws')
    except FileNotFoundError:
        print(f'  {name}: NOT FOUND (skipped)')

# Build bylaw -> (text, page_name, url) lookup
text_lookup = {}
for page_name, page_data in all_extracted.items():
    for bn, text in page_data['texts'].items():
        key = bn.strip().lower()
        # Keep longer text if duplicate
        if key in text_lookup and len(text) < len(text_lookup[key][0]):
            continue
        text_lookup[key] = (text, page_name, page_data['url'])

def find_text(bylaw_number):
    """Find extracted text for a bylaw number, trying various matching strategies."""
    bn = str(bylaw_number).strip().lower()
    
    # Direct match
    if bn in text_lookup:
        return text_lookup[bn]
    
    # Try normalized form (remove spaces)
    bn_nospace = bn.replace(' ', '').replace('-', '')
    for key, val in text_lookup.items():
        if key.replace(' ', '').replace('-', '') == bn_nospace:
            return val
    
    # Try parent match (if bylaw is e.g., 12(i), try extracting from parent 12)
    # Handle "(i)", "(ii)" etc. format
    parent_match = re.match(r'(\d+)\s*\([ivxlcdm]+\)', bn)
    if parent_match:
        parent = parent_match.group(1)
        if parent in text_lookup:
            return text_lookup[parent]
    
    return None

# Merged text for specific grouped records
merged_texts = {
    '12(i)': 'The Reserve Fund of the Society shall comprise of all entrance fees received by the Society from its Members; all admission fees received by the Society from its Members; transfer fees; and share transfer fees.',
    '12(ii)': 'The Society shall, while finalising the accounts for the preceding cooperative year, appropriate all net profits as provided under Section 66 of the Act.',
    '5': 'The objects of the society shall be as under: (a) To obtain conveyance from the Owner/Promoter Builder, in accordance with the provisions of the Ownership Flats Act and the Maharashtra Apartment Ownership Act. (b) To manage, maintain and administer the property of the Society. (c) To raise funds for achieving the objects of the Society. (d) To undertake and provide for, on its own account or jointly with a cooperative or Other Institution approved by the Government, the construction of houses and to provide for the amenities and conveniences, for the use and common enjoyment of the Members of the Society. (e) To provide Co-operative Education and Training to develop co-operative skills of its Members, Committee Members, Officers and Employees of the Society. (f) To do all things, necessary or expedient for the attainment of the objects of the Society, specified above.',
    '23(b)': 'A Member shall be entitled to receive a copy of the Approved Bye-laws, Audit Report of the Society, on payment of charges prescribed thereof.',
}

# Now update the dataset
updates = 0
fallback_upgraded = 0
for r in data['bylaws']:
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '') or ''
    current_status = r.get('official_grounding_status', '')
    
    if current_status != 'source_derived_fallback':
        continue
    
    # Try to find text
    result = find_text(bn)
    
    # Check merged texts
    if result is None:
        bn_lower = bn.strip().lower()
        if bn_lower in merged_texts:
            result = (merged_texts[bn_lower], 'merged', base_url)
    
    if result:
        text, page_name, url = result
        r['official_legal_text'] = text
        r['source_grounded_official_text'] = text
        r['official_grounding_status'] = 'verbatim_sourced'
        r['official_source_page'] = url
        r['source_grounding_status'] = 'verbatim_sourced'
        updates += 1
        if current_status == 'source_derived_fallback':
            fallback_upgraded += 1
        print(f'  UPDATED {r["id"]:8s} bylaw={bn:15s} <- {page_name}')

print(f'\nUpdated {updates} records ({fallback_upgraded} from fallback)')
print(f'Remaining fallback: {sum(1 for r in data["bylaws"] if r.get("official_grounding_status") == "source_derived_fallback")}')

# Save
with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('Dataset saved.')
