import json

with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for r in data:
    if r.get('chapter_slug') == 'member-rights-duties':
        vl = r.get('verbatim_source_link', '') or ''
        text = r.get('text', '') or ''
        print(f'{r["id"]:10s} | {str(r.get("bylaw_number","")):15s} | labels={r.get("labels",[])} | vl={vl[:50]} | text={text[:80]}')
