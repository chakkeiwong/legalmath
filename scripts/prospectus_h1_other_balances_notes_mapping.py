"""Original other-asset/liability tables and accompanying conditional readings."""
SPECS = [
    ('other-assets-table',134,41,107,'Retain other-asset subcategories, signed debtor impairment, pensions, unsettled transactions and totals at June2010/December2009 in EUR thousands; do not infer availability or net assets against liabilities.'),
    ('locarent-loans',135,1,2,'Loans to companies with non-controlling interest include110000thousand loans to Locarent; inclusion is not the whole category.'),
    ('employee-loan-difference',135,3,8,'Prepayments include57266thousand/65613thousand nominal-versus-grant-date-fair-value differences for employee loans under the collective labour agreement. The report charges this over the lower of remaining loan maturity and estimated remaining employee service life, citing IAS39.'),
    ('asset-pending-settlement',135,9,11,'Stock-exchange asset transactions are for third parties, recognised on trade date and pending settlement, with Note2.6; do not infer settlement or apply the statement to all assets.'),
    ('debtor-impairment',135,12,41,'Retain signed debtor impairment movements and unknown dash. Preserve the six-month caption and December column without inferring a full-year duration.'),
    ('other-liabilities-table',146,1,56,'Retain creditor/accrued/deferred/unsettled liability categories, original date/unit association and unknown foreign-exchange dash; long-service benefits cite Note12.'),
    ('liability-pending-settlement',146,57,59,'The other-liability note repeats third-party stock transactions recognised on trade date and pending settlement, with Note2.6. Preserve both occurrences and their asset/liability contexts.')
]

TABLES = [
    {'key':'other-assets','page':134,'unit_order':43,'date_orders':[44,53],
     'section_orders':[45,99,103],'periods':None,'rows':[
       ('options',[46],[54,64]),('futures',[47],[55,65]),('collateral',[48],[56,66]),
       ('mortgage-subsidies',[49],[57,67]),('noncontrolling-loans',[50],[58,68]),
       ('public',[51],[59,69]),('sundry-debtors',[52],[60,70]),
       ('gross-debtors',[],[61,71]),('impairment',[98],[62,72]),('net-debtors',[],[63,73]),
       ('precious-liquid',[100,101],[74,77]),('other',[102],[75,78]),('other-total',[],[76,79]),
       ('accrued',[80],[81,82]),('prepayments',[83],[84,85]),
       ('fx-unsettled',[104],[86,90]),('stock-unsettled',[105],[87,91]),
       ('other-unsettled',[106],[88,92]),('unsettled-total',[],[89,93]),
       ('pensions',[107],[94,95]),('total',[],[96,97])],
     'subtotals':[
       (['options','futures','collateral','mortgage-subsidies','noncontrolling-loans','public','sundry-debtors'],'gross-debtors'),
       (['gross-debtors','impairment'],'net-debtors'),(['precious-liquid','other'],'other-total'),
       (['fx-unsettled','stock-unsettled','other-unsettled'],'unsettled-total'),
       (['net-debtors','other-total','accrued','prepayments','unsettled-total','pensions'],'total')]},
    {'key':'debtor-impairment','page':135,'unit_order':13,'date_orders':[21,22,23],
     'section_orders':[],'caption_order':14,'periods':[6,None,6],'rows':[
       ('opening',[15],[24,25,26]),('charge',[16],[27,31,35]),('charge-off',[17],[28,32,36]),
       ('write-back',[18],[29,33,37]),('other',[19],[30,34,38]),('closing',[20],[39,40,41])],
     'subtotals':[(['opening','charge','charge-off','write-back','other'],'closing')]},
    {'key':'other-liabilities','page':146,'unit_order':3,'date_orders':[21,22],
     'section_orders':[4,8,13,17],'periods':None,'rows':[
       ('public',[5],[23,26]),('futures',[6],[24,27]),('deposits',[7],[25,28]),
       ('securities',[9],[29,34]),('suppliers',[10],[30,35]),('factoring',[11],[31,36]),
       ('sundry-creditors',[12],[32,37]),('creditors-total',[],[33,38]),
       ('service-benefits',[14],[39,42]),('other-accrued',[15],[40,43]),('accrued-total',[],[41,44]),
       ('deferred',[16],[45,46]),('stock-unsettled',[18],[47,51]),('fx-unsettled',[19],[48,52]),
       ('other-unsettled',[20],[49,53]),('unsettled-total',[],[50,54]),('total',[],[55,56])],
     'subtotals':[
       (['public','futures','deposits','securities','suppliers','factoring','sundry-creditors'],'creditors-total'),
       (['service-benefits','other-accrued'],'accrued-total'),
       (['stock-unsettled','fx-unsettled','other-unsettled'],'unsettled-total'),
       (['creditors-total','accrued-total','deferred','unsettled-total'],'total')]}
]

DISTINCTIONS = {'historical_report_assertions_only': True, 'table_unit': 'EUR_THOUSANDS', 'note28_direction': 'ASSETS', 'note36_direction': 'LIABILITIES', 'asset_liability_netting_inferred': False, 'dash_status': 'PRINTED_DASH_UNKNOWN_NOT_ZERO', 'locarent_loan_thousands': 110000, 'locarent_is_included_not_whole_category': True, 'employee_loan_difference_thousands': {'2010-06-30': 57266, '2009-12-31': 65613}, 'employee_loan_difference': 'NOMINAL_LOAN_MINUS_FAIR_VALUE_AT_GRANT', 'employee_loan_fair_value_reference': 'IAS_39_HISTORICAL_REPORT_STATEMENT', 'act_meaning': 'COLLECTIVE_LABOUR_AGREEMENT_FOR_BANKING_SECTOR', 'employee_loan_charge_period': 'LOWER_OF_REMAINING_LOAN_MATURITY_AND_ESTIMATED_REMAINING_EMPLOYEE_SERVICE_LIFE', 'employee_loan_difference_is_entire_prepayment_balance': False, 'pending_stock_transactions_on_behalf_of': 'THIRD_PARTIES', 'pending_stock_recognition': 'TRADE_DATE', 'pending_stock_settlement': 'PENDING', 'pending_stock_reference': 'NOTE_2_6', 'pending_stock_description_applies_to_both_asset_and_liability_notes': True, 'pending_stock_description_generalized_to_all_balances': False, 'service_benefit_reference': 'NOTE_12', 'pension_assets_are_reported_not_freely_available_inferred': True, 'impairment_caption': 'Six month period ended', 'impairment_december_duration': 'UNINFERRED_CAPTION_DATE_TENSION', 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
