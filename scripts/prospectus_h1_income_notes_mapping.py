"""Original note associations; arithmetic never fills a printed unknown."""
SPECS = [
    ('interest-table',103,1,53,'Retain all interest income/expense rows, subtotals and net result, with six-month 2010/2009 columns and thousands of euro; preserve the expense-row income label and printed dash.'),
    ('unwind-discount',103,54,56,'Interest from loans includes reported discount unwind of EUR 10,815 thousand in 2010 and 10,813 thousand in 2009 for impaired overdue customer loans; retain Note 21.'),
    ('risk-derivatives',103,57,60,'Risk-management derivative interest includes designated hedges and derivatives managing certain FVTPL asset/liability risks; retain Notes 2.4, 2.18, 2.5, 2.6 and 2.8.'),
    ('fee-table',104,1,41,'Retain every fee income/expense category, subtotal and net amount for both six-month periods in thousands of euro.'),
    ('service-rights',115,1,5,'The Note 12 continuation uses effective remuneration when premiums are due and proportional early-retirement/disability awards through the next payment date, referring to policy 2.15.'),
    ('service-amounts',115,6,9,'Separate service liabilities of EUR 29,275/28,602 thousand at June 2010/December 2009 from six-month expenses of EUR 2,433/1,612 thousand in June 2010/June 2009; retain Note 36.'),
    ('service-assumptions',115,10,11,'Pension actuarial assumptions apply to service liabilities when applicable; do not remove that qualification.'),
    ('administrative-table',115,12,70,'Retain all seventeen administrative expense categories and total in thousands of euro for the six-month periods ended June 2010 and June 2009.'),
    ('other-costs',115,71,72,'Other costs includes specialized security, information and database services, training costs and external suppliers; the list is not exhaustive.')
]

# Rows identify original source positions; values come from exact source quotes
# and are compared with the separately typed image transcript.
TABLES = [
    {'key':'interest','page':103,'unit_order':3,'period_order':4,'date_orders':[5,21],
     'section_orders':[6,14],
     'rows':[
        ('income-loans',7,22,29),('income-fvtpl',8,23,30),
        ('income-bank-deposits',9,24,31),('income-afs',10,25,32),
        ('income-risk-derivatives',11,26,33),('income-htm',12,27,34),
        ('income-other',13,28,35),('income-total',None,36,37),
        ('expense-debt-securities',15,38,44),('expense-customers',16,39,45),
        ('expense-central-and-other-banks',17,40,46),
        ('expense-risk-derivatives',18,41,47),('expense-subordinated',19,42,48),
        ('expense-other-printed-income',20,43,49),('expense-total',None,50,51),
        ('net-interest',None,52,53)]},
    {'key':'fees','page':104,'unit_order':3,'period_order':4,'date_orders':[5,17],
     'section_orders':[6,12],
     'rows':[
        ('income-banking',7,18,23),('income-guarantees',8,19,24),
        ('income-securities',9,20,25),('income-commitments',10,21,26),
        ('income-other',11,22,27),('income-total',None,28,29),
        ('expense-banking',13,30,34),('expense-securities',14,31,35),
        ('expense-guarantees',15,32,36),('expense-other',16,33,37),
        ('expense-total',None,38,39),('net-fees',None,40,41)]},
    {'key':'administrative','page':115,'unit_order':14,'period_order':15,'date_orders':[16,34],
     'section_orders':[],
     'rows':[
        ('rental',17,35,52),('advertising',18,36,53),('communication',19,37,54),
        ('maintenance',20,38,55),('travel',21,39,56),('transportation',22,40,57),
        ('insurance',23,41,58),('it',24,42,59),('independent-work',25,43,60),
        ('temporary-work',26,44,61),('electronic-payments',27,45,62),
        ('advisory',28,46,63),('legal',29,47,64),('consultants-auditors',30,48,65),
        ('water-energy-fuel',31,49,66),('consumables',32,50,67),('other',33,51,68),
        ('total',None,69,70)]}
]

# Separately image-checked; native text was seen before transcription.
DISTINCTIONS = {'historical_report_assertions_only': True, 'table_unit': 'EUR_THOUSANDS', 'table_period_months': 6, 'table_period_ends': ['2010-06-30', '2009-06-30'], 'expenses_presented_as': 'POSITIVE_MAGNITUDES', 'printed_dash_semantics': 'UNKNOWN_NOT_ASSUMED_ZERO', 'unlabelled_subtotals_and_net_labels': 'INTERPRETIVE_LABELS_WITH_PRINTED_POSITION_RETAINED', 'interest_expense_other_printed_label': 'Other interest and similar income', 'interest_expense_label_anomaly_preserved': True, 'unwind_discount_eur_thousands': {'2010-06-30': 10815, '2009-06-30': 10813}, 'unwind_discount_scope': 'IMPAIRMENT_LOSSES_ON_OVERDUE_LOANS_AND_ADVANCES_TO_CUSTOMERS', 'unwind_discount_cross_reference': 'NOTE_21', 'risk_derivative_categories': ['HEDGING_DERIVATIVES', 'DERIVATIVES_MANAGING_FVTPL_DESIGNATED_ASSET_AND_LIABILITY_RISK'], 'risk_derivative_cross_references': ['NOTE_2_4', 'NOTE_2_18', 'NOTE_2_5', 'NOTE_2_6', 'NOTE_2_8'], 'service_premium_base': 'EFFECTIVE_MONTHLY_REMUNERATION_WHEN_DUE', 'service_early_retirement_disability': 'PROPORTIONAL_TO_NEXT_PAYMENT_DATE', 'service_liabilities_eur_thousands': {'2010-06-30': 29275, '2009-12-31': 28602}, 'service_six_month_expenses_eur_thousands': {'2010-06-30': 2433, '2009-06-30': 1612}, 'service_liability_and_expense_dates_distinct': True, 'service_cross_references': ['NOTE_2_15', 'NOTE_36'], 'service_pension_assumptions': 'WHEN_APPLICABLE', 'other_administrative_cost_examples': ['SECURITY', 'INFORMATION', 'DATABASES', 'TRAINING', 'EXTERNAL_SUPPLIERS'], 'note12_complete': False, 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
