"""Original provisions and tax source associations; no correction of anomalies."""
SPECS = [
    ('provisions-table',141,1,60,'Retain restructuring/other/total provisions and movements between printed balance dates, signed charges and unknown printed dashes in EUR thousands.'),
    ('other-provisions',141,61,63,'Other provisions cover reported contingencies; preserve the dated thousand-euro total and do not equate provisions with certain losses.'),
    ('boavista-contingency',141,64,67,'Retain the reported Boavista/Bradesco exchange contingencies and approximate million-euro amounts with 2009 comparative.'),
    ('bankruptcy-contingency',141,68,71,'Bankruptcy-related legal processes might cause losses; retain conditional wording and approximate dated provisions.'),
    ('tax-contingency',141,72,74,'Ongoing tax-process provisions are approximate EUR62.6million with explicitly printed 31December2008 EUR60.8million comparative; do not correct the year.'),
    ('remaining-contingencies',141,75,78,'Remaining approximate provisions concern potential normal-activity losses including fraud, robbery and ongoing judicial cases.'),
    ('historical-tax-2009',142,1,6,'Retain the report\'s Portugal-domiciled bank/subsidiary scope, IRC/local-tax references and 26.5percent 2009 nominal rate; no present-law conclusion.'),
    ('historical-tax-2010',142,7,9,'Six-month2010 taxes use reported26.5percent plus2.5percent and named Decree-law; enactment or substantial enactment is attributed to the report.'),
    ('tax-review-contingency',142,10,14,'Retain the reported four-year review, possible additional assessments from interpretation differences and Board confidence; confidence is not certainty.'),
    ('deferred-balances',142,15,131,'Preserve six asset/liability/net date columns, signed values, unknown dashes and separate compensation/net rows in EUR thousands.'),
    ('movement-introduction',142,132,132,'Carry the deferred-tax change introduction into the next-page table.'),
    ('deferred-movement',143,1,25,'Deferred-tax movements compare six months2010 with year2009, preserving signs and footnote marker.'),
    ('associate-tax-footnote',143,26,29,'Comprehensive income additionally includes associates fair-value-reserve deferred tax:5481thousand costs versus12545thousand gains.'),
    ('tax-recognition',143,30,117,'Preserve current/deferred taxes in profit/loss and reserves, with mixed6/12month scope, signed values and unknown dashes.'),
    ('reserve-tax-2009',143,118,121,'Preserve literal944million prose against table944thousand and current-tax sentence describing deferred components; neither inconsistency is silently repaired.'),
    ('reserve-tax-2010',143,122,125,'Preserve explicit nil net and966thousand capital profit,914thousand pension cost and52thousand share-payment cost; nil prose does not redefine printed table dashes.'),
    ('tax-reconciliation',144,1,72,'Preserve dated percentage/amount columns, exact decimal signs including(0.0), original labels and inconsistent printed figures; arithmetic is diagnostic only.')
]

TABLES = [
    {'key':'provisions','page':141,'unit_order':3,'headers':[[4,5],[6,7],[8]],
     'dates':[], 'periods':None, 'rows':[
        ('balance-2008',[9],[10,11,12]),
        ('charge-h1-2009',[13],[16,19,22]),
        ('charge-off-h1-2009',[14],[17,20,23]),
        ('exchange-h1-2009',[15],[18,21,24]),
        ('balance-h1-2009',[59],[25,26,27]),
        ('charge-h2-2009',[28],[31,34,37]),
        ('charge-off-h2-2009',[29],[32,35,38]),
        ('exchange-h2-2009',[30],[33,36,39]),
        ('balance-2009',[40],[41,42,43]),
        ('charge-h1-2010',[44],[47,50,53]),
        ('charge-off-h1-2010',[45],[48,51,54]),
        ('exchange-h1-2010',[46],[49,52,55]),
        ('balance-h1-2010',[60],[56,57,58])]},
    {'key':'deferred-balances','page':142,'unit_order':17,
     'headers':[[19],[20],[22],[23],[25],[26]],
     'group_headers':[[18],[21],[24]],'dates':['2010-06-30','2009-12-31']*3,'periods':None,
     'rows':[(key,[27+i],[39+i,51+i,63+i,75+i,87+i,99+i]) for i,key in enumerate(
        ['derivatives','customer-loans','property','intangibles','investments','provisions',
         'pensions','sams','service-benefits','debt','other','tax-losses'])]+[
        ('gross',[111],[112,113,114,115,116,117]),
        ('offset',[130],[118,119,120,121,122,123]),
        ('net',[131],[124,125,126,127,128,129])]},
    {'key':'deferred-movement','page':143,'unit_order':1,'headers':[[4],[13]],
     'period_headers':[[2,3],[12]],'dates':['2010-06-30','2009-12-31'],'periods':[6,12],
     'rows':[(key,[label],[14+i,20+i]) for i,(key,label) in enumerate([
        ('opening',5),('income',6),('fair-value',8),('other-reserves',9),('exchange',10),('closing',11)])]},
    {'key':'tax-recognition','page':143,'unit_order':37,
     'headers':[[33,35],[34,36],[39,41],[40,42]],'date_orders':[32,38],
     'dates':['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],'periods':[6,6,12,12],
     'rows':[(key,[43+i],[55+i,67+i,79+i,91+i]) for i,key in enumerate(
        ['derivatives','customer-loans','property','intangibles','investments','provisions',
         'pensions','sams','service-benefits','debt','other','tax-losses'])]+[
        ('deferred',[103],[104,105,106,107]),('current',[108],[109,110,111,112]),
        ('total',[113],[114,115,116,117])]},
    {'key':'tax-reconciliation','page':144,'unit_order':2,
     'headers':[[5],[20],[21],[22]],'date_orders':[4,3],
     'dates':['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],'periods':None,
     'rows':[
        ('profit',[6],[None,23,None,24]),('statutory-rate',[7],[25,None,26,None]),
        ('calculated-tax',[8],[None,32,None,43]),('subsidiary-rates',[9],[27,33,38,44]),
        ('dividends',[10],[28,34,39,45]),('offshore',[11],[29,35,40,46]),
        ('gains',[12],[30,36,41,47]),('estimates',[13],[31,37,42,48]),
        ('tax-losses',[14,15],[49,54,59,64]),('associates',[16],[50,55,60,65]),
        ('nondeductible',[17],[51,56,61,66]),('additional-tax',[18],[52,57,62,67]),
        ('other',[19],[53,58,63,68]),('total',[],[69,70,71,72])]}
]

DISTINCTIONS = {'historical_report_assertions_only': True, 'table_dash_status': 'PRINTED_DASH_UNKNOWN_NOT_ZERO', 'blank_cell_status': 'UNPRINTED_POSITION_NOT_ZERO', 'provision_columns': ['RESTRUCTURING', 'OTHER', 'TOTAL'], 'provision_balance_dates': ['2008-12-31', '2009-06-30', '2009-12-31', '2010-06-30'], 'provision_movement_periods': 'BETWEEN_PRINTED_BALANCE_DATES', 'contingency_prose_unit': 'EUR_MILLIONS_APPROXIMATE', 'tax_contingency_comparative_date': '2008-12-31', 'tax_contingency_comparative_amount': '60.8', 'other_contingency_comparative_date': '2009-12-31', 'tax_contingency_date_corrected': False, 'tax_subjects': 'BANK_AND_SUBSIDIARIES_DOMICILED_IN_PORTUGAL', 'reported_2009_nominal_tax_percent': '26.5', 'reported_2010_tax_percent_components': ['26.5', '2.5'], 'reported_legal_references': ['Law nr. 107-B/2003 from 31 December', 'Law nr. 2/2007 of 15 January', 'Decree-law nr 12-A of 30 June'], 'rate_enactment': 'REPORT_SAYS_ENACTED_OR_SUBSTANTIALLY_ENACTED_AT_BALANCE_SHEET_DATE', 'reported_tax_review_years': 4, 'additional_tax_assessment_possible': True, 'board_position': 'CONFIDENT_NO_MATERIAL_DIFFERENCES_IN_FINANCIAL_STATEMENTS', 'board_confidence_is_tax_certainty': False, 'deferred_assets_liabilities_net_distinct': True, 'offsetting_preserved': True, 'tax_movement_and_recognition_period_months': [6, 12], 'associate_fair_value_reserve_tax': {'2010-06-30': {'amount': 5481, 'unit': 'EUR_THOUSANDS', 'direction': 'COST'}, '2009-12-31': {'amount': 12545, 'unit': 'EUR_THOUSANDS', 'direction': 'GAIN'}}, 'associate_tax_additional_to_comprehensive_income': True, 'reserve_tax_2009_table': {'amount': 944, 'unit': 'EUR_THOUSANDS'}, 'reserve_tax_2009_prose': {'amount': 944, 'unit': 'EUR_MILLIONS'}, 'reserve_tax_2009_unit_conflict': 'UNRESOLVED_PRINTED_CONFLICT', 'reserve_tax_2009_prose_classification': 'CURRENT_TAX_SENTENCE_DESCRIBES_DEFERRED_TAX_COMPONENTS', 'reserve_tax_2009_components_thousands': {'capital_income': 823, 'pension_expense': 1671, 'share_payment_expense': 96}, 'reserve_tax_2010_prose_net': 'NIL', 'reserve_tax_2010_components_thousands': {'capital_profit': 966, 'pension_cost': 914, 'share_payment_cost': 52}, '2010_nil_does_not_redefine_table_dashes': True, 'reported_reconciliation_total_percent': ['4.1', '16.0'], 'reported_reconciliation_total_amount_thousands': [21516, 109819], 'reconciliation_percent_amount_consistency': 'NOT_ASSUMED_PRESERVE_PRINTED_VALUES', 'signed_zero_preserved': '2009_ESTIMATES_PERCENT_PRINTED_(0.0)', 'source_label_typos_and_clipping_preserved': True, 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
