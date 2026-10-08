"""Encode the specific page-image readings made in this continuation."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[4]
if str(ROOT/'src') not in sys.path:
    sys.path.insert(0,str(ROOT/'src'))
from legalmath.prospectus.successor.contracts import digest
BASE='basf-base-september-2022-exchange';FINAL='basf-2032-final'
out=ROOT/'docs/implementation/prospectus-basf-scope-repair/source-review-001'
graph=json.loads((ROOT/'docs/implementation/prospectus-repair-2026-10-06/phases/P1/attempt-009/source-graph.json').read_text())
units={u['id']:u for u in graph['units']}
admission=json.loads((ROOT/'docs/implementation/prospectus-basf-continuation-2026-10-05/phases/012-construct/basf-selection-admission.json').read_text())
construction=json.loads((ROOT/'docs/implementation/prospectus-adoption/phases/A1/attempt-006/product.json').read_text())
rows=json.loads((out/'baseline-brackets.json').read_text());brackets={r['id']:r for r in rows}

def source(document,page,line,quote=None):
    u=units[f'{document}:p{page}:l{line}'];a=0 if quote is None else u['raw'].index(quote);z=len(u['raw']) if quote is None else a+len(quote)
    return {'unit':u['id'],'document':document,'source_sha256':u['source_sha256'],'start':a,'end':z,'quote':u['raw'][a:z]}

def final(page,*lines):return [source(FINAL,page,i) for i in lines]

def margin(page,start,end):
    return [source(BASE,page,i) for i in range(start,end+1)
            if f'{BASE}:p{page}:l{i}' in units and units[f'{BASE}:p{page}:l{i}']['bbox'][0]<155]

premises={
    'issuer':final(2,10,11,12),
    'currency':final(3,20,21,22,23),
    'icsd':final(3,41,42,43,44,45,46,47),
    'temporary':final(3,36,37,38,39,40),
    'ngn':final(3,48,49,50,51),
    'holder_put':final(6,35,36,37,38,39,40,41,42,43),
    'issuer_call':final(6,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25),
    'rmb_call':final(6,44,45,46,54,55),
    'agent':final(7,20,21,22,23,24,25,26,27,28,29),
    'german_translation':final(7,48,49,50,51,52,53)+final(8,1,2,3,4),
    'listed_notice':final(7,40,41,42,43,44,45,46,47)+final(13,44,45,46,47,48,49,50,51),
}
rules=[]
def rule(number,kind,why,conditions,governing=(),value=None):
    row=brackets[number]
    target={k:row[k] for k in ('start','end','text','spans')}
    rule={'id':number,'operation':kind,'reason':why,'target':target,
          'premises':[s for condition in conditions for s in premises[condition]],
          'governing':list(governing),'review':'IMPLEMENTER_SOURCE_IMAGE_REVIEW; NOT INDEPENDENT LEGAL ADJUDICATION'}
    if value:
        rule['value']=value
        rule['premises'].append(value)
    rules.append(rule)

for number,kind,reason,conditions,governing in [
 ('B03','select','Non-CDS clearing alternative; both CBL and Euroclear selected',['icsd'],[]),
 ('B04','instruction','Multiple selected clearing systems: retain jeweils',['icsd'],[]),
 ('B05','select','Retain the selected CBL/Euroclear definition',['icsd'],[]),
 ('B06','exclude','Guarantee heading belongs to the BASF Finance alternative',['issuer'],margin(110,81,83)+margin(111,1,4)),
 ('B09','select','Payments through global note; preserve nested temporary-note certification',['temporary','icsd'],margin(113,70,76)),
 ('B10','exclude','EUR issue does not select RMB settlement proviso',['currency'],[]),
 ('B11','select','ICSD global-note payment discharges issuer under selected branch',['icsd'],margin(114,40,50)),
 ('B14','instruction','Retain call-amount reference for the selected issuer call',['issuer_call'],[]),
 ('B15','exclude','No specified-price holder put; change-of-control right is separate',['holder_put'],[]),
 ('B17','exclude','EUR issue does not select RMB maturity proviso',['currency'],[]),
 ('B19','select','BASF SE tax-call variant',['issuer'],margin(118,24,30)),
 ('B20','exclude','BASF Finance tax-call variant does not apply',['issuer'],margin(118,59,65)),
 ('B28','exclude','Specified-price holder-put priority in dated call is unselected',['holder_put'],[]),
 ('B30','instruction','NGN partial-redemption accounting applies in dated call',['ngn','icsd'],[]),
 ('B32','exclude','Specified-price holder-put priority in make-whole call is unselected',['holder_put'],[]),
 ('B34','instruction','NGN partial-redemption accounting applies in make-whole call',['ngn','icsd'],[]),
 ('B38','exclude','RMB-call paragraph reference is unselected',['rmb_call','currency'],[]),
 ('B46','select','Three named agent roles require the printed comma alternative',['agent'],[]),
 ('B47','exclude','Three-role heading uses comma then final conjunction',['agent'],[]),
 ('B48','select','Calculation-agent role is selected by final terms',['agent'],[]),
 ('B49','select','Three-role list uses comma before paying agent',['agent'],[]),
 ('B50','exclude','Use final conjunction before calculation agent',['agent'],[]),
 ('B51','select','Initially appointed calculation agent is supplied',['agent'],[]),
 ('B52','select','Non-CDS fiscal and paying agent address applies',['icsd','agent'],margin(124,1,7)),
 ('B53','select','Calculation-agent branch applies; designated office field remains unresolved',['agent','issuer_call'],margin(124,26,42)),
 ('B55','select','Three-role list uses comma before paying agent',['agent'],[]),
 ('B56','exclude','Use final conjunction before calculation agent',['agent'],[]),
 ('B57','select','Calculation-agent reference applies',['agent'],[]),
 ('B58','select','Plural designated offices for the selected agent roles',['agent'],[]),
 ('B59','select','Plural designated offices for the selected agent roles',['agent'],[]),
 ('B60','select','Calculation-agent appointment/change provision applies',['agent'],[]),
 ('B61','select','Replacement calculation-agent provision applies',['agent'],[]),
 ('B63','exclude','EUR instrument does not select US-dollar payment office provision',['currency'],[]),
 ('B64','exclude','CDS Canadian-agent provision is unselected',['icsd'],[]),
 ('B65','instruction','Maintain a calculation agent; numbering still requires explicit review',['agent'],[]),
 ('B67','select','Three-role list uses comma before paying agent',['agent'],[]),
 ('B68','exclude','Use final conjunction before calculation agent',['agent'],[]),
 ('B69','select','Calculation agent acts as issuer agent in the selected list',['agent'],[]),
 ('B70','select','BASF SE taxation variant',['issuer'],margin(125,3,9)),
 ('B71','exclude','BASF Finance taxation variant does not apply',['issuer'],margin(125,51,57)),
 ('B72','select','BASF SE default/quorum/notice variant',['issuer'],margin(126,34,40)),
 ('B73','exclude','BASF Finance default/quorum/notice variant does not apply',['issuer'],margin(127,46,52)),
 ('B74','select','BASF SE successor-debtor variant',['issuer'],margin(128,49,55)),
 ('B75','exclude','BASF Finance successor-debtor variant does not apply',['issuer'],margin(128,62,68)),
 ('B76','select','BASF SE guarantee-extension condition survives in substitution',['issuer'],margin(129,5,11)),
 ('B77','exclude','Guarantee amendment heading follows the inapplicable Finance variant',['issuer'],margin(131,32,38)),
 ('B78','exclude','BASF Finance guarantee amendment variant does not apply',['issuer'],margin(131,32,38)),
 ('B81','exclude','BASF Finance service-agent appointment is inapplicable',['issuer'],margin(132,50,56)),
 ('B83','exclude','German-only version unselected; German with English translation controls',['german_translation'],margin(133,37,43)),
]:rule(number,kind,reason,conditions,governing)

for number,page,line,quote,reason in [
 ('B01',3,29,None,'Copy the stated German aggregate principal amount'),
 ('B02',3,31,None,'Copy the stated German aggregate principal in words'),
 ('B07',4,58,None,'Copy the interest commencement date'),
 ('B08',4,60,'8. März','Copy day/month; the template itself supplies eines jeden Jahres'),
 ('B18',5,48,None,'Copy the selected maturity date'),
 ('B22',6,17,None,'Copy the selected call-date range without converting it into an event'),
 ('B23',6,21,None,'Copy the stated call amount description'),
 ('B41',5,48,None,'Copy maturity in the make-whole definition'),
 ('B42',5,48,None,'Copy maturity in the make-whole definition'),
 ('B43',7,11,'0,300','Copy the percentage numeral; the template already supplies percent'),
 ('B44',5,48,None,'Copy maturity in the benchmark definition'),
 ('B45',5,48,None,'Copy maturity in the benchmark definition'),
]:rule(number,'substitute',reason,[],value=source(FINAL,page,line,quote))

# Old code selected this entire branch just because Clearing System was checked.
raw=construction['raw_body'];old=next(r for r in construction['rules'] if r['rule']=='notice_clearing:selected')
a,b=old['start'],old['end'];spans=[]
for s in construction['source_map']:
    left,right=max(a,s['start']),min(b,s['end'])
    if left<right:spans.append(source(BASE,s['page'],int(s['unit'].rsplit('l',1)[1]),raw[left:right]))
notice_margin=[source(BASE,132,13,'Im Fall von')]+margin(132,14,19)
rules.append({'id':'notice-unlisted','operation':'exclude','reason':'Listed configuration uses §13(1) and its own §13(2); unlisted alternative does not apply',
 'target':{'start':a,'end':b,'text':raw[a:b],'spans':spans},'premises':premises['listed_notice'],
 'governing':notice_margin,'review':'IMPLEMENTER_SOURCE_IMAGE_REVIEW; NOT INDEPENDENT LEGAL ADJUDICATION'})

scope_pages={'base':[108,109,110,111,113,114,115,118,119,120,121,123,124,125,126,127,128,129,131,132,133],
             'final':[2,3,4,5,6,7,8,13]}
fields=('id','document','source_sha256','page','raw','bbox','text_sha256','visible')
guard_ids={s['unit'] for r in rules for s in r['target']['spans']+r['premises']+r['governing']}
# Pin reviewed page membership as well as values, including added instructions.
guarded_pages={BASE:scope_pages['base'],FINAL:scope_pages['final']}
guard_ids.update(u['id'] for u in graph['units'] if u['page'] in guarded_pages.get(u['document'],[]))
data={'version':'basf-reviewed-scope.v1','instrument_id':admission['issue_id'],'admission_sha256':digest(admission),
 'raw_body_sha256':digest(raw.encode()),'source_review':'docs/implementation/prospectus-basf-scope-repair/source-review-001/REVIEW.md',
 'guard_fields':list(fields),'guarded_pages':guarded_pages,'units':{key:digest({k:units[key][k] for k in fields}) for key in sorted(guard_ids)},
 'rules':rules,'independent_legal_review':False}
target=ROOT/'src/legalmath/prospectus/successor/basf_scope_review.json'
target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
resolved={r['id']:r['operation'] for r in rules}
notes=[]
for r in rows:
    parent=next((x for x in rules if x['operation']=='exclude' and x['target']['start']<=r['start'] and r['end']<=x['target']['end']),None)
    status=resolved.get(r['id']) or ('covered-by-exclusion:'+parent['id'] if parent else 'UNRESOLVED')
    reason='Explicit source-reviewed operation' if status!='UNRESOLVED' else (
        'Numbering/reference requires consistent section-wide transformation and source map' if r['text'].replace('[','').replace(']','').replace('(','').replace(')','').strip().isdigit() or r['id'] in ('B37','B62','B66') else
        'Additional call-table row layout is unspecified; retain empty placeholders for review' if r['id'] in ('B24','B25','B26','B27') else
        'Final terms names the calculation agent but supplies no designated office; do not erase that missing part')
    notes.append({'id':r['id'],'status':status,'reason':reason,'start':r['start'],'end':r['end'],'preview':r['preview']})
(out/'dispositions.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
review={'reviewed_pages':scope_pages,'image_hashes':{f'{label}-{p}.png':hashlib.sha256((out/f'{label}-{p}.png').read_bytes()).hexdigest() for label,pages in scope_pages.items() for p in pages},
 'data_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'explicit_rules':len(rules),'baseline_brackets':len(rows),
 'unresolved_inventory':[r['id'] for r in notes if r['status']=='UNRESOLVED'],'independent_legal_review':False}
(out/'review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({k:v for k,v in review.items() if k!='image_hashes'},indent=2))
