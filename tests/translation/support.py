from copy import deepcopy
from tests.search.support import packet, generation
from legalmath.translation.model import from_reading

AT = '2026-09-25T00:00:00.000000Z'


def fixture():
    g = generation()
    g['readings'][0]['formalization']['types'] = []
    f = g['readings'][0]['formalization']
    t = {'record_type':'RuleInterpretationTask', 'task_id':'fixture.shared',
         'packet':packet(), 'question':g['readings'][0]['statement'],
         'facts':f['facts'], 'types':[], 'result_type':'bool', 'profile':'ruleir.v1',
         'valid_from':AT, 'valid_until':None}
    return deepcopy(t), g


def model():
    t, g = fixture()
    return from_reading(g['readings'][0],t['packet'],AT,
                        coverage=g['coverage'],dimensions=g['dimensions'])


def snapshot(m, values):
    from legalmath.translation.policy import evidence_paths
    evidence={p:['fixture'+p] for f in m['facts'] for p in evidence_paths(m,f['type'],values[f['name']],'/'+f['name'])}
    return {'subject_id':'fixture', 'evidence':evidence, 'facts':{
        f['name']:{'status':'known', 'type':f['type'], 'value':values[f['name']],
                   'evidence_ids':evidence['/'+f['name']], 'complete':True,
                   'valid_from':AT, 'valid_until':None, 'recorded_at':AT}
        for f in m['facts']}}


def rich_model():
    t,g = fixture();r=g['readings'][0]
    text=('For this synthetic calculation, sum the exact amounts of active entries and add the rate when present; '
          'an absent rate contributes zero. Separate output controls return the fixed choice payload (zero for Empty), '
          'an optional one-third, an absent option, a Fixed two-thirds choice, the product of two-thirds and three-quarters, '
          'and the sum of 101 and minus one money minor units.')
    t['packet']['selected_slice']='Exact collection and optional-value compiler controls'
    t['packet']['units'][0]['text']=text
    r.update(statement='Sum active entry amounts and add the optional rate.',
             citations=[{'unit_id':'p1','quote':text}])
    types=[{'name':'Entry','kind':'record','fields':[
        {'name':'amount','type':'decimal','meaning':'Exact amount','unit':'ratio'},
        {'name':'active','type':'bool','meaning':'Whether included','unit':'Boolean'}], 'cases':[]},
        {'name':'Choice','kind':'enum','fields':[],
         'cases':[{'name':'Fixed','type':'decimal'},{'name':'Empty','type':None}]}]
    r['formalization'].update(types=types,result_type='decimal',
        result='(+ (sum (map item (filter item entries (field item active)) (field item amount))) (option rate amount amount (decimal 0 1)))',
        facts=[{'name':name,'type':typ,'meaning':meaning,'unit':'dimensionless ratio',
                'source_unit_ids':['p1'],'requires_judgment':False} for name,typ,meaning in
               [('entries','list[Entry]','Complete collection of exact amounts and inclusion flags'),
                ('rate','optional[decimal]','Known absence or observed exact rate'),
                ('choice','Choice','Fixed exact amount or explicit Empty alternative')]])
    m=from_reading(r,t['packet'],AT,profile='complete.v1')
    # Explicit handwritten multi-output compiler fixture, not model criticism.
    m['review'].update(origin='manual',reading=None)
    from legalmath.translation.expressions import expression
    for name,typ,expr in [('enum','decimal','(match choice (Fixed amount amount) (Empty _ (decimal 0 1)))'),
                          ('optional','optional[decimal]','(some (decimal 1 3))'),
                          ('none','optional[decimal]','(none decimal)'),
                          ('variant','Choice','(variant Choice Fixed (decimal 2 3))'),
                          ('product','decimal','(* (decimal 2 3) (decimal 3 4))'),
                          ('money','money_hkd','(sum (list money_hkd (money_hkd 101) (money_hkd -1)))')]:
        m['rules'].append({**deepcopy(m['rules'][0]),'id':name,'type':typ,
                          'scope':expression('true',name+'.scope'),'body':expression(expr,name+'.body')})
    return m
