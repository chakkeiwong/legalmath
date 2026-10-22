"""Inspected original Note2.2–2.7 and Note47 meanings; no automatic IFRS inference."""
from copy import deepcopy
from scripts.prospectus_annual_basis_reading import refs, section

PROFILE = 'bes-annual2010-statements-consolidation-events.v4'
FIELD = 'consolidation_assets_subsequent_events'
NEW_PAGES = (103, 104, 105, 106, 107, 108, 187)


def reading(graph):
    units = {u['id']: u for u in graph['units']}
    make = lambda name, meaning, *parts: section(units, name, meaning, refs(*parts))
    policies = [
        make('subsidiary-control', {
            'note': '2.2', 'scope': 'BES_SUBSIDIARIES_AND_ATTRIBUTABLE_ASSOCIATE_RESULTS',
            'consistent_group_policies': True, 'voting_rights_control_presumption': {'operator': 'GT', 'percent': 50},
            'control_below_50_possible': True, 'alternative_control': 'DIRECT_OR_INDIRECT_POWER_TO_GOVERN_FINANCIAL_AND_OPERATING_POLICIES_FOR_BENEFITS',
            'full_consolidation_period': 'FROM_CONTROL_TRANSFER_UNTIL_CONTROL_CEASES',
            'nci_losses_through_2009': 'EXCESS_OVER_NCI_EQUITY_TO_GROUP_WITH_SUBSEQUENT_PROFITS_UNTIL_RECOVERY',
            'nci_losses_from_2010': 'PROPORTIONATE_ATTRIBUTION_EVEN_IF_NCI_DEFICIT',
            'step_acquisition_from_2010': 'PRIOR_INTEREST_FAIR_VALUE_REMEASUREMENT_THROUGH_INCOME_ON_CONTROL',
            'retained_interest_on_loss_of_control': 'FAIR_VALUE_AT_LOSS_DATE_WITH_GAIN_OR_LOSS_IN_INCOME',
        }, (103, '15-32')),
        make('associate-influence', {
            'note': '2.2', 'significant_influence_is_control': False,
            'voting_rights_influence_presumption': {'operator': 'GT', 'percent': 20},
            'influence_below_20_possible': True, 'alternative_influence': ['POLICY_PARTICIPATION', 'EXECUTIVE_BOARD_REPRESENTATION'],
            'method': 'EQUITY_METHOD_FROM_INFLUENCE_TRANSFER_UNTIL_CEASES',
            'carrying_value': 'INCLUDES_GOODWILL_NET_OF_IMPAIRMENT',
            'step_acquisition_from_2010': 'REPORTED_FAIR_VALUE_REMEASUREMENT_OF_PREVIOUS_STAKE_THROUGH_INCOME',
            'loss_limit_includes_long_term_interest': True,
            'loss_limit_exceptions': ['LEGAL_OR_CONSTRUCTIVE_COVERAGE_OBLIGATION', 'PAYMENTS_ON_BEHALF_OF_ASSOCIATE'],
            'share_sale_gain_loss': 'INCOME_EVEN_WITHOUT_LOSS_OF_SIGNIFICANT_INFLUENCE',
        }, (103, '33-41'), (104, '0-3')),
        make('spe-and-managed-funds', {
            'note': '2.2', 'spe_ownership_percentage_decisive': False, 'source_standard': 'SIC_12',
            'spe_control_factors': ['SPECIFIC_GROUP_BUSINESS_NEEDS_AND_BENEFITS', 'DECISION_POWER_FOR_MAJORITY_BENEFITS',
                                    'RIGHTS_TO_MAJORITY_BENEFITS_AND_EXPOSURE_TO_RISK', 'MAJORITY_RESIDUAL_OR_OWNERSHIP_RISKS'],
            'managed_funds_normally_consolidated': False, 'managed_fund_exception': 'CONTROL_UNDER_SIC_12',
            'fund_control_presumption': {'operator': 'GT', 'participation_units_percent': 50},
        }, (104, '4,6-18')),
        make('goodwill-policy', {
            'note': '2.2', 'reported_transition_date': '2004-01-01',
            'reported_prior_combination_treatment': 'OFFSET_AGAINST_RESERVES_UNDER_IFRS1_OPTION',
            '2004_to_2009': 'PURCHASE_METHOD_WITH_DIRECT_ACQUISITION_COSTS',
            'from_2010': 'FAIR_VALUE_CONSIDERATION_INCLUDING_PRIOR_INTEREST_LESS_IDENTIFIABLE_NET_ASSETS',
            'transaction_costs_from_2010': 'EXPENSE_AS_INCURRED',
            'nci_measurement_election': 'PROPORTIONATE_IDENTIFIABLE_NET_ASSETS_WITHOUT_NCI_GOODWILL',
            'recognized_goodwill_scope': 'PARENT_EQUITY_HOLDERS_ONLY',
            'goodwill_amortised': False, 'associate_goodwill': 'INCLUDED_IN_EQUITY_METHOD_CARRYING_VALUE',
            'negative_goodwill': 'INCOME_IN_COMBINATION_PERIOD', 'recoverability_review': 'ANNUAL_EVEN_WITHOUT_IMPAIRMENT_INDICATION',
            'impairment_loss_destination': 'INCOME_STATEMENT', 'source_margin_number_not_monetary_amount': True,
        }, (104, '19-26,28-37')),
        make('nci-transactions', {
            'note': '2.2', 'through_2009_acquisition_difference': 'GOODWILL',
            'through_2009_dilution_sale_no_loss_control': 'INCOME_GAIN_OR_LOSS',
            'from_2010_acquisitions': 'EQUITY_TRANSACTIONS_WITH_NO_GOODWILL',
            'from_2010_sales_dilutions_without_loss_control': 'EQUITY_MOVEMENT_NO_INCOME_GAIN_OR_LOSS',
            'sale_or_dilution_with_loss_control': 'INCOME_GAIN_OR_LOSS',
        }, (104, '38-50')),
        make('group-currency-translation', {
            'note': '2.2', 'functional_currency_basis': 'PRIMARY_ECONOMIC_ENVIRONMENT',
            'group_presentation_currency': 'EUR', 'assets_liabilities_rate': 'BALANCE_SHEET_DATE',
            'income_expense_rate': 'APPROXIMATE_TRANSACTION_DATE_RATES',
            'translation_differences': 'RESERVES', 'sale_recycling': 'INCOME_AS_PART_OF_SALE_GAIN_OR_LOSS',
            'source_wording_discrepancy': 'INTRODUCTION_SAYS_TRANSLATE_INTO_EURO_SUBPOINTS_SAY_FUNCTIONAL_CURRENCY',
            'source_wording_corrected': False,
        }, (104, '51-53'), (105, '0-6')),
        make('consolidation-eliminations', {
            'note': '2.2', 'group_balances_transactions_and_unrealised_gains_losses_eliminated': True,
            'impairment_loss_exception': True, 'associate_elimination_scope': 'EXTENT_OF_GROUP_INTEREST',
            'associate_impairment_loss_exception': True,
        }, (105, '50,46-48,7-8')),
        make('foreign-currency-transactions', {
            'note': '2.3', 'initial_rate': 'TRANSACTION_DATE', 'monetary_closing_rate': 'BALANCE_SHEET_DATE',
            'monetary_exchange_differences': 'INCOME', 'historical_cost_nonmonetary_rate': 'TRANSACTION_DATE',
            'fair_value_nonmonetary_rate': 'FAIR_VALUE_DETERMINATION_DATE',
            'fair_value_exchange_differences_default': 'INCOME', 'afs_equity_exception': 'EQUITY_FAIR_VALUE_RESERVE',
        }, (105, '9-16')),
        make('derivatives-and-hedge-qualification', {
            'note': '2.4', 'risk_management_derivatives_include_nonhedge_designated': True,
            'other_derivatives': 'TRADING', 'initial_recognition': 'FAIR_VALUE_ON_TRADE_DATE',
            'subsequent_measurement': 'REGULAR_FAIR_VALUE', 'gain_loss_default': 'INCOME',
            'hedge_gain_loss_depends_on_risk_and_model': True,
            'fair_value_sources': ['ACTIVE_MARKET_QUOTE_IF_AVAILABLE', 'VALUATION_TECHNIQUES_INCLUDING_DCF_AND_OPTION_MODELS'],
            'hedge_qualification_operator': 'AND', 'hedge_qualification': ['DESIGNATION_AND_DOCUMENTATION_AT_INCEPTION',
                'EXPECTED_HIGH_EFFECTIVENESS_AT_INCEPTION_AND_ONGOING', 'RELIABLY_MEASURABLE_EFFECTIVENESS_AT_INCEPTION_AND_ONGOING',
                'CASH_FLOWS_HIGHLY_PROBABLE_FOR_CASH_FLOW_HEDGE'],
        }, (105, '17-36')),
        make('fair-value-hedge', {
            'note': '2.4', 'hedged_item_adjustment': 'ONLY_FAIR_VALUE_CHANGE_ATTRIBUTABLE_TO_HEDGED_RISK',
            'hedge_derivative_and_item_changes': 'INCOME', 'criteria_failure': 'DERIVATIVE_TO_TRADING_AND_PROSPECTIVE_DISCONTINUATION',
            'eir_item_cumulative_adjustment': 'AMORTISE_TO_INCOME_OVER_REMAINING_MATURITY',
        }, (105, '37-43')),
        make('cash-flow-hedge-and-embedded-derivatives', {
            'note': '2.4', 'cash_flow_effective_portion': 'EQUITY_THEN_INCOME_WHEN_HEDGED_ITEM_AFFECTS_INCOME',
            'cash_flow_ineffective_portion': 'IMMEDIATE_INCOME',
            'expiry_sale_or_qualification_loss': 'ACCUMULATED_EQUITY_TO_INCOME_WHEN_HEDGED_TRANSACTION_AFFECTS_INCOME',
            'transaction_no_longer_expected': 'IMMEDIATE_INCOME_AND_DERIVATIVE_TO_TRADING',
            'reported_cash_flow_hedges_in_covered_periods': False,
            'embedded_separation_operator': 'AND', 'embedded_separation_conditions': ['RISKS_NOT_CLOSELY_RELATED_TO_HOST', 'HOST_NOT_AT_FVPL'],
            'separated_embedded_measurement': 'FAIR_VALUE_CHANGES_IN_INCOME',
        }, (106, '0-7,9-13')),
        make('customer-loan-recognition', {
            'note': '2.5', 'scope': 'ORIGINATED_LOANS_NOT_INTENDED_FOR_SHORT_TERM_SALE',
            'recognition': 'WHEN_CASH_ADVANCED', 'derecognition_operator': 'OR',
            'derecognition_alternatives': ['CONTRACTUAL_CASH_FLOW_RIGHTS_EXPIRE', 'SUBSTANTIALLY_ALL_RISKS_AND_REWARDS_TRANSFERRED',
                'SOME_BUT_NOT_SUBSTANTIALLY_ALL_RISKS_RETAINED_AND_CONTROL_TRANSFERRED'],
            'initial_measurement': 'FAIR_VALUE_PLUS_TRANSACTION_COSTS', 'subsequent_default': 'AMORTISED_COST_USING_EIR_LESS_IMPAIRMENT',
            'documented_risk_management_exception': 'CERTAIN_LOANS_AT_FVPL_TO_ELIMINATE_DERIVATIVE_ACCOUNTING_MISMATCH_WITHOUT_HEDGE_ACCOUNTING',
            'cross_references': ['Note 2.4', 'Note 2.6'],
        }, (106, '14-21,23-27')),
        make('customer-loan-impairment', {
            'note': '2.5', 'assessment_cadence': 'EACH_BALANCE_SHEET_DATE',
            'recognition_and_subsequent_decrease_reversal': 'INCOME_STATEMENT', 'loss_condition_operator': 'AND',
            'loss_conditions': ['OBJECTIVE_EVIDENCE_OF_EVENT_AFTER_INITIAL_RECOGNITION', 'RELIABLY_ESTIMABLE_IMPACT_ON_FUTURE_CASH_FLOWS'],
            'later_ifrs9_ecl_inferred': False, 'individual_assessment_first': True,
            'individual_factors': ['AGGREGATE_EXPOSURE_AND_NONPERFORMING_LOANS', 'BUSINESS_VIABILITY_AND_DEBT_SERVICE_CASH_FLOW',
                'SENIOR_CREDITOR_COMMITMENTS', 'COLLATERAL_NATURE_AND_REALISABLE_VALUE', 'FINANCIAL_SECTOR_EXPOSURE', 'RECOVERY_AMOUNT_AND_TIMING'],
            'individually_unimpaired_collective_test': True, 'individually_impaired_in_collective_test': False,
            'loss_measure': 'CARRYING_VALUE_MINUS_PRESENT_VALUE_EXPECTED_FUTURE_RECOVERIES',
            'fixed_rate_discount': 'ORIGINAL_EFFECTIVE_INTEREST_RATE', 'variable_rate_discount': 'CURRENT_CONTRACT_EFFECTIVE_INTEREST_RATE',
            'carrying_value_reduction': 'ALLOWANCE_ACCOUNT', 'unwinding_discount': 'INTEREST_INCOME',
            'collateral_cashflows': 'FORECLOSURE_RECOVERIES_LESS_OBTAINING_AND_SELLING_COSTS',
            'collective_grouping': 'SIMILAR_CREDIT_RISK', 'collective_cashflows': 'CONTRACTUAL_CASHFLOWS_AND_HISTORICAL_LOSS_EXPERIENCE',
            'collective_assumptions_reviewed_regularly': True,
            'writeoff_conditions': ['CONSIDERED_UNCOLLECTIBLE', '100_PERCENT_IMPAIRMENT_RECOGNISED'], 'writeoff_against': 'RELATED_ALLOWANCE',
        }, (106, '28-52'), (107, '0-5')),
        make('other-asset-classification-recognition', {
            'note': '2.6', 'classification_time': 'INITIAL_RECOGNITION',
            'fvpl_categories': ['HELD_FOR_TRADING', 'DESIGNATED_AT_INCEPTION'],
            'trading_criteria': 'SHORT_TERM_SALE_OR_MANAGED_PORTFOLIO_WITH_RECENT_SHORT_TERM_PROFIT_PATTERN',
            'fvpl_designation_alternatives': ['MANAGED_AND_EVALUATED_ON_FAIR_VALUE', 'ECONOMIC_HEDGE_ELIMINATES_MISMATCH', 'EMBEDDED_DERIVATIVE'],
            'acquired_structured_products': 'FVPL', 'cross_reference': 'Note 23',
            'htm_conditions': ['NON_DERIVATIVE', 'FIXED_OR_DETERMINABLE_PAYMENTS', 'FIXED_MATURITY', 'INTENTION_AND_ABILITY_TO_HOLD', 'NOT_INITIAL_FVPL_OR_AFS'],
            'afs': 'NON_DERIVATIVE_INDEFINITE_HOLD_OR_INITIAL_DESIGNATION_OR_OTHER_CATEGORY_RESIDUAL',
            'purchase_sale_recognition': 'TRADE_DATE', 'initial_measurement': 'FAIR_VALUE_PLUS_TRANSACTION_COSTS_EXCEPT_FVPL_COSTS_EXPENSED',
            'derecognition_operator': 'OR', 'derecognition_alternatives': ['RIGHTS_EXPIRE', 'SUBSTANTIALLY_ALL_RISKS_REWARDS_TRANSFERRED',
                'SOME_NOT_SUBSTANTIALLY_ALL_RISKS_RETAINED_AND_CONTROL_TRANSFERRED'],
        }, (107, '6,23,7-21,48,24-33')),
        make('other-asset-measurement-reclassification', {
            'note': '2.6', 'fvpl': 'FAIR_VALUE_CHANGES_IN_INCOME',
            'afs_fair_value_changes': 'EQUITY_UNTIL_DERECOGNITION_OR_IMPAIRMENT_THEN_INCOME',
            'afs_equity_fx': 'EQUITY', 'afs_debt_fx': 'INCOME', 'interest_eir_and_dividends': 'INCOME',
            'htm': 'AMORTISED_COST_USING_EIR_NET_OF_IMPAIRMENT',
            'quoted_active_market_value': 'CURRENT_BID_PRICE', 'unlisted_value': 'VALUATION_TECHNIQUES_WITH_MARKET_INFORMATION',
            'only_reported_reclassification_route': 'AFS_TO_HTM',
            'reclassification_conditions': ['NON_DERIVATIVE', 'FIXED_OR_DETERMINABLE_PAYMENTS', 'FIXED_MATURITY', 'INTENTION_AND_ABILITY_TO_HOLD'],
            'reclassification_measurement': 'FAIR_VALUE_AT_RECLASSIFICATION',
            'reclassification_difference_and_reserve': 'INCOME_OVER_MATURITY_USING_EIR',
            'reported_reclassifications_2009_2010': False,
        }, (107, '34-45'), (108, '0-6')),
        make('other-asset-impairment', {
            'note': '2.6', 'objective_evidence_after_initial_recognition': True,
            'equity_trigger': 'SIGNIFICANT_OR_PROLONGED_FAIR_VALUE_DECLINE_BELOW_COST',
            'debt_trigger': 'EVENT_WITH_RELIABLY_ESTIMABLE_FUTURE_CASH_FLOW_IMPACT',
            'htm_loss': 'CARRYING_VALUE_MINUS_PRESENT_VALUE_FUTURE_CASHFLOWS_USING_RECOVERY_PERIOD',
            'htm_fixed_discount': 'ORIGINAL_EIR', 'htm_variable_discount': 'CURRENT_CONTRACT_EIR', 'htm_reduction': 'ALLOWANCE',
            'htm_reversal_condition': 'DECREASE_OBJECTIVELY_RELATED_TO_EVENT_AFTER_IMPAIRMENT', 'htm_reversal_destination': 'INCOME',
            'afs_loss_recycled_from_equity': 'ACQUISITION_COST_MINUS_CURRENT_FAIR_VALUE_LESS_PRIOR_INCOME_IMPAIRMENT',
            'afs_non_equity_reversal': 'INCOME_UP_TO_ACQUISITION_COST_IF_OBJECTIVE_LATER_EVENT',
            'afs_equity_reversal': 'EQUITY',
        }, (108, '8-24')),
        make('repos-and-securities-lending', {
            'note': '2.7', 'repo_scope': 'FIXED_PRICE_OR_SALE_PRICE_PLUS_LENDER_RETURN', 'repo_securities_derecognised': False,
            'repo_liability': 'AMOUNTS_DUE_TO_BANKS_OR_CUSTOMERS', 'repo_difference': 'INTEREST_USING_EIR_OVER_AGREEMENT',
            'reverse_repo_securities_recognised': False, 'reverse_repo_price_paid': 'LOANS_TO_BANKS_OR_CUSTOMERS',
            'reverse_repo_difference': 'INTEREST_USING_EIR_OVER_AGREEMENT', 'lent_securities_derecognised': False,
            'borrowed_securities_recognised': False, 'lent_securities_measurement_cross_reference': 'Note 2.6',
        }, (108, '25,28-35')),
    ]
    events = [
        make('venezuela-branch', {
            'note': '47', 'approval_time_as_reported': 'END_OF_OCTOBER_YEAR_NOT_EXPLICIT_IN_BULLET',
            'approval_independently_verified': False, 'prior_representative_office_years': 17,
            'strategy': 'EXPAND_TO_MARKETS_WITH_CULTURAL_AND_ECONOMIC_AFFINITIES_WITH_PORTUGAL',
            'reported_portuguese_community': 'MORE_THAN_HALF_A_MILLION_PLUS_SIGNIFICANT_DESCENDANT_POPULATION',
            'intended_market': 'PORTUGUESE_COMMUNITY_BIG_COMPANIES_AND_INSTITUTIONS',
            'administrative_completion': 'MID_JANUARY_2011', 'opening_period': 'Q3_2011',
            'opening_status': 'PREDICTED_NOT_CONFIRMED', 'universal_banking_activity': 'INTENDED',
        }, (187, '0,11-17')),
        make('moza-acquisition', {
            'note': '47', 'agreement_announced': '2010-10-26', 'acquirer': 'BES_THROUGH_BES_AFRICA_SGPS_SA',
            'target': 'MOZA_BANCO_SA', 'stake_percent': '25.1', 'purchase_eur_million': '7.1',
            'simultaneous_capital_subscription_percent': '25.1', 'total_investment_eur_million': '8.1',
            'completed': '2011-01-20', 'associate_from': '2011-01-20', 'consolidated_subsidiary_inferred': False,
        }, (187, '0,6-9')),
        make('libya-aman-exposure', {
            'note': '47', 'reported_instability_period': 'FEBRUARY_2011', 'entity': 'AMAN_BANK', 'location': 'LIBYA',
            'stake_percent': '40', 'investment_eur_million': '40.3', 'cross_reference': 'Note 45',
            'reported_action': 'CLOSELY_MONITORING_SITUATION', 'quantified_impairment_loss_inferred': False,
        }, (187, '0,1-3')),
    ]
    return {'version': 'bes-annual2010-consolidation-events.v1', 'policies': policies, 'events': events,
            'all_notes_interpreted': False, 'independent_legal_or_financial_acceptance': False,
            'source_authenticity': 'NOT_ESTABLISHED', 'scope': 'ISSUER_STATEMENTS_NOTE_2_2_TO_2_7_AND_NOTE_47_ONLY'}


def combine(old, graph):
    result = deepcopy(old)
    assert FIELD not in result
    result[FIELD] = reading(graph)
    result['source_context']['source_pages'] = sorted(set(result['source_context']['source_pages']) | set(NEW_PAGES))
    result['source_context']['scope'] += '; Note 2.2–2.7 and Note 47; remaining policies and numerical notes remain incomplete'
    assert result['source_context']['all_notes_read'] is False
    return result
