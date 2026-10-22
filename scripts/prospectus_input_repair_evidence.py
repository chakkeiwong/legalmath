"""Actual complete-consumer replay; caller selects source or installed legalmath."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from legalmath.prospectus.successor import service,financial_profiles,cases,source_graph

BASE='docs/implementation/prospectus-execution-authority'
FOLDERS={
 'law':BASE+'/attempts/law-applicability/attempt-007',
 'law_inputs':BASE+'/attempts/law-applicability/attempt-006',
 'conversion':BASE+'/attempts/entitlement/attempt-006',
 'documents':BASE+'/attempts/source-authority/attempt-004',
}
DENOMINATORS={'law':{'valid':21,'original_refusals':2,'malformed':52,'boundaries':16},
 'conversion':{'original':3,'valid':8,'malformed':92,'reports':2},
 'documents':{'baseline':1,'valid':8,'malformed':208,'boundaries':12}}

def hash_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def require(ok,why):
    if not ok:raise ValueError(why)
def same(a,b,why):require(digest(a)==digest(b),'Complete result differs: '+why)
def load(p):
    raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if raw[:2]==bytes((31,139)) else raw)

def checked(root,config,kind,name):
    folder=root/FOLDERS[kind];manifest=folder/'outputs.json'
    require(hash_file(manifest)==config['manifests'][FOLDERS[kind]],'Retained manifest identity changed')
    files=load(manifest)
    require(name in files and hash_file(folder/name)==files[name],'Retained input changed: '+kind+'/'+name)
    return load(folder/name)

def refusal(fn,reason,label):
    try:fn()
    except ValueError as exc:
        require(str(exc)==reason,'Refusal reason differs: '+label)
        return {'refused':True,'reason':str(exc)}
    raise ValueError('Malformed/excluded input accepted: '+label)

def validate_record(value):
    require(set(value)==set(DENOMINATORS),'Missing repair family')
    for family,groups in DENOMINATORS.items():
        require(set(value[family])==set(groups),'Missing repair group: '+family)
        for group,n in groups.items():
            rows=value[family][group]
            require(isinstance(rows,list) and len(rows)==n,'Missing cases: '+family+'/'+group)
            require(all(isinstance(row,dict) and row for row in rows),'Missing case detail')
    return {family:{key:len(rows) for key,rows in groups.items()} for family,groups in value.items()}

def evaluate(root,config):
    root=Path(root);get=lambda kind,name:checked(root,config,kind,name)
    for name,h in config['source_files'].items():require(hash_file(root/name)==h,'Original source binding changed')
    products=get('law_inputs','common-products.json.gz')
    law_cases=get('law_inputs','favorable-deposit-P4.json.gz')['payload']['cases']
    def execute(law):
        p4=service.law_product(products['P1'],products['P3'],cases=law_cases,law_input=law)
        answer=service.consume({**products,'P4':p4},root,mode='current')
        require(answer['may_execute_transaction'] is False and answer['independent_legal_acceptance'] is False,'Conditional boundary changed')
        return {'P4':p4,'answer':answer}
    law={k:[] for k in DENOMINATORS['law']};evidence=get('law','consumer-evidence.json')
    for row in evidence['valid']:
        name=row['case'];actual=execute(get('law_inputs',name+'-input.json.gz'))
        same(actual,get('law','valid/'+name+'.json.gz'),'law/'+name)
        law['valid'].append({'case':name,**actual})
    for row in evidence['original_refusals']:
        inp=get('law_inputs',row['case']+'-input.json.gz')
        law['original_refusals'].append({'case':row['case'],**refusal(lambda:execute(inp),row['reason'],row['case'])})
    favorable=get('law_inputs','favorable-deposit-input.json.gz')
    for row in evidence['new_refusals']:
        inp=deepcopy(favorable);inp[row['target']][0][row['field']]=row['value']
        law['malformed'].append({'case':row['id'],**refusal(lambda:execute(inp),row['reason'],row['id'])})
    for row in evidence['boundaries']:
        old=get('law','boundaries/'+row['case']+'.json.gz');actual=execute(old['input'])
        same(actual,{k:old[k] for k in ('P4','answer')},'law boundary '+row['case'])
        law['boundaries'].append({'case':row['case'],**actual})
    conversion={k:[] for k in DENOMINATORS['conversion']}
    original=cases.financial_cases(root);same(original,get('conversion','original-valid.json'),'all original financial cases')
    conversion['original']=original
    def assess(s):return financial_profiles.assess({'instrument_id':s['issue_id'],'documents':[{'sha256':s['source_sha256']}]},s)
    for group,filename in [('valid','valid-controls.json.gz'),('malformed','adverse-controls.json.gz')]:
        for row in get('conversion',filename):
            actual=assess(row['input']);same(actual,row['result'],'conversion '+group)
            conversion[group].append({**row,'result':actual})
    carrier={**products,'P4':get('law_inputs','open-P4.json.gz')}
    for name in ('valid','refusal'):
        financial=deepcopy(original)
        if name=='refusal':
            for item in financial:
                if item['instrument_id'].startswith('deutsche'):continue
                s=deepcopy(item['question']['value']['inputs']);s['holdings'][0]['legal_holder_id']=' '
                actual=cases.financial_cases(root,{item['instrument_id']:s})[0];item.clear();item.update(actual)
        p5=service.financial_product(products['P1'],products['P2'],products['P3'],cases=financial)
        actual={'P5':p5,'answer':service.consume({**carrier,'P5':p5},root,mode='current')}
        same(actual,get('conversion',name+'-report.json.gz'),'conversion '+name+' report')
        conversion['reports'].append({'case':name,**actual})
    documents={k:[] for k in DENOMINATORS['documents']}
    baseline=get('documents','baseline-answer.json.gz')
    request=load(root/(BASE+'/reviews/document-time-validation/request.json'))
    actual=service.assess(request,root);same(actual,baseline,'document baseline')
    documents['baseline'].append(actual)
    for row in get('documents','valid-controls.json.gz'):
        actual=service.assess(row['input'],root);same(actual,row['answer'],'document missing/null')
        documents['valid'].append({**row,'answer':actual})
    for row in get('documents','adverse-controls.json.gz'):
        inp=deepcopy(request);inp['bundle']['purpose']=row['purpose'];inp['bundle']['documents'][0][row['field']]=row['bad']
        documents['malformed'].append({**row,**refusal(lambda:service.assess(inp,root),row['reason'],row['field'])})
    for row in get('documents','boundary-controls.json.gz'):
        graph=source_graph.build(row['input']['bundle'],root);same(graph,row['graph'],'document boundary graph')
        if 'answer' in row:
            actual=service.assess(row['input'],root);same(actual,row['answer'],'document boundary answer')
            documents['boundaries'].append({**row,'graph':graph,'answer':actual})
        else:
            check=refusal(lambda:service.assess(row['input'],root),row['refusal'],'excluded document')
            documents['boundaries'].append({**row,'graph':graph,'checked_refusal':check})
    record={'law':law,'conversion':conversion,'documents':documents};validate_record(record)
    return record
