"""Source-bound conditional answers and declared, limited argument controls."""
from copy import deepcopy
from scripts.legal_mission_execution import digest, require, ref, read, save
from scripts.legal_integration_master import ROOT, BASE, DOC

SOURCE = BASE / 'remaining-work/quotation-repair-envelope.json'
BANK = 'artifacts/legal-mission-control/2026-10-12/remaining-work/conditional-source-bank.json'


def source_quote(envelope, quote, *, unit_id=None):
    """Locate the exact passage, never an unrelated prefix of a long unit."""
    require(bool(quote), 'Empty source quotation')
    hits = []
    for unit in envelope['source_packet']['units']:
        if unit_id is not None and unit['unit_id'] != unit_id:
            continue
        text = unit['text']
        count = text.count(quote)
        require(count <= 1, 'Ambiguous quotation within source unit')
        if count:
            start = text.index(quote)
            hits.append({'unit_id': unit['unit_id'], 'quote': quote,
                         'locator': unit.get('locator'), 'start': start,
                         'end': start + len(quote), 'unit_text_hash': digest(text)})
    require(len(hits) == 1, 'Quotation must identify exactly one source unit')
    return hits[0]


def circular(envelope, number):
    prefixes = {10:'u17.',11:'u18.',12:'u19.',13:'u20.',14:'u21.',15:'u22.',16:'u23.',
                'FN1':'u40.','FN5':'u44.'}
    units = [u for u in envelope['source_packet']['units']
             if u['unit_id'].startswith('d996fc27b2d2e.' + prefixes[number])]
    require(len(units) == 1, 'Circular source identity changed')
    return source_quote(envelope, units[0]['text'], unit_id=units[0]['unit_id'])


def conditional_account(qid, envelope):
    bank = read(ROOT / BANK)
    sources = {}
    def add(key, item):
        sources[key] = item
    def para(number):
        add('26EC22:' + str(number), circular(envelope, number))
    def case(tag):
        row = bank[tag]
        add(tag, source_quote(envelope, row['passage']['span']['quote']))
        sources[tag]['original'] = row['original']
        sources[tag]['numbering_limit'] = 'Use only the separately reviewed answer-passage locators.'
    if qid in ('p10', 'evidence'):
        for n in (10, 11, 12, 'FN1'):
            para(n)
        add('UT-Code:6.8', source_quote(envelope,
            '6.8 The scheme, or in the case of a unit trust, the trustee or the person so appointed by the trustee must maintain a register of holders.',
            unit_id='d497635c84096.u0.0'))
        reasoning = [
            {'source_keys':['26EC22:10','26EC22:FN1'], 'text':
             'Paragraph 10 leaves ultimate responsibility for management, operational soundness and ownership record keeping with the Product Provider despite outsourcing. Footnote 1 repeats full responsibility and explains why records reflecting investors’ ownership matter. An appointment allocates performance; it does not itself discharge this responsibility.'},
            {'source_keys':['UT-Code:6.8','26EC22:FN1'], 'text':
             'The retained Code on Unit Trusts and Mutual Funds 6.8 requires a register maintained by the scheme, trustee or person appointed by the trustee. Footnote 1 expressly preserves the Product Provider’s responsibility despite such arrangements. Section I Handbook 6.8 concerns Product Key Facts Statements and supplies no outsourcing rule. Edition and applicability still require review.'},
            {'source_keys':['26EC22:11','26EC22:12'], 'text':
             'Proper records of ownership, operational compatibility, appropriate risk measures and a robust continuity plan concern conduct and results as well as responsibility allocation. A supervision or reconciliation event is evidence relevant to these requirements, but proof that the event occurred does not establish its adequacy.'},
            {'source_keys':['26EC22:11'], 'text':
             'As a logical counterexample, two records may agree because both copied the same mistaken owner. Agreement then establishes consistency without establishing the ownership interest that the records should reflect. The legal account needs constitutive terms, rights, parties and record provenance, alongside reconciliation evidence.'},
            {'source_keys':['26EC22:10','26EC22:11'], 'text':
             'The strongest narrower reading treats paragraph 10 principally as allocation of responsibility, leaving the content of particular standards to paragraph 11, other applicable requirements and the arrangement. A stronger conduct or outcome reading needs those additional warrants. The retained wording does not by itself establish strict liability for every operational defect, or a universal deadline or action that cures a breach.'},
        ]
        facts = ['Applicable product code and source edition; provider/trustee/delegate roles and constitutive terms.',
                 'Delegation powers, monitoring access, incident chronology and actual remedial decisions.',
                 'Which record constitutes or evidences ownership; reconciliation design and independent title evidence.']
        conditions = [
            {'if':'Performance is outsourced','then':'Ultimate responsibility remains with the Product Provider under the retained wording; fulfillment still needs assessment.'},
            {'if':'Records match but identify the wrong owner','then':'Matching cannot establish proper ownership records; investigate the shared error and the governing rights.'},
            {'if':'A defect and a remedy are documented','then':'Assess the remedy against the applicable duty and facts; no universal cure rule has been established.'}]
        limits = ['No complete individual fulfillment review of the original obligations/readings.',
                  'No established general liability or cure standard beyond the inspected wording.']
        dossier = 'p10-standard' if qid == 'p10' else 'p10-effective-mitigation'
    elif qid == 'p14':
        for n in (10, 11, 12, 13, 14, 15, 16, 'FN1', 'FN5'):
            para(n)
        add('Appendix:audit', source_quote(envelope,
            'If the intermediary relies on a smart contract audit conducted by a third party, it should be able to demonstrate that it is reasonable to rely on such smart contract audit. The smart contract audit should focus on reviewing whether the smart contract is not subject to any contract vulnerabilities or security flaws with a high level of confidence.',
            unit_id='d4b586a37635c.u0.0'))
        reasoning = [
            {'source_keys':['26EC22:14'], 'text':
             'On the main-text reading, confirmation is standing while demonstration is conditional on an SFC request. The stated object includes management and operational soundness, ownership record keeping and smart-contract integrity; the demonstration is to the SFC’s satisfaction. Absence of a request answers activation of this demonstration limb only.'},
            {'source_keys':['26EC22:FN5','26EC22:14'], 'text':
             'Footnote 5 says “confirm and demonstrate” without repeating the request qualification. A standing-demonstration reading therefore remains a rival. Reading the footnote as specifying the content of the main paragraph preserves the request qualification; treating it as an additional standing obligation does not. No inspected express priority rule conclusively resolves that attachment.'},
            {'source_keys':['26EC22:FN5','Appendix:audit','26EC22:FN1'], 'text':
             'The Appendix places “with a high level of confidence” specifically in the technical smart-contract audit discussion. That supports technical attachment of the similar footnote language, without proving it exclusively qualifies that limb. Wider evidential attachment remains possible. The Appendix is non-exhaustive and referred to where applicable; it supplies no numerical threshold and does not equate technical confidence with SFC satisfaction.'},
            {'source_keys':['26EC22:15','26EC22:16'], 'text':
             'Paragraph 15 separately concerns obtaining third-party audit or verification, on request, of the stated operational, record and contract matters. Paragraph 16 concerns obtaining a satisfactory legal opinion, on request, to support the application. Neither procurement is identical to the paragraph-14 demonstration, and neither substitutes automatically for confirmation or the underlying paragraphs 10–13 requirements.'},
            {'source_keys':['Appendix:audit','26EC22:14'], 'text':
             'A report on contract V1 does not establish assurance about a materially changed deployed V2. Reliance needs a basis connecting scope, method and version to the arrangement. Even an adequate technical report does not itself establish that the SFC is satisfied.'}]
        facts = ['Whether, when and for what scope the SFC requested demonstration, audit/verification or legal opinion.',
                 'What was confirmed and by whom; deployed contract and audit versions; identified flaws and changes.',
                 'Basis for reliance on third-party work and the actual SFC response.']
        conditions = [
            {'if':'No SFC request is established','then':'Main-text demonstration is not shown activated; confirmation and underlying duties remain, and the footnote rival remains open.'},
            {'if':'A request is established but demonstration is inadequate','then':'The requested-demonstration condition is not fulfilled on that reading.'},
            {'if':'An adequate demonstration is established','then':'Only that scoped condition is fulfilled; confirmation, paragraphs 10–13 and separate requests need their own assessment.'},
            {'if':'Request status is unknown','then':'Keep both branches conditional; unknown is not no request.'}]
        limits = ['Attachment and legal priority remain unresolved.', 'No client compliance or numerical confidence conclusion.']
        dossier = 'p14-attachment'
    else:
        require(qid == 'gatecoin', 'Unknown original question')
        for tag in ('gatecoin-2023.terms-and-intention','gatecoin-2023.conclusion-82',
                    'gatecoin-2025.classification-8','gatecoin-2025.disposition-95',
                    'gatecoin-2025.annexure-issue1','gatecoin-2025.earlier-decision'):
            case(tag)
        reasoning = [
            {'source_keys':['gatecoin-2023.terms-and-intention','gatecoin-2023.conclusion-82'], 'text':
             'The 2023 decision distinguishes cryptocurrency’s capacity to be property held on trust from whether Gatecoin actually held it on trust for the relevant customers. The latter turns on the terms and objective relationship, including intention. Labels such as ownership or custody may be persuasive but are not conclusive. The decision excludes NCCs from its general 2018-terms conclusion.'},
            {'source_keys':['gatecoin-2025.classification-8','gatecoin-2025.annexure-issue1'], 'text':
             'For scenarios one to four, the 2025 direction supports NCC treatment unless there is evidence of access/use to effect the transactions. A post-change entry alone does not establish customer action. Contrary access evidence defeats reliance on this default; that defeat alone does not prove the opposite legal classification. Unknown category membership cannot establish the direction’s premise.'},
            {'source_keys':['gatecoin-2025.classification-8','gatecoin-2025.annexure-issue1'], 'text':
             'Scenarios five and six have different prima facie treatment and specified exceptions concerning earlier or non-platform instructions. The Annexure and factual reasons constrain those exceptions. The event category, actor, instruction date and actual platform action matter; neither “every entry proves consent” nor “entries are irrelevant” follows.'},
            {'source_keys':['gatecoin-2025.classification-8','gatecoin-2025.disposition-95'], 'text':
             'The reasons say scenario-seven transactions did not exist and the customers should not be regarded as NCC; paragraph 95 nevertheless includes scenarios five to seven in exception language. This retained tension requires authoritative clarification or later treatment. It cannot supply an adverse premise about scenarios one to four.'},
            {'source_keys':['gatecoin-2025.disposition-95'], 'text':
             'The decision separately rejects a Gatecoin trust for Mr Samara and treats the specified account as not NCC. Rights against another party do not by themselves establish that separate trust relationship. Transferring any proposition to a Product Provider needs the target asset/right, governing law, parties, constitutive terms, consent history and record role; the court’s NCC direction is not a universal token-holder rule.'}]
        facts = ['Governing terms and dates, relevant customer/provider/intermediary relationships and property rights.',
                 'Transaction category, instruction timing, actual access/use evidence and contrary evidence.',
                 'Official correction, further direction, appeal or reasoned later treatment of the scenario-seven inconsistency.']
        conditions = [
            {'if':'Scenario one to four is established and no contrary evidence is established under the direction','then':'The scoped defeasible direction supports NCC treatment.'},
            {'if':'Access/use evidence to effect that transaction is established','then':'The NCC default is defeated; determine the legal classification from the remaining terms, evidence and directions.'},
            {'if':'Category or contrary-evidence status is unknown','then':'Keep the default’s application conditional; do not silently treat an unknown fact as false.'},
            {'if':'The target is a Product Provider under 26EC22','then':'Establish the legal and factual bridge; do not transplant NCC presumptions or case-specific deadlines.'}]
        limits = ['Scenario-seven tension unresolved; no exhaustive later-treatment search completed.',
                  'Only identified answer passages have scoped locator review; full judgments remain unqualified.']
        dossier = 'gatecoin-transfer'
    return {'profile':'source-bound-conditional-account.v2','question_id':qid,
        'question':next(q['text'] for q in envelope['original_questions'] if q['question_id']==qid),
        'source':ref(ROOT,SOURCE),'sources':sources,'reasoning':reasoning,
        'conditions':conditions,'facts_required':facts,'remaining_limits':limits,
        'dossier':ref(ROOT,DOC/'results'/(dossier+'.md')),
        'original_inventory_fulfilled':False,'actual_product_answer':False,
        'current_law_exhaustive':False,'status':'CONDITIONAL_SOURCE_ACCOUNT'}


def graph_proposal(qid, case, envelope):
    """Expose reading and fact premises; unknown premises block their arguments."""
    def quote(item):
        return {k:item[k] for k in ('unit_id','quote')}
    def argument(name, cid, conclusion, source, assumptions):
        return {'argument_id':name,'candidate_id':cid,'parents':[],
            'premises':[{'premise_id':name+'.source','proposition':{'atom':name+'.wording','negative':False},
                'kind':'ORDINARY','status':'SUPPORTED','evidence':[source],
                'explanation':'Only the presence of this exact wording is established.'},
                *[{'premise_id':name+'.'+key,'proposition':{'atom':key,'negative':False},
                    'kind':'ASSUMPTION','status':status,'evidence':[], 'explanation':explanation}
                  for key,status,explanation in assumptions]],
            'inference_id':'inf.'+name,'inference_kind':'DEFEASIBLE',
            'inference':'Apply the stated restricted reading to the explicitly assumed facts only.',
            'conclusion':conclusion,'evidence':[source]}
    attacks=[]
    if qid=='gatecoin':
        require(case in ('SUPPORTED','ADVERSE','UNKNOWN'), 'Unknown Gatecoin control')
        source=quote(source_quote(envelope,
            'The customers should be regarded as NCCs unless there is evidence to show that they have accessed or used the Platform to effect the transactions;',
            unit_id='dbccd54bdabce.u0.0'))
        primary=argument('default','gatecoin.scenarios-one-to-four',
            {'atom':'ncc','negative':False}, source,
            [('category','QUESTIONED' if case=='UNKNOWN' else 'STATED','Hypothetical membership of scenarios one to four in this liquidation.'),
             ('direction','STATED','Use the scoped NCC direction; do not infer missing facts to be false.')])
        args=[primary]
        if case=='ADVERSE':
            contrary=argument('access','gatecoin.contrary-access',
                {'atom':'applicable.inf.default','negative':True},source,
                [('access_use','STATED','Hypothetical evidence of access/use to effect the relevant transaction is established.')])
            args.append(contrary)
            attacks=[{'attacker':'access','target':'default','kind':'UNDERCUT','target_component':'inf.default',
                      'rationale':'The express unless clause defeats the default; it does not prove non-NCC status.'}]
        expected={'SUPPORTED':['default'],'ADVERSE':['access'],'UNKNOWN':[]}[case]
    else:
        require(qid=='p14' and case in ('NO_REQUEST_RIVALS','REQUEST_INADEQUATE','REQUEST_ADEQUATE','UNKNOWN'),
                'Unknown P14 control')
        main=quote(circular(envelope,14)); foot=quote(circular(envelope,'FN5'))
        if case=='NO_REQUEST_RIVALS':
            args=[argument('main','p14.main-request-reading',{'atom':'standing_demonstration','negative':True},main,
                    [('main_reading','STATED','Assume demonstration is qualified by the main-text request trigger.'),
                     ('no_request','STATED','Hypothetical absence of an applicable SFC request.')]),
                  argument('footnote','p14.footnote-standing-reading',{'atom':'standing_demonstration','negative':False},foot,
                    [('footnote_reading','STATED','Assume footnote 5 imposes standing demonstration.'),
                     ('no_request','STATED','Same hypothetical absence of a request.')])]
            attacks=[{'attacker':a,'target':b,'kind':'REBUT','target_component':b,
                      'rationale':'Opposed conditional readings are retained without an authoritative preference.'}
                     for a,b in [('main','footnote'),('footnote','main')]]
            expected=[]
        else:
            adequate=case=='REQUEST_ADEQUATE'
            args=[argument('main','p14.requested-demonstration',{'atom':'requested_demonstration_satisfied','negative':not adequate},main,
                [('main_reading','STATED','Assume the scoped main-text demonstration reading.'),
                 ('request','QUESTIONED' if case=='UNKNOWN' else 'STATED','An applicable request is hypothetical, or explicitly unknown.'),
                 ('adequacy','QUESTIONED' if case=='UNKNOWN' else 'STATED',
                  'Demonstration is assumed adequate.' if adequate else 'Demonstration is assumed inadequate, or unknown in the unknown control.')])]
            expected=[] if case=='UNKNOWN' else ['main']
    value={'arguments':args,'attacks':attacks,'preferences':[],'cases':[],'case_queries':[],
           'questions':['Reading assumptions and hypothetical facts are not established client facts or authoritative legal priorities.']}
    return value,expected


def run_graph(qid,envelope,directory):
    from scripts.legal_independent_tools import IndependentProductToolBackend
    from legalmath.interpretation.assurance.arguments import evaluate_criticism
    backend=IndependentProductToolBackend(['pyarg','carneades','clingo'])
    identity=backend.identity(); rows={}
    cases=('SUPPORTED','ADVERSE','UNKNOWN') if qid=='gatecoin' else (
        'NO_REQUEST_RIVALS','REQUEST_INADEQUATE','REQUEST_ADEQUATE','UNKNOWN')
    for case in cases:
        proposal,expected=graph_proposal(qid,case,envelope)
        candidates=sorted({a['candidate_id'] for a in proposal['arguments']})
        evaluation=evaluate_criticism(proposal,envelope['source_packet'],candidates)
        require(evaluation['semantics']['grounded']==expected, 'Unexpected declared graph consequence')
        output=backend.criticism(envelope['source_packet'],{'proposal':proposal,'evaluation':evaluation},directory/case)
        require(output['status']=='PASS' and len(output['results'])==3
                and all(r['status']=='PASS' for r in output['results']), 'Native argument adapter failed')
        rows[case]={'proposal':proposal,'expected_grounded':expected,'evaluation':evaluation,'native':output}
    require(backend.identity()==identity,'Native implementation changed during controls')
    path=directory/'targets.json'
    save(path,{'profile':'warranted-conditional-graph.v2','question':qid,'source':ref(ROOT,SOURCE),
        'executions':rows,'identity':identity,'answer_effect_evaluated':False,
        'legal_warrant':'Reviewed only for the explicitly stated conditional interpretation and hypothetical premises.',
        'limit':'Native consequences do not select the authoritative reading or establish client facts.'})
    return {'targets':ref(ROOT,path),'cases':list(cases),'native_adapters':['pyarg','carneades','clingo'],
        'answer_effect_evaluated':False,'_conclusion':qid+' scoped warranted controls executed; complete original answers and matched effects remain open.'}
