"""Source associations for original Note11 and the separate employee count."""
SPECS = [
 ('staff-cost-table',107,40,65,'Preserve six-month staff costs in thousands of euro. Wages and salaries is the parent of remuneration and long-term-service benefits; do not sum the parent again with its components. Pension and service-benefit references to Note12 remain explicit.'),
 ('incentive-inclusions',107,66,70,'SIBA181thousand and PPRV2150thousand are included in other costs in both periods. Retain Note2.15 accounting-policy and Note12 detail references; these inclusions do not equal all other costs or prove payments to a particular employee.'),
 ('employee-count',108,1,12,'Preserve the point-in-time employee count for BES and Group subsidiaries at June2010 and June2009. These are persons, not thousands of euro, average headcount or full-time-equivalent counts.')]

TABLES = [
 {'key':'staff-costs','page':107,'unit_order':42,'headers':[[44],[51]],'date_orders':[44,51],
  'rows':[('wages-salaries',[45],[52,58]),('remuneration',[46],[53,59]),
   ('long-service',[47],[54,60]),('social-charges',[48],[55,61]),('pensions',[49],[56,62]),
   ('other-costs',[50],[57,63]),('total',[],[64,65])]},
 {'key':'employees','page':108,'unit_order':1,'headers':[[2],[3]],'date_orders':[2,3],
  'rows':[('bes',[4],[6,8]),('subsidiaries',[5],[7,9]),('total',[10],[11,12])]}
]

DISTINCTIONS = {'historical_report_assertions_only': True, 'cost_unit': 'EUR_THOUSANDS', 'cost_period_months': [6, 6], 'wages_salary_components': ['REMUNERATION', 'LONG_TERM_SERVICE_BENEFITS'], 'wages_parent_and_components_double_counted': False, 'long_service_and_pension_references': 'NOTE_12_RETAINED_NOT_RESOLVED_BY_NOTE11', 'siba_included_in_other_costs_thousands': {'2010-06-30': 181, '2009-06-30': 181}, 'pprv_included_in_other_costs_thousands': {'2010-06-30': 2150, '2009-06-30': 2150}, 'incentive_inclusions_equal_all_other_costs': False, 'incentive_costs_prove_individual_payment': False, 'incentive_policy_reference': 'NOTE_2_15_RETAINED_NOT_RESOLVED_BY_NOTE11', 'incentive_detail_reference': 'NOTE_12_RETAINED_NOT_RESOLVED_BY_NOTE11', 'headcount_unit': 'PERSONS', 'headcount_scope': 'BES_AND_GROUP_SUBSIDIARIES', 'headcount_time_basis': 'POINT_IN_TIME_30_JUNE_2010_AND_2009', 'headcount_is_period_average_or_fte': False, 'cost_per_average_employee_inferred': False, 'note10_on_page107': 'RETAINED_PRIOR_SEMANTICS_AND_CONTEXT', 'note12_on_page108': 'PARTIAL_CONTEXT_NOT_COMPLETE_NOTE12_DELIVERY', 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
