import json, copy, sys
from pathlib import Path

# Paths
DATASET_PATH = Path("dataset/bylaws_dataset.json")
BACKUP_PATH = Path("dataset/bylaws_dataset_backup_structural_repair.json")

# Read dataset
with open(DATASET_PATH, "r", encoding="utf-8") as f:
    dataset = json.load(f)

# Backup
with open(BACKUP_PATH, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)
print(f"Backup saved to {BACKUP_PATH}")

bylaws = dataset["bylaws"]
original_total = dataset["metadata"]["total_bylaws"]

def subsection_id(bylaw_num_str, sub):
    """Generate a subsection identifier like '22(A)' or '115(e)'."""
    return f"{bylaw_num_str}({sub})"

def clone_record(source, new_id, bylaw_label, section_code, title,
                 official_excerpt, normalized_legal_text, legal_text,
                 retrieval_text_override=None):
    """Deep-copy a source record and override key fields."""
    rec = copy.deepcopy(source)
    rec["id"] = new_id
    rec["bylaw_label"] = bylaw_label
    rec["section_code"] = section_code
    rec["title"] = title
    rec["official_excerpt"] = official_excerpt
    rec["normalized_legal_text"] = normalized_legal_text
    rec["official_bylaw_number"] = bylaw_label
    rec["official_clause_reference"] = f"Model Bye-law {bylaw_label}"

    # Official legal text
    rec["official_legal_text"] = legal_text
    rec["source_grounded_official_text"] = legal_text

    # Build primary retrieval text
    byline = f"Bye-law {bylaw_label}. {title}."
    ret = f"{byline} Official text: {legal_text}. {normalized_legal_text}. Legal focus: {title}."
    if retrieval_text_override:
        ret = retrieval_text_override
    rec["retrieval_text"] = ret
    rec["primary_retrieval_text"] = ret

    # Keywords (simplified: title + bylaw ref)
    keywords = [f"bye-law {bylaw_label}", bylaw_label.lower(), section_code.lower() if section_code else ""]
    words = title.lower().replace(",", "").replace(".", "").split()
    keywords.extend(w for w in words if len(w) > 2 and w not in keywords)
    rec["keywords"] = keywords
    rec["technical_terms"] = list(keywords)
    rec["layman_keywords"] = [w for w in words if w in ("member", "rights", "election", "committee", "flat", "permission", "society", "application")]

    # Metadata updates
    rec["plain_english"] = f"This bye-law governs {title}."
    rec["detailed_explanation"] = f"This bye-law governs {title}. It applies as specified in the official text. Official text: {legal_text}"
    rec["bye_law_summary"] = f"This bye-law governs {title}. Official text: {legal_text}"
    rec["source_grounded_specific_summary"] = title
    rec["last_reviewed"] = "2026-05-09"
    rec["verification_status"] = "generated_needs_review"
    rec["provenance"] = {
        "generated_by": "AI-assisted enrichment pipeline",
        "reviewed_by": None,
        "review_notes": "Auto-generated metadata should be reviewed for high-frequency or legally sensitive bye-laws."
    }
    # Reset misc fields
    rec["structured_specific_data"] = {k: [] for k in rec.get("structured_specific_data", {})}
    rec["specific_data_mentions"] = []
    rec["specific_data_summary"] = ""
    rec["has_specific_data"] = False
    rec["specific_data_count"] = 0
    rec["specific_data_text"] = ""
    rec["official_grounding_status"] = "verbatim_sourced"
    rec["topic"] = source.get("topic", "")
    rec["semantic_category"] = source.get("semantic_category", "")
    rec["source_grounding_status"] = "verbatim_sourced"
    rec["official_source_page"] = "source_grounded"

    # Clear related_bylaws (will need context-specific setting)
    rec["related_bylaws"] = []
    return rec

# ========================
# 1. SPLIT BL_038 (bylaw 22) into 6 records
# ========================
bl38 = None
bl38_idx = None
for i, b in enumerate(bylaws):
    if b["id"] == "BL_038":
        bl38 = b
        bl38_idx = i
        break

# Modify BL_038 in-place to be 22(a)
bl38["bylaw_label"] = "22(A)"
bl38["section_code"] = "A"
bl38["title"] = "Rights of Members"
bl38["official_excerpt"] = "Bye-law 22(A) governs the rights of a Member to exercise rights as provided in the Act, Rules and Bye-laws, subject to payment of dues and acquiring interest in the Society."
bl38[
    "normalized_legal_text"
] = "Bye-law 22(A) governs rights of members to exercise rights as provided in the Act, Rules and Bye-laws."
bl38[
    "official_legal_text"
] = "A Member shall be entitled to exercise such rights as provided in the Act, Rules and Bye-laws. Provided that no Member shall exercise the rights of Member of a Society, until he has made such payment to the Society in respect of Membership, or acquired such interest in the Society."
bl38["source_grounded_official_text"] = bl38["official_legal_text"]
bl38["official_bylaw_number"] = "22(A)"
bl38["official_clause_reference"] = "Model Bye-law 22(A)"
bl38["last_reviewed"] = "2026-05-09"
bl38["topic"] = "member_rights"
bl38["topic_group"] = "member_rights"
bl38["issue_category"] = "member_rights"
bl38["semantic_category"] = "member_rights"
bl38["plain_english"] = "This bye-law governs the rights of Members to exercise their membership rights as provided in the Act, Rules and Bye-laws."
bl38["why_this_matters"] = "This bye-law applies when a Member's right to vote, access documents, or participate in society affairs is questioned."
bl38["applies_when"] = [
    "a Member's right to participate in meetings or voting is disputed",
    "payment of membership dues or share capital is in question",
    "a Member claims entitlement to society benefits or services"
]
bl38["does_not_apply_when"] = [
    "the issue is about committee elections or nominations",
    "the matter concerns property repairs or alterations",
    "the dispute is about sub-letting or flat transfer"
]
bl38["possible_concerns"] = [
    "Member may not have fulfilled payment obligations",
    "Member may not have acquired required interest in the Society"
]
bl38["required_procedure"] = [
    "Verify Member has made required payments to the Society",
    "Confirm Member has acquired the required interest in the Society",
    "Check the Act, Rules and Bye-laws for the specific right claimed"
]
bl38["possible_violations"] = [
    "Exercising membership rights without fulfilling payment obligations",
    "Denying legitimate rights to a Member who has complied with requirements"
]
bl38["documents_to_check"] = [
    "membership register",
    "share certificate",
    "payment receipts",
    "society's books of account"
]
bl38["member_rights"] = [
    "May exercise rights as provided in the Act, Rules and Bye-laws",
    "Must have made required payments and acquired interest to exercise rights"
]
bl38["committee_obligations"] = [
    "Must not deny legitimate rights to members who have complied",
    "Must verify member compliance before allowing exercise of rights"
]
bl38["layman_action_steps"] = [
    "Confirm you have made all required payments to the Society",
    "Check the Act, Rules and Bye-laws for your specific right",
    "Approach the Committee in writing if your right is denied"
]
bl38["real_world_examples"] = [
    "A Member wants to vote at the Annual General Meeting but has not paid maintenance dues",
    "A new Member wants to access society records before completing share capital payment"
]
bl38["common_disputes"] = ["Dispute over Member's right to vote or access society records"]
bl38["followup_questions"] = [
    "Has the Member made all required payments to the Society?",
    "What specific right is the Member trying to exercise?"
]
bl38["keywords"] = [
    "bye-law 22(A)",
    "22(a)",
    "rights of members",
    "member rights",
    "membership rights",
    "act rules and bye-laws",
    "payment",
    "interest in society"
]
bl38["technical_terms"] = list(bl38["keywords"])
bl38["layman_keywords"] = ["member", "rights", "payment"]
bl38[
    "retrieval_text"
] = "Bye-law 22(A). Rights of Members. Official text: A Member shall be entitled to exercise such rights as provided in the Act, Rules and Bye-laws. Provided that no Member shall exercise the rights of Member of a Society, until he has made such payment to the Society in respect of Membership, or acquired such interest in the Society.. Bye-law 22(A) governs rights of members to exercise rights as provided in the Act, Rules and Bye-laws.. Legal focus: Rights of Members."
bl38["primary_retrieval_text"] = bl38["retrieval_text"]
bl38[
    "detailed_explanation"
] = "This bye-law governs Rights of Members. It specifies that a Member is entitled to exercise rights as provided in the Act, Rules and Bye-laws, but only after making required payments and acquiring interest in the Society. Official text: A Member shall be entitled to exercise such rights as provided in the Act, Rules and Bye-laws. Provided that no Member shall exercise the rights of Member of a Society, until he has made such payment to the Society in respect of Membership, or acquired such interest in the Society."
bl38[
    "bye_law_summary"
] = "This bye-law governs Rights of Members. A Member may exercise rights under the Act, Rules and Bye-laws only after making required payments and acquiring interest in the Society."
bl38["source_grounded_specific_summary"] = "Rights of Members"
bl38["source_grounding_status"] = "verbatim_sourced"
bl38["official_grounding_status"] = "verbatim_sourced"
bl38["official_source_page"] = "source_grounded"
bl38["confidence_signals"] = [
    "legal text sourced verbatim from mysocietyclub.com",
    "title directly names the issue: Rights of Members",
    "official excerpt is source-grounded",
    "primary retrieval text prioritizes the governing clause"
]
bl38["confidence_context"]["source_quality"] = "verbatim_source_text"
bl38["verification_status"] = "verbatim_sourced"
bl38["provenance"]["review_notes"] = "Legal text sourced from mysocietyclub.com detail page. Metadata auto-generated."
bl38["governance_area"] = "member rights and responsibilities"

# 22(b) - provided further increase in min contribution
bl22b_text = (
    "Provided further that, in case of increase in minimum contribution of "
    "Member in share capital to exercise right of Membership, the Society "
    "shall give a due notice of demand to the Members and give reasonable "
    "period of time to comply with."
)
bl22b_normalized = "Bye-law 22(B) governs the procedure when the Society increases minimum share capital contribution for membership rights."
bl22b_excerpt = "Bye-law 22(B) provides that if the Society increases the minimum share capital contribution, it must give due notice and reasonable time to comply."

# 22(c) - Active Member definition
bl22c_text = (
    "A Member shall be termed as an 'Active Member' if he / she fulfill the "
    "following conditions: viz. i. He / She has attended at least One General "
    "Body Meeting in previous consecutive period of five years, ii. He / She "
    "has purchased and owns Flat / Unit in the Society, and iii. He / She has "
    "paid the Society Maintenance Service and other charges regularly."
)
bl22c_normalized = "Bye-law 22(C) defines the conditions for a Member to be classified as an Active Member."
bl22c_excerpt = "Bye-law 22(C) defines Active Member as one who has attended at least one General Body Meeting in five years, owns a flat, and has paid charges regularly."

# 22(d) - Non-Active Member definition
bl22d_text = "A Member who is not an 'Active Member' shall be 'Non-Active Member'."
bl22d_normalized = "Bye-law 22(D) defines a Non-Active Member as any Member who does not meet the Active Member conditions."
bl22d_excerpt = "Bye-law 22(D) defines Non-Active Member as a Member who is not an Active Member."

# 22(e) - Classification at close of financial year
bl22e_text = (
    "Society shall classify the Members as 'Active' or 'Non-Active' Member "
    "at the close of every financial year. i. Society shall communicate to "
    "every Non-Active Member about his classification, within a period of 30 "
    "days from 31st March of every year as prescribed under these By-laws as "
    "per Appendix No. 30 [FORM J-1]. ii. In case of a dispute about "
    "classification of a Member being Active or Non-Active, an appeal shall "
    "lie with the Registrar within a period of 60 days from the date of "
    "communication of such classification."
)
bl22e_normalized = "Bye-law 22(E) requires the Society to classify Members annually and communicate the classification."
bl22e_excerpt = "Bye-law 22(E) governs annual classification of Members as Active or Non-Active and the appeal process."

# 22(f) - Reclassification
bl22f_text = (
    "A 'Non Active Member' can be reclassified as 'Active Member' from "
    "the date he satisfies the conditions laid down under Byelaw no. 22(c)."
)
bl22f_normalized = "Bye-law 22(F) governs reclassification of a Non-Active Member to Active Member."
bl22f_excerpt = "Bye-law 22(F) allows a Non-Active Member to be reclassified as Active when conditions under 22(c) are satisfied."

# Create 22(b)-(f) records by cloning from 38
new_records = []
next_num = 230

subsection_defs = [
    ("22(B)", "B", "Increase in minimum contribution of Member in share capital", bl22b_excerpt, bl22b_normalized, bl22b_text),
    ("22(C)", "C", "Definition and conditions of Active Member", bl22c_excerpt, bl22c_normalized, bl22c_text),
    ("22(D)", "D", "Definition of Non-Active Member", bl22d_excerpt, bl22d_normalized, bl22d_text),
    ("22(E)", "E", "Annual classification of Members as Active or Non-Active", bl22e_excerpt, bl22e_normalized, bl22e_text),
    ("22(F)", "F", "Reclassification of Non-Active Member to Active Member", bl22f_excerpt, bl22f_normalized, bl22f_text),
]

topic = "member_rights"
for label, sc, ttl, excerpt, norm, legal_txt in subsection_defs:
    rec = clone_record(bl38, f"BL_{next_num}", label, sc, ttl, excerpt, norm, legal_txt)
    rec["topic"] = topic
    rec["topic_group"] = topic
    rec["issue_category"] = topic
    rec["semantic_category"] = topic
    rec["chapter"] = "Members, Their Rights, Responsibilities and Liabilities"
    new_records.append(rec)
    next_num += 1

# ========================
# 2. ADD BL for 46(c)
# ========================
bl46c_text = "No structural changes are permissible, without the prior permission of the concerned competent authority."
bl46c_normalized = "Bye-law 46(C) prohibits structural changes without prior permission of the concerned competent authority."
bl46c_excerpt = "Bye-law 46(C) provides that no structural changes to a flat are permissible without prior permission of the competent authority."
bl46c_title = "Restriction on structural changes in flat without permission of competent authority"

# Find BL_076 (46b) to use as template
bl076 = None
for b in bylaws:
    if b["id"] == "BL_076":
        bl076 = b
        break

bl46c_rec = clone_record(bl076, f"BL_{next_num}", "46(C)", "C", bl46c_title, bl46c_excerpt, bl46c_normalized, bl46c_text)
bl46c_rec["topic"] = "property_management"
bl46c_rec["topic_group"] = "property_management"
bl46c_rec["issue_category"] = "property_management"
bl46c_rec["semantic_category"] = "property_management"
bl46c_rec["chapter"] = "Responsibilities and Liabilities of Members"
bl46c_rec["bylaw_number"] = "46"
bl46c_rec["official_bylaw_number"] = "46(C)"
bl46c_rec["official_clause_reference"] = "Model Bye-law 46(C)"
bl46c_rec["source_reference"] = "https://mysocietyclub. com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/"
new_records.append(bl46c_rec)
next_num += 1

# ========================
# 3. SPLIT BL_155 (bylaw 115) into 5 records
# ========================
bl155 = None
bl155_idx = None
for i, b in enumerate(bylaws):
    if b["id"] == "BL_155":
        bl155 = b
        bl155_idx = i
        break

# Modify BL_155 in-place to be 115(a) - Election once in 5 years
bl155["bylaw_label"] = "115(A)"
bl155["section_code"] = "A"
bl155["title"] = "Election of the Committee once in five years"
bl155[
    "official_excerpt"
] = "Bye-law 115(A) governs the election of the Committee once in 5 years and the duty of the Committee to intimate the State Election Authority."
bl155[
    "normalized_legal_text"
] = "Bye-law 115(A) requires election of the Committee once in 5 years and intimation to the State Election Authority."
bl155[
    "official_legal_text"
] = (
    "Election of all the Members of the Committee shall be held once in 5 years, "
    "before the expiry of its term, in accordance with the provisions of Sec 73-CB "
    "of the Act and the Rules / procedure framed there under. It shall be the duty "
    "of the Committee to intimate to the State Election Authority for holding of its "
    "election before expiry of its term. On failure the Committee Members shall "
    "cease to hold office after expiry of its term, and attract action by the "
    "Registrar under section 77 A."
)
bl155["source_grounded_official_text"] = bl155["official_legal_text"]
bl155["official_bylaw_number"] = "115(A)"
bl155["official_clause_reference"] = "Model Bye-law 115(A)"
bl155["last_reviewed"] = "2026-05-09"
bl155["topic"] = "committee_governance"
bl155["topic_group"] = "committee_governance"
bl155["issue_category"] = "committee_governance"
bl155["semantic_category"] = "committee_governance"
bl155["plain_english"] = "This bye-law requires the Committee to be elected once every 5 years and the Committee must inform the State Election Authority before the term expires."
bl155["why_this_matters"] = "This bye-law applies when the Committee's term is approaching expiry or when there is a dispute about election timing."
bl155["applies_when"] = [
    "the Committee's term is about to expire",
    "election of a new Committee needs to be conducted",
    "there is a dispute about the validity of the Committee's continuation"
]
bl155["does_not_apply_when"] = [
    "the issue is about individual member rights",
    "the matter concerns property repairs or maintenance",
    "the dispute is about day-to-day management decisions"
]
bl155["possible_concerns"] = [
    "Committee may have failed to intimate the State Election Authority on time",
    "Committee members may continue beyond their term without fresh election",
    "Election may not have been conducted in accordance with Sec 73-CB"
]
bl155["required_procedure"] = [
    "Verify the Committee's term expiry date",
    "Ensure the Committee has intimated the State Election Authority",
    "Conduct election before expiry of the term as per Sec 73-CB"
]
bl155["possible_violations"] = [
    "Committee failing to intimate the State Election Authority",
    "Committee members continuing in office after term expiry",
    "Conducting election not in accordance with the Act and Rules"
]
bl155["documents_to_check"] = [
    "Committee term records",
    "correspondence with State Election Authority",
    "election notices and results"
]
bl155["member_rights"] = [
    "May demand that election be held before Committee term expires",
    "May challenge continuation of Committee beyond its term"
]
bl155["committee_obligations"] = [
    "Must intimate State Election Authority before term expiry",
    "Must ensure election is held in accordance with Sec 73-CB"
]
bl155["layman_action_steps"] = [
    "Check the Committee's term expiry date",
    "Ask the Secretary if the State Election Authority has been informed",
    "Approach the Registrar if the Committee continues beyond its term"
]
bl155["real_world_examples"] = [
    "A Committee's 5-year term has expired and no election has been conducted",
    "The Committee failed to inform the State Election Authority about the upcoming election"
]
bl155["common_disputes"] = ["Dispute over whether election was held on time and in accordance with the law"]
bl155["followup_questions"] = [
    "Has the Committee term expired?",
    "Was the State Election Authority informed before expiry?"
]
bl155["keywords"] = [
    "bye-law 115(A)",
    "115(a)",
    "election of committee",
    "five years",
    "state election authority",
    "sec 73-CB",
    "section 77 A",
    "committee term"
]
bl155["technical_terms"] = list(bl155["keywords"])
bl155["layman_keywords"] = ["election", "committee", "term", "five years"]
bl155[
    "retrieval_text"
] = "Bye-law 115(A). Election of the Committee once in five years. Official text: Election of all the Members of the Committee shall be held once in 5 years, before the expiry of its term, in accordance with the provisions of Sec 73-CB of the Act and the Rules / procedure framed there under. It shall be the duty of the Committee to intimate to the State Election Authority for holding of its election before expiry of its term. On failure the Committee Members shall cease to hold office after expiry of its term, and attract action by the Registrar under section 77 A.. Bye-law 115(A) requires election of the Committee once in 5 years and intimation to the State Election Authority.. Legal focus: Election of the Committee once in five years."
bl155["primary_retrieval_text"] = bl155["retrieval_text"]
bl155[
    "detailed_explanation"
] = "This bye-law requires the Committee to be elected once every 5 years. The Committee must inform the State Election Authority before the term expires. Failure to do so results in the Committee members ceasing to hold office and attracting action under section 77 A of the Act."
bl155[
    "bye_law_summary"
] = "This bye-law requires election of the Committee once in 5 years. The Committee must intimate the State Election Authority before term expiry."
bl155["source_grounded_specific_summary"] = "Election of the Committee once in five years"
bl155["source_grounding_status"] = "verbatim_sourced"
bl155["official_grounding_status"] = "verbatim_sourced"
bl155["official_source_page"] = "source_grounded"
bl155["confidence_signals"] = [
    "legal text sourced verbatim from mysocietyclub.com",
    "title directly names the issue: Election of the Committee once in five years",
    "official excerpt is source-grounded",
    "primary retrieval text prioritizes the governing clause"
]
bl155["confidence_context"]["source_quality"] = "verbatim_source_text"
bl155["verification_status"] = "verbatim_sourced"
bl155["provenance"]["review_notes"] = "Legal text sourced from mysocietyclub.com detail page. Metadata auto-generated."
bl155["governance_area"] = "committee administration"

# 115(b)-(e)
bl115b_text = (
    "The Committee of the Society may co-opt two \"Expert Directors\" relating "
    "to the objects and activities under taken by the Society. The number of "
    "such co-opted Members shall not exceed two in addition to the strength of "
    "the committee as provided in bye-laws No. 113., such co-opted Members "
    "shall not have the right to vote in any election of the Society in their "
    "capacity as such Member or to be eligible to be elected as office bearers "
    "of the committee."
)
bl115b_normalized = "Bye-law 115(B) allows the Committee to co-opt two Expert Directors."
bl115b_excerpt = "Bye-law 115(B) provides that the Committee may co-opt two Expert Directors who shall not have voting rights in elections."

bl115c_text = (
    "The Committee of the Society may co-opt two \"Functional Directors\", "
    "such Members shall be excluded for the purposes of counting the total "
    "numbers of the committee and shall have no right to vote."
)
bl115c_normalized = "Bye-law 115(C) allows the Committee to co-opt two Functional Directors."
bl115c_excerpt = "Bye-law 115(C) provides that the Committee may co-opt two Functional Directors who are excluded from committee count and have no voting rights."

bl115d_text = (
    "In respect of housing society having contribution of the Government "
    "towards its share capital, then the members of the committee shall include "
    "two officers of the Government nominated by the State Government, which "
    "shall be in addition to the number of members specified as above, and as "
    "provided under section 73 AAA of the Act."
)
bl115d_normalized = "Bye-law 115(D) provides for Government nominees on the Committee for societies with government share capital."
bl115d_excerpt = "Bye-law 115(D) requires societies with government share capital to include two nominated Government officers on the Committee."

bl115e_text = (
    "The Election of the Society shall be conducted by the State Cooperative "
    "Election Authority under section 73CB."
)
bl115e_normalized = "Bye-law 115(E) provides that the Society's election shall be conducted by the State Cooperative Election Authority."
bl115e_excerpt = "Bye-law 115(E) requires the Society's election to be conducted by the State Cooperative Election Authority under section 73CB."

# Create 115(b)-(e) records
subsection_defs_115 = [
    ("115(B)", "B", "Co-option of Expert Directors", bl115b_excerpt, bl115b_normalized, bl115b_text),
    ("115(C)", "C", "Co-option of Functional Directors", bl115c_excerpt, bl115c_normalized, bl115c_text),
    ("115(D)", "D", "Government nominees on Committee for societies with government share capital", bl115d_excerpt, bl115d_normalized, bl115d_text),
    ("115(E)", "E", "Election to be conducted by State Cooperative Election Authority", bl115e_excerpt, bl115e_normalized, bl115e_text),
]

for label, sc, ttl, excerpt, norm, legal_txt in subsection_defs_115:
    rec = clone_record(bl155, f"BL_{next_num}", label, sc, ttl, excerpt, norm, legal_txt)
    rec["topic"] = "committee_governance"
    rec["topic_group"] = "committee_governance"
    rec["issue_category"] = "committee_governance"
    rec["semantic_category"] = "committee_governance"
    rec["chapter"] = "Management of the Affairs of the Society"
    rec["source_grounding_status"] = "verbatim_sourced"
    rec["official_grounding_status"] = "verbatim_sourced"
    rec["verification_status"] = "verbatim_sourced"
    new_records.append(rec)
    next_num += 1

# Append all new records
bylaws.extend(new_records)

# Update total_bylaws count
dataset["metadata"]["total_bylaws"] = len(bylaws)

# Write updated dataset
with open(DATASET_PATH, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

print(f"Structural repair complete.")
print(f"Original records: {original_total}")
print(f"New records added: {len(new_records)}")
print(f"Total records now: {len(bylaws)}")
print(f"New record IDs: {[r['id'] for r in new_records]}")
print(f"Modified records: BL_038 (now 22(A)), BL_155 (now 115(A))")
