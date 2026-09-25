"""Independent exact development specifications and references.

References implement ordinary Python mathematics, never inspect candidate code,
compiler output, or model responses. These are synthetic, not independent legal
adjudications. Expected values are kept out of converter requests.
"""
import calendar
from datetime import date
from fractions import Fraction
from itertools import product
from pathlib import Path
from legalmath.canonical import digest, loads
from legalmath.catala.native.boundary import make_snapshot

ROOT = Path(__file__).resolve().parents[3]


def f(name, typ, meaning=None, unit='dimensionless'):
    return {'name': name, 'type': typ, 'meaning': meaning or name, 'unit': unit}


def q(n, d=1):
    a = Fraction(n, d)
    return {'numerator': str(a.numerator), 'denominator': str(a.denominator)}


def frac(v):
    return Fraction(int(v['numerator']), int(v['denominator']))


def task(name, scope, text, inputs, outputs, types=()):
    return {'record_type': 'NativeCatalaTask', 'task_id': 'native.' + name,
            'packet': {'source_key': 'synthetic.native.' + name, 'authority': 'SYNTHETIC_FIXTURE',
                       'selected_slice': text, 'units': [{'unit_id': 'clause.one', 'locator': 'Synthetic clause 1', 'text': text, 'normative': True, 'span': None}],
                       'dependencies': [], 'family_ids': [name]},
            'question': 'Compute the declared outputs for the supplied primitive inputs.',
            'entry_scope': scope, 'types': list(types), 'inputs': inputs, 'outputs': outputs,
            'valid_from': '2020-01-01T00:00:00.000000Z', 'valid_until': None}


def tasks():
    return [
        task('portfolio', 'Portfolio', 'Exposure is the sum of the amounts of eligible holdings in the complete inventory. Ineligible holdings contribute zero. An empty complete inventory has zero exposure. Negative amounts are permitted. Each item represents a distinct position; do not deduplicate equal values.',
             [f('holdings', 'list[Holding]')], [f('exposure', 'decimal', unit='HKD')],
             [{'name': 'Holding', 'kind': 'record', 'fields': [f('amount', 'decimal', unit='HKD'), f('eligible', 'boolean')], 'cases': []}]),
        task('bands', 'Bands', 'The charge is amount times lowerRate up to and including threshold. Above threshold it is threshold times lowerRate plus the excess times upperRate. All inputs are nonnegative exact quantities. Calculate without intermediate rounding, then round the total once to the nearest cent, with exact half-cent ties away from zero. Money is denominated in HKD.',
             [f('amount','decimal',unit='HKD'), f('threshold','decimal',unit='HKD'), f('lowerRate','decimal'), f('upperRate','decimal')], [f('charge','money',unit='HKD cents')]),
        task('deadline', 'Deadline', 'The due date is start plus months calendar months. If the original day is absent from the target month, use the last day of the target month. months is a nonnegative integer. late is true exactly when assessed is after due; being assessed on due is not late.',
             [f('start','date'), f('months','integer',unit='calendar months'), f('assessed','date')], [f('due','date'), f('late','boolean')]),
        task('category','Classification', 'For Ordinary category the amount equals base. For Preferred category it is twice base. For Excluded category it is zero. The categories are mutually exclusive. Signed integer base values are permitted.',
             [f('category','Category'), f('base','integer')], [f('amount','integer')],
             [{'name':'Category','kind':'enum','fields':[],'cases':['Ordinary','Preferred','Excluded']}]),
        task('scopes','Household', 'Each person receives their own rate if their age is at least 18, and zero otherwise. The household total is the sum of these separately computed entitlements over a complete list of people. Evaluate the entitlement rule separately for each person, using a reusable Entitlement scope. An empty household has zero total. Each item is a distinct person.',
             [f('people','list[Person]')], [f('total','integer')],
             [{'name':'Person','kind':'record','fields':[f('age','integer'),f('rate','integer')],'cases':[]}]),
        task('exceptions','Permission', 'Permission is denied by default. A license overrides that default and permits the activity. Suspension is an exception to the licensing exception and denies permission even if licensed. Suspension without a license does not grant permission.',
             [f('licensed','boolean'),f('suspended','boolean')], [f('allowed','boolean')])]


def reference(name, v):
    if name == 'portfolio':
        z = sum((frac(h['amount']) for h in v['holdings'] if h['eligible']), Fraction(0))
        return {'exposure': q(z.numerator,z.denominator)}
    if name == 'bands':
        a, b, low, high = (frac(v[k]) for k in ('amount','threshold','lowerRate','upperRate'))
        exact = (min(a,b)*low + max(a-b,0)*high)*100
        cents = (exact.numerator*2 + exact.denominator)//(2*exact.denominator)
        return {'charge': str(cents)}
    if name == 'deadline':
        start = date.fromisoformat(v['start']); m = start.year*12 + start.month-1 + int(v['months'])
        year, month = m//12,m%12+1
        due = date(year,month,min(start.day,calendar.monthrange(year,month)[1]))
        return {'due': due.isoformat(),'late': date.fromisoformat(v['assessed']) > due}
    if name == 'category':
        return {'amount': str(int(v['base'])*{'Ordinary':1,'Preferred':2,'Excluded':0}[v['category']])}
    if name == 'scopes':
        return {'total': str(sum(int(p['rate']) for p in v['people'] if int(p['age'])>=18))}
    if name == 'exceptions':
        return {'allowed': v['licensed'] and not v['suspended']}
    raise ValueError(name)


def inputs(name):
    if name == 'portfolio':
        yield {'holdings': []}
        for values in ([(1,3,True)],[(1,3,True),(2,3,True)],[(1,3,False),(-10,7,True),(11,7,True)],[(10**30+1,3,True),(1,3,False)],[(2,1,True)]*100):
            yield {'holdings':[{'amount':q(n,d),'eligible':e} for n,d,e in values]}
    elif name == 'bands':
        for a in (q(0),q(999,100),q(10),q(1001,100),q(20),q(1,2),q(3,2),q(1,3),q(10**25)):
            yield {'amount':a,'threshold':q(10),'lowerRate':q(1,100),'upperRate':q(1,3)}
    elif name == 'deadline':
        for start, months, at in [('2024-01-31','1','2024-02-29'),('2024-01-31','1','2024-03-01'),('2023-01-31','1','2023-02-27'),('2024-02-29','12','2025-02-28'),('2024-12-31','2','2025-03-01'),('2024-02-29','0','2024-02-29')]:
            yield {'start':start,'months':months,'assessed':at}
    elif name == 'category':
        for category, base in product(('Ordinary','Preferred','Excluded'),('-2','0','99999999999999999999999999')):
            yield {'category':category,'base':base}
    elif name == 'scopes':
        for people in ([],[('17','100')],[('18','100')],[('17','100'),('18','20'),('65','30')],[('18','20'),('18','30')]):
            yield {'people':[{'age':a,'rate':r} for a,r in people]}
    else:
        for license, suspended in product((False,True),repeat=2):
            yield {'licensed':license,'suspended':suspended}


def controls():
    sources = loads((ROOT / 'examples/catala/native/control_sources.json').read_bytes())
    result = []
    for t in tasks():
        name = t['task_id'].split('.')[-1]
        src = sources[name]
        c = {'record_type':'NativeCatalaCandidate','task_hash':digest(t),'source':src,
             'interpretation': t['packet']['selected_slice'], 'assumptions':[], 'unresolved':[],
             'anchors':[{'unit_id':'clause.one','quote':t['packet']['selected_slice'], 'code_excerpt':'scope '+t['entry_scope']+':'}]}
        cases = [{'id':name+'.'+str(i),'snapshot':make_snapshot(t,v),'expected':{'status':'VALUE','value':reference(name,v)}} for i,v in enumerate(inputs(name))]
        result.append((t,c,cases))
    return result


def retained_control():
    """SFC 23EC35 Annex 1 para 3.3 arithmetic only, not SPI qualification."""
    from legalmath.sources.anchors import make_span, verify_span
    from legalmath.canonical import raw_digest
    textpath=ROOT/'.localresources/sfc/23EC35-annex1.txt'
    rawpath=ROOT/'.localresources/sfc/23EC35-annex1.pdf'
    text=textpath.read_text(); raw=rawpath.read_bytes()
    # Bind to the edition already retained and used by the shared RuleIR fixture.
    original=loads((ROOT/'docs/specs/v0.1/fixtures/source-anchor.json').read_bytes())
    assert raw_digest(raw)==original['span']['raw_sha256']
    assert raw_digest(text.encode())==original['span']['text_sha256']
    start=text.index('3.3 “Net assets”'); end=text.index('\n3.4',start)
    span=make_span('spi.annex1.3.3','23EC35/annex1',raw,text,start,end)
    quote=verify_span(span,raw,text)
    t=task('retained.netassets','NetAssets',quote,
           [f('assets','money','Total assets; classification supplied, not inferred','HKD cents'),
            f('liabilities','money','Total liabilities; classification supplied, not inferred','HKD cents'),
            f('residence','money','Value of primary residence; classification supplied, not inferred','HKD cents')],
           [f('netAssets','money',unit='HKD cents'),f('netAssetsExHome','money',unit='HKD cents')])
    t['packet'].update(source_key='sfc.23ec35.annex1.3.3',authority='RETAINED_SOURCE')
    t['packet']['units'][0].update(locator='SFC 23EC35 Annex 1 paragraph 3.3',span=span)
    t['question']='Compute only the two quantities defined in paragraph 3.3, given correctly classified HKD amounts. Asset classification, account attribution, exchange conversion and SPI eligibility are outside this question. The validity interval is a synthetic assessment setting.'
    src='```catala\nscope NetAssets:\n  definition netAssets equals assets - liabilities\n  definition netAssetsExHome equals netAssets - residence\n```'
    c={'record_type':'NativeCatalaCandidate','task_hash':digest(t),'source':src,'interpretation':t['question'],
       'assumptions':['Input classifications and HKD valuation are supplied.'],'unresolved':[],
       'anchors':[{'unit_id':'clause.one','quote':quote,'code_excerpt':'scope NetAssets:'}]}
    cases=[]
    for i,(a,l,r) in enumerate([(0,0,0),(10000,3000,2000),(100,200,10),(999999999999999999999,1,2)]):
        v={'assets':str(a),'liabilities':str(l),'residence':str(r)}
        cases.append({'id':'retained.netassets.'+str(i),'snapshot':make_snapshot(t,v),
                      'expected':{'status':'VALUE','value':{'netAssets':str(a-l),'netAssetsExHome':str(a-l-r)}}})
    return t,c,cases
