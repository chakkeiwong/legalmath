"""Supplied historical issuer meanings for original Notes 2.8–2.23."""
from copy import deepcopy
from scripts.prospectus_annual_basis_reading import refs, section

PROFILE = 'bes-annual2010-statements-remaining-policies.v5'
FIELD = 'remaining_accounting_policies'
NEW_PAGES = tuple(range(108, 115))


def reading(graph):
    units = {u['id']: u for u in graph['units']}
    make = lambda name, meaning, *parts: section(units, name, meaning, refs(*parts))
    policies = [
        make('financial-liabilities', {
            'note': '2.8', 'classification': 'CONTRACTUAL_OBLIGATION_TO_TRANSFER_CASH_OR_FINANCIAL_ASSET',
            'legal_form_decisive': False,
            'examples': ['BANK_DEPOSITS', 'CUSTOMER_DEPOSITS', 'LOANS', 'DEBT_SECURITIES', 'SUBORDINATED_DEBT', 'SHORT_SALES'],
            'preference_liability_condition': 'REIMBURSEMENT_OBLIGATION_OR_DIVIDEND_PAYMENT_OBLIGATION',
            'initial_measurement': 'FAIR_VALUE_LESS_TRANSACTION_COSTS', 'subsequent_default': 'AMORTISED_COST_USING_EIR',
            'fair_value_exceptions': ['SHORT_SALES', 'DESIGNATED_FVPL'],
            'fvpl_designation_time': 'INCEPTION', 'designation_operator': 'OR',
            'designation_conditions': ['ECONOMIC_HEDGE_ELIMINATING_ACCOUNTING_MISMATCH', 'EMBEDDED_DERIVATIVES'],
            'issued_structured_products': 'FVPL', 'quoted_value': 'CURRENT_PRICE',
            'unquoted_value': 'MARKET_BASED_VALUATION_INCLUDING_ISSUER_OWN_CREDIT_RISK',
            'repurchase': 'DERECOGNISE_AND_RECOGNISE_CARRYING_AMOUNT_LESS_ACQUISITION_COST_IN_INCOME',
        }, (108, '36-51')),
        make('equity-instruments', {
            'note': '2.9', 'definition_status': 'SOURCE_SENTENCE_COMBINES_LIABILITY_AND_RESIDUAL_INTEREST_LANGUAGE',
            'source_definition_corrected': False,
            'issue_costs': 'DEDUCT_FROM_EQUITY_PROCEEDS', 'own_equity_purchases_sales': 'EQUITY_NET_OF_TRANSACTION_COSTS',
            'distributions': 'DEBIT_EQUITY_WHEN_DECLARED', 'preference_equity_operator': 'AND',
            'preference_equity_conditions': ['NO_CONTRACTUAL_REDEMPTION_OBLIGATION', 'NONCUMULATIVE_DIVIDENDS_ONLY_IF_AND_WHEN_DECLARED'],
        }, (109, '0-5,22-23')),
        make('offsetting', {
            'note': '2.10', 'condition_operator': 'AND', 'conditions': ['LEGALLY_ENFORCEABLE_OFFSET_RIGHT', 'SETTLEMENT_INTENT'],
            'settlement_intent_alternatives': ['NET_SETTLEMENT', 'REALISE_ASSET_AND_SETTLE_LIABILITY_SIMULTANEOUSLY'],
        }, (109, '6-8')),
        make('held-for-sale', {
            'note': '2.11', 'printed_heading': 'NON_CURRENT_ASSETS_HELD_FOR_TRADE',
            'classification_operator': 'AND', 'classification_conditions': ['RECOVERY_PRINCIPALLY_BY_SALE', 'AVAILABLE_FOR_IMMEDIATE_SALE', 'SALE_HIGHLY_PROBABLE'],
            'includes_disposal_groups_and_exclusive_resale_acquisitions': True,
            'before_classification': 'UPDATE_UNDER_APPLICABLE_IFRS',
            'subsequent_measurement': 'LOWER_OF_CARRYING_AMOUNT_AND_FAIR_VALUE_LESS_SELLING_COSTS',
            'mortgage_exchange': 'PROPERTY_ACQUIRED_IN_EXCHANGE_FOR_LOANS',
            'reported_property_law': 'RGICSF_ART112_DL298_92_31DEC_AND_ART114',
            'reported_nonessential_acquisition_prohibited_with_loan_exchange_exception': True,
            'reported_sale_deadline_years': 2,
            'reported_extension': 'WRITTEN_BANK_OF_PORTUGAL_AUTHORISATION_AND_ITS_CONDITIONS',
            'law_independently_verified': False, 'objective': 'IMMEDIATE_DISPOSAL_OF_LOAN_EXCHANGE_PROPERTY',
            'loan_exchange_initial_measurement': 'LOWER_OF_FAIR_VALUE_LESS_SELLING_COSTS_AND_LOAN_CARRYING_AMOUNT',
            'loan_exchange_subsequent': 'LOWER_OF_CARRYING_AMOUNT_AND_FAIR_VALUE_LESS_SELLING_COSTS',
            'loan_exchange_property_depreciated': False, 'subsequent_write_down': 'INCOME_STATEMENT',
        }, (109, '9-20,43-46')),
        make('property-valuation', {
            'note': '2.11', 'method_selected_for_specific_asset': True,
            'methods': {'market': 'LOCAL_COMPARABLE_PROPERTY_TRANSACTIONS', 'income': 'PRESENT_VALUE_OF_NET_INCOME_USING_DCF',
                        'cost': 'LAND_AND_URBANITY_PLUS_CONSTRUCTION_PLUS_INDIRECT_COSTS'},
            'valuers': 'REPORTED_INDEPENDENT_SPECIALISED_ENTITIES',
            'internal_review': 'PROCESS_ADEQUACY_AND_SALES_VERSUS_REVALUED_AMOUNTS', 'independence_verified': False,
        }, (109, '24-35')),
        make('property-equipment', {
            'note': '2.12', 'measurement': 'COST_LESS_ACCUMULATED_DEPRECIATION_AND_IMPAIRMENT',
            'transition_date': '2004-01-01', 'deemed_cost': 'PREVIOUS_POLICY_REVALUED_AMOUNT_BROADLY_SIMILAR_TO_IFRS_DEPRECIATED_COST_ADJUSTED_FOR_PRICE_INDEX',
            'cost_includes_direct_acquisition_expenditure': True,
            'subsequent_capitalisation': 'ONLY_PROBABLE_FUTURE_ECONOMIC_BENEFITS', 'other_repairs_maintenance': 'EXPENSE_AS_INCURRED',
            'land_depreciated': False, 'depreciation_method': 'STRAIGHT_LINE',
            'useful_lives_years': {'buildings': [35, 50], 'leasehold_improvements': [10, 10], 'computers': [4, 5],
                'furniture': [4, 10], 'fixtures': [5, 12], 'security': [4, 10], 'office': [4, 10], 'vehicles': [4, 4], 'other': [5, 5]},
            'impairment_assessment': 'WHEN_INDICATION_EXISTS', 'loss_condition': 'NET_BOOK_VALUE_EXCEEDS_RECOVERABLE_AMOUNT',
            'loss_destination': 'INCOME', 'recoverable_amount': 'GREATER_OF_NET_SELLING_PRICE_AND_VALUE_IN_USE',
            'value_in_use': 'PRESENT_VALUE_OF_CONTINUING_USE_AND_ULTIMATE_DISPOSAL_CASHFLOWS',
        }, (109, '36-40'), (110, '0-3,10,5,11,7,12-30')),
        make('intangible-software', {
            'note': '2.13', 'capitalised': 'SOFTWARE_ACQUISITION_PRODUCTION_DEVELOPMENT_AND_BRINGING_TO_USE',
            'usual_life_years': [3, 6], 'development_conditions': ['DIRECTLY_ASSOCIATED_IDENTIFIABLE_APPLICATION', 'PROBABLE_BENEFITS_BEYOND_ONE_YEAR'],
            'direct_development_employee_costs_included': True, 'remaining_it_costs': 'EXPENSE_AS_INCURRED',
        }, (110, '31-37')),
        make('leases', {
            'note': '2.14', 'reported_standard': 'HISTORICAL_IAS17', 'current_standard_substituted': False,
            'classification_basis': 'SUBSTANCE_OVER_LEGAL_FORM', 'finance_criterion': 'SUBSTANTIALLY_ALL_OWNERSHIP_RISKS_AND_REWARDS_TRANSFER',
            'other_leases': 'OPERATING', 'operating_payments': 'INCOME_EXPENSE_IN_RELATED_PERIOD',
            'lessee_initial': 'ASSET_AND_LIABILITY_AT_COST_EQUAL_TO_PRESENT_VALUE_OF_OUTSTANDING_INSTALMENTS',
            'lessee_instalment_interest': 'INCOME_EXPENSE_WITH_CONSTANT_PERIODIC_RATE_ON_REMAINING_LIABILITY',
            'lessee_instalment_principal': 'REDUCE_LIABILITY', 'lessor_asset': 'LOAN_AT_NET_INVESTMENT',
            'lessor_instalment_interest': 'INCOME_WITH_CONSTANT_PERIODIC_RETURN_ON_OUTSTANDING_INVESTMENT',
            'lessor_instalment_principal': 'REDUCE_LOAN',
        }, (110, '38-53')),
        make('pension-plans', {
            'note': '2.15', 'basis': 'REPORTED_PORTUGUESE_BANKING_ACT',
            'benefits': ['RETIREMENT', 'WIDOW_ORPHAN', 'DISABILITY', 'HEALTHCARE'],
            'hire_cutoff_inclusive': '2008-03-31', 'later_hires': 'GENERAL_SOCIAL_SECURITY',
            'reported_2008_authorisations': 'PORTUGUESE_INSURANCE_INSTITUTE_TO_COVER_ALL_PENSION_AND_HEALTH_LIABILITIES',
            'manager': 'ESAF_ESPIRITO_SANTO_FUNDOS_DE_PENSOES_GROUP_SUBSIDIARY',
            'plan_type': 'DEFINED_BENEFIT', 'benefit_factors': ['AGE', 'SERVICE', 'SALARY'],
            'ifrs_transition': '2004-01-01_RETROSPECTIVE_IAS19_WITH_CORRIDOR_DEFERRAL',
            'measurement': 'PROJECTED_UNIT_CREDIT_PER_PLAN_SEMIANNUALLY_30JUN_AND_31DEC',
            'actuary_review': 'REPORTED_ANNUAL_QUALIFIED_INDEPENDENT_REVIEW',
            'discount_reference': 'HIGH_QUALITY_CORPORATE_BONDS_MATCHING_BENEFIT_CURRENCY_AND_MATURITY',
            'actuarial_changes': ['EXPERIENCE_ADJUSTMENTS', 'ASSUMPTION_CHANGES'],
            'corridor_wording': 'greater of 10% of the pension liabilities or the fair value of the plan assets',
            'corridor_percentage_scope': 'SOURCE_AMBIGUITY_PRESERVED_NO_FORMULA_INFERRED',
            'corridor_measurement_time': 'BEGINNING_OF_SEMESTER',
            'outside_corridor_amortisation_years': 15,
            'source_amortisation_limit': 'NOT_EXCEED_AVERAGE_REMAINING_WORKING_LIVES',
            'inside_corridor_to_income': False,
            'income_cost_components': ['SERVICE_COST', 'INTEREST_COST', 'EXPECTED_PLAN_ASSET_RETURN', 'CORRIDOR_PORTION', 'EARLY_RETIREMENT_CURTAILMENT_WITH_EARLY_ACTUARIAL_AMORTISATION'],
            'normal_retirement_age': 65, 'pensioner_year_end_funding_percent': 100,
            'active_employee_past_service_minimum_funding_percent': 95,
            'recognised_asset_recoverability': 'SEMIANNUALLY_PER_PLAN_EXPECTED_REDUCTION_IN_FUTURE_CONTRIBUTIONS',
        }, (111, '0-6,52,49-50,7-29')),
        make('pension-2011-transition', {
            'note': '2.15', 'effective_date': '2011-01-01', 'reported_law': 'DECREE_LAW_1_A_2011_3JAN',
            'social_security_protection': ['MATERNITY', 'PATERNITY', 'ADOPTION', 'OLD_AGE'],
            'bank_retained_protection': ['SICKNESS', 'DISABILITY', 'DEATH', 'SURVIVAL'],
            'contribution_percent': {'total': '26.6', 'employer': '23.6', 'employee': '3'},
            'replaced_scheme': 'CAFEB_ABOLISHED', 'active_service_window': 'FROM_2011_01_01_UNTIL_RETIREMENT',
            'bank_retained_differential': 'GUARANTEE_PENSION_UNDER_ACT', 'legal_effect_independently_verified': False,
        }, (111, '30-36')),
        make('healthcare', {
            'note': '2.15', 'provider': 'UNION_MANAGED_AUTONOMOUS_SAMS',
            'services': ['MEDICAL', 'DIAGNOSTIC', 'MEDICINES', 'HOSPITAL', 'SURGERY'],
            'service_conditions': 'FINANCING_AVAILABILITY_AND_INTERNAL_REGULATIONS',
            'contribution_percent': '6.5', 'contribution_base': 'TOTAL_ANNUAL_REMUNERATION_INCLUDING_HOLIDAY_AND_CHRISTMAS_SUBSIDY',
            'postretirement_measurement': 'SIMILAR_TO_PENSION', 'pension_fund_coverage_from': 2008,
        }, (111, '37-46')),
        make('long-service-benefits', {
            'note': '2.15', 'years_and_monthly_pay': [[15, 1], [25, 2], [30, 3]],
            'salary_basis': 'EFFECTIVE_MONTHLY_REMUNERATION_AT_PAYMENT',
            'early_retirement_disability': 'PROPORTIONATE_ENTITLEMENT_TO_NEXT_PAYMENT_DATE',
            'standard': 'IAS19_OTHER_LONG_TERM_EMPLOYEE_BENEFITS', 'measurement': 'SEMIANNUAL_PROJECTED_UNIT_CREDIT',
            'assumptions': ['FUTURE_SALARY_INCREASE', 'MORTALITY', 'PENSION_DISCOUNT_METHOD'],
            'liability_increase_actuarial_changes_past_service': 'INCOME_IN_PERIOD',
        }, (112, '0-5,7-12')),
        make('siba', {
            'note': '2.15', 'end': '2010-12', 'purchase': 'EMPLOYEE_DEFERRED_SETTLEMENT_FINANCED_BY_GROUP',
            'minimum_holding_years': [2, 4], 'after_holding': 'SELL_IN_MARKET_AND_REPAY_OR_SELL_BACK_TO_BES_AT_ACQUISITION_COST',
            'employee_shares': 'BES_TREASURY_STOCK', 'settlement': 'EQUITY', 'standard': 'IFRS2',
            'measurement': 'GRANT_DATE_FAIR_VALUE_EXPENSE_AND_EQUITY_OVER_VESTING',
            'annual_expense_adjustment': 'ACTUAL_NUMBER_VESTING', 'subsequent_fair_value_remeasurement': False,
        }, (112, '13-21')),
        make('pprv', {
            'note': '2.15', 'scheme': 'PPRV_2008_2010', 'shareholder_meeting': '2008-03-31',
            'benefit': 'FUTURE_CASH_FOR_BES_SHARE_APPRECIATION_ABOVE_STRIKE', 'retention_years': 3,
            'settlement': 'CASH', 'standard': 'IFRS2', 'initial_grant_fair_value': 'STAFF_COST_OVER_THREE_YEARS',
            'subsequent_fair_value_remeasurement': True, 'remeasurement': 'EACH_BALANCE_SHEET_DATE_THROUGH_INCOME',
        }, (112, '22-23,25-30')),
        make('prvif', {
            'note': '2.15', 'approval': '2010-04-06', 'executive_remuneration_approx_percent': {'fixed': 45, 'variable': 55},
            'variable_components': ['SHORT_TERM_PERFORMANCE', 'MEDIUM_TERM_PERFORMANCE'],
            'short_term': 'HALF_CASH_AND_HALF_DEFERRED_OVER_THREE_YEARS_SPLIT_HALF_CASH_HALF_SHARES',
            'medium_term': 'OPTIONS_EXERCISE_THREE_YEARS_AFTER_ATTRIBUTION',
            'executive_allocation_by': 'REMUNERATION_COMMITTEE', 'share_vesting_percent_by_year': [33, 33, 34],
            'share_roe_operator': 'GE', 'share_roe_threshold_percent': 5,
            'option_strike': 'SIMPLE_AVERAGE_EURONEXT_CLOSING_PRICE_PRECEDING_20_DAYS_PLUS_10_PERCENT',
            'option_exercise': 'MATURITY_ONLY', 'option_settlement_choice': ['PHYSICAL', 'FINANCIAL'],
            'top_management_options': 'GENERAL_MANAGERS_AND_BOARD_ADVISORS_GRANTED_BY_BOARD_ON_SIMILAR_BASIS',
            'standards': ['IFRS2', 'IAS19'], '2010_cost_eur_thousand': '3810',
            'attribution_as_of': '2010-12-31', 'shares_or_options_attributed': False,
        }, (112, '31-49')),
        make('employee-director-bonus', {
            'note': '2.15', 'standard': 'IAS19', 'recognition': 'INCOME_IN_YEAR_TO_WHICH_BONUS_RELATES',
            'scope': 'EMPLOYEES_AND_EVENTUALLY_BOARD',
        }, (113, '0-2')),
        make('income-tax', {
            'note': '2.16', 'components': ['CURRENT', 'DEFERRED'], 'recognition_default': 'INCOME',
            'direct_equity_items': 'EQUITY', 'afs_cashflow_hedge_tax_recycling': 'INCOME_WHEN_RELATED_GAINS_LOSSES_ENTER_INCOME',
            'current_tax': 'TAXABLE_YEAR_PROFIT_AT_JURISDICTION_RATES_ENACTED_OR_SUBSTANTIVELY_ENACTED_AT_BALANCE_SHEET_DATE',
            'deferred_method': 'BALANCE_SHEET_LIABILITY_FOR_CARRYING_AMOUNT_TAX_BASIS_TEMPORARY_DIFFERENCES',
            'deferred_rates': 'ENACTED_OR_SUBSTANTIVELY_ENACTED_EXPECTED_AT_REALISATION_OR_SETTLEMENT',
            'deferred_liability_exceptions': ['NONDEDUCTIBLE_GOODWILL', 'INITIAL_RECOGNITION_AFFECTING_NEITHER_ACCOUNTING_NOR_TAXABLE_PROFIT', 'SUBSIDIARY_INVESTMENT_DIFFERENCES_PROBABLY_NOT_REVERSING_FORESEEABLY'],
            'deferred_asset_condition': 'PROBABLE_FUTURE_TAXABLE_PROFITS_FOR_DEDUCTIBLE_DIFFERENCES',
            'offset_level': 'EACH_SUBSIDIARY', 'offset_operator': 'AND',
            'offset_conditions': ['LEGALLY_ENFORCEABLE_CURRENT_TAX_OFFSET_RIGHT', 'SAME_TAXATION_AUTHORITY'],
            'consolidated_presentation': 'SUM_SUBSIDIARY_NET_ASSETS_SEPARATELY_FROM_SUM_SUBSIDIARY_NET_LIABILITIES',
        }, (113, '3,21-24,4-16')),
        make('provisions', {
            'note': '2.17', 'recognition_operator': 'AND',
            'recognition_conditions': ['PRESENT_LEGAL_OR_CONSTRUCTIVE_OBLIGATION', 'PROBABLE_FUTURE_SETTLEMENT', 'RELIABLE_ESTIMATE'],
            'restructuring_plan': 'APPROVED_DETAILED_FORMAL_PLAN', 'restructuring_plan_and_progress': True,
            'restructuring_progress_operator': 'OR', 'restructuring_progress': ['COMMENCED', 'PUBLICLY_ANNOUNCED'],
            'onerous_trigger': 'EXPECTED_BENEFITS_LOWER_THAN_UNAVOIDABLE_COSTS',
            'onerous_measurement': 'PRESENT_VALUE_OF_LOWER_OF_EXPECTED_TERMINATION_COST_AND_EXPECTED_NET_CONTINUATION_COST',
        }, (113, '17-19,47-48,25-27')),
        make('interest', {
            'note': '2.18', 'eir_scope': 'NONDERIVATIVE_AMORTISED_COST_AND_AFS',
            'fvpl_nonderivative_interest': 'INTEREST_AND_SIMILAR_INCOME_OR_EXPENSE',
            'eir_definition': 'DISCOUNT_EXPECTED_LIFE_OR_APPROPRIATE_SHORTER_PERIOD_CASHFLOWS_TO_NET_CARRYING_AMOUNT',
            'eir_time': 'CALCULATED_AT_INCEPTION_NOT_SUBSEQUENTLY_REVISED_AS_REPORTED',
            'contractual_terms_include_options': True, 'future_credit_losses_included': False,
            'eir_includes': ['INTEGRAL_FEES_AND_COMMISSIONS', 'TRANSACTION_COSTS', 'PREMIUMS_AND_DISCOUNTS'],
            'impaired_assets_interest': 'RATE_USED_TO_MEASURE_IMPAIRMENT_LOSS',
            'derivative_default': 'INTEREST_NOT_SEPARATED_FROM_FVPL_NET_GAINS_LOSSES',
            'risk_management_derivative_exception': 'INTEREST_AND_SIMILAR_INCOME_OR_EXPENSE', 'cross_reference': 'Note 2.4',
        }, (113, '28-44')),
        make('fee-commission', {
            'note': '2.19', 'significant_act': 'INCOME_WHEN_COMPLETED', 'service_period': 'INCOME_DURING_SERVICE',
            'integral_to_eir': 'INCOME_USING_EFFECTIVE_INTEREST_RATE',
        }, (114, '0-6')),
        make('dividends', {'note': '2.20', 'recognition': 'WHEN_PAYMENT_RIGHT_ESTABLISHED'}, (114, '7,9')),
        make('segments', {
            'note': '2.21', 'standard': 'IFRS8_FROM_2009_01_01', 'cross_reference': 'Note 4',
            'operating': 'PRODUCT_SERVICE_ASSETS_AND_OPERATIONS_WITH_DIFFERENT_RISKS_AND_RETURNS',
            'management_review': 'PERIODIC_RESULTS_FOR_DECISIONS_WITH_REGULAR_FINANCIAL_INFORMATION',
            'geographical': 'ECONOMIC_ENVIRONMENT_WITH_DIFFERENT_RISKS_AND_RETURNS',
        }, (114, '10-17')),
        make('earnings-per-share', {
            'note': '2.22', 'basic_numerator': 'NET_INCOME_AVAILABLE_TO_ORDINARY_SHAREHOLDERS',
            'basic_denominator': 'WEIGHTED_AVERAGE_OUTSTANDING_ORDINARY_SHARES_EXCLUDING_AVERAGE_TREASURY_STOCK',
            'diluted_denominator': 'ASSUME_CONVERSION_OF_ALL_DILUTIVE_POTENTIAL_ORDINARY_SHARES',
            'examples': ['CONVERTIBLE_DEBT', 'EMPLOYEE_OPTIONS'], 'dilutive_test': 'CONVERSION_DECREASES_NET_EPS',
        }, (114, '18-21,23-24')),
        make('cash-equivalents', {
            'note': '2.23', 'scope': 'CASH_FLOW_STATEMENT', 'maturity_operator': 'LT', 'maturity_months': 3,
            'maturity_from': 'INCEPTION_DATE', 'includes': ['CASH', 'BANK_DEPOSITS'],
            'restricted_central_bank_balances_included': False,
        }, (114, '25-28')),
    ]
    return {'version': 'bes-annual2010-remaining-policies.v1', 'policies': policies,
            'scope': 'ISSUER_STATEMENTS_NOTES_2_8_TO_2_23_ONLY',
            'all_notes_interpreted': False, 'independent_legal_or_financial_acceptance': False,
            'source_authenticity': 'NOT_ESTABLISHED'}


def combine(old, graph):
    result = deepcopy(old)
    assert FIELD not in result
    result[FIELD] = reading(graph)
    result['source_context']['source_pages'] = sorted(set(result['source_context']['source_pages']) | set(NEW_PAGES))
    result['source_context']['scope'] += '; supplied Notes 2.8–2.23 now added; earlier remaining-policy caveat superseded only for these supplied sections; Note1 and numerical notes incomplete'
    assert result['source_context']['all_notes_read'] is False
    return result
