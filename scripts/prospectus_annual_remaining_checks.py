"""Separate source-qualification checks; no inference from profile fingerprints."""
from copy import deepcopy
from scripts.prospectus_annual_policy_checks import require

CASES = [
    ('liability-form', 'financial-liabilities', 'legal_form_decisive', False, True, 'independently from its'),
    ('liability-credit', 'financial-liabilities', 'unquoted_value', 'MARKET_BASED_VALUATION_INCLUDING_ISSUER_OWN_CREDIT_RISK', 'EXCLUDE_OWN_CREDIT_RISK', 'including the own credit risk'),
    ('equity-conflict', 'equity-instruments', 'source_definition_corrected', False, True, 'classified as a financial liability'),
    ('equity-and', 'equity-instruments', 'preference_equity_operator', 'AND', 'OR', 'and if dividends non-cumulative'),
    ('offset-and', 'offsetting', 'condition_operator', 'AND', 'OR', 'and there is an intention'),
    ('heldsale-and', 'held-for-sale', 'classification_operator', 'AND', 'OR', 'available for immediate sale'),
    ('heldsale-lower', 'held-for-sale', 'subsequent_measurement', 'LOWER_OF_CARRYING_AMOUNT_AND_FAIR_VALUE_LESS_SELLING_COSTS', 'GREATER_OF', 'lower of their carrying amount'),
    ('heldsale-extension', 'held-for-sale', 'reported_extension', 'WRITTEN_BANK_OF_PORTUGAL_AUTHORISATION_AND_ITS_CONDITIONS', 'AUTOMATIC', 'written authorization from the Bank of Portugal'),
    ('heldsale-depreciation', 'held-for-sale', 'loan_exchange_property_depreciated', False, True, 'is not depreciated'),
    ('valuation-specific', 'property-valuation', 'method_selected_for_specific_asset', True, False, 'specific situation of the asset'),
    ('land', 'property-equipment', 'land_depreciated', False, True, 'Land is not depreciated'),
    ('recoverable-greater', 'property-equipment', 'recoverable_amount', 'GREATER_OF_NET_SELLING_PRICE_AND_VALUE_IN_USE', 'LOWER_OF', 'greater of its net selling price and value in use'),
    ('intangible-life', 'intangible-software', 'usual_life_years', [3, 6], [1, 3], 'usually between 3 to 6 years'),
    ('intangible-remaining', 'intangible-software', 'remaining_it_costs', 'EXPENSE_AS_INCURRED', 'CAPITALISE_ALL', 'All remaining costs'),
    ('lease-historical', 'leases', 'current_standard_substituted', False, True, 'IAS 17'),
    ('lease-risk', 'leases', 'finance_criterion', 'SUBSTANTIALLY_ALL_OWNERSHIP_RISKS_AND_REWARDS_TRANSFER', 'LEGAL_OWNERSHIP_ONLY', 'substantially all the risks and rewards'),
    ('pension-cutoff', 'pension-plans', 'hire_cutoff_inclusive', '2008-03-31', '2010-12-31', 'hired until 31 March 2008'),
    ('pension-corridor', 'pension-plans', 'corridor_percentage_scope', 'SOURCE_AMBIGUITY_PRESERVED_NO_FORMULA_INFERRED', 'TEN_PERCENT_OF_BOTH_CONFIRMED', 'greater of 10% of the pension liabilities or the fair value of the plan assets'),
    ('pension-amortisation', 'pension-plans', 'outside_corridor_amortisation_years', 15, 10, '15 year period'),
    ('pension-inside', 'pension-plans', 'inside_corridor_to_income', False, True, 'within the corridor are not recognised'),
    ('pension-funding', 'pension-plans', 'active_employee_past_service_minimum_funding_percent', 95, 100, 'minimum level of 95%'),
    ('pension-pensioner', 'pension-plans', 'pensioner_year_end_funding_percent', 100, 95, 'totally funded'),
    ('transition-rates', 'pension-2011-transition', 'contribution_percent', {'total': '26.6', 'employer': '23.6', 'employee': '3'}, {'total': '26.6', 'employer': '3', 'employee': '23.6'}, '23.6% responsibility of the employer and 3%'),
    ('transition-differential', 'pension-2011-transition', 'bank_retained_differential', 'GUARANTEE_PENSION_UNDER_ACT', 'ALL_RISK_TRANSFERRED', 'banks supporting the differential'),
    ('healthcare-rate', 'healthcare', 'contribution_percent', '6.5', '5.6', '6.5%'),
    ('long-service', 'long-service-benefits', 'years_and_monthly_pay', [[15, 1], [25, 2], [30, 3]], [[15, 3], [25, 2], [30, 1]], 'respectively, to 1, 2 and 3 months'),
    ('siba-end', 'siba', 'end', '2010-12', 'ONGOING', 'ended in December 2010'),
    ('siba-settlement', 'siba', 'settlement', 'EQUITY', 'CASH', 'equity settlement'),
    ('siba-remeasure', 'siba', 'subsequent_fair_value_remeasurement', False, True, 'not remeasured'),
    ('pprv-settlement', 'pprv', 'settlement', 'CASH', 'EQUITY', 'cash settlement'),
    ('pprv-retention', 'pprv', 'retention_years', 3, 0, 'minimum period of three years'),
    ('pprv-remeasure', 'pprv', 'subsequent_fair_value_remeasurement', True, False, 're-measured at each balance sheet date'),
    ('prvif-roe', 'prvif', 'share_roe_operator', 'GE', 'GT', 'greater than or equal to 5%'),
    ('prvif-vesting', 'prvif', 'share_vesting_percent_by_year', [33, 33, 34], [34, 33, 33], '33% and 3 rd year: 34%'),
    ('prvif-exercise', 'prvif', 'option_exercise', 'MATURITY_ONLY', 'ANY_TIME', 'only be exercised at maturity'),
    ('prvif-no-awards', 'prvif', 'shares_or_options_attributed', False, True, 'no shares or share options have been attributed'),
    ('prvif-cost-units', 'prvif', '2010_cost_eur_thousand', '3810', '3810000', 'euro 3 810 thousand'),
    ('bonus-period', 'employee-director-bonus', 'recognition', 'INCOME_IN_YEAR_TO_WHICH_BONUS_RELATES', 'WHEN_PAID', 'year to which they relate'),
    ('tax-asset', 'income-tax', 'deferred_asset_condition', 'PROBABLE_FUTURE_TAXABLE_PROFITS_FOR_DEDUCTIBLE_DIFFERENCES', 'AUTOMATIC', 'probable that future taxable profits'),
    ('tax-offset-level', 'income-tax', 'offset_level', 'EACH_SUBSIDIARY', 'WHOLE_GROUP_NET', 'each subsidiary level'),
    ('tax-offset-and', 'income-tax', 'offset_operator', 'AND', 'OR', 'and (ii)'),
    ('provision-and', 'provisions', 'recognition_operator', 'AND', 'OR', 'and (iii)'),
    ('restructure-or', 'provisions', 'restructuring_progress_operator', 'OR', 'AND', 'or has been announced publicly'),
    ('restructure-plan', 'provisions', 'restructuring_plan_and_progress', True, False, 'approved a detailed and formal restructuring plan and'),
    ('onerous-lower', 'provisions', 'onerous_measurement', 'PRESENT_VALUE_OF_LOWER_OF_EXPECTED_TERMINATION_COST_AND_EXPECTED_NET_CONTINUATION_COST', 'GREATER_OF_COSTS', 'present value of the lower'),
    ('eir-loss', 'interest', 'future_credit_losses_included', False, True, 'does not consider future credit losses'),
    ('eir-options', 'interest', 'contractual_terms_include_options', True, False, 'prepayment options'),
    ('fee-act', 'fee-commission', 'significant_act', 'INCOME_WHEN_COMPLETED', 'WHEN_CONTRACT_SIGNED', 'been completed'),
    ('fee-service', 'fee-commission', 'service_period', 'INCOME_DURING_SERVICE', 'AT_INCEPTION', 'period the services are provided'),
    ('dividend-right', 'dividends', 'recognition', 'WHEN_PAYMENT_RIGHT_ESTABLISHED', 'WHEN_CASH_RECEIVED', 'right to receive payment is established'),
    ('segment-date', 'segments', 'standard', 'IFRS8_FROM_2009_01_01', 'IFRS8_FROM_2010_01_01', 'Since 1 January 2009'),
    ('eps-treasury', 'earnings-per-share', 'basic_denominator', 'WEIGHTED_AVERAGE_OUTSTANDING_ORDINARY_SHARES_EXCLUDING_AVERAGE_TREASURY_STOCK', 'INCLUDE_TREASURY_STOCK', 'excluding the average number'),
    ('eps-dilution', 'earnings-per-share', 'dilutive_test', 'CONVERSION_DECREASES_NET_EPS', 'ALL_CONVERSIONS', 'would decrease net earnings per share'),
    ('cash-strict', 'cash-equivalents', 'maturity_operator', 'LT', 'LE', 'less than three months'),
    ('cash-inception', 'cash-equivalents', 'maturity_from', 'INCEPTION_DATE', 'BALANCE_SHEET_DATE', 'from the inception date'),
    ('cash-restriction', 'cash-equivalents', 'restricted_central_bank_balances_included', False, True, 'exclude restricted balances'),
]

ORDERS = {
    'equity-instruments': [(109, [0, 1, 2, 3, 4, 5, 22, 23])],
    'held-for-sale': [(109, list(range(9, 21)) + [43, 44, 45, 46])],
    'pension-plans': [(111, list(range(7)) + [52, 49, 50] + list(range(7, 30)))],
    'income-tax': [(113, [3, 21, 22, 23, 24] + list(range(4, 17)))],
    'provisions': [(113, [17, 18, 19, 47, 48, 25, 26, 27])],
}
LIVES = {'buildings': [35, 50], 'leasehold_improvements': [10, 10], 'computers': [4, 5],
    'furniture': [4, 10], 'fixtures': [5, 12], 'security': [4, 10], 'office': [4, 10], 'vehicles': [4, 4], 'other': [5, 5]}


def check(value, graph):
    units = {u['id']: u for u in graph['units']}
    sections = value['policies']
    rows = {r['id']: r for r in sections}
    require(len(rows) == len(sections) == 24 and set(rows) == {c[1] for c in CASES}, 'Missing policy topic')
    for row in sections:
        require(row['attribution'] == 'ISSUER_ANNUAL_REPORT_2010' and row['independently_verified'] is False, 'Attribution changed')
        require(row['source'] and len({a['unit'] for a in row['source']}) == len(row['source']), 'Missing or duplicate witness')
        for anchor in row['source']:
            u = units[anchor['unit']]
            require(u['visible'] and anchor == {'unit': u['id'], 'page': u['page'], 'source_sha256': u['source_sha256'],
                'start': 0, 'end': len(u['raw']), 'quote': u['raw']}, 'Source witness changed')
    for name, key, field, expected, bad, phrase in CASES:
        require(rows[key]['meaning'][field] == expected, 'Meaning changed: ' + name)
        quote = ' '.join(' '.join(a['quote'] for a in rows[key]['source']).split())
        require(phrase in quote, 'Source qualification absent: ' + name)
    for key, parts in ORDERS.items():
        expected = [f'bes-2010-en:p{page}:l{n}' for page, numbers in parts for n in numbers]
        require([a['unit'] for a in rows[key]['source']] == expected, 'Displayed order changed: ' + key)
    require(rows['property-equipment']['meaning']['useful_lives_years'] == LIVES, 'Useful-life row mapping changed')
    require(rows['prvif']['meaning']['share_roe_threshold_percent'] == 5, 'ROE threshold changed')
    require(rows['cash-equivalents']['meaning']['maturity_months'] == 3, 'Maturity threshold changed')
    require(not value['all_notes_interpreted'] and not value['independent_legal_or_financial_acceptance'], 'Unsupported acceptance')
    return {'status': 'PASS', 'policy_topics': len(rows), 'material_conditions': len(CASES), 'displayed_orders': len(ORDERS),
            'useful_life_rows': len(LIVES), 'attribution_preserved': True}


def mutations(value):
    for name, key, field, expected, bad, phrase in CASES:
        changed = deepcopy(value)
        next(r for r in changed['policies'] if r['id'] == key)['meaning'][field] = deepcopy(bad)
        yield name, changed
    for key in ORDERS:
        changed = deepcopy(value)
        next(r for r in changed['policies'] if r['id'] == key)['source'].reverse()
        yield 'order-' + key, changed
    for key in LIVES:
        changed = deepcopy(value)
        next(r for r in changed['policies'] if r['id'] == 'property-equipment')['meaning']['useful_lives_years'][key] = [99, 99]
        yield 'life-' + key, changed
    for key, field in [('prvif', 'share_roe_threshold_percent'), ('cash-equivalents', 'maturity_months')]:
        changed = deepcopy(value)
        next(r for r in changed['policies'] if r['id'] == key)['meaning'][field] = 0
        yield 'threshold-' + key, changed
