"""Inspected, attributed annual2010 note meanings with complete source witnesses.

This prepares a supplied reading, not an automatic IFRS or legal interpreter.
The original report's dates and statements are preserved, including prospective
impact wording under an already-adopted heading and its printed spelling.
"""
from copy import deepcopy

PROFILE = 'bes-annual2010-statements-basis-estimates.v3'
NEW_PAGES = (103, 114, 115, 184, 185, 186)
SOURCE = 'f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25'


def refs(*parts):
    """Explicit reading order; do not sort displaced native paragraphs."""
    result = []
    for page, lines in parts:
        for value in lines.split(','):
            ends = [int(v) for v in value.split('-')]
            result.extend(f'bes-2010-en:p{page}:l{i}' for i in range(ends[0], ends[-1] + 1))
    return result


def section(units, name, meaning, selected):
    anchors = []
    for key in selected:
        u = units[key]
        assert u['document'] == 'bes-2010-en' and u['source_sha256'] == SOURCE and u['visible']
        anchors.append({'unit': key, 'page': u['page'], 'source_sha256': SOURCE,
                        'start': 0, 'end': len(u['raw']), 'quote': u['raw']})
    assert len(selected) == len(set(selected))
    return {'id': name, 'meaning': meaning, 'source': anchors,
            'attribution': 'ISSUER_ANNUAL_REPORT_2010', 'independently_verified': False}


def reading(graph):
    units = {u['id']: u for u in graph['units']}
    make = lambda name, meaning, selected: section(units, name, meaning, selected)
    basis = make('basis-of-preparation', {
        'scope': 'CONSOLIDATED_GROUP', 'reporting_date': '2010-12-31',
        'standard_set': 'IFRS_EFFECTIVE_AND_ADOPTED_BY_EU_AT_REPORTING_DATE',
        'reported_framework_references': ['Regulation (EC) 1606/2002', 'Decree-Law 35/2005', 'Bank of Portugal Regulation 1/2005'],
        'currency': 'EUR', 'display_unit': 'THOUSANDS', 'rounding': 'NEAREST_THOUSAND',
        'measurement_basis': 'HISTORICAL_COST_WITH_SPECIFIED_FAIR_VALUE_EXCEPTIONS',
        'fair_value_exceptions': ['DERIVATIVES', 'FINANCIAL_ASSETS_AT_FVPL', 'FINANCIAL_LIABILITIES_AT_FVPL',
                                  'AVAILABLE_FOR_SALE_ASSETS', 'RECOGNISED_FAIR_VALUE_HEDGED_ITEMS_FOR_HEDGED_RISK'],
        'management_estimates_required': True, 'future_actual_results_may_differ': True,
        'policies_consistent_with_2009_except_reported_2010_adoptions': True,
        'reported_2010_adoption_impact': 'ISSUER_REPORTS_NO_MATERIAL_IMPACT',
        'board_approval_date': '2011-02-25', 'board_approval_is_auditor_date': False,
        'cross_references': ['Note 3', 'Note 46'], 'present_day_law_verified': False,
    }, refs((103, '1-14,44-50,52-53')))
    general = make('judgment-context', {
        'alternative_treatments_can_change_reported_results': True,
        'fair_presentation_statement': 'MANAGEMENT_BELIEF_NOT_INDEPENDENT_VALIDATION',
        'cross_reference': 'Note 2',
    }, refs((114, '29-36')))
    judgments = [
        make('available-for-sale-impairment', {
            'general_triggers': ['SIGNIFICANT_OR_PROLONGED_FAIR_VALUE_DECLINE_BELOW_COST', 'EVENT_AFFECTING_ESTIMATED_FUTURE_CASH_FLOWS'],
            'requires_judgment_and_relevant_information': True,
            'equity_parameters': {'operator': 'OR', 'market_decline_percent': {'operator': 'GT', 'value': 30, 'base': 'ACQUISITION_COST'},
                'below_cost_months': {'operator': 'GT', 'value': 12}, 'role': 'REPORTED_ASSESSMENT_PARAMETERS'},
            'debt_parameters': 'OBJECTIVE_EVIDENCE_OF_EVENTS_AFFECTING_ESTIMATED_FUTURE_CASH_FLOWS',
            'equity_thresholds_apply_to_debt': False,
            'valuation_may_use_models_and_assumptions': True,
            'alternative_assumptions': 'COULD_INCREASE_IMPAIRMENT_AND_AFFECT_INCOME_STATEMENT',
        }, refs((114, '37-45'), (115, '0-1'))),
        make('derivative-fair-value', {
            'quoted_prices_if_available': True, 'otherwise': ['DEALER_QUOTES_FOR_SAME_OR_SIMILAR_INSTRUMENTS', 'PRICING_MODELS'],
            'model_factors': ['ESTIMATED_FUTURE_CASH_FLOWS', 'UNDERLYING_MARKET_CONDITIONS', 'TIME_VALUE', 'YIELD_CURVE', 'VOLATILITY'],
            'model_assumptions_and_judgments': True, 'alternatives_may_change_reported_financial_results': True,
        }, refs((115, '2-5,43-44'))),
        make('loan-impairment', {
            'regular_portfolio_review': True, 'cross_reference': 'Note 2.5',
            'factors': ['DEFAULT_FREQUENCY', 'RISK_RATINGS', 'RECOVERY_RATES', 'FUTURE_CASH_FLOW_AMOUNT', 'FUTURE_CASH_FLOW_TIMING'],
            'factors_are_exhaustive': False, 'requires_estimates_and_judgments': True,
            'alternatives_may_change_impairment_and_income': True,
        }, refs((115, '41,6-11'))),
        make('spe-consolidation', {
            'purposes': ['SECURITISATION', 'LIQUIDITY'], 'uncontrolled_spes_not_consolidated': True,
            'judgment_considers': ['RISKS_AND_REWARDS', 'OPERATIONAL_DECISION_ABILITY', 'EXPECTED_RESIDUAL_GAINS_AND_LOSSES', 'WHO_RETAINS_MAJORITY_OF_RESIDUAL_GAINS_AND_LOSSES'],
            'cross_reference': 'Note 2.2', 'alternatives_may_change_consolidation_scope_and_net_income': True,
        }, refs((115, '12-18'))),
        make('held-to-maturity', {
            'source_standard': 'IAS 39', 'instrument_conditions': ['NON_DERIVATIVE', 'FIXED_OR_DETERMINABLE_PAYMENTS', 'FIXED_MATURITY'],
            'judgment_conditions': ['INTENTION_TO_HOLD_TO_MATURITY', 'ABILITY_TO_HOLD_TO_MATURITY'],
            'noncompliance_consequence': 'ENTIRE_CLASS_RECLASSIFIED_AVAILABLE_FOR_SALE',
            'exceptions_exist': True, 'exception_example': 'INSIGNIFICANT_AMOUNT_SOLD_CLOSE_TO_MATURITY',
            'remeasurement': 'FAIR_VALUE_INSTEAD_OF_AMORTISED_COST', 'impairment_tests_required': True,
            'changed_assumptions_may_affect_income': True,
        }, refs((115, '19-26'))),
        make('income-tax-uncertainty', {
            'multiple_jurisdictions': True, 'ultimate_tax_determination_uncertain': True,
            'different_interpretations_affect_current_and_deferred_tax': True,
            'reported_review_period_years': {'ordinary': 4, 'tax_losses_carried_forward': 6},
            'additional_assessments_possible': True,
            'no_material_differences_expected': 'BOARD_CONFIDENCE_NOT_ESTABLISHED_OUTCOME',
            'current_tax_law_independently_verified': False,
        }, refs((115, '27-34'))),
        make('pension-estimation', {
            'assumptions_include': ['ACTUARIAL_PROJECTIONS', 'ESTIMATED_INVESTMENT_RETURNS'],
            'assumptions_are_exhaustive': False, 'liability_and_cost_can_change_materially': True,
        }, refs((115, '35-38'))),
    ]
    adopted_heading = refs((184, '1-3'))
    future_heading = refs((185, '13-15'))

    def pronouncement(name, state, meaning, selected):
        return make(name, {'reported_adoption': state, **meaning},
                    (adopted_heading if state == 'ADOPTED_IN_2010' else future_heading) + selected)

    adopted = 'ADOPTED_IN_2010'
    future = 'NOT_YET_ADOPTED_BY_GROUP'
    pronouncements = [
        pronouncement('ifrs1-ias27-deemed-cost', adopted, {
            'effective_for_periods_starting_on_or_after': '2009-07-01',
            'first_time_adopter_deemed_cost_options': ['FAIR_VALUE', 'PREVIOUS_GAAP_CARRYING_AMOUNT'],
            'scope': 'INVESTMENTS_IN_SUBSIDIARIES_JOINT_ENTITIES_ASSOCIATES_IN_SEPARATE_STATEMENTS',
            'impact': 'GROUP_EXPECTS_NO_IMPACT', 'prospective_impact_wording_under_adopted_heading_retained': True,
        }, refs((184, '4,6-10'))),
        pronouncement('ifrs3-ias27-business-combinations', adopted, {
            'reported_mandatory_since': '2010-01-01',
            'nci_measurement_options': ['FAIR_VALUE_FULL_GOODWILL', 'PROPORTIONATE_NET_IDENTIFIABLE_ASSETS'],
            'step_acquisition_prior_interest': 'FAIR_VALUE_REMEASUREMENT_THROUGH_INCOME',
            'acquisition_costs': 'GENERALLY_EXPENSED_NOT_GOODWILL',
            'contingent_consideration': 'FAIR_VALUE_AT_ACQUISITION_SUBSEQUENT_CHANGES_THROUGH_INCOME',
            'ownership_changes_without_loss_of_control': 'EQUITY_TRANSACTIONS',
            'nci_share_of_losses_can_create_deficit': True,
            'retained_interest_on_loss_of_control': 'FAIR_VALUE_AT_LOSS_OF_CONTROL_DATE',
            'impact': 'GROUP_REPORTS_NO_SIGNIFICANT_IMPACT',
        }, refs((184, '11-24,26'))),
        pronouncement('ifrs5-disclosures', adopted, {
            'subject': 'DISCLOSURES_FOR_HELD_FOR_SALE_ASSETS_OR_DISPOSAL_GROUPS_AND_DISCONTINUED_OPERATIONS',
            'impact': 'GROUP_REPORTS_NO_SIGNIFICANT_IMPACT',
        }, refs((184, '27-30'))),
        pronouncement('ias39-eligible-hedged-items', adopted, {
            'effective_for_periods_starting_on_or_after': '2009-07-01',
            'subject': 'ELIGIBILITY_OF_HEDGED_RISKS_OR_CASH_FLOW_PORTIONS_IN_PARTICULAR_SITUATIONS',
            'impact': 'GROUP_REPORTS_NO_IMPACT',
        }, refs((184, '31-36'))),
        pronouncement('ifric12-concessions', adopted, {
            'reported_effective_date': '2008-01-01', 'early_application_permitted': True,
            'reported_eu_endorsement_year': 2009, 'reported_group_applicable_from': '2010-01-01',
            'scope_conditions': {'operator': 'AND', 'conditions': ['PUBLIC_SECTOR_CONTROLS_OR_REGULATES_SERVICES', 'PUBLIC_SECTOR_CONTROLS_SIGNIFICANT_RESIDUAL_INFRASTRUCTURE_INTEREST']},
            'impact': 'GROUP_REPORTS_NO_IMPACT',
        }, refs((184, '37-43'))),
        pronouncement('ifric17-noncash-distributions', adopted, {
            'effective_for_periods_starting_on_or_after': '2009-07-01',
            'distribution_measurement': 'FAIR_VALUE', 'fair_value_minus_carrying_amount': 'INCOME_STATEMENT',
            'impact': 'GROUP_REPORTS_NO_IMPACT',
        }, refs((184, '44-45'), (185, '0-3'))),
        pronouncement('ifric18-customer-transfers', adopted, {
            'effective_for_periods_starting_on_or_after': '2009-07-01',
            'scope': 'CUSTOMER_TRANSFERS_PPE_TO_CONNECT_TO_NETWORK_OR_RECEIVE_ONGOING_GOODS_OR_SERVICES',
            'clarifications': ['ASSET_DEFINITION', 'INITIAL_RECOGNITION_AND_COST', 'SEPARATE_SERVICES', 'REVENUE_RECOGNITION', 'CUSTOMER_CASH_TRANSFERS'],
            'impact': 'GROUP_REPORTS_NO_IMPACT', 'printed_IFER_spelling_preserved_in_source': True,
        }, refs((185, '4-5,50-51,43-48,6'))),
        pronouncement('annual-improvements-ifrs5-disposal', adopted, {
            'effective_for_periods_starting_on_or_after': '2009-07-01',
            'condition': 'PARTIAL_DISPOSAL_PLAN_RESULTS_IN_LOSS_OF_CONTROL',
            'consequence': 'ALL_SUBSIDIARY_ASSETS_AND_LIABILITIES_CLASSIFIED_HELD_FOR_SALE',
            'impact': 'GROUP_REPORTS_NO_IMPACT',
        }, refs((185, '7-12'))),
        pronouncement('ifrs9-classification-measurement', future, {
            'reported_mandatory_from': '2013-01-01', 'early_application_permitted': True,
            'eu_status_at_report': 'NOT_YET_ADOPTED', 'source_version': 'NOVEMBER_2009_PART1_CLASSIFICATION_AND_MEASUREMENT',
            'classification_at_initial_recognition': True,
            'amortised_cost_conditions': {'operator': 'AND', 'conditions': ['DEBT_INSTRUMENT', 'BUSINESS_MODEL_HOLD_TO_COLLECT', 'CONTRACTUAL_CASH_FLOWS_ONLY_PRINCIPAL_AND_INTEREST']},
            'other_debt_measurement': 'FAIR_VALUE_THROUGH_PROFIT_OR_LOSS',
            'third_party_equity_default': 'FAIR_VALUE_THROUGH_PROFIT_OR_LOSS',
            'equity_oci_election': {'irrevocable': True, 'instrument_by_instrument': True, 'recycle_gains_losses_to_profit_loss': False, 'dividends': 'PROFIT_OR_LOSS'},
            'impact': 'GROUP_EVALUATING', 'later_ifrs9_versions_or_ecl_inferred': False,
        }, refs((185, '16-30'))),
        pronouncement('ifrs7-transfers-disclosures', future, {
            'effective_for_periods_starting_on_or_after': '2011-07-01', 'early_application_permitted': True,
            'eu_status_at_report': 'NOT_YET_ADOPTED', 'subject': 'RISKS_AND_IMPACTS_OF_FINANCIAL_ASSET_TRANSFERS_INCLUDING_SECURITISATIONS',
            'impact': 'GROUP_EVALUATING',
        }, refs((185, '31-37'))),
        pronouncement('ias24-related-parties', future, {
            'effective_for_periods_starting_on_or_after': '2011-01-01', 'early_application_permitted': True,
            'eu_status_at_report': 'NOT_YET_ADOPTED', 'subject': 'RELATED_PARTY_DEFINITION_AND_STATE_RELATED_DISCLOSURES',
            'impact': 'GROUP_EVALUATING', 'eu_status_is_report_attribution_not_verified_law': True,
        }, refs((185, '38-40'), (186, '0-2'))),
        pronouncement('ias32-rights-issues', future, {
            'effective_for_periods_starting_on_or_after': '2010-02-01', 'early_application_permitted': True,
            'equity_classification_conditions': ['FIXED_NUMBER_OF_OWN_EQUITY_INSTRUMENTS', 'FIXED_AMOUNT_OF_ANY_CURRENCY', 'PRO_RATA_OFFER_TO_ALL_EXISTING_OWNERS_OF_SAME_NON_DERIVATIVE_EQUITY_CLASS'],
            'impact': 'GROUP_EXPECTS_NO_IMPACT', 'effective_date_is_not_group_adoption_date': True,
        }, refs((186, '3,5-11'))),
        pronouncement('ifric14-minimum-funding-prepayments', future, {
            'effective_for_periods_starting_on_or_after': '2011-01-01', 'early_application_permitted': True,
            'scope': 'MINIMUM_FUNDING_REQUIREMENT_AND_EARLY_CONTRIBUTIONS_TO_COVER_IT',
            'benefit_of_prepayment_may_be_asset': True,
            'transition': 'FROM_BEGINNING_OF_EARLIEST_COMPARATIVE_PERIOD_IN_FIRST_APPLICABLE_STATEMENTS',
            'impact': 'GROUP_EVALUATING',
        }, refs((186, '12-18'))),
        pronouncement('ifric19-debt-for-equity', future, {
            'effective_for_periods_starting_on_or_after': '2010-07-01', 'early_application_permitted': True,
            'scope': 'RENEGOTIATED_FINANCIAL_LIABILITY_FULLY_OR_PARTLY_EXTINGUISHED_BY_EQUITY_ISSUE',
            'clarifications': ['CONSIDERATION_PAID_UNDER_IAS39_PARAGRAPH41', 'INITIAL_EQUITY_MEASUREMENT', 'DIFFERENCE_FROM_LIABILITY_CARRYING_AMOUNT'],
            'impact': 'GROUP_EVALUATING', 'effective_date_is_not_group_adoption_date': True,
        }, refs((186, '19-21,23-30'))),
    ]
    return {'version': 'bes-annual2010-basis-estimates.v1', 'basis': basis, 'judgment_context': general,
            'judgments': judgments, 'pronouncements': pronouncements,
            'all_notes_interpreted': False, 'source_authenticity': 'NOT_ESTABLISHED',
            'legal_or_independent_financial_acceptance': False,
            'scope_limit': 'Supplied interpretation of original2010issuer statements; legal correctness and present-day applicability not established'}


def combine(old_reading, graph):
    value = deepcopy(old_reading)
    assert 'basis_estimates_pronouncements' not in value
    value['basis_estimates_pronouncements'] = reading(graph)
    value['source_context']['source_pages'] = sorted(set(value['source_context']['source_pages']) | set(NEW_PAGES))
    value['source_context']['scope'] += '; Note2.1 basis, all seven Note3judgment topics and fourteen Note46pronouncements; other material on these pages remains context'
    assert value['source_context']['all_notes_read'] is False
    return value
