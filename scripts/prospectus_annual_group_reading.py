"""Finite inspected Note1 mapping; never infer control from economic interest."""
from copy import deepcopy
from decimal import Decimal
import re
from scripts.prospectus_annual_basis_reading import refs, section

PROFILE='bes-annual2010-statements-group-disclosures.v7'
FIELD='group_entities_and_transactions'
NEW_PAGES=(98,99,100,101,102)
# Displayed company-name occurrences, including names displaced in native order.
ENTITY_NAMES={
 98:[227,13,21,28,35,42,49,56,63,70,77,84,91,98,105,112,119,126,133,140,147,154,161,168,175,182,189,196,203,211,218,228,235,242,249,256,263,270,277,284,291,298,305,312,319,326,333,340,347],
 99:[379,376,19,26,33,40,47,54,68,69,76,83,102,103,104,151,152,123,130,137,144,153,160,167,174,181,188,195,202,209,216,224,230,237,245,251,258,267,268,277,282,287,292,304,311,318,325,332,339,346,353,360,367],
 100:[9,16,23,30,37,39,55,61,68,75,82,89,96,103,110,117,124,132,138,145,152,159,166,173,180,187,194,201,214,222,221,229,236,250,249,257,264,271,278,285,292,299,306],
}
SPE_NAMES=[326,332,338,344,350,356,362,368,374,380,387,392,398,404,410]
GROUP_HEADINGS={99:{379,268,282,292},100:{9,39,110,132,194,221,249}}
AMOUNT_COLUMNS=['ACQUISITION_COST','OTHER_INVESTMENTS','ACQUISITION_TOTAL','DISPOSAL_VALUE','OTHER_REIMBURSEMENTS','DISPOSAL_TOTAL','GAINS_LOSSES']
TRANSACTIONS={
 2010:[('aman',20,21,'SUBSIDIARIES'),('africa',28,29,'SUBSIDIARIES'),('cape-verde',36,37,'SUBSIDIARIES'),('gespastor',44,45,'SUBSIDIARIES'),('activos',52,53,'SUBSIDIARIES'),('kutaya',60,61,'SUBSIDIARIES'),('execution',68,69,'SUBSIDIARIES'),('subsidiary-total',None,77,'SUBSIDIARY_TOTAL'),
 ('ascendi',85,86,'ASSOCIATES'),('scutvias',93,94,'ASSOCIATES'),('auvisa',101,102,'ASSOCIATES'),('unicre',109,110,'ASSOCIATES'),('nanium',117,118,'ASSOCIATES'),('salgar',125,126,'ASSOCIATES'),('venezie',133,134,'ASSOCIATES'),('tradecom',141,142,'ASSOCIATES'),('tlci',149,150,'ASSOCIATES'),('ydreams',157,158,'ASSOCIATES'),('beira',165,166,'ASSOCIATES'),('grande-porto',173,174,'ASSOCIATES'),('prata',181,182,'ASSOCIATES'),('empark',189,190,'ASSOCIATES'),('neumaticos',197,198,'ASSOCIATES'),('aquaspy',205,206,'ASSOCIATES'),('concessoes',213,214,'ASSOCIATES'),('outros',229,221,'ASSOCIATES'),('associate-total',None,230,'ASSOCIATE_TOTAL'),('overall-total',None,238,'OVERALL_TOTAL')],
 2009:[('morumbi',261,262,'SUBSIDIARIES'),('esdata',269,270,'SUBSIDIARIES'),('esfc',277,278,'SUBSIDIARIES'),('angola',285,286,'SUBSIDIARIES'),('subsidiary-total',None,294,'SUBSIDIARY_TOTAL'),('empark',302,303,'ASSOCIATES'),('synergy',310,311,'ASSOCIATES'),('ydreams',318,319,'ASSOCIATES'),('venezie',326,327,'ASSOCIATES'),('aquaspy',334,335,'ASSOCIATES'),('sousacamp',342,343,'ASSOCIATES'),('nutrigreen',350,351,'ASSOCIATES'),('outsystems',358,359,'ASSOCIATES'),('ciclone',366,367,'ASSOCIATES'),('decomed',382,374,'ASSOCIATES'),('lusoscut',383,[384,385,386,387,388,389,381],'ASSOCIATES'),('outros',413,390,'ASSOCIATES'),('associate-total',None,398,'ASSOCIATE_TOTAL'),('overall-total',None,406,'OVERALL_TOTAL')],
}

def reading(graph):
    units={u['id']:u for u in graph['units']}
    def unit(p,n):return units[f'bes-2010-en:p{p}:l{n}']
    def witness(u,text=None):
        token=u['raw'].strip() if text is None else text
        start=u['raw'].index(token)
        return {'unit':u['id'],'page':u['page'],'source_sha256':u['source_sha256'],
                'start':start,'end':start+len(token),'quote':token}
    def sources(p,s):return section(units,'witness',{},refs((p,s)))['source']
    def numeric(p,n):
        w=witness(unit(p,n)); token=w['quote']
        assert re.fullmatch(r'-|\(?\d[\d,]*\)?',token),w
        value=None if token=='-' else int(token.replace(',','').replace('(','-').replace(')',''))
        return {**w,'value':value,'status':'PRINTED_DASH' if value is None else 'SOURCE_INTEGER','amount_unit':'EUR_THOUSAND'}
    def entity(p,n,spe=False):
        label=unit(p,n); y=label['bbox'][1]
        row=sorted([u for u in units.values() if u['page']==p and u['document']=='bes-2010-en' and abs(u['bbox'][1]-y)<0.01 and u['raw'].strip() and u['bbox'][0]>240],key=lambda u:u['bbox'][0])
        # Inspected fixed column boundaries, not a general table parser.
        fields={}
        for u in row:
            x=u['bbox'][0]; raw=u['raw'].strip()
            if raw in ('Full consolidation','Full Consolidation','Equity method'):key='method'
            elif '%' in raw:
                m=re.fullmatch(r'(\d+(?:\.\d+)?%)(?: (Full consolidation))?',raw)
                assert m,raw
                fields['economic_interest']={**witness(u,m[1]),'percent':str(Decimal(m[1][:-1])),'measure':'GROUP_ECONOMIC_INTEREST'}
                if m[2]:fields['method']={**witness(u,m[2]),'value':'FULL_CONSOLIDATION'}
                continue
            elif u['bbox'][2]<280:key='established'
            elif u['bbox'][2]<320:key='acquired'
            elif spe or u['bbox'][2]<390:key='headquartered'
            else:key='activity'
            assert key not in fields,(p,n,key)
            fields[key]={**witness(u),'value':raw if key!='method' else {'Full consolidation':'FULL_CONSOLIDATION','Full Consolidation':'FULL_CONSOLIDATION','Equity method':'EQUITY_METHOD'}[raw]}
        expected={'established','acquired','headquartered','economic_interest','method'}| (set() if spe else {'activity'})
        if p==98 and n==227:
            expected-={'economic_interest','method'}
            for k in ('economic_interest','method'):fields[k]={'value':None,'status':'NO_PRINTED_CELL'}
        assert expected <= fields.keys(),(p,n,fields.keys())
        return {'id':f'p{p}-l{n}','label':witness(label),'display_x':label['bbox'][0],
                'fields':fields,'direct_voting_percentage_established':False,'legal_parent_established_from_indentation':False}
    entities=[]
    for p,names in ENTITY_NAMES.items():
        group=None
        for n in names:
            r=entity(p,n)
            heading=n in GROUP_HEADINGS.get(p,set())
            if heading:group=r['id']
            r.update(table='DIRECT_PRINTED_HEADING' if p==98 else 'SUBGROUPS',display_subgroup=group,display_group_heading=heading)
            entities.append(r)
    spes=[{**entity(100,n,True),'table':'SIC12_SPECIAL_PURPOSE_ENTITIES'} for n in SPE_NAMES]
    transactions=[]
    for year,spec in TRANSACTIONS.items():
        transactions.append({'year':year,'headers':sources(102,'2-15,17,84' if year==2010 else '246-260,301'),
          'columns':AMOUNT_COLUMNS,'amount_unit':'EUR_THOUSAND','printed_disposal_sign':'NEGATIVE' if year==2010 else 'POSITIVE',
          'dash_arithmetic':'CONDITIONAL_ZERO_FOR_RECONCILIATION_ONLY_ORIGINAL_VALUE_REMAINS_UNKNOWN',
          'rows':[{'id':key,'category':category,'labels':[witness(unit(102,label))] if label is not None else [],
             'label_status':'DISPLAYED_LABEL' if label is not None else 'UNLABELLED_PRINTED_TOTAL_LOCAL_NAME',
             'cells':[numeric(102,n) for n in (list(range(start,start+7)) if isinstance(start,int) else start)]}
             for key,label,start,category in spec]})
    impact={'scope':'PRECEDING_SIC12_SPECIAL_PURPOSE_ENTITIES','headers':sources(101,'0-4'),
        'printed_dates':['31.12.2010','3.12.2009'],'comparative_date_corrected':False,'amount_unit':'EUR_THOUSAND',
        'rows':[{'labels':[witness(unit(101,n))],'cells':[numeric(101,n+1),numeric(101,n+2)]} for n in (5,8,11,14,17)]}
    make=lambda name,meaning,*parts:section(units,name,meaning,refs(*parts))
    narratives=[
      make('interpretation-basis',{'percentage':'GROUP_ECONOMIC_INTEREST','full_basis':'CONTROL','equity_basis':'SIGNIFICANT_INFLUENCE','policy_reference':'Note 2.2','control_inferred_from_majority':False,'twenty_percent_exclusion':False,'SPE_policy':'SIC 12','table_heading_determines_method':False},(98,'0'),(99,'0'),(100,'313-316,416')),
      make('source-discrepancies',{'bes_africa_years':{'p98':['2009','2009'],'p99':['2006','2006']},'bes_africa_resolution':'UNRESOLVED_SOURCE_CONFLICT','impact_comparative_date':'3.12.2009','impact_label':'Due to costumers (net of impairment)','label_reinterpreted_as_customer_loans':False,'domicile_inferred_from_legal_suffix':False},(98,'63-65'),(99,'282-284'),(101,'4,11'),(100,'404-415')),
      make('aman-acquisition',{'date':'2010-04','interest_percent':'40','consideration':'40.3','amount_unit':'EUR_MILLION','consolidation':'FULL','basis':'MANAGEMENT_CONTROL','reference':'Note 45','table_total_eur_thousand':40269,'table_acquisition_cost_eur_thousand':24275,'table_other_investments_eur_thousand':15994,'rounded_narrative_consistent_with_table_total':True},(101,'20-23'),(102,'20-27')),
      make('other-subsidiary-changes',{'centimo_liquidation':'2010-07','cape_verde':{'date':'2010-07','share_capital_eur_million':'13','bes_africa_percent':'99.99'},'execution':{'date':'2010-11','interest_percent':'50.1','amount_eur_thousand':58165,'full_consolidation_basis':'MANAGEMENT_CONTROL','reference':'Note 45'},'kutaya_sold':'2010-11','gespastor':{'date':'2010-12','purchased_capital':'ENTIRE','amount_eur_thousand':25354,'route':'ESAF_THROUGH_ESPIRITO_SANTO_GESTION_FROM_BANCO_PASTOR','method':'FULL_CONSOLIDATION','reference':'Note 45'},'transaction_percentage_equals_group_economic_interest':False},(101,'24-31')),
      make('associate-changes',{'reference':'Note 27','nanium':{'date':'2010-03','percent':'41.06','context':'QIMONDA_BANKRUPTCY'},'auvisa':{'date':'2010-03','es_concessoes_percent':'50'},'aquaspy':{'date':'2010-06','included':False,'reason':'CHANGED_SHAREHOLDING_AND_LOSS_OF_CONTROL'},'unicre':{'date':'2010-06','added_percent':'8.41','result_percent':'17.50','basis':'SIGNIFICANT_INFLUENCE','method':'EQUITY','prior_stake_revaluation_gain_eur_thousand':7347,'reference':'IFRS 3 / Note 2.2'},'neumaticos':{'date':'2010-07','realised_gain_eur_thousand':3559},'scutvias_portvias':{'date':'2010-12','es_concessoes_percent':'22.38','amounts_eur_thousand':[50669,11]},'sgpice_exchange':{'date':'2010-12','recipient':'PT_PRIME_TRADECOM','received_percent':'33'},'salgar':{'date':'2010-12','added_percent':'23.7','amount_eur_thousand':5268,'total_percent':'47.28'},'ascendi':{'date':'2010-12','es_concessoes_percent':'40','consideration':'IN_KIND_SHARES','amount_eur_thousand':42964,'participation_in_ascendi_sgps_sold':True,'table_acquisition_cost_eur_thousand':163341,'table_and_narrative_scope_equated':False}},(101,'34,35-43,44-53')),
      make('transaction-footnotes',{'2010_other_scope':'CAPITAL_INCREASE_AND_LOANS_TO_NONCONTROLLING_INTEREST_COMPANIES','2009_other_scope':'CAPITAL_INCREASE_AND_LOANS_TO_MINORITY_INTEREST_COMPANIES','morumbi_settled':'2009-03','esdata_settled':'2009-09','esfc_settled':'2009-11','bes_angola_disposal':{'date':'2009-12','percent':'24'},'dash_proceeds_imputed_zero':False,'cross_year_disposal_sign_normalized':False},(102,'245,414-418')),
    ]
    return {'version':'bes-annual2010-group-disclosures.v1','entity_headers':sources(98,'0-5,7-8')+sources(99,'0-5,7-8')+sources(100,'0-4,6-7,316-321,323-324'),
      'entities':entities,'special_purpose_entities':spes,'impact':impact,'transactions':transactions,'narratives':narratives,
      'attribution':'ISSUER_ANNUAL_REPORT_2010','source_authenticity':'NOT_ESTABLISHED','all_notes_interpreted':False,
      'independent_legal_or_financial_acceptance':False,'scope':'NOTE1_TABLES_AND_CHANGES_PAGES98_TO102',
      'earlier_introduction_table_flag':'PRESERVED_V6_INTRODUCTION_ONLY_COVERAGE; THIS_FIELD_ADDS_SUPPLIED_GROUP_TABLES'}

def combine(old,graph):
    result=deepcopy(old)
    assert FIELD not in result
    result[FIELD]=reading(graph)
    result['source_context']['source_pages']=sorted(set(result['source_context']['source_pages'])|set(NEW_PAGES))
    result['source_context']['scope']+='; original Note1 group tables and changes98–102 supplied; later numerical notes remain incomplete'
    assert result['source_context']['all_notes_read'] is False
    return result
