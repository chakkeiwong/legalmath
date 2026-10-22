"""Source geometry, integer reconciliations and separate original statement tie-outs."""
from copy import deepcopy
from scripts.prospectus_annual_policy_checks import require

CASES=[
 ('preference-holding','group-introduction','preference_count_is_investor_holding',False,True,'600 thousand preference shares'),
 ('standalone','group-introduction','standalone_accounts_supplied',False,True,'BES Finance, Ltd'),
 ('group-threshold','group-introduction','following_table_holding_operator','GE','GT','greater or equal to 20%'),
 ('group-tables','group-introduction','following_group_tables_interpreted',False,True,'are as follows'),
 ('group-authority','group-introduction','authorisation_independently_verified',False,True,'authorised by the'),
 ('loan-unwind','interest-explanations','unwind_discount_eur_thousand',{'2010':24363,'2009':18626},{'2010':18626,'2009':24363},'24,363 thousand'),
 ('hedge-status','interest-explanations','all_risk_management_derivatives_qualify_as_hedges',False,True,'and from derivatives used to manage the risk'),
 ('own-credit','fvpl-explanations','own_credit_effect_eur_million',{'2010':'82.7','2009':'-41'},{'2010':'82.7','2009':'41'},'negative effect of euro 41 million'),
 ('own-credit-total','fvpl-explanations','own_credit_effect_is_entire_fvpl_total',False,True,'includes a positive effect'),
 ('day-one','fvpl-explanations','day_one_recognition_conditions',['FAIR_VALUE_AT_INCEPTION_AND_SUBSEQUENT_MEASUREMENT_USES_ONLY_OBSERVABLE_MARKET_DATA','REFLECTS_GROUP_WHOLESALE_MARKET_ACCESS'],[],'only based on observable market data'),
 ('day-one-unit','fvpl-explanations','approximate_day_one_gain_eur_thousand',{'2010':10446,'2009':9006},{'2010':10446000,'2009':9006000},'approximately euro 10 446 thousand'),
 ('afs-subset','afs-explanations','specified_sale_gains_equal_entire_afs_net_gains',False,True,'following these transactions'),
 ('dividend-subset','afs-explanations','named_dividends_exhaustive',False,True,'includes dividends received'),
 ('dividend-double','afs-explanations','dividends_added_to_afs_net_gains',False,True,'Dividend Income from the income statement'),
 ('fx-rate','fx-explanations','rate_date','BALANCE_SHEET_DATE','TRANSACTION_DATE','balance sheet date'),
 ('repurchase','other-income-reference','reference','Note 35','Note 37','Note 35'),
]

# Independently transcribed displayed final totals, not generated from the reading.
TOTALS={'interest':[998319,165639,1163958,1172128,28687,1200815],
 'fees':[769333,680142], 'fvpl':[12543657,12735127,-191470,13885983,13937395,-51412],
 'afs':[502038,137602,364436,344400,155161,189239],
 'fx':[1485616,1438885,46731,1139932,1081399,58533], 'other':[-13634,95831]}
ROW_COUNTS={'interest':15,'fees':12,'fvpl':26,'afs':5,'fx':2,'other':10}
DISPLACED={('interest','fvpl-income'):('labels',65),('interest','derivative-income'):('labels',66),
 ('interest','derivative-expense'):('labels',130),('fvpl','liabilities-banks'):('cell5',178),
 ('fvpl','liabilities-customers'):('cell5',179)}


def witness(a,units,full=True):
    u=units[a['unit']]
    require(u['visible'] and a['source_sha256']==u['source_sha256'] and a['page']==u['page'],'Wrong source identity')
    require(a['quote']==u['raw'][a['start']:a['end']] and a['start']>=0 and a['end']<=len(u['raw']),'Wrong source span')
    if full:
        require(a['start']==0 and a['end']==len(u['raw']),'Incomplete paragraph witness')
    return u


def check(value,graph):
    units={u['id']:u for u in graph['units']}
    tables={t['id']:t for t in value['tables']}
    require(list(tables)==list(TOTALS),'Tables missing or reordered')
    arithmetic=0
    allrows={}
    for name,t in tables.items():
        require(t['amount_unit']=='EUR_THOUSAND' and t['attribution']=='ISSUER_ANNUAL_REPORT_2010' and not t['independently_verified'],'Table unit or attribution changed')
        require(t['dash_arithmetic']=='CONDITIONAL_ZERO_FOR_RECONCILIATION_ONLY_ORIGINAL_VALUE_REMAINS_UNKNOWN','Dash condition missing')
        categories=['AMORTISED_COST_AND_AFS','FVPL','TOTAL'] if name=='interest' else ['GAINS','LOSSES','NET'] if name in ('fvpl','afs','fx') else ['AMOUNT']
        require(t['columns']==[{'year':y,'category':c} for y in (2010,2009) for c in categories],'Column meaning changed')
        for a in t['headers']: witness(a,units)
        rows={r['id']:r for r in t['rows']}
        allrows[name]=rows
        require(len(rows)==len(t['rows'])==ROW_COUNTS[name],'Row missing or duplicated')
        for r in t['rows']:
            require(len(r['cells'])==len(t['columns']),'Cell count changed')
            coords=[]
            for c in r['cells']:
                u=witness(c,units,False)
                require(c['amount_unit']=='EUR_THOUSAND','Cell units changed')
                raw=c['quote']
                expected=None if raw=='-' else int(raw.replace(',','').replace('(','-').replace(')',''))
                require(c['value']==expected and c['status']==('PRINTED_DASH' if expected is None else 'SOURCE_INTEGER'),'Cell value/sign/dash changed')
                coords.append(u['bbox'])
            require(max(b[1] for b in coords)-min(b[1] for b in coords)<1,'Different displayed rows mixed')
            require(all(coords[i][2]<coords[i+1][2] for i in range(len(coords)-1)),'Displayed columns reordered')
            for a in r['labels']: witness(a,units)
            is_total=r['id'].endswith('-total') or r['id'].startswith('net-')
            if not is_total:
                require(r['labels'] and abs(units[r['labels'][-1]['unit']]['bbox'][1]-coords[0][1])<1,'Wrong row label')
            vals=[0 if c['value'] is None else c['value'] for c in r['cells']]
            if len(vals)==6:
                for off in (0,3):
                    expected=vals[off]+vals[off+1] if name=='interest' else vals[off]-vals[off+1]
                    require(expected==vals[off+2],'Row total does not reconcile')
                    arithmetic+=1
        require([c['value'] for c in t['rows'][-1]['cells']]==TOTALS[name],'Independent displayed total mismatch')
        def vals(key): return [0 if c['value'] is None else c['value'] for c in rows[key]['cells']]
        def subtotal(target,children):
            nonlocal arithmetic
            require(vals(target)==[sum(vals(k)[i] for k in children) for i in range(len(t['columns']))],'Subtotal mismatch: '+target)
            arithmetic+=len(t['columns'])
        def net(target,inc,exp):
            nonlocal arithmetic
            require(vals(target)==[a-b for a,b in zip(vals(inc),vals(exp))],'Income/expense sign mismatch')
            arithmetic+=len(t['columns'])
        if name in ('interest','fees'):
            subtotal('income-total',[k for k in rows if k.endswith('-income')])
            subtotal('expense-total',[k for k in rows if k.endswith('-expense')])
            net('net-interest' if name=='interest' else 'net-fees','income-total','expense-total')
        elif name=='fvpl':
            for prefix in ('trading','derivative','other-assets','liabilities'):
                subtotal(prefix+'-total',[k for k in rows if k.startswith(prefix+'-') and not k.endswith('-total')])
            subtotal('designated-securities-total',['designated-government','designated-other-bonds','designated-shares','designated-other'])
            subtotal('designated-total',['designated-securities-total','other-assets-total','liabilities-total'])
            subtotal('fvpl-total',['trading-total','derivative-total','designated-total'])
        else:
            subtotal(t['rows'][-1]['id'],[r['id'] for r in t['rows'][:-1]])
    for (tab,row),(kind,n) in DISPLACED.items():
        r=allrows[tab][row]
        a=r['labels'][-1] if kind=='labels' else r['cells'][5]
        require(a['unit'].endswith(':l'+str(n)),'Displaced source binding changed')
    narratives={r['id']:r for r in value['narratives']}
    require(len(narratives)==len(value['narratives'])==6,'Narrative omitted')
    for r in narratives.values():
        require(r['attribution']=='ISSUER_ANNUAL_REPORT_2010' and not r['independently_verified'],'Narrative attribution changed')
        for a in r['source']:witness(a,units)
    for name,key,field,expected,bad,phrase in CASES:
        r=narratives[key]
        require(r['meaning'][field]==expected,'Meaning changed: '+name)
        require(phrase in ' '.join(' '.join(a['quote'] for a in r['source']).split()),'Source qualification lost: '+name)
    require([a['unit'] for a in narratives['group-introduction']['source']]==[f'bes-2010-en:p97:l{n}' for n in list(range(4))+[19,20]+list(range(14,18))+list(range(4,12))],'Group display order changed')
    require(not value['all_notes_interpreted'] and not value['independent_legal_or_financial_acceptance'],'Unsupported acceptance')
    return {'status':'PASS','tables':6,'rows':sum(ROW_COUNTS.values()),'integer_equalities':arithmetic,'narratives':6,'material_qualifiers':len(CASES)}


def tieouts(value,old):
    rows=old['primary_statements']['profile']['reading']['tables']['income']['rows']
    # Unlabelled statement subtotal rows are valid, but cannot be a named comparator.
    primary=[(r['labels'][0]['quote'].strip(),[c['value'] for c in r['cells']]) for r in rows if r['labels']]
    tables={t['id']:{r['id']:[c['value'] for c in r['cells']] for r in t['rows']} for t in value['tables']}
    pairs=[('interest','income-total','Interest and similar income',1),('interest','expense-total','Interest expense and similar charges',1),
      ('interest','net-interest','Net interest income',1),('fees','income-total','Fee and commission income',1),
      ('fees','expense-total','Fee and commission expense',-1),
      ('fvpl','fvpl-total','Net gains from financial assets at fair value through profit or loss',1),
      ('afs','afs-total','Net gains from available-for-sale financial assets',1),
      ('fx','fx-total','Net gains from foreign exchange differences',1),('other','operating-total','Other operating income and expense',1)]
    checked=[]
    for tab,key,label,sign in pairs:
        matches=[(k,v) for k,v in primary if ' '.join(k.lower().split())==' '.join(label.lower().split())]
        require(len(matches)==1,'Primary statement label not matched: '+label)
        vals=tables[tab][key]
        vals=[vals[2],vals[5]] if len(vals)==6 else vals
        require([sign*v for v in vals]==matches[0][1],'Primary statement tie-out failed: '+label)
        checked.append(label)
    return {'status':'PASS','two_year_tieouts':len(checked),'labels':checked}


def mutations(value):
    for name,key,field,expected,bad,phrase in CASES:
        c=deepcopy(value); next(r for r in c['narratives'] if r['id']==key)['meaning'][field]=deepcopy(bad)
        yield name,c
    for table in value['tables']:
        for kind in ('year','unit','number','dash-condition','cell-order','row-label'):
            c=deepcopy(value); t=next(t for t in c['tables'] if t['id']==table['id'])
            if kind=='year':t['columns'][0]['year']=2009
            elif kind=='unit':t['amount_unit']='EUR_MILLION'
            elif kind=='number':t['rows'][0]['cells'][0]['value']+=1
            elif kind=='dash-condition':t['dash_arithmetic']='UNCONDITIONAL_ZERO'
            elif kind=='cell-order':t['rows'][0]['cells'].reverse()
            else:t['rows'][0]['labels']=t['headers']
            yield table['id']+'-'+kind,c
    c=deepcopy(value); c['narratives'][0]['source'].reverse();yield 'group-order',c
    c=deepcopy(value); t=next(t for t in c['tables'] if t['id']=='fvpl'); rows={r['id']:r for r in t['rows']}; rows['liabilities-banks']['cells'][5]=deepcopy(rows['liabilities-customers']['cells'][5]);yield 'displaced-loss',c
    c=deepcopy(value); t=next(t for t in c['tables'] if t['id']=='interest'); t['rows'][1]['cells'][0]['value']=0;yield 'dash-imputed',c
