"""Inspected annual income tables; all numeric cells retain their original tokens."""
from copy import deepcopy
import re
from scripts.prospectus_annual_basis_reading import refs, section

PROFILE='bes-annual2010-statements-income-notes.v6'
FIELD='income_notes_and_group_context'
NEW_PAGES=(97,120,121,122)

# Rows specify displayed label and cell occurrence IDs, never inferred adjacency.
SPECS={
 'interest': (120, '0-22', [
    ('loan-income','24',list(range(25,31))),('fvpl-income','65',list(range(31,37))),
    ('bank-income','37',list(range(38,44))),('afs-income','44',list(range(45,51))),
    ('htm-income','51',list(range(52,58))),('derivative-income','66',list(range(58,64))),
    ('other-income','67',list(range(69,75))),('income-total','23',list(range(75,81))),
    ('debt-expense','82',list(range(83,89))),('customer-expense','89',list(range(90,96))),
    ('bank-expense','96',list(range(97,103))),('subordinated-expense','103',list(range(104,110))),
    ('derivative-expense','130',list(range(110,116))),('expense-total','81',list(range(117,123))),
    ('net-interest',None,list(range(124,130)))]),
 'fees': (120,'138-143',[
    ('bank-income','145',[146,147]),('guarantee-income','148',[149,150]),('securities-income','151',[152,153]),
    ('commitment-income','154',[155,156]),('other-income','157',[159,160]),('income-total','144',[161,162]),
    ('bank-expense','164',[165,166]),('securities-expense','167',[168,169]),('guarantee-expense','170',[171,172]),
    ('other-expense','173',[174,175]),('expense-total','163',[177,178]),('net-fees',None,[180,181])]),
 'fvpl': (121,'0-10',[
    ('trading-government','11,228,12',list(range(13,19))),('trading-other-bonds','20',list(range(21,27))),
    ('trading-shares','28',list(range(29,35))),('trading-other','36',list(range(37,43))),('trading-total','11',list(range(44,50))),
    ('derivative-fx','50,52',list(range(53,59))),('derivative-interest','60',list(range(60,66))),
    ('derivative-equity','67',list(range(68,74))),('derivative-credit','75',list(range(76,82))),
    ('derivative-other','83',list(range(84,90))),('derivative-total','50',list(range(90,96))),
    ('designated-government','96-97,99,101',list(range(102,108))),('designated-other-bonds','109',list(range(110,116))),
    ('designated-shares','117',list(range(118,124))),('designated-other','125',list(range(126,132))),
    ('designated-securities-total','97',list(range(133,139))),
    ('other-assets-banks','139,141',list(range(142,148))),('other-assets-loans','149',list(range(150,156))),
    ('other-assets-total','139',list(range(157,163))),
    ('liabilities-banks','163,165',[166,167,168,169,170,178]),('liabilities-customers','172',[173,174,175,176,177,179]),
    ('liabilities-debt','181',list(range(182,188))),('liabilities-subordinated','189',list(range(190,196))),
    ('liabilities-total','163',list(range(197,203))),('designated-total','96',list(range(204,210))),
    ('fvpl-total',None,list(range(210,216)))]),
 'afs': (122,'0-10',[
    ('government-bonds','12-13',list(range(14,20))),('other-bonds','20',list(range(21,27))),
    ('shares','27',list(range(28,34))),('other','34',list(range(35,41))),('afs-total',None,list(range(42,48)))]),
 'fx': (122,'56-58,61,63,65-66,60,67-69',[
    ('translation','64',list(range(70,76))),('fx-total',None,list(range(76,82)))]),
 'other': (122,'84-86,88-90',[
    ('technology','91',[92,93]),('repurchase','94',[95,96]),('credit','97',[98,99]),('advisory','100',[101,102]),
    ('taxes','103',[104,105]),('guarantee-fund','106',[107,108]),('donations','109',[110,111]),
    ('customer-funds','112',[113,114]),('other','115',[116,117]),('operating-total',None,[119,120])]),
}


def reading(graph):
    units={u['id']:u for u in graph['units']}
    make=lambda name,meaning,*parts:section(units,name,meaning,refs(*parts))
    def witnesses(page,numbers):
        return section(units,'witness',{},refs((page,numbers)))['source']
    def cell(page,n):
        u=units[f'bes-2010-en:p{page}:l{n}']
        # Four inspected mixed/whitespace occurrences end with the numeric token.
        token=u['raw'].strip()
        if page==121 and n==60:
            token=token.split()[-1]
        assert re.fullmatch(r'-|\(?\d{1,3}(?:,\d{3})*\)?|\d+',token),u['id']
        start=u['raw'].rfind(token)
        value=None if token=='-' else int(token.replace(',','').replace('(','-').replace(')',''))
        return {'unit':u['id'],'page':page,'source_sha256':u['source_sha256'],'start':start,'end':start+len(token),
                'quote':token,'value':value,'status':'PRINTED_DASH' if value is None else 'SOURCE_INTEGER',
                'amount_unit':'EUR_THOUSAND'}
    tables=[]
    for name,(page,headers,rows) in SPECS.items():
        categories=['AMORTISED_COST_AND_AFS','FVPL','TOTAL'] if name=='interest' else ['GAINS','LOSSES','NET'] if name in ('fvpl','afs','fx') else ['AMOUNT']
        columns=[{'year':year,'category':category} for year in (2010,2009) for category in categories]
        tables.append({'id':name,'note':str({'interest':5,'fees':6,'fvpl':7,'afs':8,'fx':9,'other':10}[name]),
            'headers':witnesses(page,headers),'columns':columns,'amount_unit':'EUR_THOUSAND',
            'attribution':'ISSUER_ANNUAL_REPORT_2010','independently_verified':False,
            'dash_arithmetic':'CONDITIONAL_ZERO_FOR_RECONCILIATION_ONLY_ORIGINAL_VALUE_REMAINS_UNKNOWN',
            'rows':[{'id':key,'labels':witnesses(page,label) if label else [],
                     'label_status':'DISPLAYED_LABEL' if label else 'UNLABELLED_PRINTED_TOTAL_LOCAL_NAME',
                     'cells':[cell(page,n) for n in indices]} for key,label,indices in rows]})
    narratives=[
        make('group-introduction',{
            'note':'1_INTRODUCTION_ONLY','report_date':'2010-12-31','entity':'BANCO_ESPIRITO_SANTO_SA_GROUP',
            'headquarters':'AVENIDA_DA_LIBERDADE_195_LISBON_PORTUGAL',
            'authorisation':'ISSUER_REPORTS_PORTUGUESE_AND_RELEVANT_FOREIGN_AUTHORITY_AUTHORISATION',
            'authorisation_independently_verified':False,'foundation':'LAST_QUARTER_19TH_CENTURY',
            'commercial_operations_start':1937,'merger':'BANCO_ESPIRITO_SANTO_AND_BANCO_COMERCIAL_DE_LISBOA',
            'former_name':'BANCO_ESPIRITO_SANTO_E_COMERCIAL_DE_LISBOA','name_change_deed':'1999-07-06',
            'bank_listing':'NYSE_EURONEXT_LISBON','bes_finance_preference_shares_thousand':600,
            'bes_finance_listing':'LUXEMBOURG_STOCK_EXCHANGE','preference_count_is_investor_holding':False,
            'standalone_accounts_supplied':False,'espirito_santo_group_member_since':1992,
            'consolidating_parents':['BESPAR_SGPS_SA_LISBON','ESPIRITO_SANTO_FINANCIAL_GROUP_SA_LUXEMBOURG'],
            'bespar_address':'RUA_DE_SAO_BERNARDO_62_LISBON',
            'portugal_branches':{'2010':828,'2009':799},
            'international_branches':['LONDON','SPAIN','NEW_YORK','NASSAU','CAYMAN_ISLANDS','CAPE_VERDE'],
            'madeira_free_zone_branch':True,'overseas_representatives':{'2010':10,'2009':12},
            'following_table_holding_operator':'GE','following_table_holding_percent':20,
            'following_table_additional_condition':'CONTROL_OR_SIGNIFICANT_INFLUENCE_AND_INCLUDED_IN_CONSOLIDATION',
            'following_group_tables_interpreted':False,
        },(97,'0-3,19-20,14-17,4-11')),
        make('interest-explanations',{
            'note':'5','unwind_discount_eur_thousand':{'2010':24363,'2009':18626},
            'unwind_scope':'IMPAIRMENT_OF_OVERDUE_CUSTOMER_LOANS','loan_reference':'Note 21',
            'derivative_interest_includes':['HEDGING_DERIVATIVES','RISK_MANAGEMENT_FOR_DESIGNATED_FVPL_ASSETS_AND_LIABILITIES'],
            'all_risk_management_derivatives_qualify_as_hedges':False,
            'policy_references':['Note 2.4','Note 2.18','Note 2.5','Note 2.6','Note 2.8'],
        },(120,'131-135')),
        make('fvpl-explanations',{
            'note':'7','footnote_scope':'FAIR_VALUE_CHANGES_OF_HEDGED_ASSETS_LIABILITIES_OR_FAIR_VALUE_OPTION',
            'own_credit_effect_eur_million':{'2010':'82.7','2009':'-41'},
            'own_credit_effect_is_entire_fvpl_total':False,
            'initial_fair_value_best_evidence':'TRANSACTION_PRICE',
            'day_one_difference':'VALUATION_DIFFERENCE_FROM_TRANSACTION_PRICE_IN_PARTICULAR_CIRCUMSTANCES_INCLUDING_BUILT_IN_FEE',
            'day_one_recognition_conditions':['FAIR_VALUE_AT_INCEPTION_AND_SUBSEQUENT_MEASUREMENT_USES_ONLY_OBSERVABLE_MARKET_DATA','REFLECTS_GROUP_WHOLESALE_MARKET_ACCESS'],
            'day_one_products':['DERIVATIVES','FOREIGN_EXCHANGE_PRODUCTS'],
            'approximate_day_one_gain_eur_thousand':{'2010':10446,'2009':9006},
        },(121,'216-226')),
        make('afs-explanations',{
            'note':'8','sale_route':'MARKET_PRICES_THROUGH_STOCK_EXCHANGE',
            'ordinary_shares_sold_million':{'2010':{'EDP':'43.2','PT':'11.7','BRADESCO':'52.5'},'2009':{'EDP':'111.6','PT':'69.4','BRADESCO':'23.0'}},
            'specified_sale_net_gains_eur_million':{'2010':'287.6','2009':'52.1'},
            'specified_sale_gains_equal_entire_afs_net_gains':False,
            '2010_dividend_income_eur_thousand':193292,
            'named_dividends_eur_million':{'2010':{'PT':'129.1','BRADESCO':'32.4','EDP':'17.2'},'2009':{'PT':'34.3','BRADESCO':'27.7','EDP':'15.6'}},
            'named_dividends_exhaustive':False,'dividends_added_to_afs_net_gains':False,'related_party_reference':'Note 41',
        },(122,'48-55')),
        make('fx-explanations',{
            'note':'9','scope':'TRANSLATION_OF_MONETARY_ASSETS_AND_LIABILITIES',
            'rate_date':'BALANCE_SHEET_DATE','policy_reference':'Note 2.3',
        },(122,'82-83')),
        make('other-income-reference',{'note':'10','repurchased_instruments':'GROUP_DEBT_SECURITIES','reference':'Note 35'},(122,'94')),
    ]
    return {'version':'bes-annual2010-income-context.v1','tables':tables,'narratives':narratives,
        'all_notes_interpreted':False,'independent_legal_or_financial_acceptance':False,
        'scope':'NOTE1_INTRODUCTION_AND_NOTES5_TO10_ONLY','source_authenticity':'NOT_ESTABLISHED'}


def combine(old,graph):
    result=deepcopy(old)
    assert FIELD not in result
    result[FIELD]=reading(graph)
    result['source_context']['source_pages']=sorted(set(result['source_context']['source_pages'])|set(NEW_PAGES))
    result['source_context']['scope']+='; Note1 introduction and income Notes5–10 supplied; group tables and remaining numerical notes incomplete'
    assert result['source_context']['all_notes_read'] is False
    return result
