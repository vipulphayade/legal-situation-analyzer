import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Build bylaw_number -> record id mapping (dry run)
bylaw_to_records = {}
for r in data['bylaws']:
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
    if bn:
        key = str(bn).strip()
        bylaw_to_records.setdefault(key, []).append((r['id'], r.get('official_grounding_status', '')))

# Check which extracted bylaws would match
test_bylaws = ['110','111','112','113','114','115(a)','115(b)','115(c)','115(d)','115(e)',
               '116','117','118','119(a)','119(b)','120','121','122(a)','122(b)',
               '123','124','125(a)','125(b)','126','127(a)','127(b)','128','129','130',
               '131(a)','131(b)','131(c)','131(d)','131(e)','132','133','134','135',
               '136','137','138','139','140',
               '85','86','87','88(a)','88(b)','89','90','91','92','93',
               '94(a)','94(b)','95','96','97','98','99','100','101','102','103',
               '104','105','106','107','108','109']

for bn in test_bylaws:
    if bn in bylaw_to_records:
        for rid, status in bylaw_to_records[bn]:
            print(f'{bn:10s} -> {rid:10s} (status={status})')
    else:
        # Try partial matching
        found = False
        for key, records in bylaw_to_records.items():
            if key.startswith(bn) or key.replace(' ','').lower() == bn.replace(' ','').lower():
                for rid, status in records:
                    print(f'{bn:10s} -> {rid:10s} via key={key} (status={status})')
                found = True
        if not found:
            print(f'{bn:10s} -> NO MATCH')
