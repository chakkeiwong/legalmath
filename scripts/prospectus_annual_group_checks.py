"""Independent token/geometry, subtotal and semantic guards for supplied Note1."""
from copy import deepcopy
from decimal import Decimal
from scripts.prospectus_annual_policy_checks import require

CASES=[
 ('majority','interpretation-basis','control_inferred_from_majority',False,True,'control over their activities'),
 ('threshold','interpretation-basis','twenty_percent_exclusion',False,True,'significant influence'),
 ('heading-method','interpretation-basis','table_heading_determines_method',False,True,'Subsidiaries consolidated directly'),
 ('interest-type','interpretation-basis','percentage','GROUP_ECONOMIC_INTEREST','VOTING_POWER','economic interest'),
 ('africa-reconciled','source-discrepancies','bes_africa_resolution','UNRESOLVED_SOURCE_CONFLICT','RESOLVED','2006'),
 ('date-corrected','source-discrepancies','impact_comparative_date','3.12.2009','31.12.2009','3.12.2009'),
 ('loan-label','source-discrepancies','label_reinterpreted_as_customer_loans',False,True,'Due to costumers'),
 ('suffix-jurisdiction','source-discrepancies','domicile_inferred_from_legal_suffix',False,True,'Portugal'),
 ('aman-control','aman-acquisition','basis','MANAGEMENT_CONTROL','MAJORITY_OWNERSHIP','management control'),
 ('aman-cost','aman-acquisition','table_acquisition_cost_eur_thousand',24275,40269,'24,275'),
 ('aman-total','aman-acquisition','table_total_eur_thousand',40269,24275,'40,269'),
 ('ownership-equated','other-subsidiary-changes','transaction_percentage_equals_group_economic_interest',False,True,'entire share capital'),
 ('dash-proceeds','transaction-footnotes','dash_proceeds_imputed_zero',False,True,'Disposal of 24%'),
 ('year-signs','transaction-footnotes','cross_year_disposal_sign_normalized',False,True,'minority interests'),
]

def check(value,graph):
    units={u['id']:u for u in graph['units']}
    def witness(w):
        require(w['unit'] in units,'Missing source')
        u=units[w['unit']]
        require(w['page']==u['page'] and w['source_sha256']==u['source_sha256'] and u['raw'][w['start']:w['end']]==w['quote'],'Source witness mismatch')
        return u
    def scan(x):
        if isinstance(x,dict):
            if 'unit' in x and 'quote' in x:witness(x)
            for z in x.values():scan(z)
        elif isinstance(x,list):
            for z in x:scan(z)
    scan(value)
    entities=value['entities']; spes=value['special_purpose_entities']
    require(len(entities)==145 and len(spes)==15,'Entity coverage changed')
    rows={r['id']:r for r in entities+spes}
    require(len(rows)==160,'Duplicate entity')
    for r in entities+spes:
        u=witness(r['label']); y=u['bbox'][1]
        require(r['display_x']==u['bbox'][0] and not r['direct_voting_percentage_established'] and not r['legal_parent_established_from_indentation'],'Unsupported hierarchy/ownership')
        for k,c in r['fields'].items():
            if c.get('status')=='NO_PRINTED_CELL':
                require(r['id']=='p98-l227' and k in ('method','economic_interest') and c['value'] is None,'Invented blank')
                continue
            s=witness(c)
            require(abs(s['bbox'][1]-y)<0.01,'Wrong entity row')
            if k=='economic_interest':
                require(c['measure']=='GROUP_ECONOMIC_INTEREST' and Decimal(c['percent'])==Decimal(c['quote'].removesuffix('%')),'Interest altered')
            elif k=='method':
                require(c['value']=={'full consolidation':'FULL_CONSOLIDATION','equity method':'EQUITY_METHOD'}[c['quote'].lower()],'Method altered')
            else:require(c['value']==c['quote'],'Entity field altered')
        require(r['fields']['headquartered']['value'] not in ('','-'),'Missing domicile')
    # Separately declared display anchors and method counterexamples.
    for key,pct,method in [('p98-l28','40.00','FULL_CONSOLIDATION'),('p98-l175','40.96','FULL_CONSOLIDATION'),('p98-l347','17.50','EQUITY_METHOD'),('p99-l54','9.77','EQUITY_METHOD'),('p99-l144','12.50','EQUITY_METHOD'),('p99-l245','49.00','FULL_CONSOLIDATION'),('p99-l267','48.15','FULL_CONSOLIDATION'),('p100-l264','9.17','EQUITY_METHOD')]:
        require(rows[key]['fields']['economic_interest']['percent']==pct and rows[key]['fields']['method']['value']==method,'Threshold counterexample altered')
    require([rows['p98-l63']['fields'][k]['value'] for k in ('established','acquired')]==['2009','2009'] and [rows['p99-l282']['fields'][k]['value'] for k in ('established','acquired')]==['2006','2006'],'Africa discrepancy erased')
    for key,group in [('p99-l376','p99-l379'),('p99-l277','p99-l268'),('p99-l287','p99-l282'),('p99-l367','p99-l292'),('p100-l55','p100-l39'),('p100-l214','p100-l194'),('p100-l222','p100-l194'),('p100-l250','p100-l221'),('p100-l306','p100-l249')]:
        require(rows[key]['display_subgroup']==group,'Display subgroup lost')
    require(rows['p100-l404']['fields']['headquartered']['value']=='Portugal' and rows['p100-l410']['fields']['headquartered']['value']=='Netherlands','Source domicile corrected')
    require(all(r['fields']['method']['value']=='FULL_CONSOLIDATION' for r in spes),'SPE method altered')
    impact=value['impact']
    require(impact['printed_dates']==['31.12.2010','3.12.2009'] and not impact['comparative_date_corrected'],'Impact date repaired silently')
    require(impact['scope']=='PRECEDING_SIC12_SPECIAL_PURPOSE_ENTITIES' and impact['amount_unit']=='EUR_THOUSAND','Impact scope/unit')
    require(impact['rows'][2]['labels'][0]['quote']=='Due to costumers (net of impairment)','Impact label changed')
    def numbers(row):
        ys=[]; xs=[]; vals=[]
        for c in row['cells']:
            u=witness(c);q=c['quote']; expected=None if q=='-' else int(q.replace(',','').replace('(','-').replace(')',''))
            require(c['value']==expected and c['status']==('PRINTED_DASH' if expected is None else 'SOURCE_INTEGER') and c['amount_unit']=='EUR_THOUSAND','Number/sign/dash/unit changed')
            ys.append(u['bbox'][1]);xs.append(u['bbox'][0]);vals.append(expected)
        require(max(ys)-min(ys)<0.01 and xs==sorted(xs),'Displayed cells displaced')
        for label in row['labels']:require(abs(witness(label)['bbox'][1]-ys[0])<0.01,'Displayed label displaced')
        return vals
    require([numbers(r) for r in impact['rows']]==[[468085,235561],[406734,None],[5715334,4346416],[1208319,1527467],[14346,10540]],'Impact table altered')
    require([t['year'] for t in value['transactions']]==[2010,2009],'Transaction years/order')
    checks=0; tables={}
    for t in value['transactions']:
        require(t['columns']==['ACQUISITION_COST','OTHER_INVESTMENTS','ACQUISITION_TOTAL','DISPOSAL_VALUE','OTHER_REIMBURSEMENTS','DISPOSAL_TOTAL','GAINS_LOSSES'],'Transaction columns')
        require(t['amount_unit']=='EUR_THOUSAND' and t['dash_arithmetic']=='CONDITIONAL_ZERO_FOR_RECONCILIATION_ONLY_ORIGINAL_VALUE_REMAINS_UNKNOWN','Unit/dash interpretation')
        require(t['printed_disposal_sign']==('NEGATIVE' if t['year']==2010 else 'POSITIVE'),'Historical signs normalized')
        require(len(t['rows'])==(28 if t['year']==2010 else 19),'Transaction rows lost')
        raw={r['id']:numbers(r) for r in t['rows']}
        require(len(raw)==len(t['rows']),'Duplicate transaction')
        v={k:[0 if n is None else n for n in ns] for k,ns in raw.items()}
        for r in t['rows']:
            a=v[r['id']]
            require(a[0]+a[1]==a[2] and a[3]+a[4]==a[5],'Conditional row sum')
            checks+=2
        for category,total in [('SUBSIDIARIES','subsidiary-total'),('ASSOCIATES','associate-total')]:
            selected=[v[r['id']] for r in t['rows'] if r['category']==category]
            require([sum(a[i] for a in selected) for i in range(7)]==v[total],'Conditional subtotal')
            checks+=7
        require([a+b for a,b in zip(v['subsidiary-total'],v['associate-total'])]==v['overall-total'],'Conditional grand total')
        checks+=7; tables[t['year']]=raw
    require(tables[2010]['overall-total']==[394921,63581,458502,-169254,-5355,-174609,46401],'2010 grand total')
    require(tables[2009]['overall-total']==[92247,87181,179428,261308,4149,265457,184286],'2009 grand total')
    ns={n['id']:n for n in value['narratives']}
    require(len(ns)==6,'Narratives lost')
    for name,key,field,expected,bad,phrase in CASES:
        r=ns[key]
        require(r['meaning'][field]==expected,'Meaning altered: '+name)
        require(phrase in ' '.join(' '.join(w['quote'] for w in r['source']).split()),'Source qualifier missing: '+name)
    aman=ns['aman-acquisition']['meaning']
    require(Decimal(tables[2010]['aman'][2])/1000>=Decimal(aman['consideration'])-Decimal('0.05') and Decimal(tables[2010]['aman'][2])/1000<Decimal(aman['consideration'])+Decimal('0.05'),'AMAN rounding inconsistent')
    assoc=ns['associate-changes']['meaning']
    require(assoc['unicre']['method']=='EQUITY' and assoc['unicre']['prior_stake_revaluation_gain_eur_thousand']==7347 and assoc['unicre']['result_percent']=='17.50','UNICRE transaction')
    require(assoc['ascendi']['consideration']=='IN_KIND_SHARES' and assoc['ascendi']['amount_eur_thousand']==42964 and not assoc['ascendi']['table_and_narrative_scope_equated'] and assoc['ascendi']['table_acquisition_cost_eur_thousand']==tables[2010]['ascendi'][0],'Ascendi scopes conflated')
    require(assoc['neumaticos']['realised_gain_eur_thousand']==tables[2010]['neumaticos'][6] and assoc['salgar']['amount_eur_thousand']==tables[2010]['salgar'][0],'Narrative transaction mismatch')
    require(ns['other-subsidiary-changes']['meaning']['execution']['amount_eur_thousand']==tables[2010]['execution'][0] and ns['other-subsidiary-changes']['meaning']['gespastor']['amount_eur_thousand']==tables[2010]['gespastor'][0],'Subsidiary transaction mismatch')
    require(not value['all_notes_interpreted'] and not value['independent_legal_or_financial_acceptance'],'False acceptance')
    # Exact supplied-profile schema protects further narrative fields; the
    # independent rules above, not this common construction, support diagnostics.
    from scripts.prospectus_annual_group_reading import reading
    require(value==reading(graph),'Supplied mapping or narrative changed')
    return {'status':'PASS','entities':145,'special_purpose_entities':15,'transaction_rows':47,'impact_rows':5,'conditional_integer_equalities':checks,'qualifiers':len(CASES),'narratives':6}

def mutations(value):
    for name,key,field,expected,bad,phrase in CASES:
        c=deepcopy(value);next(n for n in c['narratives'] if n['id']==key)['meaning'][field]=deepcopy(bad);yield name,c
    for year in (2010,2009):
        for kind in ('year','unit','number','dash-condition','column-order','row-label','sign','subtotal'):
            c=deepcopy(value);t=next(t for t in c['transactions'] if t['year']==year)
            if kind=='year':t['year']=1999
            elif kind=='unit':t['amount_unit']='EUR_MILLION'
            elif kind=='number':t['rows'][0]['cells'][2]['value']=1
            elif kind=='dash-condition':t['dash_arithmetic']='UNCONDITIONAL_ZERO'
            elif kind=='column-order':t['rows'][0]['cells'].reverse()
            elif kind=='row-label':t['rows'][0]['labels']=t['rows'][1]['labels']
            elif kind=='sign':t['printed_disposal_sign']='NORMALIZED_POSITIVE'
            else:t['rows'][-1]['cells'][0]['value']+=1
            yield str(year)+'-'+kind,c
    for key in ('p98-l28','p98-l347','p99-l245','p100-l214','p100-l250'):
        c=deepcopy(value);r=next(r for r in c['entities'] if r['id']==key);r['fields']['method']['value']='EXCLUDED';yield key+'-method',c
    for name in ('dash-imputed','impact-date','display-parent','africa-years','spe-domicile','ascendi-scope','unicre-gain','entity-row'):
        c=deepcopy(value)
        if name=='dash-imputed':c['impact']['rows'][1]['cells'][1]['value']=0
        elif name=='impact-date':c['impact']['printed_dates'][1]='31.12.2009'
        elif name=='display-parent':next(r for r in c['entities'] if r['id']=='p100-l214')['display_subgroup']='p100-l221'
        elif name=='africa-years':next(r for r in c['entities'] if r['id']=='p99-l282')['fields']['established']['value']='2009'
        elif name=='spe-domicile':next(r for r in c['special_purpose_entities'] if r['id']=='p100-l404')['fields']['headquartered']['value']='Netherlands'
        elif name=='ascendi-scope':next(n for n in c['narratives'] if n['id']=='associate-changes')['meaning']['ascendi']['table_and_narrative_scope_equated']=True
        elif name=='unicre-gain':next(n for n in c['narratives'] if n['id']=='associate-changes')['meaning']['unicre']['prior_stake_revaluation_gain_eur_thousand']=3559
        else:c['entities'][2]['fields']['economic_interest']=deepcopy(c['entities'][3]['fields']['economic_interest'])
        yield name,c
