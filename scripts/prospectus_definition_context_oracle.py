"""Independently authored context choices and complete answer expectations."""
from copy import deepcopy
from legalmath.prospectus.successor.contracts import digest

KEY = 'definition_context_review'
VERSION = 'definition-context-review.v1'
# Source starts were read from026 and checked in surrounding selected prose.
STARTS = {
 'D03': [363,9178,32964],
 'D04': [538,887],
 'D05': [732,763,822,1024,1330,1479,1704,1945,2219,2333,2457,4641,8319],
 'D06': [927,952,1057,1394],
 'D07': [2601,2704,2732,7911,8007,8141,8237,8403,8499,9269,9800,18671,20021,34629,42983,43240,43382,43726,43778,45075,45389,45430,45902],
 'D08': [2870,2969,18753,20103],
 'D09': [2880,2956,2977,18761,20111],
 'D10': [3000,3024,3195,3341,3392,3453,3693,3862,4273,4376,4790],
 'D11': [3112,3130],
 'U01': [3324,3379,3415,3835,4363,4777,18739,20089],
}
LINKS = {
 'D03': ('basf-amount:issue-amount','amount_reading','SPECIFIED_CURRENCY_EUR'),
 'D04': ('basf-amount:issue-amount','amount_reading','DENOMINATION_100000_EUR'),
 'D05': ('basf-records:form-authentication','records_reading','TEMPORARY_GLOBAL_NOTE'),
 'D06': ('basf-records:form-authentication','records_reading','PERMANENT_GLOBAL_NOTE'),
 'D07': ('basf-records:clearing-definition','records_reading','SELECTED_CLEARING_SYSTEMS_AND_FUNCTIONAL_SUCCESSORS'),
 'D08': ('basf-records:clearing-definition','records_reading','CLEARSTREAM_BANKING_SA'),
 'D09': ('basf-records:clearing-definition','records_reading','EUROCLEAR_BANK_SA_NV'),
 'D10': ('basf-records:clearing-definition','records_reading','EACH_OR_BOTH_ICSDS'),
 'D11': ('basf-records:ngn-custody','records_reading','NEW_GLOBAL_NOTE'),
 'U01': ('basf-records:records-evidence','records_reading','ICSD_CUSTOMER_SHARE_RECORDS'),
}
REASONS = {
 'D03': 'The issue declaration supplies EUR; the payment and successor-payment clauses expressly reuse that specified currency. No actual payment or substitution follows.',
 'D04': 'The issue denomination is reused for notes represented by the exchange certificate; it does not establish aggregate principal or a holding.',
 'D05': 'These references identify the initially temporary certificate through authentication, exchange, records and certified interest; separate exchange prerequisites remain.',
 'D06': 'These references identify the permanent certificate supplied on exchange, retaining authentication and the separate exchange prerequisites.',
 'D07': 'The surrounding provisions refer to the selected clearing arrangement in custody, payment, redemption, notices or enforcement; functional succession is conditional.',
 'D08': 'The alias names Clearstream Banking S.A. in the definition and two partial-redemption record provisions; it does not name Euroclear or a supplied account.',
 'D09': 'The alias names Euroclear Bank SA/NV in the definition and two partial-redemption record provisions; the occurrence inside the full name is retained separately.',
 'D10': 'The declaration distinguishes each institution from the pair; singular and plural references preserve the exact relevant system or systems.',
 'D11': 'The full form name and its acronym refer to the selected NGN/common-safekeeper arrangement, without actual custody evidence.',
 'U01': 'These are the customer-share records of the ICSDs, including partial-redemption updates; their contractual evidence role does not prove actual balances or court effect.',
}


def expected_content(ordinary, decisions):
    old = ordinary['definition_use_bindings']
    uses = deepcopy(old['uses'])
    for use in uses:
        use['prior_disposition'] = use['disposition']
        use['context_binding'] = None
    by_id = {r['record']: r for r in decisions}
    records = []
    for record in old['records']:
        row = by_id.get(record['id'])
        indices = list(record['use_indices'])
        if row is not None:
            expected = {u['start']: u for u in row['uses']}
            assert len(expected) == len(indices)
            for index in indices:
                use = uses[index]
                decision = expected[use['start']]
                assert (use['end'], use['quote'], use['interval']) == (decision['end'], decision['quote'], decision['interval'])
                binding = {k: deepcopy(row[k]) for k in ('record','concept','reason','declarations','meaning','extra_meanings')}
                binding.update({k: deepcopy(decision[k]) for k in ('context','source_piece_indices','number','kind')})
                use['context_binding'] = binding
                use['disposition'] = decision['kind']
                use['remaining'] = (['ACTUAL_FACTS_NOT_ESTABLISHED'] if decision['kind'] == 'BOUND_CONTEXTUALLY'
                                    else ['MENTION_IS_NOT_AN_OPERATIVE_USE'])
        records.append({**deepcopy(record), 'context_reviewed': row is not None,
            'context_use_indices': indices if row is not None else []})
    return {'records': records, 'uses': uses, 'reviewed_records': len(decisions),
        'reviewed_associations': sum(len(r['uses']) for r in decisions),
        'original_associations': 610, 'supplemental_associations': 2}


def expected_report(ordinary, products, profile, content):
    return {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary),
        'definition_report_sha256': digest(ordinary['definition_sources']),
        'prior_binding_report_sha256': digest(ordinary['definition_use_bindings']),
        **deepcopy(content), 'question_links': deepcopy(ordinary['definition_use_bindings']['question_links']),
        'assistance': 'EXACT_OCCURRENCE_SUPPLIED_SOURCE_REVIEW',
        'prior_answer_preserved': True, 'all_governing_uses_established': False,
        'actual_facts_established': False, 'historical_law_established': False,
        'automatic_legal_interpretation': False, 'whole_task_complete': False}


def verify(actual, ordinary, products, profile, content):
    expected = {**ordinary, KEY: expected_report(ordinary, products, profile, content)}
    expected['report_sha256'] = digest({k:v for k,v in expected.items() if k != 'report_sha256'})
    assert actual == expected, 'Whole answer differs from frozen source-context expectation'
    return {'status':'PASS','whole_answer_equal_to_independent_expectation':True,
            'reviewed_records':10,'reviewed_associations':75,'new_context_bindings':72}
