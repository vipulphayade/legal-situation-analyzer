import re, json

def extract_bylaws(html_source):
    """Extract bylaw number -> text content from scraped HTML."""
    bylaws = {}
    
    # Strategy: find all h4 headings with Bye Law, then capture following content
    # Pattern: <h4[^>]*>...Bye Law No X...</h4> followed by <div class="left-padding-bye-laws">...</div>
    
    # Find all h4 headings  
    h4_pattern = re.compile(r'<(?:h4|h3)[^>]*>(.*?)</(?:h4|h3)>', re.I | re.DOTALL)
    
    # Pre-extract all heading positions and their text
    headings = []
    for m in h4_pattern.finditer(html_source):
        htext = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        headings.append((m.start(), m.end(), htext))
    
    # Now find content divs after each heading
    for i, (hstart, hend, htext) in enumerate(headings):
        # Extract bylaw number from heading text
        bylaw_match = re.search(r'Bye[- ]?Law\s+No\.?\s*(\d+[A-Za-z]?(?:\([a-z]\))*)', htext, re.I)
        if not bylaw_match:
            continue
        
        raw_num = bylaw_match.group(1)
        
        # Normalize: strip leading zeros, handle parenthesized parts
        bylaw_id = raw_num.strip()
        
        # Find the content div after this heading
        after_heading = html_source[hend:]
        # Try to find <div class="left-padding-bye-laws">
        div_match = re.search(r'<div\s+class="left-padding-bye-laws"[^>]*>', after_heading)
        if not div_match:
            # Try finding the next heading or end
            continue
        
        div_start = div_match.start()
        div_content_start = div_match.end()
        
        # Find matching closing div
        depth = 1
        pos = div_content_start
        while depth > 0 and pos < len(after_heading):
            open_tag = after_heading.find('<div', pos)
            close_tag = after_heading.find('</div>', pos)
            if close_tag == -1:
                break
            if open_tag != -1 and open_tag < close_tag:
                depth += 1
                pos = open_tag + 4
            else:
                depth -= 1
                if depth == 0:
                    div_end = close_tag + 6
                else:
                    pos = close_tag + 6
        
        if depth != 0:
            div_end = len(after_heading)
        
        content_html = after_heading[div_start:div_end]
        
        # Check if this div contains sub-bylaw headings - if so, extract sub-bylaws
        sub_items = extract_sub_bylaws(content_html)
        if sub_items:
            for sub_id, sub_text in sub_items.items():
                full_id = f"{bylaw_id}{sub_id}" if sub_id.startswith('(') else f"{bylaw_id} {sub_id}"
                bylaws[full_id] = sub_text
        else:
            text = clean_html(content_html)
            if text:
                bylaws[bylaw_id] = text
    
    return bylaws

def extract_sub_bylaws(content_html):
    """Extract sub-bylaws from within a content div."""
    sub_items = {}
    
    # Find h4 headings within this content
    h4_pattern = re.compile(r'<(?:h4|h3)[^>]*>(.*?)</(?:h4|h3)>', re.I | re.DOTALL)
    sub_headings = []
    for m in h4_pattern.finditer(content_html):
        htext = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        sub_match = re.search(r'Bye[- ]?Law\s+No\.?\s*\d+[A-Za-z]?((?:\([a-z]\))+)', htext, re.I)
        if sub_match:
            sub_headings.append((m.start(), m.end(), sub_match.group(1)))
    
    if not sub_headings:
        return {}
    
    for i, (hstart, hend, sub_id) in enumerate(sub_headings):
        # Content from end of this heading to start of next heading
        if i + 1 < len(sub_headings):
            content = content_html[hend:sub_headings[i+1][0]]
        else:
            content = content_html[hend:]
        
        text = clean_html(content)
        if text:
            sub_items[sub_id] = text
    
    return sub_items

def clean_html(html):
    """Strip HTML tags and return cleaned text."""
    # Remove script and style
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.I | re.DOTALL)
    # Replace br with newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    # Replace p/li tags with newlines
    text = re.sub(r'</?(?:p|li|div|ul|ol|h[1-6])[^>]*>', '\n', text, flags=re.I)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up whitespace
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    return text

def extract_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    return extract_bylaws(html)

if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        print(f'\n=== {path} ===')
        result = extract_from_file(path)
        for bid in sorted(result.keys(), key=lambda x: (int(re.search(r'\d+', x).group() if re.search(r'\d+', x) else '0'), x)):
            text = result[bid]
            print(f'\n--- {bid} ---')
            print(text[:300] + ('...' if len(text) > 300 else ''))
