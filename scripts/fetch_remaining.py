import urllib.request, os

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

base = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws'

for name in pages:
    path = f'scraped_{name}.html'
    if os.path.exists(path):
        print(f'SKIP {name}: already exists')
        continue
    url = f'{base}/{name}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'OK   {name}: {len(html)} bytes')
    except Exception as e:
        print(f'FAIL {name}: {e}')
