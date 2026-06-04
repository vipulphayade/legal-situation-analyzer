import json, re, subprocess, sys

# Extract from all scraped pages
pages = [
    'preliminary', 'interpretation', 'area-of-operation', 'objects', 'affiliation',
    'raising-funds', 'share-capital', 'limit-of-liabilities',
    'constitution-of-reserve-fund', 'society-other-fund-creation',
    'society-fund-utilisation', 'society-fund-investment',
    'membership', 'maintenance-flat-members', 'member-explusion',
    'membership-cessation', 'member-liabilities', 'other-matters',
    'levy-of-charges-of-society', 'incorporation-duties-powers-of-society',
    'maintenance-accounts', 'appropriation-profit', 'irrecoverable-dues',
    'society-audit-accounts', 'deemed-conveyance', 'miscellaneous-matters',
    'housing-society-building-redevelopment',
]

# Re-use the extraction function
import importlib.util
spec = importlib.util.spec_from_file_location("extract", "scripts/extract_verbatim.py")
extract_mod = importlib.util.module_from_spec(spec)
# We only need the function, run as module is complex
# Let's just inline the extraction

import re

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

all_results = {}
for name in pages:
    path = f'scraped_{name}.html'
    results = extract_verbatim_texts(path)
    if results:
        print(f'\n=== {name} ({len(results)} bylaws) ===')
        for bid in sorted(results.keys(), key=lambda x: (
            int(re.search(r'\d+', x).group()),
            x
        )):
            text = results[bid]
            print(f'  {bid}: {text[:100]}...')
        all_results[name] = results
    else:
        print(f'\n=== {name} (no bylaws found) ===')

# Save for later use
with open('extracted_all.json', 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
