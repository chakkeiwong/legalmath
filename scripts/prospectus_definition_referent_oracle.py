"""Source-first referent decisions and an independent full-answer comparator."""
from copy import deepcopy
from legalmath.prospectus.successor.contracts import digest

KEY = 'definition_referent_review'
VERSION = 'definition-referent-review.v1'
STARTS = {
 'D01': [34,243,271,586,683,858,1516,1741,1857,1981,2256,2645,3069,3272,3512,3631,3767,3981,4077,4436,4530,4603,4836,4963,5035,5449,6200,6509,6920,6999,7090,7514,7829,8076,8282,9149,9410,10081,10186,10248,10311,10399,10500,11282,11429,11479,11557,12430,13000,13825,13906,14572,16651,16752,17083,17184,17370,17897,18042,18205,18454,18511,18598,19002,19319,19464,19627,19861,19948,20358,20581,20681,20797,20862,20982,21439,21583,21684,21736,21864,22029,22601,22851,25164,26623,28220,28341,28726,31325,31747,31833,31953,32319,32575,32714,32917,33622,33710,34298,34545,34823,36434,38469,38625,38783,41727,41829,42025,42132,42251,42565,42724,43008,43942,44171,44385,44571,44745,44915,45256,45517,45850,45991],
 'D02': [299,309,325,1155,4110,4691,5128,5243,5411,6905,9219,10660,11115,11635,11999,12715,12904,13425,13721,13938,14326,14558,15328,15397,15719,17213,17285,17305,17929,18349,18917,18937,19351,19799,20279,20332,20670,20953,23785,24066,24839,24961,25720,26305,28099,28533,28650,29073,29320,29953,30286,30429,30565,30637,30900,31004,31287,32210,32686,33085,33474,33563,34215,34267,35083,35890,36114,38178,38511,38829,39088,39507,39647,39886,40397,40514,40805,41754,42095,42229,42294,43162,44017,44455,44523],
 'D12': [4822,4860,5819,9480,9575,10805,10913,11095,11787,13683,15792,16080,17882,18374,19304,19824,21148,24356,25027,25112,25837,25993,28309,28879,30233,30954,31732,32381,33266,33364,34396,34758,35135,35159,35222,35272,35339,35428,35833,35859,36248,36304,36326,36493,36600,36717,36796,36864,36909,37097,37609,37778,38349,39686,39907,40431,40835,41346,41811,42484,43281,43406,43485,43999,44371,44505,45812,45960],
}
LINKS = {'D01':('basf-amount:issue-amount','amount_reading'),
         'D02':('basf-amount:issue-amount','amount_reading'),
         'D12':('basf-amount:holder-definition','amount_reading')}
SUPPORT = {'D01':[(6072,6457),(32191,34125),(41705,42079)],
           'D02':[(32191,34125),(34125,34657)],
           'D12':[(28908,30278)]}

def decision(key, start, quote):
    if key == 'D01':
        kind, referent = 'BOUND_REFERENT', 'DEFINED_SERIES'
        reason = 'The surrounding provision refers to the series defined in section 1(1), including a note or subset of that series.'
        qualification = 'Issue amount remains subject to section 1(4); no actual holding, balance, issuance or performance is established.'
        if start in (34,4836,41727):
            kind,referent,reason='HEADING_MENTION','MENTION_ONLY','This exact fragment is a document or clause heading; operative prose follows separately.'
        elif start == 6200:
            kind,referent,reason='GENERIC_SECURITY_CLASS','BONDS_IN_CAPITAL_MARKET_DEBT','The definition describes debt represented by bonds or other securities, not only this series.'
        elif start == 34823:
            kind,referent,reason='NAME_COMPONENT','STATUTE_TITLE','This word occurs within the title of the statute, not an invocation of the series alias.'
        elif start == 33710:
            kind,referent,reason='CONDITIONAL_REFERENT','NOTES_UNDER_SUCCESSOR_OBLIGATION','Section 10(d) extends specified programme obligations to successor notes only in the stated substitution setting.'
            qualification='Retain every section 10 condition, the original issuer guarantees and successor distinction; no substitution, release or current debtor is established.'
        elif start == 41829:
            kind,referent,reason='CONDITIONAL_REFERENT','FURTHER_NOTES_JOINING_SERIES','Section 12 permits further notes with matching terms and the stated issue-date, interest-start and price exceptions to form one series.'
            qualification='Permission and matching-term exceptions do not prove a further issue or the actual aggregate outstanding amount.'
    elif key == 'D02':
        kind='BOUND_REFERENT'
        referent='NAMED_BASF_SE' if quote=='BASF' else 'ISSUER_ROLE_WITH_ORIGINAL_BASF_IDENTITY'
        reason='The declaration names BASF SE; this occurrence preserves either that explicit company name or its issuer role.'
        qualification='Section 10 permits conditional substitution but does not globally replace the named company, establish a current debtor or discharge the original issuer guarantees.'
        if start==299:
            kind,referent,reason='NAME_COMPONENT','FULL_COMPANY_NAME','This BASF token is within BASF SE, before the two alias declarations.'
        elif start in (17285,18917,20279,24839,34215):
            kind,referent,reason='HEADING_MENTION','MENTION_ONLY','The exact issuer token belongs to the heading, not the operative sentence following it.'
    else:
        assert key=='D12'
        kind,referent='BOUND_REFERENT','CONTRACTUAL_COOWNER_OR_COMPARABLE_RIGHT_HOLDER'
        reason='This provision refers to the holders described by section 1(5), with the complete qualified source reading retained.'
        qualification='No actual ownership, qualifying comparable right, proprietary-law status, voting eligibility or procedural standing is established.'
        if start in (4822,35833):
            kind,referent,reason='HEADING_MENTION','MENTION_ONLY','The exact holder token is a heading fragment; the subsequent operative sentence is distinct.'
        elif start==30233:
            kind,referent,reason='OTHER_CREDITORS','CREDITORS_OF_OTHER_SECURED_INDEBTEDNESS','Section 9(c) refers to creditors entitled under security for the other indebtedness, not automatically holders of this series.'
    return {'kind':kind,'referent':referent,'reason':reason,'qualification':qualification}

def expected_content(ordinary, decisions):
    prior=ordinary['definition_context_review']; uses=deepcopy(prior['uses']); records=[]
    chosen={r['record']:r for r in decisions}
    for use in uses:
        use['prior_referent_disposition']=use['disposition'];use['referent_binding']=None
    for record in prior['records']:
        row=chosen.get(record['id']);indices=list(record['use_indices'])
        if row is not None:
            expected={(u['interval'],u['start'],u['end']):u for u in row['uses']}
            assert len(expected)==len(indices)
            for index in indices:
                use=uses[index];item=expected[(use['interval'],use['start'],use['end'])]
                assert use['quote']==item['quote'] and use['disposition']=='UNRECONCILED'
                binding={k:deepcopy(row[k]) for k in ('record','declarations','meaning','support')}
                binding.update({k:deepcopy(item[k]) for k in ('context','source_piece_indices','kind','referent','reason','qualification')})
                use.update(referent_binding=binding,disposition=item['kind'],remaining=['SOURCE_READING_IS_CONDITIONAL;ACTUAL_FACTS_AND_HISTORICAL_LAW_OPEN'])
        records.append({**deepcopy(record),'referent_reviewed':row is not None,'referent_use_indices':indices if row is not None else []})
    return {'records':records,'uses':uses,'reviewed_records':3,'reviewed_associations':276,
            'original_associations':610,'supplemental_associations':2}

def expected_report(ordinary,products,profile,content):
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'definition_report_sha256':digest(ordinary['definition_sources']),
        'prior_context_report_sha256':digest(ordinary['definition_context_review']),**deepcopy(content),
        'question_links':deepcopy(ordinary['definition_context_review']['question_links']),
        'assistance':'EXACT_OCCURRENCE_SUPPLIED_SOURCE_REVIEW','prior_answer_preserved':True,
        'all_governing_uses_established':False,'actual_facts_established':False,
        'historical_law_established':False,'automatic_legal_interpretation':False,'whole_task_complete':False}

def verify(actual,ordinary,products,profile,content):
    expected={**ordinary,KEY:expected_report(ordinary,products,profile,content)}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    assert actual==expected,'Whole answer differs from frozen referent expectation'
    return {'status':'PASS','whole_answer_equal_to_independent_expectation':True,
            'reviewed_records':3,'reviewed_associations':276}
