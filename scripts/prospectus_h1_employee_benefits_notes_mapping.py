"""Original employee-benefit conditions and printed table associations."""

SPECS = [
 ('pension-cohort',108,13,19,'Retain the ACT pension, disability and widows pension commitment, service-linked negotiated salary basis and 31 March 2008 hiring boundary. Later hires fall under Portuguese Social Security as reported; no present unconditional entitlement is inferred.'),
 ('fund-scope',108,20,24,'Retain the 30 December 1987 fund, reported authorisation for expanded pension and health-care coverage, 2009 death allowance and named Portuguese fund manager.'),
 ('actuarial-assumptions',108,25,49,'Retain dated financial assumptions, sex-specific mortality tables and the literal Project Unit Credit Method. These are historical report inputs, not current valuation defaults.'),
 ('covered-persons',109,1,12,'Preserve covered employees and pensioners as persons at the two June dates, distinct from all Group employees and from average full-time-equivalent staff.'),
 ('recognised-balance',109,13,52,'Keep signed pension and health-care obligations, plan assets, amounts payable to the fund, unrecognised actuarial losses and recognised accounting assets distinct. The positive recognised asset does not establish a funding surplus.'),
 ('asset-recoverability',109,53,57,'Retain other-assets inclusion and Notes28/2.15 references. Recoverability is assessed separately for each plan at each balance date using expected reductions in future contributions; no unconditional recovery or legal title follows.'),
 ('obligation-movement',110,1,85,'Preserve pension, health-care and total columns at both dates, signed movements and unknown dashes. The table says beginning/end of period but does not itself print duration.'),
 ('sams-sensitivity',110,86,88,'Preserve the literal increase of1% in contributions to SAMS and liability/cost sensitivities17.3/16.4 and1.1/1.2million. Do not silently replace percent with percentage points or a realised change.'),
 ('plan-assets-movement',110,89,117,'Preserve actual return, contributions, benefits and exchange movements for six months2010 versus year2009. Actual return is distinct from expected return used in benefit expense.'),
 ('plan-assets-allocation',110,118,136,'Preserve shares, fixed-income securities, real estate and other plan assets with both balance dates.'),
 ('group-assets-intro',110,137,138,'The next-page table is the included Group-rented property and Group-issued securities, not all plan assets.'),
 ('group-assets',111,1,15,'Preserve Group-related shares, securities and property as an included subset; do not double-count with all plan assets.'),
 ('bes-share-count',111,16,17,'Retain10.9/10.3million BES shares held by the pension fund at the respective dates; share count is not a monetary balance.'),
 ('actuarial-loss-movement',111,18,50,'Preserve unrecognised actuarial-loss movement and within/outside-corridor subsets, signed gains/losses and six-month/year comparison. Corridor categories do not themselves establish beneficiary rights.'),
 ('funding-movement',111,51,85,'Retain negative underfunding and positive overfunding, expected asset return and signed charges; distinguish these from recognised accounting assets.'),
 ('benefit-cost-intro',111,86,86,'Retain the introduction to the next-page net periodic benefit cost.'),
 ('benefit-cost',112,1,29,'Keep service cost, interest, negative expected return and amortisation with six/year/six-month periods; totals are not cash benefits paid.'),
 ('recognised-asset-movement',112,30,52,'Preserve recognised accounting asset movement with cost deductions, contributions and other amounts for six months2010/year2009.'),
 ('benefit-history',112,53,109,'Preserve all five printed dates, signed pension/health-care obligations, assets, funding and separate experience adjustments. The June2010 observation is not a full-year result.'),
 ('siba-rights',112,110,116,'Retain SIBA sale of ordinary shares with deferred settlement stated as two to four years, mandatory holding, and subsequent market sale, retention plus payment of debt, or sell-back at acquisition cost.'),
 ('siba-characteristics',113,1,29,'Retain two2004blocks, expected maturities, grant/current shares, euro strike prices, unknown dashes, coverage percentage and2006capital-increase share-premium inclusion.'),
 ('siba-share-movement',113,30,60,'Keep share counts distinct from thousand-euro amounts in six-month2010/year2009 movements. Shares sold include post-sell-back market sales and employee payments at maturity.'),
 ('siba-initial-valuation',113,61,78,'Retain initial maturities24/60months, volatility, block-specific risk-free rates, dividend yield and grant fair value. Preserve the tension with the two-to-four-year narrative rather than correcting either.'),
 ('siba-costs',113,79,93,'Retain181/362/181thousand costs with six/year/six-month durations and Note11 reference; costs are not proof of individual payment.'),
 ('siba-recognition',114,1,2,'Retain staff-cost recognition against other reserves and the Note2.15 reference.'),
 ('pprv-rights',114,3,10,'Retain plan label2008/2010, shareholder-meeting date and the cash appreciation right. The report expressly denies stock, stock-option and shareholder-equivalent rights.'),
 ('pprv-initial-valuation',114,11,34,'Retain initial versus post2009capital-increase columns, printed dates2008–2011, rights and reference prices, rates, initial fair value and dilution footnote. Unprinted right-column positions remain unknown blanks, not copied initial values.'),
 ('pprv-recognition',114,35,40,'Retain initial12902thousand staff-cost recognition over three years and2150thousand each June period. Preserve the report wording financial assets at fair value through profit or loss for subsequent changes without resolving its tension with the liability description.'),
 ('pprv-liability',114,41,42,'Retain monthly remeasurement and liability4/394thousand at June2010/December2009; do not equate these balances with initial plan value or staff expense.'),
 ('long-service-rights',115,1,5,'Retain qualifying service, actual monthly remuneration when due and proportionate early-retirement/disability premiums; the note does not supply every eligibility fact.'),
 ('long-service-amounts',115,6,9,'Keep liabilities29275/28602thousand at June/December dates separate from2433/1612thousand six-month costs at June2010/2009; preserve Note36 reference.'),
 ('long-service-assumptions',115,10,11,'Pension actuarial assumptions apply only when applicable. The remainder of page115 is prior Note13 context, not new Note12 coverage.')
]


def block(keys, labels, starts):
    return [(key,[label],[start+i for start in starts]) for i,(key,label) in enumerate(zip(keys,labels))]


def table(key,page,unit,headers,dates,period,rows,unit_order=None,date_orders=(),**extra):
    return dict(key=key,page=page,unit=unit,headers=headers,dates=dates,period_months=period,
                rows=rows,unit_order=unit_order,date_orders=list(date_orders),**extra)


BALANCE = ['2010-06-30','2009-12-31']
JUNES = ['2010-06-30','2009-06-30']
THREE = ['2010-06-30','2009-12-31','2009-06-30']
TABLES = [
 table('financial-assumptions',108,'PERCENT',[[27],[28]],BALANCE,None,
       block(['salary','pension','expected-return','discount'],range(38,42),[29,33]),date_orders=[27,28]),
 table('demographic-assumptions',108,'PRINTED_TEXT',[[26]],None,None,[
       ('men',[44],[47]),('women',[45],[48]),('method',[46],[49])],columns=['SHARED_PRINTED_VALUE']),
 table('covered-persons',109,'PERSONS',[[2],[3]],JUNES,None,
       [('employees',[4],[5,6]),('pensioners',[7],[8,9]),('total',[10],[11,12])],1,[2,3]),
 table('recognised-balance',109,'EUR_THOUSANDS',[[16],[17]],BALANCE,None,[
       ('pension-pensioners',[20],[22,25]),('pension-employees',[21],[23,26]),('pension-total',[],[24,27]),
       ('health-pensioners',[50],[28,31]),('health-employees',[51],[29,32]),('health-total',[],[30,33]),
       ('total-obligation',[52],[34,35]),('plan-assets',[37],[38,39]),('funding',[40],[41,42]),
       ('unrecognised-losses',[43],[44,45]),('recognised-asset',[46],[47,48])],15,[16,17]),
 table('obligation-movement',110,'EUR_THOUSANDS',[[4,5],[17,18],[20],[21,22],[23,24],[25]],
       [*([BALANCE[0]]*3),*([BALANCE[1]]*3)],None,[
       ('beginning',[6],list(range(26,32))),
       *block(['service','interest','participants'],[7,8,9],[32,35,38,41,44,47]),
       *block(['assumptions','experience','pensions','group-benefits','exchange'],range(11,16),[50,55,60,65,70,75]),
       ('ending',[16],list(range(80,86)))],2,[3,19],
       columns=['PENSION_2010','HEALTH_2010','TOTAL_2010','PENSION_2009','HEALTH_2009','TOTAL_2009']),
 table('plan-assets-movement',110,'EUR_THOUSANDS',[[92,93,95],[94,96]],BALANCE,[6,12],[
       ('beginning',[97],[98,99]),
       *block(['actual-return','group-contributions','participants','pensions','exchange'],range(100,105),[105,110]),
       ('ending',[117],[115,116])],91,[95,96]),
 table('plan-assets-allocation',110,'EUR_THOUSANDS',[[119],[126]],BALANCE,None,[
       *block(['shares','bonds','property','other'],range(120,124),[127,131]),
       ('total',[124],[135,136])],125,[119,126]),
 table('group-assets',111,'EUR_THOUSANDS',[[2],[3]],BALANCE,None,[
       *block(['shares','bonds','property'],range(4,7),[7,10]),('total',[13],[14,15])],1,[2,3]),
 table('actuarial-loss-movement',111,'EUR_THOUSANDS',[[20,21,23],[22,24]],BALANCE,[6,12],[
       ('beginning',[25],[26,27]),
       *block(['assumptions','experience','amortisation','other'],range(29,33),[33,37]),
       ('ending',[41],[42,43]),('within-corridor',[45],[47,49]),('outside-corridor',[46],[48,50])],19,[23,24]),
 table('funding-movement',111,'EUR_THOUSANDS',[[54,55,57],[56,58]],BALANCE,[6,12],[
       ('beginning',[53],[59,60]),('obligation-adjustment',[61],[69,71]),('asset-adjustment',[62],[70,72]),
       *block(['service','interest','expected-return','other','contributions'],range(64,69),[73,78]),
       ('ending',[83],[84,85])],52,[57,58]),
 table('benefit-cost',112,'EUR_THOUSANDS',[[1,2,3],[6,8],[5,7,9]],THREE,[6,12,6],[
       *block(['service','interest','expected-return','amortisation'],range(10,14),[14,18,22]),
       ('total',[26],[27,28,29])],4,[3,8,9]),
 table('recognised-asset-movement',112,'EUR_THOUSANDS',[[33,34,36],[35,37]],BALANCE,[6,12],[
       ('beginning',[38],[39,40]),*block(['cost','contributions','other'],range(41,44),[44,47]),
       ('ending',[50],[51,52])],32,[36,37]),
 table('benefit-history',112,'EUR_THOUSANDS',[[56],[57],[107],[108],[109]],
       ['2010-06-30','2009-12-31','2008-12-31','2007-12-31','2006-12-31'],None,[
       ('pension',[105],[58,60,62,64,66]),('health',[106],[59,61,63,65,67]),('total',[],list(range(68,73))),
       ('assets',[73],list(range(74,79))),('funding',[79],list(range(80,85))),
       ('pension-experience',[86],[88,90,92,94,96]),('health-experience',[87],[89,91,93,95,97]),
       ('assets-experience',[98],list(range(99,104)))],55,[56,57,107,108,109]),
 table('siba-characteristics',113,'MIXED',[[2,3],[8,9,10],[19,20],[15,16,18],[23,24]],None,None,[
       ('block1',[5],[11,13,21,25,27]),('block2',[6],[12,14,22,26,28])],
       columns=['MATURITY','GRANT_SHARES','STRIKE','CURRENT_SHARES','COVERAGE'],
       column_units=['PRINTED_TEXT','SHARES','EUR','SHARES','PERCENT']),
 table('siba-share-movement',113,'MIXED',[[33,34],[36,37],[40,41],[38,39]],
       ['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],[6,6,12,12],[
       ('beginning',[42],[45,47,49,51]),('sold',[44],[46,48,50,52]),('ending',[53],[54,55,56,57])],
       date_orders=[32,35],columns=['SHARES_2010','AMOUNT_2010','SHARES_2009','AMOUNT_2009'],
       column_units=['SHARES','EUR_THOUSANDS','SHARES','EUR_THOUSANDS']),
 table('siba-initial-valuation',113,'MIXED',[[62]],None,None,[
       ('maturity1',[64],[71]),('maturity2',[65],[72]),('volatility',[66],[73]),
       ('riskfree1',[68],[74]),('riskfree2',[69],[75]),('dividend',[70],[76]),('fair-value',[77],[78])],
       columns=['PLAN_2004'],row_units=['MONTHS','MONTHS','PERCENT','PERCENT','PERCENT','PERCENT','EUR_THOUSANDS']),
 table('siba-costs',113,'EUR_THOUSANDS',[[81,82,83],[88,90],[87,89,92]],THREE,[6,12,6],
       [('cost',[84],[85,91,93])],86,[83,90,92]),
 table('pprv-initial-valuation',114,'MIXED',[[13,14],[15,16]],None,None,[
       ('initial-date',[17],[18,None]),('final-date',[19],[20,None]),('rights',[21],[22,23]),
       ('price',[24],[25,26]),('interest',[27],[28,None]),('volatility',[29],[30,None]),
       ('fair-value',[31],[32,None])],columns=['INITIAL','AFTER_2009_CAPITAL_INCREASE'],
       row_units=['PRINTED_TEXT','PRINTED_TEXT','RIGHTS','EUR','PERCENT','PERCENT','EUR_THOUSANDS'])
]

DISTINCTIONS = {
 'historical_report_assertions_only':True,
 'dash_status':'PRINTED_DASH_UNKNOWN_NOT_ZERO',
 'blank_status':'UNPRINTED_UNKNOWN_NOT_COPIED_FROM_OTHER_COLUMN',
 'pension_hiring_cutoff':'2008-03-31','later_hires_scheme':'PORTUGUESE_SOCIAL_SECURITY_AS_REPORTED',
 'actuarial_method_literal':'Project Unit Credit Method',
 'mortality':{'men':'TV 73/77 (adjusted)','women':'TV 88/90'},
 'demographic_values_shared_across_dated_columns':'PRINTED_SPANNING_VALUES_NO_SEPARATE_DATE_VALUES',
 'assumptions_are_current_valuation_defaults':False,
 'covered_persons_equal_all_group_employees':False,
 'positive_recognised_asset_means_funding_surplus':False,
 'asset_recoverability':'EACH_PLAN_EACH_BALANCE_DATE_EXPECTED_REDUCTION_IN_FUTURE_CONTRIBUTIONS',
 'obligation_movement_duration':'UNPRINTED_NOT_INFERRED',
 'sams_shock_literal':'increase of 1%','sams_percentage_point_interpretation_inferred':False,
 'sams_liability_sensitivity_millions':['17.3','16.4'],'sams_cost_sensitivity_millions':['1.1','1.2'],
 'actual_and_expected_returns_distinct':True,
 'actual_asset_return_2010_thousands':-44392,'expected_asset_return_2010_thousands':57247,
 'group_assets_are_included_subset':True,'bes_shares_held_millions':['10.9','10.3'],
 'funding_balance_and_recognised_asset_distinct':True,
 'corridor_within_and_outside_are_subsets':True,
 'june_history_is_full_year':False,
 'siba_deferred_settlement_years_literal':'two to four years',
 'siba_initial_maturities_months':[24,60],
 'siba_duration_tension':'PRESERVE_BOTH_UNRESOLVED',
 'siba_requires_holding_during_deferral':True,
 'siba_after_holding_choices':['MARKET_SALE','RETAIN_AND_PAY_DEBT','SELL_BACK_AT_ACQUISITION_COST'],
 'siba_shares_include_2006_share_premium_capital_increase':True,
 'siba_sold_includes_employee_payments_at_maturity':True,
 'siba_staff_cost_recognition':'AGAINST_OTHER_RESERVES',
 'pprv_label_literal':'PPRV – 2008/2010','pprv_reference_dates':['2008-06-02','2011-06-02'],
 'pprv_label_date_tension':'PRESERVE_BOTH_UNRESOLVED',
 'pprv_right':'FUTURE_CASH_PAYMENT_EQUIVALENT_TO_SHARE_APPRECIATION',
 'pprv_grants_shares_options_or_shareholder_rights':False,
 'pprv_after_capital_increase_blanks_inherit_initial_values':False,
 'pprv_dilution_adjustment_preserved':True,
 'pprv_initial_fair_value_thousands':12902,'pprv_cost_recognition_years':3,
 'pprv_june_costs_thousands':[2150,2150],
 'pprv_subsequent_changes_literal':'profit/loss from financial assets at fair value through profit or loss',
 'pprv_asset_liability_wording_tension':'PRESERVE_SOURCE_WORDING_UNRESOLVED',
 'pprv_liability_thousands':[4,394],'pprv_remeasurement':'END_OF_EACH_MONTH',
 'long_service_premium_basis':'EFFECTIVE_MONTHLY_REMUNERATION_AT_DUE_DATE',
 'long_service_early_retirement_disability':'PROPORTIONAL_TO_NEXT_PAYMENT_IF_REMAINED_IN_SERVICE',
 'long_service_liabilities_thousands':[29275,28602],'long_service_six_month_costs_thousands':[2433,1612],
 'long_service_pension_assumptions':'ONLY_WHEN_APPLICABLE',
 'cross_references':'RETAINED_NOT_AUTOMATICALLY_RESOLVED_BY_THIS_NOTE',
 'individual_entitlement_or_payment_proved':False,
 'adjacent_notes_11_13':'RETAINED_PRIOR_SEMANTICS_AND_CONTEXT',
 'current_law_or_standard_verified':False,'source_authority_or_incorporation_resolved':False
}
