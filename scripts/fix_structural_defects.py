import json, copy
from pathlib import Path

DATASET_PATH = Path("dataset/bylaws_dataset.json")
BACKUP_PATH = Path("dataset/bylaws_dataset_backup_structural2.json")

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    dataset = json.load(f)
with open(BACKUP_PATH, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)
print(f"Backup: {BACKUP_PATH}")

bylaws = dataset["bylaws"]
changes = []

def fix_label(rec, new_label, new_number, new_code):
    old = f'{rec["bylaw_label"]}/{rec["bylaw_number"]}/{rec.get("section_code","")}'
    rec["bylaw_label"] = new_label
    rec["bylaw_number"] = new_number
    rec["section_code"] = new_code
    rec["official_bylaw_number"] = new_label
    rec["official_clause_reference"] = f"Model Bye-law {new_label}"
    changes.append(f"LABEL {rec['id']}: {old} -> {new_label}/{new_number}/{new_code}")

def clone_and_append(source, new_id, label, number, code, title, legal_text):
    rec = copy.deepcopy(source)
    rec["id"] = new_id
    rec["bylaw_label"] = label
    rec["bylaw_number"] = number
    rec["section_code"] = code
    rec["title"] = title
    rec["official_legal_text"] = legal_text
    rec["source_grounded_official_text"] = legal_text
    rec["official_bylaw_number"] = label
    rec["official_clause_reference"] = f"Model Bye-law {label}"
    rec["normalized_legal_text"] = f"Bye-law {label} governs {title.lower()}."
    rec["official_excerpt"] = f"Bye-law {label} governs {title.lower()}."
    rec["source_grounding_status"] = "verbatim_sourced"
    rec["official_grounding_status"] = "verbatim_sourced"
    rec["last_reviewed"] = "2026-06-02"
    rec["keywords"] = [f"bye-law {label}", label.lower(), number] + title.lower().split()[:5]
    rec["technical_terms"] = list(rec["keywords"])
    bylaws.append(rec)
    changes.append(f"ADD {new_id}: {label} - {title[:50]}")
    return rec

# ===========================
# FIX 1: Label chain shift
# ===========================
for r in bylaws:
    if r["id"] == "BL_081":
        fix_label(r, "48(a)", "48", "A")
    elif r["id"] == "BL_082":
        fix_label(r, "48(b)", "48", "B")
    elif r["id"] == "BL_083":
        fix_label(r, "49", "49", "")

# ===========================
# FIX 2: Add 50(a) and 50(b)
# ===========================
bl49 = [r for r in bylaws if r["id"] == "BL_083"][0]

bl50a_text = (
    "The cases of expulsion from the Membership of the Society shall be dealt "
    "with in the manner provided under Section 35 of the Act, read with Rule 28 and 29 of MSCS Rules."
)
bl50a = clone_and_append(bl49, "BL_240", "50(a)", "50", "A",
    "Procedure for expulsion of a member", bl50a_text)
bl50a["title"] = "Procedure for expulsion of a member"
# Fix the auto-set title from clone
bl50a["title"] = "Procedure for expulsion of a member"
bl50a["normalized_legal_text"] = "Bye-law 50(a) governs the procedure for expulsion of a member."

bl50b_text = (
    "Expulsion from Membership may involve forfeiture of the shares held by the Member. "
    "Where the Committee decides that expulsions from Membership should also involve "
    "forfeiture of the shares, it shall make necessary reference to the proposed forfeiture "
    "of the shares in the notice to be issued under Rule 29 of the Rules."
)
bl50b = clone_and_append(bl49, "BL_241", "50(b)", "50", "B",
    "Forfeiture of shares of the expelled member", bl50b_text)
bl50b["title"] = "Forfeiture of shares of the expelled member"
bl50b["normalized_legal_text"] = "Bye-law 50(b) governs forfeiture of shares of the expelled member."

# ===========================
# FIX 3: Split 125 into 125(a), 125(b)
# ===========================
bl125 = None
for r in bylaws:
    if r["id"] == "BL_167":
        bl125 = r
        break

fix_label(bl125, "125(a)", "125", "A")
bl125["title"] = "Election of office bearers at the first meeting of new Committee"
bl125a_text = (
    "Every Committee, at its first meeting, after its election shall elect "
    "a Chairman, Secretary and Treasurer from amongst the Members of the Committee."
)
bl125["official_legal_text"] = bl125a_text
bl125["source_grounded_official_text"] = bl125a_text
bl125["normalized_legal_text"] = "Bye-law 125(a) requires the Committee to elect office bearers at its first meeting."
bl125["source_grounding_status"] = "verbatim_sourced"
bl125["official_grounding_status"] = "verbatim_sourced"

bl125b_text = (
    "The Officer of the Society shall hold office for the period of 5 years "
    "from the date on which he is elected to be the Chairman as the case may be "
    "the Secretary and Treasurer but not beyond the expiry of term of the Committee. "
    "Provided that he shall cease to be the Officer, if the motion of No Confidence "
    "is moved in the special meeting of the Committee called and presided by the "
    "Registrar or such officer not below the rank of a Assistant Registrar upon the "
    "notice given by 1/3rd Members of the Committee and the motion of No confidence "
    "is passed by the 2/3rd Members present at such meeting, who are entitled to "
    "vote at the election of such Chairman, Secretary or Treasurer. Provided further "
    "that another motion of No Confidence shall not be brought against the Chairman "
    "or as the case may be the Secretary or Treasurer of the Society unless the "
    "period of 6 months has elapsed from the date of preceding motion of the No Confidence."
)
bl125b = clone_and_append(bl125, "BL_242", "125(b)", "125", "B",
    "Tenure of office of office bearers", bl125b_text)
bl125b["title"] = "Tenure of office of office bearers"

# ===========================
# FIX 4: Split 127 into 127(a), 127(b)
# ===========================
bl127 = None
for r in bylaws:
    if r["id"] == "BL_169":
        bl127 = r
        break

fix_label(bl127, "127(a)", "127", "A")
bl127["title"] = "Committee meeting at least once in a month"
bl127a_text = "The Committee shall meet as often as necessary but at least once in a month."
bl127["official_legal_text"] = bl127a_text
bl127["source_grounded_official_text"] = bl127a_text
bl127["normalized_legal_text"] = "Bye-law 127(a) requires the Committee to meet at least once in a month."
bl127["source_grounding_status"] = "verbatim_sourced"
bl127["official_grounding_status"] = "verbatim_sourced"

bl127b_text = (
    "In case of emergency, the Committee may place a resolution and get the same "
    "passed by the Committee Members, however the same be placed before the next "
    "subsequent meeting."
)
bl127b = clone_and_append(bl127, "BL_243", "127(b)", "127", "B",
    "Emergency resolutions passed by circulation", bl127b_text)
bl127b["title"] = "Emergency resolutions passed by circulation"

# ===========================
# FIX 5: Split 131 into 131(a)-(e)
# ===========================
bl131 = None
for r in bylaws:
    if r["id"] == "BL_173":
        bl131 = r
        break

fix_label(bl131, "131(a)", "131", "A")
bl131["title"] = "Resignation of the Chairman"
bl131a_text = (
    "The Chairman of the Society may resign his office as Chairman by a letter "
    "addressed to the Secretary of the Society."
)
bl131["official_legal_text"] = bl131a_text
bl131["source_grounded_official_text"] = bl131a_text
bl131["normalized_legal_text"] = "Bye-law 131(a) governs resignation of the Chairman."
bl131["source_grounding_status"] = "verbatim_sourced"
bl131["official_grounding_status"] = "verbatim_sourced"

subsections_131 = [
    ("131(b)", "B", "Resignation of the Secretary or Treasurer",
     "The Secretary or Treasurer of the Society may resign his office as Secretary or Treasurer by a letter addressed to the Chairman of the Society."),
    ("131(c)", "C", "When resignation of office bearer becomes effective",
     "Chairman/Secretary/Treasurer's resignation will be effective only after its acceptance and handing over the charge to the newly elected Chairman/Secretary/Treasurer, as the case may be."),
    ("131(d)", "D", "Conditions for acceptance of resignation of office bearer",
     "The Committee may accept the resignation of the office of the Chairman/Secretary/Treasurer only after it is satisfied that the Chairman or as the case may be the Secretary or Treasurer of the Society has brought upto date the work entrusted to him and has produced the entire papers and property of the Society, in his possession, before the Committee."),
    ("131(e)", "E", "Resignation of the entire Committee",
     "In case entire committee intends to resign, the resignations of the committee shall be placed before the General Body and such resignations shall be effective from the date of acceptance of such resignations by the General Body. This fact of acceptance of resignations of the entire Committee by the General Body, shall be communicated to the Registrar by the outgoing officers and Registrar may take necessary action as provided under section 77 A of the Act. However the existing Committee shall continue to carry on with only routine functioning of the Society, till alternate arrangement is made by the Registrar."),
]

next_id = 244
for label, sc, ttl, txt in subsections_131:
    rec = clone_and_append(bl131, f"BL_{next_id}", label, "131", sc, ttl, txt)
    rec["title"] = ttl
    next_id += 1

# ===========================
# Update metadata
# ===========================
dataset["metadata"]["total_bylaws"] = len(bylaws)
dataset["metadata"]["last_updated"] = "2026-06-02"

with open(DATASET_PATH, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

print(f"\nTotal records: {len(bylaws)}")
print(f"Changes:")
for c in changes:
    print(f"  {c}")
