"""Original Notes 25–26 associations, including discrepant printed labels."""

SPECS = [
    ('property-balance',129,19,86,'Preserve property, equipment, other and work-in-progress components, gross totals and signed accumulated depreciation with both balance dates. The preceding Note24 movement is context only.'),
    ('property-movement-intro',130,1,1,'The following table reports movements in property and equipment; preserve the original heading without inventing a period duration.'),
    ('property-movement',130,2,226,'Keep acquisition cost, depreciation and net amounts in separate sections, with five category columns and all intervening balance dates. The 2010 acquisition-cost section literally labels one row Depreciation of the year; retain that label without correcting it to acquisitions or counting it again as depreciation.'),
    ('property-transfer-a',130,227,228,'Retain the 5224thousand acquisition cost and1193thousand accumulated-depreciation transfer inclusion for discontinued branches, including both other-assets and held-for-sale wording.'),
    ('property-transfer-b',130,229,230,'Retain the 693thousand acquisition cost and533thousand accumulated-depreciation transfer inclusion and the stated discontinued-branch scope.'),
    ('property-transfer-c',130,231,232,'Retain the 1692thousand acquisition cost and521thousand accumulated-depreciation transfer inclusion, linked to the correct 2010 transfer rows.'),
    ('intangible-balance',131,1,34,'Keep goodwill, internally developed software, software acquired from third parties, other assets and work in progress distinct. Preserve gross cost, signed accumulated amortisation and impairment separately from net assets.'),
    ('internal-software',131,35,37,'The report attributes future economic benefits to costs of developing and implementing software applications and refers to Note2.13; it does not independently establish realizable value or resolve the reference.'),
    ('intangible-movement-intro',132,1,1,'Retain the movement introduction and original dates, without treating table counts as valuation evidence.'),
    ('intangible-movement',132,2,273,'Preserve acquisition cost, amortisation, impairment and net amounts with five category columns, unknown dashes and signed movements. Internally developed/acquired categories and acquisition footnote markers stay distinct.'),
    ('es-data-liquidation',132,274,274,'The report says3691thousand goodwill was recognised against the income statement in ES Data liquidation. Preserve the disposal association; do not generalize to all goodwill.'),
    ('aman-acquisition',132,275,275,'The report attributes13326thousand goodwill to Aman Bank acquisition and refers to Note45. Keep the footnote amount distinct from the13475thousand goodwill acquisition row; no silent equality or reference-resolution inference.'),
    ('concordia-impairment',132,276,276,'Preserve the attribution of goodwill impairment to Concordia and its two marked loss rows; no new current impairment conclusion.')
]


def block(keys, labels, starts):
    return [(key,[label],[start+i for start in starts]) for i,(key,label) in enumerate(zip(keys,labels))]


TABLES = [
 {'key':'property-balance','page':129,'unit_order':21,'headers':[[41],[42]],'date_orders':[41,42],
  'rows':[
   ('own-property',[23],[43,46]),('leasehold',[24],[44,47]),('property-other',[25],[45,48]),
   ('property-total',[],[49,50]),
   *[(key,[27+i],[51+i,58+i]) for i,key in enumerate(['computer','fixtures','furniture','security','office','vehicles','equipment-other'])],
   ('equipment-total',[],[65,66]),('other',[34],[67,68]),('operating-gross',[],[69,70]),
   *[(key,[36+i],[71+i,75+i]) for i,key in enumerate(['wip-leasehold','wip-property','wip-equipment','wip-other'])],
   ('wip-total',[],[79,80]),('gross',[],[81,82]),('depreciation',[40],[83,84]),('net',[],[85,86])]},
 {'key':'property-cost','page':130,'unit_order':2,'headers':[[3],[4],[7],[5,6],[8]],'date_orders':[],
  'rows':[
   *block(['balance-2008','acquisitions-h1-2009','disposals-h1-2009','transfers-a','exchange-h1-2009'],range(10,15),[15,20,25,30,35]),
   *block(['balance-h1-2009','acquisitions-h2-2009','disposals-h2-2009','transfers-b','exchange-h2-2009'],range(40,45),[45,50,55,60,65]),
   ('balance-2009',[70],[71,72,73,74,75]),
   *block(['consolidation-h1-2010','printed-depreciation-in-cost','disposals-h1-2010','transfers-c','exchange-h1-2010'],range(222,227),[76,81,86,91,96]),
   ('balance-h1-2010',[101],[102,103,104,105,106])]},
 {'key':'property-depreciation','page':130,'unit_order':2,'headers':[[3],[4],[7],[5,6],[8]],'date_orders':[],
  'rows':[
   *block(['balance-2008','charge-h1-2009','disposals-h1-2009','transfers-a','exchange-h1-2009'],range(108,113),[113,118,123,128,133]),
   *block(['balance-h1-2009','charge-h2-2009','disposals-h2-2009','transfers-b','exchange-h2-2009'],range(138,143),[143,148,153,158,163]),
   *block(['balance-2009','charge-h1-2010','disposals-h1-2010','transfers-c','exchange-h1-2010'],range(168,173),[173,178,183,188,193]),
   ('balance-h1-2010',[198],[199,200,201,202,203])]},
 {'key':'property-net','page':130,'unit_order':2,'headers':[[3],[4],[7],[5,6],[8]],'date_orders':[],
  'rows':[('net-h1-2010',[204],[205,206,207,208,209]),('net-2009',[210],[211,212,213,214,215]),
          ('net-h1-2009',[216],[217,218,219,220,221])]},
 {'key':'intangible-balance','page':131,'unit_order':3,'headers':[[4],[5]],'date_orders':[4,5],
  'rows':[('goodwill',[6],[7,8]),('internal-software',[9,10],[11,12]),
   ('third-party-software',[13,14],[16,18]),('third-party-other',[15],[17,19]),
   ('third-party-total',[],[20,21]),('wip',[32],[22,23]),('gross',[],[24,25]),
   ('amortisation',[33],[26,28]),('impairment',[34],[27,29]),('net',[],[30,31])]},
 {'key':'intangible-cost','page':132,'unit_order':2,'headers':[[3],[11],[14],[12,13],[15]],'date_orders':[],
  'rows':[('balance-2008',[5],[16,17,18,19,20]),
   *block(['internal-h1-2009','acquired-h1-2009','transfers-h1-2009','exchange-h1-2009'],range(7,11),[21,25,29,33,37]),
   ('balance-h1-2009',[41],[48,49,50,51,52]),
   *block(['internal-h2-2009','acquired-h2-2009','disposals-a','transfers-h2-2009','exchange-h2-2009'],range(43,48),[53,58,63,68,73]),
   ('balance-2009',[78],[86,87,88,89,90]),
   *block(['internal-h1-2010','acquired-b','disposals-h1-2010','transfers-h1-2010','exchange-h1-2010'],[80,82,83,84,85],[91,96,101,106,111]),
   ('balance-h1-2010',[116],[117,118,119,120,121])]},
 {'key':'intangible-amortisation','page':132,'unit_order':2,'headers':[[3],[11],[14],[12,13],[15]],'date_orders':[],
  'rows':[
   *block(['balance-2008','charge-h1-2009','exchange-h1-2009'],range(123,126),[126,129,132,135,138]),
   *block(['balance-h1-2009','charge-h2-2009','disposals-h2-2009','exchange-h2-2009'],range(141,145),[145,149,153,157,161]),
   *block(['balance-2009','charge-h1-2010','disposals-h1-2010','transfers-h1-2010','exchange-h1-2010'],range(165,170),[170,175,180,185,190]),
   ('balance-h1-2010',[195],[196,197,198,199,200])]},
 {'key':'intangible-impairment','page':132,'unit_order':2,'headers':[[3],[11],[14],[12,13],[15]],'date_orders':[],
  'rows':[
   *block(['balance-2008','loss-c-h1-2009','exchange-h1-2009'],range(202,205),[205,208,211,214,217]),
   *block(['balance-h1-2009','loss-c-h2-2009','exchange-h2-2009'],range(220,223),[223,226,229,232,235]),
   *block(['balance-2009','exchange-h1-2010'],range(238,240),[240,242,244,246,248]),
   ('balance-h1-2010',[250],[251,252,253,254,255])]},
 {'key':'intangible-net','page':132,'unit_order':2,'headers':[[3],[11],[14],[12,13],[15]],'date_orders':[],
  'rows':[('net-h1-2010',[256],[257,258,259,260,261]),('net-2009',[262],[263,264,265,266,267]),
          ('net-h1-2009',[268],[269,270,271,272,273])]}
]

DISTINCTIONS = {'historical_report_assertions_only': True, 'dash_status': 'PRINTED_DASH_UNKNOWN_NOT_ZERO', 'balance_dates': ['2010-06-30', '2009-12-31'], 'movement_balance_dates': ['2008-12-31', '2009-06-30', '2009-12-31', '2010-06-30'], 'movement_periods': 'BETWEEN_PRINTED_BALANCE_DATES', 'property_cost_and_depreciation_sections_distinct': True, 'property_2010_cost_row_label': 'Depreciation of the year', 'property_cost_row_relabelled_as_acquisitions': False, 'property_cost_row_values': [3061, 9631, None, 70298, 82990], 'property_label_section_tension': 'PRESERVE_PRINTED_COST_SECTION_AND_DEPRECIATION_LABEL_UNRESOLVED', 'property_transfer_footnotes': {'a': {'cost_thousands': 5224, 'accumulated_depreciation_thousands': 1193, 'period': '2008-12-31_TO_2009-06-30'}, 'b': {'cost_thousands': 693, 'accumulated_depreciation_thousands': 533, 'period': '2009-06-30_TO_2009-12-31'}, 'c': {'cost_thousands': 1692, 'accumulated_depreciation_thousands': 521, 'period': '2009-12-31_TO_2010-06-30'}}, 'property_transfer_footnote_scope': 'INCLUDED_DISCONTINUED_BRANCHES_WITH_BOTH_OTHER_ASSETS_AND_NON_CURRENT_ASSETS_HELD_FOR_SALE_WORDING', 'property_transfers_prove_completed_sales': False, 'internal_and_third_party_software_distinct': True, 'internal_software_scope': 'GROUP_COSTS_OF_DEVELOPING_AND_IMPLEMENTING_SOFTWARE_APPLICATIONS', 'future_software_economic_benefits': 'REPORT_ASSERTION_NOT_INDEPENDENTLY_VERIFIED', 'internal_software_reference': 'NOTE_2_13_RETAINED_NOT_RESOLVED_BY_THIS_NOTE', 'cost_amortisation_impairment_and_net_distinct': True, 'es_data_liquidation_goodwill_thousands': 3691, 'es_data_liquidation_recognition': 'AGAINST_INCOME_STATEMENT_AS_REPORTED', 'aman_goodwill_footnote_thousands': 13326, 'goodwill_acquired_2010_row_thousands': 13475, 'aman_footnote_equals_whole_acquisition_row': False, 'aman_reference': 'NOTE_45_RETAINED_NOT_RESOLVED_BY_THIS_NOTE', 'impairment_loss_attribution': 'CONCORDIA_GOODWILL', 'impairment_loss_attributed_rows': ['loss-c-h1-2009', 'loss-c-h2-2009'], 'net_assets_are_realizable_value_inferred': False, 'note24_on_page129': 'RETAINED_PRIOR_SEMANTICS_AND_CONTEXT_NOT_NEW_NOTE25_COVERAGE', 'current_law_or_standard_verified': False, 'source_authority_or_incorporation_resolved': False}
