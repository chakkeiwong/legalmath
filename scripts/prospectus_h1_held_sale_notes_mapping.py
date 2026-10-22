"""Original held-for-sale source rows and conditional category scope."""
SPECS = [
 ('balance-table',128,1,41,'Retain separate dated asset/liability columns for resale subsidiaries, property/equipment and signed impairment; unknown liability dashes are not zero and no cross-side netting is inferred.'),
 ('held-sale-scope',128,42,44,'The amounts concern controlled-company investments acquired exclusively for short-term resale, assets acquired for loans and discontinued branches available for immediate sale; readiness is not completed sale.'),
 ('branch-inclusion',128,45,47,'Property includes discontinued branches36729/35558thousand with related impairment9544/8764thousand; these are subsets, not whole property or impairment balances.'),
 ('impairment-table',128,48,77,'Retain three dated signed impairment movements and literal six-month caption; December duration is not silently assigned.'),
 ('movement-introduction',128,78,78,'Carry the non-current-assets-held-for-sale movement introduction into the next-page table.'),
 ('asset-movement',129,1,18,'Retain dated opening/addition/sale/other/closing asset balances and signs; closing gross-to-net arithmetic is diagnostic, not a source-label rewrite.')
]
TABLES=[
 {'key':'held-sale-balances','page':128,'unit_order':3,
  'headers':[[6],[7],[8],[9]],'date_orders':[5,4],'rows':[
   ('resale-subsidiaries',[10],[11,12,13,14]),('property',[15],[17,20,23,26]),
   ('equipment',[16],[18,21,24,27]),('property-equipment-gross',[],[19,22,25,28]),
   ('impairment',[29],[30,31,32,33]),('property-equipment-net',[],[34,35,36,37]),
   ('total',[],[38,39,40,41])]},
 {'key':'impairment-movement','page':128,'unit_order':49,
  'headers':[[51],[52],[53]],'date_orders':[51,52,53],'caption_orders':[50],
  'rows':[('opening',[77],[54,55,56]),('charge',[57],[61,65,69]),
   ('charge-off',[58],[62,66,70]),('write-back',[59],[63,67,71]),
   ('exchange',[60],[64,68,72]),('closing',[73],[74,75,76])]},
 {'key':'asset-movement','page':129,'unit_order':1,'headers':[[2],[3]],
  'date_orders':[2,3],'rows':[
   ('opening',[14],[4,5]),('additions',[15],[6,9]),('sales',[16],[7,10]),
   ('other',[17],[8,11]),('closing',[18],[12,13])]}
]
DISTINCTIONS = {'historical_report_assertions_only': True, 'asset_and_liability_columns_distinct': True, 'asset_liability_netting_inferred': False, 'dash_status': 'PRINTED_DASH_UNKNOWN_NOT_ZERO', 'resale_subsidiaries': 'CONTROLLED_COMPANIES_ACQUIRED_EXCLUSIVELY_FOR_SHORT_TERM_RESALE', 'additional_categories': ['ASSETS_ACQUIRED_IN_EXCHANGE_FOR_LOANS', 'DISCONTINUED_BRANCHES_AVAILABLE_FOR_IMMEDIATE_SALE'], 'available_for_sale_means_sale_completed': False, 'discontinued_branch_property_thousands': {'2010-06-30': 36729, '2009-12-31': 35558}, 'discontinued_branch_impairment_thousands': {'2010-06-30': 9544, '2009-12-31': 8764}, 'branch_property_is_included_not_whole_category': True, 'branch_impairment_is_included_not_whole_category': True, 'impairment_caption': 'Six month period ended', 'impairment_december_duration': 'UNINFERRED_CAPTION_AND_OPENING_BALANCE_TENSION', 'asset_movement_period_duration': 'NOT_INDEPENDENTLY_PRINTED_NO_DURATION_INFERRED', 'reported_asset_movement_closing_thousands': [549431, 460251], 'reported_balance_net_assets_thousands': [486369, 407585], 'reported_impairment_thousands': [63062, 52666], 'gross_to_net_relation_role': 'EXPLANATORY_ARITHMETIC_NOT_REPLACEMENT_OF_PRINTED_LABEL', 'note25_on_page129': 'CONTEXT_ONLY_NOT_NOTE24_SEMANTIC_COVERAGE', 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
