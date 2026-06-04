import json
from collections import Counter

with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    data = json.load(f)

records = data['bylaws']

# Question templates indexed by title keywords
QUESTION_TEMPLATES = {
    # === Names / Identity ===
    'name': [
        'What is the name of the society?',
        'Can the society change its name?',
        'How to change the society name?',
        'What is the procedure for changing society name?',
    ],
    'classification': [
        'What type of society is this?',
        'How is the society classified?',
        'What is the classification of the society?',
    ],
    'address': [
        'What is the registered address of the society?',
        'Can the society change its address?',
        'How to change society address?',
        'How to intimate address change to society?',
        'Where should the society name board be displayed?',
    ],
    'interpretation': [
        'What do the terms in the bye-laws mean?',
        'How are words defined in the bye-laws?',
        'What is the interpretation clause?',
        'Where can I find definitions of legal terms?',
    ],
    'area': [
        'What is the area of operation of the society?',
        'Where does the society operate?',
        'What is the territorial jurisdiction of the society?',
    ],
    'objects': [
        'What are the objects of the society?',
        'What is the purpose of the society?',
        'What are the main objectives of the society?',
    ],
    'affiliation': [
        'Can the society affiliate with other institutions?',
        'How to affiliate the society with other co-operative bodies?',
        'What is the procedure for affiliation?',
    ],
    'raise': [
        'How can the society raise funds?',
        'What are the different modes of raising funds?',
        'Can the society borrow money from members?',
        'What are the sources of funds for the society?',
    ],
    'share capital': [
        'What is the authorised share capital of the society?',
        'What is the share capital of the society?',
        'How much is the share capital?',
        'Can the share capital be increased?',
    ],
    'share certificate': [
        'When will I get my share certificate?',
        'How to get a share certificate?',
        'What does a share certificate contain?',
        'How are share certificates issued?',
    ],
    'seal': [
        'What is the society seal?',
        'Who signs the share certificate?',
        'Who are the authorised signatories?',
        'How is the common seal used?',
    ],
    'liability': [
        'What is the liability of a member?',
        'Can the society incur liabilities?',
        'What are the restrictions on incurring liabilities?',
        'Is my liability limited as a member?',
    ],
    'fund': [
        'What funds does the society maintain?',
        'How is the reserve fund constituted?',
        'How is the sinking fund created?',
        'What is the reserve fund used for?',
        'Can the society use the reserve fund for repairs?',
        'What is the sinking fund for?',
        'How is the education fund created?',
        'What is the contribution to reserve fund?',
        'How can the society invest its funds?',
        'What are the permitted investments for society funds?',
        'How is profit distributed?',
    ],
    'membership class': [
        'What are the classes of membership?',
        'Who can be a member of the society?',
        'What types of membership exist?',
        'What is an associate member?',
        'What is a nominal member?',
    ],
    'eligibility': [
        'Who is eligible for membership?',
        'Can a minor become a member?',
        'Can a company become a member?',
        'Can a firm become a member?',
        'What are the conditions for membership?',
        'What are the eligibility criteria for membership?',
        'Can an individual become a member?',
        'What documents are needed for membership?',
    ],
    'admission': [
        'How to apply for membership?',
        'How is a membership application processed?',
        'What is the procedure for admission?',
        'How long does membership approval take?',
        'Who approves membership applications?',
    ],
    'application': [
        'How to apply?',
        'What is the application process?',
        'How is the application disposed?',
        'What happens after I submit my application?',
    ],
    'rights': [
        'What are the rights of a member?',
        'Can a member inspect society records?',
        'Can a member get copies of documents?',
        'What are my rights as a member?',
        'Can I inspect the society books?',
        'What is the right to information of a member?',
    ],
    'occupation': [
        'What are the rights of occupation of a flat?',
        'Can I occupy my flat?',
        'What rights do I have to occupy my flat?',
    ],
    'nominal': [
        'What rights does a nominal member have?',
        'Can a nominal member vote?',
        'Can a nominal member become chairman?',
    ],
    'associate': [
        'What rights does an associate member have?',
        'What can an associate member do?',
    ],
    'resign': [
        'How to resign from the society?',
        'What is the procedure for resignation?',
        'Can a member resign from the society?',
        'How much notice is required for resignation?',
        'Can resignation be rejected?',
        'What happens if I have dues when I resign?',
        'Can an associate member resign?',
        'Can a nominal member resign?',
    ],
    'rejection': [
        'Can the society reject my resignation?',
        'Why was my resignation rejected?',
        'What are the reasons for resignation rejection?',
    ],
    'nomination': [
        'Can a member make a nomination?',
        'How to nominate someone for shares?',
        'What is the procedure for nomination?',
        'Can I revoke my nomination?',
        'How to change my nominee?',
        'Who can be a nominee?',
        'How to record a nomination?',
    ],
    'transfer': [
        'How to transfer shares?',
        'Can I transfer my shares to another person?',
        'What is the procedure for transfer?',
        'How to transfer shares after death?',
        'Who gets my shares after I die?',
        'Can a deceased member shares be transferred to heir?',
        'How to transfer shares to a nominee?',
        'What documents are needed for transfer?',
        'Can transfer be refused?',
        'How to apply for transfer of shares?',
    ],
    'exchange': [
        'Can members exchange flats?',
        'How to apply for exchange of flats?',
        'What is the procedure for flat exchange?',
    ],
    'sub-let': [
        'Can I sub-let my flat?',
        'How to get permission to sub-let?',
        'Can I give my flat on leave and license?',
        'Can I rent out my flat?',
        'What is the procedure for sub-letting?',
    ],
    'assignment': [
        'Can I assign my occupancy rights?',
        'Can I transfer my right to occupy?',
        'What are restrictions on assignment?',
    ],
    'clean': [
        'Do I have to keep my flat clean?',
        'What are my obligations to maintain my flat?',
        'Must I keep the flat clean?',
    ],
    'alteration': [
        'Can I make alterations to my flat?',
        'Can I renovate my flat?',
        'Do I need permission for alterations?',
        'How to get permission for alterations?',
        'What structural changes are not allowed?',
    ],
    'repair report': [
        'Can the secretary inspect my flat?',
        'Who can inspect my flat for repairs?',
        'What happens if repairs are needed?',
        'Can the society enter my flat for repairs?',
    ],
    'storing': [
        'What items cannot be stored in the flat?',
        'Are there restrictions on storing goods?',
        'What can I store in my flat?',
    ],
    'nuisance': [
        'What can I do if a member is causing nuisance?',
        'Can I complain about a noisy neighbour?',
        'What is considered nuisance in the society?',
        'How to deal with a troublesome member?',
    ],
    'expulsion': [
        'Can the society expel a member?',
        'What are grounds for expulsion?',
        'How to expel a member from the society?',
        'What is the procedure for expulsion?',
        'Can membership be cancelled?',
        'How can a member be removed?',
        'What happens to the shares of an expelled member?',
        'Can an expelled member get back the flat?',
    ],
    're-admission': [
        'Can an expelled member rejoin the society?',
        'Can an expelled member be readmitted?',
        'What is the procedure for re-admission after expulsion?',
    ],
    'cease': [
        'When does a person cease to be a member?',
        'How does membership end?',
        'What are the grounds for cessation of membership?',
        'What happens when membership ceases?',
    ],
    'charges': [
        'What charges does the society levy?',
        'What are society charges?',
        'How are society charges composed?',
        'What is included in the service charges?',
        'How are charges shared among members?',
        'How are repairs and maintenance charges determined?',
    ],
    'payment': [
        'How to pay society charges?',
        'When are society charges due?',
        'How to pay maintenance charges?',
        'What is the due date for payment of charges?',
        'Can charges be paid online?',
    ],
    'default': [
        'What happens if I do not pay charges?',
        'What is the procedure for default in payment?',
        'How are defaulting members dealt with?',
        'What is considered a default?',
        'What is the interest on late payment?',
        'Can the society charge interest on overdue amounts?',
        'What is the rate of interest on defaulted charges?',
    ],
    'set-off': [
        'Can the society deduct dues from my shares?',
        'Can the society adjust charges against my shares?',
        'What is set-off of charges?',
    ],
    'write off': [
        'Can society charges be written off?',
        'How to write off irrecoverable dues?',
        'What is the procedure for write off?',
        'Who can approve write off of charges?',
    ],
    'book': [
        'What books of account must the society maintain?',
        'What registers must the society keep?',
        'What records must be maintained by the society?',
    ],
    'records separate': [
        'What separate records must the society keep?',
        'How should society records be maintained?',
    ],
    'cash': [
        'What is the cash on hand limit?',
        'How much cash can the society keep?',
        'What is the maximum cash limit?',
    ],
    'cheque': [
        'What payments must be made by cheque?',
        'When must the society use banking mode?',
        'What is the limit for cash payments?',
    ],
    'accounts': [
        'When are accounts finalised?',
        'How are accounts closed at year end?',
        'What is the accounting year of the society?',
    ],
    'security': [
        'Do society employees need to give security?',
        'What is the security deposit for employees?',
    ],
    'auditor': [
        'How is the auditor appointed?',
        'Who appoints the auditor?',
        'What is the procedure for appointment of auditor?',
        'Can the society choose its own auditor?',
        'Does the secretary have to produce records to auditor?',
        'What happens after the audit?',
        'How is the audit rectification report prepared?',
    ],
    'committee': [
        'Who manages the society?',
        'What is the managing committee?',
        'What are the powers of the managing committee?',
        'Can the committee open a bank account?',
        'What is the strength of the committee?',
        'How many members are on the committee?',
    ],
    'election': [
        'How is the committee elected?',
        'What is the procedure for election?',
        'Who can vote in committee elections?',
        'How are committee members elected?',
    ],
    'disqualification': [
        'Who cannot be on the committee?',
        'What disqualifies a person from committee?',
        'What are the disqualifications for committee membership?',
    ],
    'constitution': [
        'How is the committee constituted?',
        'What is the composition of the committee?',
    ],
    'cessation committee': [
        'When does a committee member cease to hold office?',
        'How can a committee member be removed?',
        'What happens when a committee member ceases?',
    ],
    'interested': [
        'Can a committee member vote on matters they are interested in?',
        'What is conflict of interest for committee members?',
        'Can an interested committee member participate?',
    ],
    'term': [
        'What is the term of office of the committee?',
        'How long can committee members serve?',
        'When does the committee term end?',
        'What is the period of office of elected committee?',
    ],
    'first meeting': [
        'When is the first meeting of new committee?',
        'How is the first committee meeting called?',
    ],
    'custody': [
        'Who keeps the society records?',
        'Who is responsible for society documents?',
        'Who has custody of society records?',
    ],
    'handover': [
        'How does the outgoing committee hand over charge?',
        'What is the procedure for handover?',
        'What records must be handed over?',
    ],
    'office bearers': [
        'How are office bearers elected?',
        'Who are the office bearers of the society?',
        'How to elect chairman and secretary?',
        'What is the procedure for election of office bearers?',
    ],
    'quorum': [
        'What is the quorum for committee meetings?',
        'How many members are needed for a committee meeting?',
        'What is the quorum requirement?',
    ],
    'meetings frequency': [
        'How many committee meetings must be held?',
        'How often does the committee meet?',
        'What is the minimum number of committee meetings?',
    ],
    'casual vacancy': [
        'How to fill a casual vacancy in the committee?',
        'Can the committee co-opt a member?',
        'How to replace a committee member who resigns?',
        'What is the procedure for co-option?',
    ],
    'co-opted term': [
        'How long can a co-opted member serve?',
        'What is the term of a co-opted committee member?',
    ],
    'resignation committee': [
        'Can a committee member resign?',
        'How does a committee member resign?',
        'What is the procedure for committee resignation?',
    ],
    'resignation chairman': [
        'Can the chairman resign?',
        'How does the chairman resign?',
    ],
    'resignation secretary': [
        'Can the secretary resign?',
        'How does the secretary resign?',
    ],
    'resignation treasurer': [
        'Can the treasurer resign?',
    ],
    'notice meeting': [
        'How much notice is required for a committee meeting?',
        'What is the notice period for committee meetings?',
    ],
    'chairman preside': [
        'Who presides over committee meetings?',
        'Does the chairman preside over meetings?',
    ],
    'majority': [
        'How are decisions taken in committee meetings?',
        'Does the committee decide by majority?',
        'How does voting work in committee?',
    ],
    'special meeting committee': [
        'How to call a special committee meeting?',
        'Can members request a special committee meeting?',
        'What is the procedure for special committee meeting?',
    ],
    'minutes': [
        'Who records the minutes of committee meetings?',
        'How are minutes of meetings recorded?',
        'What is the role of secretary in meetings?',
    ],
    'joint liability': [
        'Are committee members personally liable?',
        'What is the liability of committee members?',
        'Are committee members jointly liable?',
    ],
    'duties committee': [
        'What are the duties of the committee?',
        'What are the functions of the managing committee?',
        'What are the powers of the committee?',
    ],
    'duties chairman': [
        'What are the powers of the chairman?',
        'What can the chairman do?',
        'What are the functions of the chairman?',
    ],
    'duties secretary': [
        'What are the duties of the secretary?',
        'What does the secretary do?',
        'What are the functions of the secretary?',
    ],
    'expert director': [
        'Can the committee co-opt an expert director?',
        'What is an expert director?',
        'How to appoint an expert director?',
    ],
    'functional director': [
        'Can the committee co-opt a functional director?',
        'What is a functional director?',
    ],
    'government nominee': [
        'Can the government nominate someone to the committee?',
        'Are there government nominees on the committee?',
    ],
    'election commission': [
        'Who conducts committee elections?',
        'Does the election commission conduct society elections?',
        'What is the role of state co-op election commission?',
    ],
    'meeting notice period': [
        'How many days notice is required for a general meeting?',
        'What is the notice period for AGM?',
        'When must notice of general meeting be given?',
    ],
    'agm': [
        'When should the AGM be held?',
        'What is the period for holding AGM?',
        'When is the annual general meeting held?',
        'What business is transacted at the AGM?',
        'What happens at the annual general meeting?',
    ],
    'sgm': [
        'When can a special general meeting be called?',
        'How to call a special general body meeting?',
        'What is the procedure for SGM?',
        'How to requisition a special general meeting?',
    ],
    'first general meeting': [
        'When is the first general meeting held?',
        'How is the first general meeting called?',
        'What is the purpose of first general meeting?',
        'Who calls the first general meeting?',
    ],
    'notice general meeting': [
        'How is notice of general meeting given?',
        'What should a general meeting notice contain?',
        'How to give notice for general body meeting?',
    ],
    'quorum general meeting': [
        'What is the quorum for general body meeting?',
        'How many members are needed for a general meeting?',
        'What if there is no quorum?',
        'What happens if quorum is not present?',
    ],
    'adjourned meeting': [
        'Can a meeting be adjourned due to lack of quorum?',
        'What happens to an adjourned meeting?',
    ],
    'postpone meeting': [
        'Can a general body meeting be postponed?',
        'What happens if the meeting cannot finish business?',
    ],
    'chairman general meeting': [
        'Who presides over the general body meeting?',
        'Does the chairman preside over the AGM?',
    ],
    'proxy': [
        'Can a member send a proxy to the meeting?',
        'Can someone attend the meeting on my behalf?',
        'What are the restrictions on proxy attendance?',
    ],
    'voting right': [
        'Who can vote at the general meeting?',
        'What are the voting rights of a member?',
        'Can every member vote?',
    ],
    'one vote': [
        'How many votes does each member have?',
        'Does each member have one vote?',
        'What is the one member one vote rule?',
    ],
    'decisions': [
        'How are decisions taken at the meeting?',
        'How does voting work at general meetings?',
        'How are resolutions passed?',
    ],
    'resolution': [
        'Can a previous resolution be cancelled?',
        'How to cancel a resolution?',
    ],
    'supreme authority': [
        'Who is the supreme authority in the society?',
        'Is the general body the supreme authority?',
    ],
    'complaint': [
        'How do I file a complaint?',
        'How to make a complaint to the society?',
        'What is the complaint procedure?',
        'What if the society does not act on my complaint?',
    ],
    'action complaint': [
        'What action must the committee take on a complaint?',
        'How does the committee handle complaints?',
        'What is the timeline for committee action?',
    ],
    'registrar complaint': [
        'Can I complain to the registrar?',
        'How to approach the registrar?',
        'What if the society ignores my complaint?',
    ],
    'co-operative court': [
        'Can I approach the co-operative court?',
        'How to file a case in co-operative court?',
        'What disputes go to co-operative court?',
    ],
    'civil court': [
        'Can I approach the civil court?',
        'When can I file a civil suit?',
    ],
    'municipal': [
        'Can I complain to the municipal corporation?',
    ],
    'police complaint': [
        'Can I file a police complaint?',
        'When to approach the police?',
    ],
    'general body complaint': [
        'Can I raise my complaint at the general body meeting?',
    ],
    'federation': [
        'Can I complain to the federation?',
    ],
    'redevelopment': [
        'How does society redevelopment work?',
        'What is the procedure for redevelopment?',
        'Who decides on redevelopment?',
        'What are the rules for building redevelopment?',
    ],
    'conveyance': [
        'What is deemed conveyance?',
        'How to get conveyance of the property?',
        'What is the procedure for deed of conveyance?',
        'Who executes the conveyance deed?',
    ],
    'structural audit': [
        'What is a structural audit?',
        'Is structural audit mandatory?',
        'How often should structural audit be done?',
    ],
    'insurance': [
        'Does the society need building insurance?',
        'Is building insurance compulsory?',
    ],
    'trees': [
        'Who maintains the trees in the compound?',
        'Can trees be cut in the society?',
    ],
    'allotment': [
        'How are flats allotted?',
        'What is the policy for allotment of flats?',
        'Can flat allotment be cancelled?',
        'How is possession of flat given?',
    ],
    'change of use': [
        'Can I change the use of my flat?',
        'Can I use my flat for commercial purpose?',
    ],
    'possession certificate': [
        'What is a possession certificate?',
        'How to get possession certificate from society?',
    ],
    'maintain property': [
        'Who is responsible for maintaining the society property?',
        'What is the committee responsibility for property?',
    ],
    'inspect property': [
        'Can the committee inspect the property for repairs?',
        'How is property inspection done?',
    ],
    'execute repairs': [
        'Who executes repairs of society property?',
        'What repairs does the committee do?',
    ],
    'repairs redevelopment': [
        'What is the process for repairs and redevelopment?',
    ],
    'cost repairs': [
        'Who pays for repairs?',
        'What repairs are at society cost?',
        'What repairs are at member cost?',
    ],
    'notice board': [
        'What notices are put on the notice board?',
        'Where are society notices displayed?',
        'Is the society required to have a notice board?',
    ],
    'penalty': [
        'What are the penalties for breach of bye-laws?',
        'Can the society fine a member?',
        'What happens if bye-laws are violated?',
    ],
    'amendment': [
        'Can the bye-laws be amended?',
        'How to change the bye-laws?',
        'What is the procedure for amendment of bye-laws?',
    ],
    'lifts': [
        'Who maintains the lifts?',
        'What are the rules for lift operation?',
        'Who maintains common facilities?',
    ],
    'games': [
        'Can members play games in common areas?',
        'Are there restrictions on playing games?',
    ],
    'common space': [
        'Can common spaces be rented out?',
        'Can open spaces be used by members?',
        'Are common areas for all members?',
    ],
    'terrace': [
        'Can I use the terrace temporarily?',
        'Who can use the open space?',
    ],
    'fees': [
        'What fees are charged for copies of documents?',
        'How much does it cost to get document copies?',
    ],
    'notice': [
        'How are notices served to members?',
        'What is the mode of communication of notices?',
        'How does the society send notices?',
    ],
    'accounting year': [
        'What is the accounting year of the society?',
        'When does the financial year end?',
    ],
    'provisional committee': [
        'What is a provisional committee?',
        'Who appoints the provisional committee?',
        'What are the powers of the provisional committee?',
        'What is the term of the provisional committee?',
    ],
    'promoter': [
        'Who is the chief promoter?',
        'What records must the promoter hand over?',
    ],
}

# Build reverse lookup from keyword groups to records
def build_question_map():
    qmap = {}
    for keywords, questions in QUESTION_TEMPLATES.items():
        qmap[keywords] = questions
    return qmap

qmap = build_question_map()

total_added = 0
updated = 0
stats_by_topic = Counter()

for r in records:
    title = r.get('title', '').lower()
    chapter = r.get('chapter', '').lower()
    combined = title + ' ' + chapter
    existing = list(r.get('followup_questions', []) or [])
    existing_set = set(e.lower().rstrip('?') for e in existing)
    
    new_questions = []
    
    # Match each keyword group against title+chapter
    for keywords, questions in QUESTION_TEMPLATES.items():
        kws = keywords.split()
        if all(kw in combined for kw in kws):
            for q in questions:
                q_key = q.lower().rstrip('?')
                if q_key not in existing_set:
                    new_questions.append(q)
                    existing_set.add(q_key)
    
    # Also add a bylaw-specific question from title
    title_clean = r.get('title', '')
    bn = r.get('bylaw_number', '')
    sc = r.get('section_code', '')
    if title_clean:
        ref_q = f"What does bye-law {bn}{'('+sc+')' if sc else ''} say about {title_clean.lower()}?"
        q_key = ref_q.lower().rstrip('?')
        if q_key not in existing_set:
            new_questions.append(ref_q)
            existing_set.add(q_key)
    
    if new_questions:
        r['followup_questions'] = (existing + new_questions)[:10]  # cap at 10
        total_added += len(new_questions)
        updated += 1

avg = sum(len(r.get('followup_questions',[]) or []) for r in records) / len(records)
print(f'Records updated: {updated}/{len(records)}')
print(f'Total questions added: {total_added}')
print(f'Avg questions per record: {avg:.1f}')

# Show examples from weak areas
print('\n=== MEMBERSHIP EXAMPLES ===')
for bn in ['16', '17', '18', '21', '27', '31', '32', '50', '51', '52', '55']:
    r = next((x for x in records if x.get('bylaw_number') == bn and not x.get('section_code')), None)
    if not r:
        r = next((x for x in records if x.get('bylaw_number') == bn), None)
    if r:
        qs = r.get('followup_questions', [])
        print(f'\nBylaw {bn}: {r["title"][:60]}')
        for q in qs:
            print(f'  - {q}')

print('\n=== CHARGES EXAMPLES ===')
for bn in ['65', '66', '67', '69', '70', '71', '74']:
    r = next((x for x in records if x.get('bylaw_number') == bn), None)
    if r:
        qs = r.get('followup_questions', [])
        print(f'\nBylaw {bn}: {r["title"][:60]}')
        for q in qs:
            print(f'  - {q}')

print('\n=== COMMITTEE EXAMPLES ===')
for bn in ['111', '114', '115', '121', '125', '128', '129', '130']:
    r = next((x for x in records if x.get('bylaw_number') == bn), None)
    if r:
        qs = r.get('followup_questions', [])
        print(f'\nBylaw {bn}: {r["title"][:60]}')
        for q in qs:
            print(f'  - {q}')

with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('\nSaved.')
