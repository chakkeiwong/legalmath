"""Source-facing semantic checks, separate from the exact-profile production gate."""


def require(value, reason):
    if not value:
        raise ValueError(reason)


def check(value, graph):
    units = {u['id']: u for u in graph['units']}
    sections = [value['basis'], value['judgment_context'], *value['judgments'], *value['pronouncements']]
    require(len({s['id'] for s in sections}) == len(sections), 'Duplicate meaning identity')
    for s in sections:
        require(s['attribution'] == 'ISSUER_ANNUAL_REPORT_2010' and s['independently_verified'] is False,
                'Issuer attribution promoted')
        require(s['source'] and len({a['unit'] for a in s['source']}) == len(s['source']), 'Missing or duplicate source witness')
        for a in s['source']:
            u = units[a['unit']]
            require(a == {'unit': u['id'], 'page': u['page'], 'source_sha256': u['source_sha256'],
                          'start': 0, 'end': len(u['raw']), 'quote': u['raw']}, 'Source witness changed')
    by_id = {s['id']: s for s in sections}
    text = lambda key: ' '.join(a['quote'] for a in by_id[key]['source'])
    meaning = lambda key: by_id[key]['meaning']
    require(value['all_notes_interpreted'] is False and value['legal_or_independent_financial_acceptance'] is False,
            'Unsupported complete/independent interpretation')
    b = meaning('basis-of-preparation')
    require(b['standard_set'] == 'IFRS_EFFECTIVE_AND_ADOPTED_BY_EU_AT_REPORTING_DATE' and
            b['reporting_date'] == '2010-12-31' and 'effective and adopted by the EU until' in text('basis-of-preparation'),
            'EU/date boundary erased')
    require(b['measurement_basis'] == 'HISTORICAL_COST_WITH_SPECIFIED_FAIR_VALUE_EXCEPTIONS' and
            len(b['fair_value_exceptions']) == 5 and 'except for the assets and liabilities accounted at fair value' in text('basis-of-preparation'),
            'Historical-cost exceptions erased')
    require(b['management_estimates_required'] and b['future_actual_results_may_differ'] and
            'Actual results in the future may differ' in text('basis-of-preparation'), 'Estimation uncertainty erased')
    require(b['board_approval_date'] == '2011-02-25' and not b['board_approval_is_auditor_date'] and
            '25 February 2011' in text('basis-of-preparation'), 'Board approval conflated with audit closing')
    require(len(value['judgments']) == 7, 'Seven judgment topics required')
    a = meaning('available-for-sale-impairment')
    require(a['equity_parameters'] == {'operator': 'OR', 'market_decline_percent': {'operator': 'GT', 'value': 30, 'base': 'ACQUISITION_COST'},
                                     'below_cost_months': {'operator': 'GT', 'value': 12}, 'role': 'REPORTED_ASSESSMENT_PARAMETERS'} and
            'above 30%' in text('available-for-sale-impairment') and 'or market value below' in text('available-for-sale-impairment') and
            'longer than' in text('available-for-sale-impairment'), 'Equity impairment condition changed')
    require(a['equity_thresholds_apply_to_debt'] is False and
            a['debt_parameters'] == 'OBJECTIVE_EVIDENCE_OF_EVENTS_AFFECTING_ESTIMATED_FUTURE_CASH_FLOWS' and
            '(ii) Debt securities: objective evidence' in text('available-for-sale-impairment'), 'Debt/equity conditions conflated')
    require([a['unit'] for a in by_id['derivative-fair-value']['source']][-2:] ==
            ['bes-2010-en:p115:l43', 'bes-2010-en:p115:l44'], 'Displayed derivative consequence lost')
    require(by_id['loan-impairment']['source'][0]['unit'] == 'bes-2010-en:p115:l41' and
            'Note 2.5' in text('loan-impairment') and 'amount and timing' in text('loan-impairment'), 'Displayed loan heading/body misbound')
    h = meaning('held-to-maturity')
    require(h['exceptions_exist'] and h['exception_example'] == 'INSIGNIFICANT_AMOUNT_SOLD_CLOSE_TO_MATURITY' and
            'other than for the specific circumstances' in text('held-to-maturity'), 'Held-to-maturity exception erased')
    t = meaning('income-tax-uncertainty')
    require(t['reported_review_period_years'] == {'ordinary': 4, 'tax_losses_carried_forward': 6} and
            t['ultimate_tax_determination_uncertain'] and t['additional_assessments_possible'] and
            t['no_material_differences_expected'] == 'BOARD_CONFIDENCE_NOT_ESTABLISHED_OUTCOME' and
            not t['current_tax_law_independently_verified'] and 'four years or six years' in text('income-tax-uncertainty'),
            'Tax qualification erased or promoted')
    adopted = {'ifrs1-ias27-deemed-cost', 'ifrs3-ias27-business-combinations', 'ifrs5-disclosures',
               'ias39-eligible-hedged-items', 'ifric12-concessions', 'ifric17-noncash-distributions',
               'ifric18-customer-transfers', 'annual-improvements-ifrs5-disposal'}
    future = {'ifrs9-classification-measurement', 'ifrs7-transfers-disclosures', 'ias24-related-parties',
              'ias32-rights-issues', 'ifric14-minimum-funding-prepayments', 'ifric19-debt-for-equity'}
    require({p['id'] for p in value['pronouncements']} == adopted | future, 'Fourteen distinct pronouncements required')
    for p in value['pronouncements']:
        expected = 'ADOPTED_IN_2010' if p['id'] in adopted else 'NOT_YET_ADOPTED_BY_GROUP'
        heading = 'ALREADY ADOPTED BY THE GROUP' if p['id'] in adopted else 'YET TO BE ADOPTED BY THE GROUP'
        require(p['meaning']['reported_adoption'] == expected and heading in text(p['id']), 'Adoption heading/state changed')
        require(p['meaning']['impact'].startswith('GROUP_'), 'Impact promoted to independent outcome')
    c = meaning('ifric12-concessions')
    require((c['reported_effective_date'], c['reported_eu_endorsement_year'], c['reported_group_applicable_from']) ==
            ('2008-01-01', 2009, '2010-01-01') and 'only applicable to' in text('ifric12-concessions') and
            'Group from 1 January 2010' in text('ifric12-concessions'), 'IFRIC12EU/application dates collapsed')
    f = meaning('ifrs9-classification-measurement')
    require(f['reported_mandatory_from'] == '2013-01-01' and f['eu_status_at_report'] == 'NOT_YET_ADOPTED' and
            f['amortised_cost_conditions']['operator'] == 'AND' and len(f['amortised_cost_conditions']['conditions']) == 3 and
            not f['later_ifrs9_versions_or_ecl_inferred'] and 'both the objective' in text('ifrs9-classification-measurement'),
            'IFRS9reported version, date or conditions changed')
    require(f['equity_oci_election']['recycle_gains_losses_to_profit_loss'] is False and
            'no recycling' in text('ifrs9-classification-measurement'), 'IFRS9equity election changed')
    expected_dates = {'ifrs7-transfers-disclosures': '2011-07-01', 'ias24-related-parties': '2011-01-01',
                      'ias32-rights-issues': '2010-02-01', 'ifric14-minimum-funding-prepayments': '2011-01-01',
                      'ifric19-debt-for-equity': '2010-07-01'}
    for key, date in expected_dates.items():
        require(meaning(key)['effective_for_periods_starting_on_or_after'] == date, 'Reported period-start condition changed')
    require(meaning('ifrs1-ias27-deemed-cost')['impact'] == 'GROUP_EXPECTS_NO_IMPACT' and
            'does not expect any impact' in text('ifrs1-ias27-deemed-cost'), 'Prospective impact wording changed')
    require(all(meaning(k)['impact'] == 'GROUP_EVALUATING' for k in future - {'ias32-rights-issues'}), 'Impact evaluation promoted')
    require([a['unit'] for a in by_id['ifric18-customer-transfers']['source']][5:7] ==
            ['bes-2010-en:p185:l50', 'bes-2010-en:p185:l51'], 'Displayed IFRIC18body misbound')
    return {'status': 'PASS', 'judgment_topics': 7, 'adopted_pronouncements': 8,
            'pending_pronouncements': 6, 'source_attribution_preserved': True}


def mutations(value):
    from copy import deepcopy
    specs = [
        ('eu-scope', 'basis-of-preparation', 'standard_set', 'ALL_IASB_STANDARDS'),
        ('cost-exceptions', 'basis-of-preparation', 'fair_value_exceptions', []),
        ('estimate-certainty', 'basis-of-preparation', 'future_actual_results_may_differ', False),
        ('board-date', 'basis-of-preparation', 'board_approval_date', '2011-03-04'),
        ('equity-to-debt', 'available-for-sale-impairment', 'equity_thresholds_apply_to_debt', True),
        ('held-maturity-exception', 'held-to-maturity', 'exceptions_exist', False),
        ('tax-certainty', 'income-tax-uncertainty', 'additional_assessments_possible', False),
        ('tax-window', 'income-tax-uncertainty', 'reported_review_period_years', {'ordinary': 4, 'tax_losses_carried_forward': 4}),
        ('ifric12-date', 'ifric12-concessions', 'reported_group_applicable_from', '2008-01-01'),
        ('ifrs9-adoption', 'ifrs9-classification-measurement', 'reported_adoption', 'ADOPTED_IN_2010'),
        ('ifrs9-impact', 'ifrs9-classification-measurement', 'impact', 'INDEPENDENTLY_VERIFIED_NO_IMPACT'),
        ('ifrs9-date', 'ifrs9-classification-measurement', 'reported_mandatory_from', '2018-01-01'),
        ('ias32-period', 'ias32-rights-issues', 'effective_for_periods_starting_on_or_after', '2010-01-01'),
        ('expected-to-observed', 'ifrs1-ias27-deemed-cost', 'impact', 'GROUP_REPORTS_NO_IMPACT'),
    ]
    for label, key, field, replacement in specs:
        changed = deepcopy(value)
        row = next(s for s in [changed['basis'], changed['judgment_context'], *changed['judgments'], *changed['pronouncements']] if s['id'] == key)
        row['meaning'][field] = replacement
        yield label, changed
    changed = deepcopy(value)
    changed['judgments'][0]['meaning']['equity_parameters']['operator'] = 'AND'
    yield 'equity-or-to-and', changed
    changed = deepcopy(value)
    changed['pronouncements'][8]['meaning']['amortised_cost_conditions']['operator'] = 'OR'
    yield 'ifrs9-and-to-or', changed
    changed = deepcopy(value)
    changed['judgments'][1]['source'] = changed['judgments'][1]['source'][:-2]
    yield 'lost-model-consequence', changed
    changed = deepcopy(value)
    changed['pronouncements'][6]['source'] = changed['pronouncements'][6]['source'][:5]
    yield 'lost-ifric18-body', changed
