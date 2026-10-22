"""Original EPS and bank-note positions; preserve printed temporal anomalies."""
SPECS=[
    ('eps-definition',116,1,4,'Basic EPS divides profit attributable to Bank equity holders by weighted average outstanding ordinary shares.'),
    ('eps-table',116,5,34,'Retain the mixed six-month2010, annual2009 and six-month2009 columns; profits are EUR thousands, weighted shares are thousands, and EPS is euro per share. Treasury stock is subtracted from weighted ordinary shares.'),
    ('preference-adjustment',116,35,36,'The profit footnote adjusts for preference-share dividends accounted as an equity movement.'),
    ('dilution',116,37,42,'Diluted EPS adjusts for all dilutive potential ordinary shares; the report says outstanding SIBA plans are not dilutive and diluted EPS equals basic EPS.'),
    ('central-cash-table',116,43,61,'Retain cash and Bank of Portugal/other central-bank balances and totals at June2010/December2009, in EUR thousands.'),
    ('mandatory-reserves',117,1,8,'Retain mandatory Bank of Portugal reserves, the historical regulation,2percent basis with strictly less than two years maturity and the ESCB-subject institution exclusion, and dated interest rates; do not infer current law or free availability.'),
    ('bank-deposit-table',117,9,36,'Retain domestic/foreign demand balances, uncollected cheques, other foreign balances and totals at June2010/December2009 in EUR thousands.'),
    ('cheque-collection',117,37,38,'Cheques were sent for collection during first working days after the reference dates; do not infer completed settlement.'),
    ('bank-advance-table',122,1,49,'Retain domestic/foreign advance categories, subtotals, signed impairment deductions and net total for June2010/December2009 in EUR thousands.'),
    ('bank-rates',122,50,52,'Domestic advances report average annual rates1.36percent and1.44percent; foreign advances use international market rates where the Group operates.'),
    ('system-deposits',122,53,55,'Keep reported system deposits425/3750026 EUR thousands, their June2010/December2009 dates and the printed European Central Banks System 0 wording without silently removing the zero.'),
    ('impairment-movement',122,56,82,'Retain the opening/charge/write-back/exchange/closing table and signed parentheses; its six-month caption, December column and during-the-year prose coexist, so do not infer the December duration.')
]

TABLES=[
    {'key':'eps','page':116,'date_orders':[8,9,13],'period_orders':[5,6,7,11,12],
     'unit_order':10,'section_orders':[],'dates':['2010-06-30','2009-12-31','2009-06-30'],
     'period_months':[6,12,6],
     'rows':[
         ('profit',33,[15,16,17],'EUR_THOUSANDS'),
         ('ordinary-shares',18,[20,22,24],'SHARES_THOUSANDS'),
         ('treasury-shares',19,[21,23,25],'SHARES_THOUSANDS'),
         ('outstanding-shares',26,[27,28,29],'SHARES_THOUSANDS'),
         ('basic-eps',34,[30,31,32],'EUR_PER_SHARE')]},
    {'key':'central-cash','page':116,'date_orders':[46,47],'period_orders':[],
     'unit_order':45,'section_orders':[51],'dates':['2010-06-30','2009-12-31'],'period_months':None,
     'rows':[
         ('cash',48,[49,50],'EUR_THOUSANDS'),('bank-portugal',52,[54,56],'EUR_THOUSANDS'),
         ('other-central-banks',53,[55,57],'EUR_THOUSANDS'),('central-total',None,[58,59],'EUR_THOUSANDS'),
         ('total',None,[60,61],'EUR_THOUSANDS')]},
    {'key':'bank-deposits','page':117,'date_orders':[19,20],'period_orders':[],
     'unit_order':11,'section_orders':[12,15],'dates':['2010-06-30','2009-12-31'],'period_months':None,
     'rows':[
         ('portugal-demand',13,[21,23],'EUR_THOUSANDS'),('portugal-cheques',14,[22,24],'EUR_THOUSANDS'),
         ('portugal-total',None,[25,26],'EUR_THOUSANDS'),('abroad-demand',16,[27,30],'EUR_THOUSANDS'),
         ('abroad-cheques',17,[28,31],'EUR_THOUSANDS'),('abroad-other',18,[29,32],'EUR_THOUSANDS'),
         ('abroad-total',None,[33,34],'EUR_THOUSANDS'),('total',None,[35,36],'EUR_THOUSANDS')]},
    {'key':'bank-advances','page':122,'date_orders':[4,5],'period_orders':[],
     'unit_order':3,'section_orders':[6,43],'dates':['2010-06-30','2009-12-31'],'period_months':None,
     'rows':[
         ('portugal-interbank',7,[13,19],'EUR_THOUSANDS'),('portugal-deposits',8,[14,20],'EUR_THOUSANDS'),
         ('portugal-loans',9,[15,21],'EUR_THOUSANDS'),('portugal-short-deposits',10,[16,22],'EUR_THOUSANDS'),
         ('portugal-repos',11,[17,23],'EUR_THOUSANDS'),('portugal-other',12,[18,24],'EUR_THOUSANDS'),
         ('portugal-total',None,[25,26],'EUR_THOUSANDS'),
         ('abroad-deposits',44,[27,32],'EUR_THOUSANDS'),('abroad-short-deposits',45,[28,33],'EUR_THOUSANDS'),
         ('abroad-loans',46,[29,34],'EUR_THOUSANDS'),('abroad-repos',47,[30,35],'EUR_THOUSANDS'),
         ('abroad-other',48,[31,36],'EUR_THOUSANDS'),('abroad-total',None,[37,38],'EUR_THOUSANDS'),
         ('impairment',49,[39,40],'EUR_THOUSANDS'),('net-total',None,[41,42],'EUR_THOUSANDS')]},
    {'key':'bank-impairment','page':122,'date_orders':[60,61,62],'period_orders':[59],
     'unit_order':58,'section_orders':[],'dates':['2010-06-30','2009-12-31','2009-06-30'],
     'period_months':None,'period_scope':'PRINTED_CAPTION_RETAINED; DECEMBER_COLUMN_DURATION_NOT_INFERRED',
     'rows':[
         ('opening',63,[64,65,66],'EUR_THOUSANDS'),('charge',67,[70,73,76],'EUR_THOUSANDS'),
         ('write-back',68,[71,74,77],'EUR_THOUSANDS'),('exchange-other',69,[72,75,78],'EUR_THOUSANDS'),
         ('closing',79,[80,81,82],'EUR_THOUSANDS')]}
]

# Manually image-checked; native text was seen first.
DISTINCTIONS={'historical_report_assertions_only': True, 'eps_period_months': [6, 12, 6], 'eps_dates': ['2010-06-30', '2009-12-31', '2009-06-30'], 'eps_profit_unit': 'EUR_THOUSANDS', 'eps_share_unit': 'SHARES_THOUSANDS', 'eps_result_unit': 'EUR_PER_SHARE', 'eps_denominator': 'WEIGHTED_AVERAGE_ORDINARY_SHARES_LESS_TREASURY_SHARES', 'eps_profit_preference_dividend_adjusted': True, 'preference_dividend_accounted_as': 'EQUITY_MOVEMENT', 'diluted_eps_adjusts_all_dilutive_potential_ordinary_shares': True, 'siba_outstanding_plans_reported_nondilutive': True, 'reported_basic_equals_diluted': True, 'bank_balance_dates': ['2010-06-30', '2009-12-31'], 'bank_balance_units': 'EUR_THOUSANDS', 'mandatory_reserves_eur_thousands': {'2010-06-30': 596816, '2009-12-31': 641802}, 'mandatory_reserve_purpose': 'LEGAL_MINIMUM_CASH_REQUIREMENTS', 'reported_reserve_regulation': 'ECB_CE_2818_98_1998_12_01', 'reported_reserve_percent': 2, 'reserve_maturity_comparison': 'STRICTLY_LESS_THAN_TWO_YEARS', 'reserve_basis': 'DEPOSITS_AND_DEBT_CERTIFICATES', 'reserve_exclusion': 'DEPOSITS_AND_DEBT_CERTIFICATES_OF_INSTITUTIONS_SUBJECT_TO_ESCB_MINIMUM_RESERVES', 'reserve_interest_percent': {'2010-06-30': '1.00', '2009-12-31': '1.27'}, 'restricted_balances_assumed_freely_available': False, 'cheques_collection': 'SENT_DURING_FIRST_WORKING_DAYS_AFTER_REFERENCE_DATES', 'cheques_already_settled_inferred': False, 'domestic_advance_average_annual_interest_percent': {'2010-06-30': '1.36', '2009-12-31': '1.44'}, 'foreign_advance_interest': 'INTERNATIONAL_MARKET_RATES_WHERE_GROUP_OPERATES', 'system_deposit_eur_thousands': {'2010-06-30': 425, '2009-12-31': 3750026}, 'system_deposit_printed_name': 'European Central Banks System 0', 'system_deposit_stray_zero_preserved': True, 'impairment_parentheses_are_negative': True, 'impairment_movement_caption': 'Six month period ended', 'impairment_prose_says': 'changes occurred during the year', 'impairment_december_duration_inferred': False, 'printed_period_tension_preserved': True, 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
