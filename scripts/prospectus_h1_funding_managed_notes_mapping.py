"""Original funding liabilities and managed assets, with distinct unit scopes."""
SPECS = [
    ('central-funding-table',136,1,25,'Retain ESCB and other central-bank funding liabilities, their subcategories, subtotals and total at June2010/December2009 in EUR thousands.'),
    ('escb-collateral',136,26,28,'Specified ESCB other funds of EUR6730million/2000million are covered by pledged available-for-sale securities, with Note39; do not extend the assertion to all liabilities.'),
    ('angola-deposits',136,29,30,'Other central-bank deposits include EUR862million/1083million from the Central Bank of Angola at June2010/December2009; the inclusion is not the whole category.'),
    ('bank-funding-table',137,1,40,'Deposits from banks are funding liabilities, distinct from deposits with banks; preserve domestic/international categories, dates, thousands-of-euro units, subtotals and total.'),
    ('customer-funding-table',137,41,78,'Retain customer demand, time, savings and other-funds categories, their individual rows/subtotals and total at June2010/December2009 in EUR thousands.'),
    ('managed-liability',153,1,4,'The report states fund management companies and the depositary bank are jointly liable before participants for non-fulfilment of obligations under law and fund regulations; do not infer universal investment-loss protection or verified current law.'),
    ('managed-assets-table',153,5,29,'Retain six managed-asset categories and total at June2010/December2009 in EUR thousands; management does not by itself establish bank ownership.'),
    ('managed-fair-value',153,30,31,'The report measures amounts in these accounts at fair value determined at the balance-sheet date; preserve attribution and date.')
]

TABLES = [
    {'key':'central-funding','page':136,'date_orders':[4,11],'unit_order':3,
     'section_orders':[5,8],'rows':[
         ('escb-deposits',6,12,14),('escb-other',7,13,15),('escb-total',None,16,17),
         ('other-central-deposits',9,18,20),('other-central-repos',10,19,21),
         ('other-central-total',None,22,23),('total',None,24,25)],
     'subtotals':[
         (['escb-deposits','escb-other'],'escb-total'),
         (['other-central-deposits','other-central-repos'],'other-central-total'),
         (['escb-total','other-central-total'],'total')]},
    {'key':'bank-funding','page':137,'date_orders':[15,16],'unit_order':3,
     'section_orders':[4,9],'rows':[
         ('domestic-interbank',5,17,21),('domestic-deposits',6,18,22),
         ('domestic-short-funds',7,19,23),('domestic-other',8,20,24),
         ('domestic-total',None,25,26),('international-deposits',10,27,32),
         ('international-loans',11,28,33),('international-short-funds',12,29,34),
         ('international-repos',13,30,35),('international-other',14,31,36),
         ('international-total',None,37,38),('total',None,39,40)],
     'subtotals':[
         (['domestic-interbank','domestic-deposits','domestic-short-funds','domestic-other'],'domestic-total'),
         (['international-deposits','international-loans','international-short-funds',
           'international-repos','international-other'],'international-total'),
         (['domestic-total','international-total'],'total')]},
    {'key':'customer-funding','page':137,'date_orders':[44,45],'unit_order':43,
     'section_orders':[46,50,73,76],'rows':[
         ('demand',47,48,49),('time-deposits',51,53,55),('time-other',52,54,56),
         ('time-total',None,57,58),('savings-pensioners',74,59,61),
         ('savings-other',75,60,62),('savings-total',None,63,64),
         ('other-repos',77,65,67),('other-other',78,66,68),
         ('other-total',None,69,70),('total',None,71,72)],
     'subtotals':[
         (['time-deposits','time-other'],'time-total'),
         (['savings-pensioners','savings-other'],'savings-total'),
         (['other-repos','other-other'],'other-total'),
         (['demand','time-total','savings-total','other-total'],'total')]},
    {'key':'managed-assets','page':153,'date_orders':[14,15],'unit_order':7,
     'section_orders':[],'rows':[
         ('securities-funds',8,16,22),('real-estate-funds',9,17,23),
         ('pension-funds',10,18,24),('bancassurance',11,19,25),
         ('portfolio-management',12,20,26),('other',13,21,27),('total',None,28,29)],
     'subtotals':[
         (['securities-funds','real-estate-funds','pension-funds','bancassurance',
           'portfolio-management','other'],'total')]}
]

# Filled only from the separately typed and reviewed image record before freezing.
DISTINCTIONS = {'historical_report_assertions_only': True, 'table_dates': ['2010-06-30', '2009-12-31'], 'table_unit': 'EUR_THOUSANDS', 'notes29_30_31_direction': 'FUNDING_LIABILITIES', 'deposits_from_distinct_from_deposits_with': True, 'collateral_sentence_unit': 'EUR_MILLIONS', 'escb_other_funds_eur_millions': {'2010-06-30': 6730, '2009-12-31': 2000}, 'collateral_scope': 'SPECIFIED_ESCB_OTHER_FUNDS', 'collateral_assets': 'AVAILABLE_FOR_SALE_SECURITIES_PLEDGED', 'collateral_reference': 'NOTE_39', 'all_funding_assumed_collateralized': False, 'angola_sentence_unit': 'EUR_MILLIONS', 'angola_deposits_eur_millions': {'2010-06-30': 862, '2009-12-31': 1083}, 'angola_deposits_included_in': 'OTHER_CENTRAL_BANK_DEPOSITS', 'angola_amount_is_not_entire_category': True, 'customer_categories': ['DEMAND', 'TIME', 'SAVINGS', 'OTHER_FUNDS'], 'savings_pensioners_distinct': True, 'managed_assets_assumed_bank_owned': False, 'managed_liability_actors': ['FUND_MANAGEMENT_COMPANIES', 'DEPOSITARY_BANK'], 'managed_liability_beneficiaries': 'FUND_PARTICIPANTS', 'managed_liability_type': 'JOINT', 'managed_liability_trigger': 'NON_FULFILMENT_OF_ASSUMED_OBLIGATIONS_UNDER_LAW_AND_FUND_MANAGEMENT_REGULATIONS', 'universal_investment_loss_guarantee_inferred': False, 'governing_law_identified_or_verified': False, 'managed_measurement': 'FAIR_VALUE_AT_BALANCE_SHEET_DATE', 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
