import json, re

# Load dataset
with open('dataset/bylaws_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Mapping of source page URL -> list of extracted bylaw texts
# Each entry: (bylaw_number_pattern, text, source_url_slug)

# Handle merged bylaw 94 (source has 94a+94b, dataset has single '94')
merged_94_text = (
    'The Annual General Body Meeting of the Society shall be held on or before 30th September each year as provided under Section 75(1) of the Act. '
    'In case of default in calling the Annual General Body Meeting as stipulated, shall attract disqualification and action as provided under section 75(5) of the Act.'
)

extracted = {
    # member-rights-duties page (already mostly verbatim_source_verified)
    # We'll update source_derived_fallback records in this chapter too
    
    # management-affairs page
    'management-affairs': {
        '110': 'Subject to the provisions of the Act, the Rules and the Bye-laws of the Society, the final authority of the Society shall vest in its General Body Meeting, summoned in such manner as is specified in the Act, the Rules and these Bye-laws.',
        '111': 'The Management of the affairs of the Society shall vest in the Committee duly constituted in accordance with the provisions of the Act, the Rules and the Bye-laws of the Society.',
        '112': 'Subject to the direction given or regulation made by a Meeting of The General Body of the Society, the Committee shall exercise all powers, expressly conferred on it and discharge all functions entrusted to it under the Act, Rules, Bye-laws or any other law for the time being in force and generally to do all acts for the management of the affairs of the Society, and for the conduct of its business.',
        '113': 'A Banking Account shall be opened by the Society in the nearest State or District Central Co-op Bank / a Scheduled Bank having awarded "A" Audit Class in last three consecutive years, , nationalised Bank or any other bank which may be approved by the Registrar or any officer authorised by him, from time to time, within the area of operation of the Society, to which the Registrar may accord his approval for this purpose in writing. The Society shall keep its funds in the said bank.',
        '114': 'The Committee shall consist of *11 / 13 / 15 / 17 / 19 Members of the Society. This strength includes the reservation of seats as provided under section 73B and 73C of the Act. Note: *The strength shall be as decided by the General Body from time to time.',
        '115(a)': 'Election of all the Members of the Committee shall be held once in 5 years, before the expiry of its term, in accordance with the provisions of Sec 73- CB of the Act and the Rules / procedure framed there under. The Committee shall be elected by the Members of the Society, at a General Body Meeting from amongst the Active Members of the Society.',
        '115(b)': 'The Committee of the Society may co-opt two "Expert Directors" relating to the objects and activities under taken by the Society..The number of such co-opted Members shall not exceed two in addition to the total strength of the Committee as provided under bye-law 114. The Expert Directors shall have the right to vote in the meeting of the Committee.',
        '115(c)': 'The Committee of the Society may co-opt two "Functional Directors", such Members shall be excluded for the purposes of counting the total numbers of the committee and shall have no right to vote.',
        '115(d)': 'In respect of housing society having contribution of the Government towards its share capital, then the members of the committee shall include two officers of the Government nominated by the State Government or as the case may be the Central Government. Such nominated Members shall have right to vote and other privileges of the Members of the Committee.',
        '115(e)': 'The Election of the Society shall be conducted by the State Cooperative Election Authority under section 73CB of the Act.',
        '116': 'No Officer of the Society shall have any interest, directly or indirectly, otherwise than as such officer: (a) In any contract made with the Society.(b) In any property sold or purchased by the Society. (c) In any other matter relating to the business of the Society, Provided that, if any such officer has any interest, he shall disclose the nature and extent of his interest to the Committee and the Officer concerned shall not be present at the meeting of the Committee, when any such matter is considered.',
        '117': 'A person shall be disqualified for being elected or for continuing as a Member of the Committee of the Society or of any other Committee constituted under the Act, Rules or these Bye-laws if',
        '118': 'In a General Election of Members of the Committee of a Society, on the election of two-thirds or more number of Members, the Returning Officer or any other Officer or Authority conducting such election shall declare the election of the full Committee and draw lots and assign to the remaining members, period of office ranging from one to five years.',
        '119(a)': 'A person shall cease to be the Member of the Committee, if: i. he has incurred any of the disqualifications mentioned under the byelaw No. 117 or ; ii. he has failed to attend any three consecutive meetings of the Committee, without leave of the Committee / General Body till date of third meeting ; iii. he absents himself from the area of operation of the Society for a continuous period of four months ; iv. he has obtained the leave of the committee/general body ;',
        '119(b)': 'If a Member of the Committee attracts any of the disqualifications under the bye-law no. 119 (1), the Committee shall record the fact in the minutes of its meeting and the Secretary of the Society shall communicate the said fact to the Member concerned and to the Registrar within one month.',
        '120': 'No Member of the Committee shall be present at the consideration of any matter, in which he is directly or indirectly interested.',
        '121': 'The period of office of the Committee elected under the bye-law No. 115(a) shall be for 5 years from the date of assuming the office.',
        '122(a)': 'The first meeting of the newly elected jointly with outgoing Committee shall be held within 30 days from the date of constitution of the new committee as per bye-law No. 117 and the provisions of Section 75 of the Act.',
        '122(b)': 'Subject to the provisions of the bye-law No. 122(a) the Secretary of the outgoing Committee shall issue notice of the first meeting to the Members of the newly elected Committee and the outgoing Committee at least 7 days before the date of the said meeting.',
        '123': 'All records of the Society shall be kept at its premises, convenient to the secretary, with the approval of the Committee of the Society.',
        '124': 'When the new Committee is elected, the Secretary of the outgoing committee shall prepare the list of papers and property of the Society in his custody and hand over the charge thereof to the Secretary of the newly elected Committee against proper receipt and submit a report of handing over charge to the new Committee at its first meeting.',
        '125(a)': 'Every Committee, at its first meeting, after its election shall elect a Chairman, Secretary and Treasure from amongst the Members of the Committee.',
        '125(b)': 'The Officer of the Society shall hold office for the period of 5 years from the date on which he is elected to be the Chairman as the case may be the Secretary and Treasurer but not beyond the expiry of term of the Committee or till the new officer is elected subsequent to the election of new Committee whichever is earlier.',
        '126': 'The Committee meeting shall be normally held in the premises of the Society. The quorum for Committee Meeting shall be as mentioned in Bye-law No. 113. It shall not be competent for the Committee to transact any business at a meeting, if the number of Members present is less than the quorum.',
        '127(a)': 'The Committee shall meet as often as necessary but at least once in a month.',
        '127(b)': 'in case of emergency, the Committee may place a resolutions and get the same passed by the Committee Members, however the same be placed before the next subsequent meeting.',
        '128': 'The Committee may fill a casual vacancy on the Committee by nomination out of a same class of Active Members in respect of which the casual vacancy has arisen as per section 73 CB and as per the instructions of the State Co-operative Election Authority.',
        '129': 'The period of office of the co-opted Member of the Committee shall be coterminous with tenure of Office of the Committee.',
        '130': 'A Member of the Committee may, by a letter addressed to the Chairman of the Society, resign his Membership of the committee. The resignation shall be effective from the date it is accepted by the Committee.',
        '131(a)': 'The Chairman of the Society may resign his office as Chairman by a letter addressed to the Secretary of the Society;',
        '131(b)': 'The Secretary or Treasurer of the Society may resign his office as Secretary or Treasurer by a letter addressed to the Chairman of the Society.',
        '131(c)': 'Chairman/Secretary/Treasurer\'s resignation will be effective only after its acceptance and handing over the charge to the newly elected Chairman/Secretary/Treasurer, as the case may be.',
        '131(d)': 'The Committee may accept the resignation of the office of the Chairman/Secretary/Treasurer only after it is satisfied that the Chairman or as the case may be the Secretary or Treasurer of the Society has handed over the charge of all the records, property, documents and papers & amounts of and belonging to the Society.',
        '131(e)': 'In case entire committee intends to resign, the resignations of the committee shall be placed before the General Body and such resignations shall be effective from the date of acceptance of such resignation by the General Body.',
        '132': 'The Secretary of the Society shall give 3 clear day\'s notice of meetings of the Committee to all the Members of the Committee which shall state the date, time and place of the meeting and the business to be transacted thereat.',
        '133': 'The Chairman of the Society shall preside over all the meetings of the Committee, provided that if at any meeting of the Committee, he is absent, those Members of the Committee present shall elect one from amongst themselves to preside over such meeting.',
        '134': 'Every Member of the Committee shall have one vote. However in case of equality of votes the chairman of the meeting will have a second or casting vote. All decisions shall be taken by majority of votes.',
        '135': 'On a requisition by 1/3rd of the Members of the committee, the Secretary of the Society shall convene a special meeting of the Committee within 7 days of the date of receipt of the requisition to discuss the matters specified in the requisition.',
        '136': 'The Secretary of the Society shall attend every meeting of the committee and record its minutes and place the same for confirmation before the next meeting of the committee, after the minutes are signed by the Chairman of the meeting.',
        '137': 'The Members of the Committee shall be jointly and severally responsible for all the decisions taken by the committee during its term relating to the business of the Society.',
        '138': 'Subject to the bye - law 111 the Committee shall exercise the powers and discharge the functions and duties as mentioned hereunder:\nSr. No.\nItems of the powers, functions and duties\nThe bye-law no.\nunder which the Power, Function of duty falls\n1\nAdmission of Members\n22\n2\nAllotment or refusal of Shares\n17-A\n3\nExpulsion of a Member\n50 (a)\n4\nMaintenance of the Register of Members\n15\n5\nMaintenance of Books, Registers and documents\n151 to 152\n6\nIssue of Share Certificate, duplicate thereof\n11\n7\nPermission for the transfer of shares and interest in the capital/property of the Society\n38\n8\nPermission for Exchange of flats\n41\n9\nPermission for Sub-letting\n43\n10\nPermission to create a charge on the flat\n44\n11\nInspection of the documents of the Society\n23\n12\nDeciding the dis-qualification of a Member of the Committee\n117 and 119\n13\nConfirm the minutes of the meetings of the Committee, The Annual General Body Meeting & Special General Body Meeting\n108, 136\n14\nOpening of Banking Account of the Society\n113\n15\nTo operate Society Bank Account\n113\n16\nApprove the proposals for Inviting Deposits from Members and Non-Members\n69\n17\nAppointment of the Secretary, if not Member of the Committee\n111\n18\nTo write off a debt as irrecoverable\n114\n19\nTo approve and accept the resignation of the Member\n27\n20\nTo approve and accept the resignation of the Member of the Committee\n130\n21\nTo call General Body Meeting\n96\n22\nConvening of the Special General Body Meeting\n96\n23\nTo invest the funds of the Society\n147\n24\nTo approve loans and advances\n72\n25\nTo purchase and sell property of the Society or to create charge on its property\n82A\n26\nConduct of the business of the Society\nPowers, functions and duties as provided under the Act, Rules and the Bye-laws.\n27\nAny other powers, functions and duties as are assigned by the General Body from time to time.',
        '139': 'The Chairman of the Society shall have the power of overall superintendence, control and guidance in respect of management of the affairs of the Society within the frame-work of the MCS Act 1960. Rules and the Bye-laws of the Society.',
        '140': 'The functions of the Secretary of the Society shall be those mentioned below:\nSr. No.\nItems of the powers, functions and duties\nThe bye-law no. under which the Power, Function of duty falls\n1\nTo grant inspection of books, registers, documents, etc.\n23\n2\nTo allow nomination/deletion/ alteration of the name of nominee\n32, 33\n3\nTo record the fact of expulsion of a Member and send a copy thereof to the Member concerned and the Registrar\n50 (a) and (b)\n4\nTo bring to the notice of the Committee, the matters relating to disqualification of a Member of Committee\n117, 119\n5\nTo receive and present to the Committee, the application for membership, shares, transfer of shares, sub-letting, exchange of flats, creating charge etc.\n38, 41, 43 and 44\n6\nTo handover the charge of papers and property of the Society, after new Committee is elected\n124\n7\nTo issue notice of General Body Meetings\n99\n8\nTo issue notice of Committee Meetings\n132\n9\nTo record minutes of the Committee meetings\n136\n10\nTo record minutes of General Body Meetings\n108\n11\nTo bring to the notice of the Committee, the resignation of a Member\n27(a)\n12\nTo receive and reply to the Complaints from Members\nBye-laws for Complaints\n13\nTo file the returns of the Society to the Registrar and other authorities under the Act, Rules and the Bye-laws\n25\n14\nTo carry on correspondence on behalf of the Society\n15\nTo make payments and maintain accounts of the Society\n16\nTo implement the decisions of the Committee, General Body and the Registrar/ other authorities\n17\nTo maintain records, papers, documents and property of the Society in his custody\n123\n18\nTo prepare the Agenda for the meeting of the Committee and the General Body Meeting\n19\nTo report all cases of litigation and legal matters involving a Society to the Committee\n20\nTo discharge such other duties as may be assigned to him by the Chairman, Committee or General Body\n21\nIn the absence of Secretary, any other Officer authorized by the Committee shall discharge the functions of the Secretary.\n22\nHe shall be responsible to implement all the decisions taken by the Committee and General Body.',
    },
    
    # first-general-meeting page
    'first-general-meeting': {
        '85': 'The First General Body meeting of the Promoters, who have signed the Application for Registration of the Society, shall be held within the period of three months of the date of the registration of the Society.',
        '86': 'On failure of the Chief Promoter of the Society to hold the First General Body meeting within the period mentioned in bye-law no 85, the Registering Authority shall cause it to be convened.',
        '87': 'Clear fourteen days Notice of the First General Body Meeting of the Society shall be given by the Chief Promoter of the Society or as the case may be, by the Officer Authorized by the Registering Authority, to all the Promoters who have signed the Application for Registration of the Society.',
        '88(a)': 'At the First General Body Meeting of the Society, the following business shall be transacted:\ni. Election of a President for the meeting,\nii. Admission of new Members (other than the promoters) who have applied for Membership of the Society and their admission,\niii. Confirmation of the provisional allotment of shares,\niv. Reading and confirmation of the draft bye-laws of the Society,\nv. Election of the Chairman, the Secretary and the Treasurer and other Members of the Provisional Committee from amongst the persons who have signed the application for registration of the Society as Members,\nvi. To authorize the Chairman of the meeting to handover charge of records including the minutes of the First General Body Meeting to the Chairman of the Society elected at the first meeting of the Provisional Committee or the Committee nominated by the Registering Authority,\nvii. To pass a resolution regarding the remuneration payable to the Secretary of the Society, if he is not a Member of the Society,\nviii. To authorize the Secretary or any other Officer to open a Bank Account of the Society and to operate the same,\nix. To fix the rate of Honorarium payable to the Chairman, if any, for attending the meetings of the Committee,\nx. Such other business as may be brought before the meeting with the permission of the President.',
        '88(b)': 'Where the First General Meeting fails to elect a Provisional Committee, the Registering Authority shall be competent to Nominate such a Committee, including the Chairman and the Secretary of the Society.',
        '89': 'The person, who presides over the First General Meeting shall record the Minutes of the Meeting, sign them and hand them over to the Secretary of the Society elected at the first meeting of the Provisional Committee or the Committee nominated by the Registering Authority.',
        '90': 'The Chief Promoter of the Society shall, immediately after election of the Office Bearers of the Society, at the first meeting of the Provisional Committee or its nomination by the Registering Authority, handover charge of all the papers, documents and property of the Society to the Chairman of the Society or to the Secretary, as the case may be, under a proper receipt. The list of papers, documents and the property to be handed over shall be as under:\ni. Certificates of Registration of the Society under the MCS Act. 1960,\nii. Certificate of Registration of the Bye-laws of the Society,\niii. Copies of the Act, Rules and Bye-laws,\niv. Share Certificates and blank Share Certificates with counterfoils,\nv. Application forms for Membership from the Members of the Society along with the fees paid by them,\nvi. Register of Members,\nvii. Register of Shares,\nviii. Register of Nominations, with necessary forms,\nix. Register of Transfers of Shares,\nx. Receipt books for payment of fees, share money received from the Members and for collection of admission fees,\nxi. Books of Accounts and all other books, registers and documents of the Society,\nxii. Letter of Allotment of Shares to the Members of the Society,\nxiii. Any other documents belonging to the Society.',
        '91': 'The Provisional Committee or the Nominated Committee shall have the all powers and functions as the committee duly elected in accordance with the Act, Rules & Bye-laws of the Society.',
        '92': 'The Provisional Committee or the Nominated Committee shall be in office for a period of one year or until the regular elections are held under the Bye-laws of the Society.',
        '93': 'The Chairman of the Provisional Committee or the Nominated Committee shall handover charge of all the assets and documents & papers of the Society to the Chairman of the newly elected Committee at the first meeting of the elected Committee. The handover shall be under a proper receipt containing a list of papers, documents, property etc. handed over to the Chairman of the newly elected Committee.',
    },
    
    # annual-general-meeting page
    'annual-general-body-meetings': {
        '94(a)': 'The Annual General Body Meeting of the Society shall be held on or before 30th September each year as provided under Section 75(1) of the Act. (as there is no provision for extension of time to hold the Annual General Meeting under the Act)',
        '94(b)': 'In case of default in calling the Annual General Body Meeting as stipulated in bye-law 94(a) above, shall attract disqualification and action as provided under section 75(5) of the Act.',
        '95': 'The Annual General Body Meeting of the Society shall transact the following business:\na. to read the minutes of the last annual General Body Meeting of the Society and the Special General Body Meeting held after the last Annual General Body Meeting and to confirm them,\nb. to consider and adopt the annual report of the activities of the Society,\nc. to consider the audit report of the Society and to adopt the same,\nd. to consider the annual accounts of the Society and to adopt the same,\ne. to consider the annual budget of the Society and to adopt the same,\nf. to appoint auditors and fix their remuneration,\ng. to elect the Members of the Committee and the Officer Bearers of the Society, if due,\nh. to appoint the Secretary of the Society, if required,\ni. to fill in the vacancies of the Committee, if any,\nj. to consider the amendments, if any, to the Bye-laws of the Society,\nk. to review the progress of the implementation of the development and other activities undertaken by the Society,\nl. to consider the programme for the development of the property of the Society and the maintenance thereof,\nm. to transact such other business as may be brought before the meeting with the permission of the Chairman.',
    },
    
    # special-general-meeting page
    'special-general-body-meetings': {
        '96': 'A Special General Body Meeting of the Society may be called at any time at the instance of the Chairman or by the decision of the majority of the Committee and shall be called within one month of the receipt of requisition from the Members of the Society, under the bye-law No. 97.',
        '97': 'The requisition for the special general body meeting of the Society, under the bye-law no. 95 shall be placed within 7 days of its receipt, before the Meeting of the Committee, by the Secretary of the Society.',
        '98': 'The committee shall decide the date, time and place of every General Body Meeting of the Society and the business to be transacted thereat; provided that the business to be transacted at the requisitioned meeting of the Society shall not be changed and the meeting shall be called within the period as specified in the bye-law no. 96.',
        '99': 'In case of the Annual General Body Meeting, 14 clear day\'s Notice and in the case of the special general body meeting, 5 clear day\'s notice of the meeting shall be given to all the Members of the Society.',
        '100': 'The quorum for every general body meeting of the Society shall be 2/3rd of the total number of Members of the Society or 20, whichever is less.',
        '101': 'If within half an hour after the time appointed for general body meeting of the Society, there is no quorum, the meeting, if convened upon the requisition of the Members, shall be dissolved. In any other case, it shall stand adjourned to the same day in the next week, at the same time and place and if on the adjourned meeting, a quorum is not present, the Members present shall form the quorum and may transact the business for which the meeting was called.',
        '102': 'If all the business on the agenda of the General Body Meeting of the Society cannot be transacted on the day on which the General Body Meeting is convened, the meeting shall be postponed to any other suitable date, to be decided by the Chairman of the meeting within 7 days.',
        '103': 'The Chairman of the Society shall preside over all General Body Meetings of the Society, in case if the Chairman is absent or if present and is unwilling to preside, the Members present may elect a person from amongst themselves to preside over the meeting.',
        '104': 'No proxy or a holder of power of attorney or letter of authority shall be eligible to attend a General Body Meeting of the Society on behalf of a Member of the Society.',
        '105': 'Voting right of a Member and the Associate Member of the Society shall be regulated in accordance with the provisions of Section 27 of the Act.',
        '106': 'At the General Body Meeting of the Society, every Active Member of the Society and in his absence, his Associate Member shall have one vote only. In case of equality of votes, the Chairman of the meeting will have a second or casting vote.',
        '107': 'Unless otherwise specifically provided under the Act, the Rules and the Bye-laws of the Society, all questions at a General Body Meeting of the Society shall be decided by a simple majority of Members present and voting.',
        '108': 'The committee shall finalise the draft minutes of every general body meeting of the Society within 3 months of the date of the meeting and circulate the draft minutes amongst all the Members of the Society or get the minutes approved in the next general body meeting. The minutes shall be signed by the Chairman of that meeting.',
        '109': 'No resolution can be brought at a General Body Meeting of the Society, cancelling its previous resolution, unless six clear months have elapsed, after passing of the previous resolution.',
    },
}

# Build bylaw_number -> record mapping
bylaw_to_records = {}
for r in data['bylaws']:
    bn = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
    if bn:
        bylaw_to_records.setdefault(str(bn).strip(), []).append(r)

# Update records
source_urls = {
    'management-affairs': 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/management-affairs',
    'first-general-meeting': 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/first-general-meeting',
    'annual-general-body-meetings': 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/annual-general-body-meetings',
    'special-general-body-meetings': 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/special-general-body-meetings',
}

updated_count = 0
verbatim_sourced_count = 0
for page_slug, bylaws in extracted.items():
    url = source_urls[page_slug]
    for bylaw_num, text in bylaws.items():
        if bylaw_num in bylaw_to_records:
            for record in bylaw_to_records[bylaw_num]:
                old_status = record.get('official_grounding_status', '')
                # Only update if currently fallback or verbatim_source_verified (upgrade to verbatim_sourced)
                # Special case: merge 94(a)+94(b) into bylaw 94
            if bylaw_num in ('94(a)', '94(b)') and '94' in bylaw_to_records:
                for record in bylaw_to_records['94']:
                    old_status = record.get('official_grounding_status', '')
                    if old_status in ('source_derived_fallback', 'verbatim_source_verified', ''):
                        record['official_legal_text'] = merged_94_text
                        record['source_grounded_official_text'] = merged_94_text
                        record['official_grounding_status'] = 'verbatim_sourced'
                        record['official_source_page'] = 'https://mysocietyclub.com/bye-laws/maharashtra-cooperative-housing-society-bye-laws/annual-general-body-meetings'
                        record['source_grounding_status'] = 'verbatim_sourced'
                        print(f'  Updated {record["id"]} (94): {old_status} -> verbatim_sourced (merged 94a+94b)')
                continue
            
            if old_status in ('source_derived_fallback', 'verbatim_source_verified', ''):
                    record['official_legal_text'] = text
                    record['source_grounded_official_text'] = text
                    record['official_grounding_status'] = 'verbatim_sourced'
                    record['official_source_page'] = url
                    record['source_grounding_status'] = 'verbatim_sourced'
                    updated_count += 1
                    if old_status != 'verbatim_sourced':
                        verbatim_sourced_count += 1
                    print(f'  Updated {record["id"]} ({bylaw_num}): {old_status} -> verbatim_sourced')
        else:
            print(f'  WARNING: No record found for bylaw {bylaw_num}')

print(f'\nUpdated {updated_count} records ({verbatim_sourced_count} newly verbatim_sourced)')

# Save updated dataset
with open('dataset/bylaws_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('Dataset saved.')
