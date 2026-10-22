"""Material source qualifications checked separately from profile fingerprint admission."""
from copy import deepcopy


def require(value, reason):
    if not value:
        raise ValueError(reason)


# Each condition has a concrete source phrase, a material expected meaning and
# an adverse alternative. These are source-review cases, not general IFRS rules.
CASES = [
    ('control', 'subsidiary-control', 'control_below_50_possible', True, False, 'even if its shareholding is less than 50%'),
    ('nci-deficit', 'subsidiary-control', 'nci_losses_from_2010', 'PROPORTIONATE_ATTRIBUTION_EVEN_IF_NCI_DEFICIT', 'PARENT_ABSORBS_ALL_EXCESS', 'having a deficit balance'),
    ('influence', 'associate-influence', 'influence_below_20_possible', True, False, 'less than 20%'),
    ('loss-exception', 'associate-influence', 'loss_limit_exceptions', ['LEGAL_OR_CONSTRUCTIVE_COVERAGE_OBLIGATION', 'PAYMENTS_ON_BEHALF_OF_ASSOCIATE'], [], 'except when it has a legal or constructive obligation'),
    ('spe-control', 'spe-and-managed-funds', 'spe_ownership_percentage_decisive', False, True, 'independently of the percentage'),
    ('fund-control', 'spe-and-managed-funds', 'managed_fund_exception', 'CONTROL_UNDER_SIC_12', 'NO_EXCEPTION', 'except in the cases where control'),
    ('goodwill-cost', 'goodwill-policy', 'transaction_costs_from_2010', 'EXPENSE_AS_INCURRED', 'CAPITALISE', 'Transaction costs are expensed as incurred'),
    ('goodwill-nci', 'goodwill-policy', 'recognized_goodwill_scope', 'PARENT_EQUITY_HOLDERS_ONLY', 'ALL_INTERESTS_FULL_GOODWILL', 'only to the portion attributable'),
    ('nci-loss-control', 'nci-transactions', 'sale_or_dilution_with_loss_control', 'INCOME_GAIN_OR_LOSS', 'EQUITY_ONLY', 'results a loss of control'),
    ('fx-wording', 'group-currency-translation', 'source_wording_corrected', False, True, 'translated into the functional currency'),
    ('elimination', 'consolidation-eliminations', 'impairment_loss_exception', True, False, 'unless unrealised losses provide evidence'),
    ('afs-fx', 'foreign-currency-transactions', 'afs_equity_exception', 'EQUITY_FAIR_VALUE_RESERVE', 'INCOME', 'except if related to equity'),
    ('hedge-and', 'derivatives-and-hedge-qualification', 'hedge_qualification_operator', 'AND', 'OR', 'provided the following criteria are met'),
    ('fair-risk', 'fair-value-hedge', 'hedged_item_adjustment', 'ONLY_FAIR_VALUE_CHANGE_ATTRIBUTABLE_TO_HEDGED_RISK', 'ALL_FAIR_VALUE_CHANGES', 'attributable to the risks being hedged'),
    ('no-cash-hedges', 'cash-flow-hedge-and-embedded-derivatives', 'reported_cash_flow_hedges_in_covered_periods', False, True, 'did not have any transactions classified as cash flow hedge'),
    ('embedded-and', 'cash-flow-hedge-and-embedded-derivatives', 'embedded_separation_operator', 'AND', 'OR', 'and the host contract is not carried'),
    ('derecognition', 'customer-loan-recognition', 'derecognition_operator', 'OR', 'AND', 'or (iii)'),
    ('incurred-loss', 'customer-loan-impairment', 'later_ifrs9_ecl_inferred', False, True, 'events that occurred after its initial recognition'),
    ('loan-loss-and', 'customer-loan-impairment', 'loss_condition_operator', 'AND', 'OR', 'and (ii)'),
    ('collective', 'customer-loan-impairment', 'individually_unimpaired_collective_test', True, False, 'no evidence of loss has been identified'),
    ('no-double-count', 'customer-loan-impairment', 'individually_impaired_in_collective_test', False, True, 'not included in a collective assessment'),
    ('variable-rate', 'customer-loan-impairment', 'variable_rate_discount', 'CURRENT_CONTRACT_EFFECTIVE_INTEREST_RATE', 'ORIGINAL_EFFECTIVE_INTEREST_RATE', 'current effective interest rate'),
    ('trade-date', 'other-asset-classification-recognition', 'purchase_sale_recognition', 'TRADE_DATE', 'SETTLEMENT_DATE', 'recognised on trade date'),
    ('no-reclassification', 'other-asset-measurement-reclassification', 'reported_reclassifications_2009_2010', False, True, 'there were no reclassifications'),
    ('equity-reversal', 'other-asset-impairment', 'afs_equity_reversal', 'EQUITY', 'INCOME', 'reversal is recognised in equity'),
    ('htm-reversal', 'other-asset-impairment', 'htm_reversal_condition', 'DECREASE_OBJECTIVELY_RELATED_TO_EVENT_AFTER_IMPAIRMENT', 'ANY_VALUE_INCREASE', 'related objectively to an event occurring after'),
    ('repo', 'repos-and-securities-lending', 'repo_securities_derecognised', False, True, 'are not derecognised'),
    ('reverse-repo', 'repos-and-securities-lending', 'reverse_repo_securities_recognised', False, True, 'reverse repos'),
    ('borrowed', 'repos-and-securities-lending', 'borrowed_securities_recognised', False, True, 'Securities borrowed under borrowing agreements are not recognised'),
    ('opening', 'venezuela-branch', 'opening_status', 'PREDICTED_NOT_CONFIRMED', 'COMPLETED', 'predictably'),
    ('opening-date', 'venezuela-branch', 'opening_period', 'Q3_2011', 'JANUARY_2011', 'third quarter of 2011'),
    ('moza-date', 'moza-acquisition', 'completed', '2011-01-20', '2010-10-26', 'operation took place on January 20, 2011'),
    ('moza-total', 'moza-acquisition', 'total_investment_eur_million', '8.1', '7.1', 'total investment of euro 8.1 million'),
    ('moza-percent', 'moza-acquisition', 'stake_percent', '25.1', '100', 'stake of 25.1%'),
    ('aman-unit', 'libya-aman-exposure', 'investment_eur_million', '40.3', '40300', 'million as disclosed in Note 45'),
    ('aman-loss', 'libya-aman-exposure', 'quantified_impairment_loss_inferred', False, True, 'closely monitoring'),
]


def check(value, graph):
    units = {u['id']: u for u in graph['units']}
    sections = value['policies'] + value['events']
    rows = {s['id']: s for s in sections}
    require(len(rows) == len(sections) == 20, 'Seventeen policy topics and three events required')
    require(set(rows) == {r[1] for r in CASES}, 'Source topics omitted or renamed')
    for section in sections:
        require(section['attribution'] == 'ISSUER_ANNUAL_REPORT_2010' and section['independently_verified'] is False,
                'Issuer attribution promoted')
        require(section['source'] and len({a['unit'] for a in section['source']}) == len(section['source']), 'Missing/duplicate witness')
        for a in section['source']:
            u = units[a['unit']]
            require(u['visible'] and a == {'unit': u['id'], 'page': u['page'], 'source_sha256': u['source_sha256'],
                'start': 0, 'end': len(u['raw']), 'quote': u['raw']}, 'Source witness differs')
    for name, key, field, expected, bad, phrase in CASES:
        require(rows[key]['meaning'][field] == expected, 'Meaning changed: ' + name)
        require(phrase in ' '.join(a['quote'] for a in rows[key]['source']), 'Source qualification absent: ' + name)
    require([a['unit'] for a in rows['consolidation-eliminations']['source']] ==
            ['bes-2010-en:p105:l' + str(n) for n in [50, 46, 47, 48, 7, 8]], 'Displayed elimination order lost')
    require(rows['other-asset-classification-recognition']['source'][1]['unit'] == 'bes-2010-en:p107:l23' and
            rows['other-asset-classification-recognition']['source'][17]['unit'] == 'bes-2010-en:p107:l48',
            'Displayed asset headings lost')
    require([r['id'] for r in value['events']] == ['venezuela-branch', 'moza-acquisition', 'libya-aman-exposure'], 'Displayed event order lost')
    require(not value['all_notes_interpreted'] and not value['independent_legal_or_financial_acceptance'], 'Unsupported completion/acceptance')
    require(rows['venezuela-branch']['meaning']['approval_time_as_reported'] == 'END_OF_OCTOBER_YEAR_NOT_EXPLICIT_IN_BULLET', 'Unstated approval year inferred')
    return {'status': 'PASS', 'policy_topics': 17, 'events': 3, 'material_conditions': len(CASES), 'attribution_preserved': True}


def mutations(value):
    for name, key, field, expected, bad, phrase in CASES:
        changed = deepcopy(value)
        next(r for r in changed['policies'] + changed['events'] if r['id'] == key)['meaning'][field] = deepcopy(bad)
        yield name, changed
    changed = deepcopy(value)
    next(r for r in changed['policies'] if r['id'] == 'consolidation-eliminations')['source'] = [
        a for a in next(r for r in changed['policies'] if r['id'] == 'consolidation-eliminations')['source']
        if a['unit'] not in ('bes-2010-en:p105:l46', 'bes-2010-en:p105:l47', 'bes-2010-en:p105:l48')]
    yield 'displaced-elimination', changed
    changed = deepcopy(value)
    changed['events'].reverse()
    yield 'event-order', changed
