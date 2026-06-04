import urllib.request, re

url = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode('utf-8', errors='replace')

# Find all chapter-section links
for match in re.finditer(r'<a href="([^"]+)"[^>]*>XIII\.|XIV\.|XV\.|XVI\.|XVII\.|XVIII\.|XIX\.', html, re.I):
    print(match.group(0)[:200])

# Search specifically for audit, books, redevelopment links
for term in ['audit', 'books of account', 'redevelopment', 'maintenance of books']:
    for match in re.finditer(r'href="([^"]*' + re.escape(term.replace(' ', '-')) + r'[^"]*)"', html, re.I):
        print(f'{term}: {match.group(1)}')
    for match in re.finditer(r'href="([^"]*' + re.escape(term.replace(' ', '')) + r'[^"]*)"', html, re.I):
        print(f'{term} (no space): {match.group(1)}')

# Extract all unique chapter page URLs
chapter_urls = set()
for match in re.finditer(r'<a href="(https://mysocietyclub\.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/[^"]+)"', html):
    chapter_urls.add(match.group(1))
print(f'\nAll unique chapter URLs ({len(chapter_urls)}):')
for u in sorted(chapter_urls):
    print(f'  {u}')
