"""Original reserve movements and non-controlling-interest source associations."""
SPECS = [
    ('legal-reserve',149,1,7,'Retain the historical legal-reserve restriction to accumulated-loss absorption or capital increase, the cited Article97 and the10percent transfer until reserve equals share capital; no current-law or cash-availability conclusion.'),
    ('fair-value-definition',149,8,12,'Fair-value reserve concerns unrealized available-for-sale gains/losses, net of income-statement impairment, deferred taxes and non-controlling interest; do not treat it as gross gains or cash.'),
    ('reserve-periods',149,13,14,'Retain the explicitly reported six-month2010/year2009 comparison and the intervening balance dates printed in the table.'),
    ('reserve-table',149,15,196,'Preserve seven distinct reserve columns, signed movements, unknown dashes, unprinted positions and the capital-increase parent/detail hierarchy; do not double-count its components.'),
    ('fair-value-movement-intro',149,197,198,'Carry the net-of-deferred-tax/impairment/non-controlling-interest scope into the next-page fair-value-reserve movement.'),
    ('fair-value-movement',150,1,21,'Preserve the dated signed fair-value movement, disposals, impairment and deferred-tax entries with reported opening/closing balances; arithmetic is explanatory only.'),
    ('nci-introduction',150,22,23,'Non-controlling interest is analysed by subsidiary, separate from the parent shareholders reserve categories.'),
    ('nci-subsidiaries',150,24,108,'Keep balance-sheet amounts separate from income-statement amounts at each printed date; preserve signed losses, unknown AMAN comparative dashes and all subsidiary labels. Income durations are not independently printed in this table.'),
    ('nci-movement-periods',150,109,110,'Preserve the literal six-month-period description covering June2010,December2009 and June2009; do not silently rewrite December to a year.'),
    ('nci-movement',150,111,146,'Retain three dated non-controlling-interest movements and signed consolidation/capital/dividend/fair-value/exchange/profit categories. December profit31354 differs from subsidiary-table52978; preserve both scopes without a silent replacement.')
]

TABLES = [
    {'key':'reserves','page':149,'unit_order':15,
     'headers':[[22,23,24,25],[26,27,28],[186,187,188],[189],[191,192],[18,19,20,21],[193,194,195,196]],
     'group_headers':[[16],[17]],'date_orders':[], 'rows':[
        ('balance-2008',[176],[29,30,31,32,33,34,35]),
        ('capital-increase',[177],[36,37,38,39,40,41,42]),
        ('capital-decrease',[178],[43,45,47,49,51,53,55]),
        ('special-reserve',[179],[44,46,48,50,52,54,56]),
        ('siba-h1-2009',[180],[57,59,61,62,64,66,68]),
        ('dividends-h1-2009',[181],[58,60,190,63,65,67,69]),
        ('fair-value-h1-2009',[70],[71,72,78,80,73,74,75]),
        ('exchange-h1-2009',[81],[76,77,79,84,86,88,90]),
        ('transfer-h1-2009',[82],[None,None,83,85,87,89,91]),
        ('balance-h1-2009',[182],[92,93,94,95,96,97,98]),
        ('siba-h2-2009',[183],[99,100,101,102,103,104,105]),
        ('fair-value-h2-2009',[106],[107,108,109,110,111,112,113]),
        ('exchange-h2-2009',[114],[115,116,117,118,119,120,121]),
        ('balance-2009',[122],[123,124,125,126,127,128,129]),
        ('siba-h1-2010',[130],[131,133,135,137,139,141,143]),
        ('dividends-h1-2010',[184],[132,134,136,138,140,142,144]),
        ('fair-value-h1-2010',[145],[146,147,148,149,150,151,152]),
        ('exchange-h1-2010',[153],[155,157,159,161,163,165,167]),
        ('transfer-h1-2010',[154],[156,158,160,162,164,166,168]),
        ('balance-h1-2010',[185],[169,170,171,172,173,174,175])]},
    {'key':'fair-value-movement','page':150,'unit_order':1,'headers':[[2],[3]],
     'date_orders':[2,3],'rows':[
        ('opening',[4],[5,8]),('fair-value',[6],[7,9]),('disposals',[10],[12,13]),
        ('impairment',[11],[14,15]),('deferred-tax',[16],[17,18]),('closing',[19],[20,21])]},
    {'key':'nci-subsidiaries','page':150,'unit_order':43,
     'headers':[[25,27],[26,28],[45,47],[46,48]],'date_orders':[24,44],
     'rows':[(key,[29+i],[49+i,63+i,77+i,91+i]) for i,key in enumerate([
         'es-concessoes','bes-angola','aman-bank','esaf','bes-acores','best',
         'bes-investimento-brasil','bes-securities','fcr-ventures-ii','fcr-ventures-iii',
         'fcr-pme-bes','multimercado','absolute-return','other'])]+[
         ('total',[],[105,106,107,108])]},
    {'key':'nci-movement','page':150,'unit_order':111,'headers':[[112],[113],[114]],
     'date_orders':[112,113,114],'rows':[
         (key,[115+4*i],[116+4*i,117+4*i,118+4*i]) for i,key in enumerate([
             'opening','consolidation','capital','dividends','fair-value','exchange','profit','closing'])]}
]

DISTINCTIONS = {'historical_report_assertions_only': True, 'legal_reserve_permitted_uses': ['ABSORB_ACCUMULATED_LOSSES', 'INCREASE_SHARE_CAPITAL'], 'legal_reserve_reported_transfer_percent': 10, 'legal_reserve_transfer_until': 'RESERVE_EQUALS_SHARE_CAPITAL', 'legal_reserve_reported_law': 'ARTICLE_97_DECREE_LAW_298_92_31_DECEMBER', 'legal_reserve_distributability_inferred': False, 'fair_value_origin': 'UNREALIZED_AVAILABLE_FOR_SALE_SECURITY_GAINS_AND_LOSSES', 'fair_value_net_of': ['INCOME_STATEMENT_IMPAIRMENT_CURRENT_OR_PRIOR_YEARS', 'DEFERRED_TAX', 'NON_CONTROLLING_INTEREST'], 'reserves_are_cash_inferred': False, 'reserve_columns': ['AVAILABLE_FOR_SALE', 'DEFERRED_TAX', 'TOTAL_FAIR_VALUE', 'LEGAL_RESERVE', 'EXCHANGE_DIFFERENCES', 'OTHER_RESERVES_RETAINED_EARNINGS', 'TOTAL_OTHER_RESERVES_RETAINED_EARNINGS'], 'reserve_balance_dates': ['2008-12-31', '2009-06-30', '2009-12-31', '2010-06-30'], 'reserve_reporting_period_months': [6, 12], 'reserve_movement_periods': 'BETWEEN_PRINTED_BALANCE_DATES', 'capital_increase_components': ['CAPITAL_DECREASE', 'SPECIAL_RESERVE_INCORPORATION'], 'capital_parent_and_children_double_counted': False, 'table_dash_status': 'PRINTED_DASH_UNKNOWN_NOT_ZERO', 'blank_cell_status': 'UNPRINTED_POSITION_NOT_ZERO', 'blank_positions': ['TRANSFER_H1_2009_AVAILABLE_FOR_SALE', 'TRANSFER_H1_2009_DEFERRED_TAX'], 'nci_is_parent_shareholder_equity_inferred': False, 'nci_balance_sheet_and_income_statement_distinct': True, 'nci_subsidiary_income_periods': 'NOT_INDEPENDENTLY_PRINTED_NO_DURATION_INFERRED', 'nci_movement_caption': 'six months period ended 30 June 2010, 31 December 2009 and 30 June 2009', 'nci_december_duration': 'UNINFERRED_CAPTION_AND_OPENING_BALANCE_TENSION', 'nci_december_subsidiary_income_thousands': 52978, 'nci_december_movement_profit_thousands': 31354, 'nci_june2009_movement_profit_thousands': 21624, 'nci_december_income_difference_thousands': 21624, 'nci_december_comparison': 'PRESERVE_DISTINCT_TABLES_WITHOUT_DURATION_OR_CORRECTION_INFERENCE', 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
