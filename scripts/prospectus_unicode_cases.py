"""Author independent exact-source cases before the optional parser exists."""
from datetime import datetime, timezone
import hashlib, json, time
from scripts import prospectus_publication_routes as prior

ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/unicode-labels-322'
PLAN='docs/plans/prospectus-unicode-label-discovery-2026-10-19.md'
METHOD='scripts/prospectus_unicode_cases.py'
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
AUDIT='docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-09/attempt-002/statutory-2010.txt'
NOTE='docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-07/attempt-002/en-note-page.txt'


def marked(value):
    text='';spans=[]
    while '[[' in value:
        a,value=value.split('[[',1);text+=a
        word,value=value.split(']]',1)
        start=len(text);text+=word;spans.append([start,len(text)])
    return text+value,spans


def case(identity,markup,convention='english',names=None,issues=(),regions=None):
    text,uses=marked(markup)
    name_spans=uses if names is None else [uses[i] for i in names]
    return {'id':identity,'origin':'CONSTRUCTED','text':text,'quotation_convention':convention,
        'language':'en' if convention!='german' else 'de',
        'expected_names':name_spans,'expected_uses':uses,'expected_issue_kinds':list(issues),
        'regions':regions,'scope_admitted':False,'meaning_admitted':False}


def original(identity,path,labels):
    text=(ROOT/path).read_text();spans=[];cursor=0
    for label in labels:
        start=text.index(label,cursor);end=start+len(label)
        assert text[start-1]=='“' and text[end]=='”'
        spans.append([start,end]);cursor=end
    return {'id':identity,'origin':'ORIGINAL_RETAINED','source':{'path':path,'sha256':sha(ROOT/path)},
        'text':text,'quotation_convention':'english','language':'en','regions':None,
        'expected_names':spans,'expected_uses':spans,'expected_issue_kinds':[],
        'scope_admitted':False,'meaning_admitted':False}


def main():
    assert not (PREP/'cases.json').exists() and not (PREP/'candidate.py').exists()
    began=time.monotonic()
    from legalmath.prospectus.execution_authority import Authority
    events=Authority(ROOT).events()
    assert read(AUTH/'program.json')['revision']==321
    assert [e['kind'] for e in events if e.get('attempt')==rel(prior.HERE)][-1]=='RECORD'
    save(PREP/'accounting-start.json',{'prior':prior.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    rows=[
        original('audit-code-names',AUDIT,[
            'Código dos Valores Mobiliários','Código dos Valores Mobiliários',
            'Ordem dos\nAnnual Report BES Group\n190 Revisores Oficiais de Contas',
            'Código\ndas Sociedades Comerciais']),
        original('quoted-ordinary-finance-phrase',NOTE,['gross capital inflow']),
        case('english','“[[Alpha]]” means X. [[Alpha]] applies.',names=[0]),
        case('german','„[[Alpha]]“ bezeichnet X. [[Alpha]] gilt.','german',names=[0]),
        case('guillemets','«[[Alpha]]» denotes X. [[Alpha]] applies.','guillemets',names=[0]),
        case('ascii','"[[Alpha]]" means X. [[Alpha]] applies.',names=[0]),
        case('forward','[[Alpha]] applies. “[[Alpha]]” means X.',names=[1]),
        case('duplicate','“[[Alpha]]” means X. “[[Alpha]]” means Y. [[Alpha]] applies.',names=[0,1]),
        case('ordinary-speech','They said “[[it is fine]]”.',names=[0]),
        case('whitespace','“[[Alpha\n Beta]]” applies to [[Alpha\tBeta]].',names=[0]),
        case('nbsp','“[[Alpha\u00a0Beta]]” and [[Alpha Beta]].',names=[0]),
        case('compound','“[[Alpha]]” then Alpha-beta, preAlpha, Alpha/beta and [[Alpha]].',names=[0]),
        case('combining-mark','“[[A]]” then A\u0301 but [[A]].',names=[0]),
        case('nested','“Outer "inner" label”',names=[],issues=['NESTED_QUOTE']),
        case('unbalanced','“Alpha',names=[],issues=['UNBALANCED_QUOTE']),
        case('unmatched-close','Alpha”',names=[],issues=['UNMATCHED_QUOTE']),
        case('empty','“  ”',names=[],issues=['EMPTY_QUOTE']),
        case('wrong-convention','„Alpha“','english',names=[],issues=['UNSUPPORTED_QUOTE','UNBALANCED_QUOTE']),
        case('unsupported-guillemet','«Alpha»','english',names=[],issues=['UNSUPPORTED_QUOTE']),
        case('mixed-nesting','“Outer «inside» label”','english',names=[],issues=['UNSUPPORTED_QUOTE']),
        case('no-label','Alpha has no quote.',names=[]),
    ]
    row=case('excluded-region','“[[Alpha]]” then Alpha.',names=[0])
    split=row['text'].index(' then')
    row['regions']=[{'id':'selected','start':0,'end':split,'selected':True,'language':'en'},
        {'id':'excluded','start':split,'end':len(row['text']),'selected':False,'language':'en'}]
    rows.append(row)
    row=case('different-language','“[[Alpha]]” then Alpha.',names=[0])
    row['regions']=[{'id':'selected','start':0,'end':split,'selected':True,'language':'en'},
        {'id':'other','start':split,'end':len(row['text']),'selected':True,'language':'de'}]
    rows.append(row)
    row=case('split-quote','“Alpha”',names=[],issues=['UNBALANCED_QUOTE','UNMATCHED_QUOTE'])
    row['regions']=[{'id':'a','start':0,'end':3,'selected':True,'language':'en'},
        {'id':'b','start':3,'end':len(row['text']),'selected':True,'language':'en'}]
    rows.append(row)
    for row in rows:
        row['text_sha256']=hashlib.sha256(row['text'].encode()).hexdigest()
        if row['regions'] is None:
            row['regions']=[{'id':'source','start':0,'end':len(row['text']),'selected':True,'language':row['language']}]
        for a,b in row['expected_names']+row['expected_uses']:
            assert 0<=a<b<=len(row['text'])
    save(PREP/'cases.json',{'version':'unicode-label-cases.v1','cases':rows,
        'ordinary_quotes_are_not_declarations':True,'page_header_contamination_preserved':True})
    save(PREP/'cases-freeze.json',{'cases_sha256':sha(PREP/'cases.json'),
        'authoring_method':METHOD,'authoring_method_sha256':sha(ROOT/METHOD),
        'plan':PLAN,'plan_sha256':sha(ROOT/PLAN),'candidate_exists':False,
        'temporal_separation':'same agent authored expectations before candidate; not a blind annotation study',
        'source_files':{AUDIT:sha(ROOT/AUDIT),NOTE:sha(ROOT/NOTE)},
        'frozen_at':datetime.now(timezone.utc).isoformat()})
    from legalmath.prospectus.successor.definition_discovery import discover
    baseline={}
    for row in rows[:2]:
        result=discover({k:row[k] for k in ('text','text_sha256','language','regions')})
        baseline[row['id']]={'names':result['names'],'uses':result['uses'],'issues':result['issues'],
            'required_names':row['expected_names'],'exact_naming_match':False}
        assert not result['names'] and row['expected_names']
    save(PREP/'baseline.json',baseline)
    elapsed=time.monotonic()-began
    assert elapsed<30 and sum(p.stat().st_size for p in PREP.rglob('*') if p.is_file())<1024**2
    save(PREP/'case-preparation.json',{'status':'PASS','cases':len(rows),'original_cases':2,
        'baseline_miss_reproduced':True,'wall_seconds':elapsed,
        'command':['.venv/bin/python','-m','scripts.prospectus_unicode_cases']})
    print(json.dumps({'status':'PASS','cases':len(rows),'baseline_miss_reproduced':True,'wall_seconds':elapsed}))


if __name__=='__main__':main()
