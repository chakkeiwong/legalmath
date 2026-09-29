"""Complementary assurance evidence and durable bounded discrepancy actions.

Agreement remains a scoped observation. No API in this module grants legal
acceptance or changes a candidate to fit another backend.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import fcntl
import hashlib
import json
import re


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def page_discrepancy(left,right):
    """Whitespace normalization only; token deltas explain, never certify equality."""
    norm=lambda text:re.sub(r'\s+',' ',text).strip()
    a,b=norm(left),norm(right)
    return {'agreement':bool(a) and a==b,'left_empty':not a,'right_empty':not b,
            'left_sha256':identity(left),'right_sha256':identity(right),
            'left_only':list((Counter(a.split())-Counter(b.split())).elements()),
            'right_only':list((Counter(b.split())-Counter(a.split())).elements()),
            'comparison':'whitespace-normalized exact sequence; token deltas diagnostic only'}


def assess_methods(results,required,claim_hash):
    if not required or len(required)!=len(set(required)):raise ValueError('Explicit unique required methods needed')
    findings=[];by_id={}
    for row in results:
        mid=row.get('method_id')
        if not isinstance(mid,str) or mid in by_id:raise ValueError('Missing or duplicate method identity')
        by_id[mid]=row
        if row.get('claim_hash')!=claim_hash:findings.append({'method':mid,'kind':'STALE_INPUT'})
        if row.get('status') not in ('AGREES','DISAGREES','UNRESOLVED','UNAVAILABLE','ERROR'):
            raise ValueError('Unknown method status')
        if not row.get('family') or not row.get('evidence_hash') or not isinstance(row.get('shared_dependencies'),list):
            raise ValueError('Missing provenance')
        if row['status']!='AGREES':findings.append({'method':mid,'kind':row['status']})
    for mid in required:
        if mid not in by_id:findings.append({'method':mid,'kind':'MISSING_REQUIRED_METHOD'})
    families={r['family'] for r in results if r['method_id'] in required}
    if len(families)<2:findings.append({'kind':'INSUFFICIENT_METHOD_FAMILIES'})
    return {'claim_hash':claim_hash,'status':'UNCERTAINTY_RETAINED' if findings else 'REQUIRED_CHECKS_AGREE',
            'findings':findings,'required':required,'methods':deepcopy(results),'families':sorted(families),
            'statistical_independence_established':False,'legal_correctness_established':False,'release_eligible':False}


class Investigation:
    """Reserve before dispatch. Resume preserves consumed actions and uncertainty.

    Result-producing callbacks perform fixed evidence actions. They cannot mark
    a legal issue resolved; disposition remains an explicit later decision.
    """
    def __init__(self,path,inputs,maximum=2):
        if type(maximum) is not int or not 0<=maximum<=3:raise ValueError('Action budget must be between zero and three')
        self.path=Path(path);self.inputs=identity(inputs);self.maximum=maximum

    def run(self,actions):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            data=json.loads(self.path.read_text()) if self.path.exists() else {
                'input_hash':self.inputs,'maximum':self.maximum,'actions':[],'status':'UNRESOLVED','release_eligible':False}
            if data['input_hash']!=self.inputs or data['maximum']!=self.maximum:raise ValueError('Stale investigation input or budget')
            if len(data['actions'])>self.maximum or len({r['name'] for r in data['actions']})!=len(data['actions']):
                raise ValueError('Invalid action history length or duplicate name')
            for index,row in enumerate(data['actions']):
                if row['sequence']!=index or row['action_id']!=identity([self.inputs,index,row['name']]):raise ValueError('Corrupt action history')
                if row['status']=='RESERVED':row['status']='INTERRUPTED'
                if row['status'] not in ('EXECUTED','FAILED','INTERRUPTED'):raise ValueError('Invalid action outcome')
                if row['status']=='EXECUTED' and ('result' not in row or 'result_hash' not in row):raise ValueError('Missing executed evidence')
                if 'result' in row and row.get('result_hash')!=identity(row['result']):raise ValueError('Result history changed')
            names=[a[0] for a in actions]
            if len(names)!=len(set(names)):raise ValueError('Action names must be unique')
            for name,action in actions:
                if any(r['name']==name for r in data['actions']):continue
                if len(data['actions'])>=self.maximum:break
                index=len(data['actions']);row={'sequence':index,'name':name,'action_id':identity([self.inputs,index,name]),'status':'RESERVED'}
                data['actions'].append(row);save(self.path,data)
                try:
                    result=action();row.update(status='EXECUTED',result=result,result_hash=identity(result))
                except Exception as exc:
                    row.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
                save(self.path,data)
            data['status']='UNCERTAINTY_RETAINED';data['budget_exhausted']=len(data['actions'])>=self.maximum
            data['resolution']='No automatic semantic resolution from retries or agreement.'
            save(self.path,data);return data


def conclusion_support(extensions,conclusions,complete):
    if not complete:return {'status':'INCOMPLETE_ENUMERATION','skeptical_conclusions':[]}
    if not extensions:return {'status':'NO_STABLE_EXTENSION','skeptical_conclusions':[]}
    values=[{conclusions[a] for a in ext} for ext in extensions]
    return {'status':'COMPLETE_NONEMPTY','skeptical_conclusions':sorted(set.intersection(*values))}


def clingo_extensions(arguments,attacks,maximum_models=4096):
    """Numeric encoding prevents model-written ASP or identifier injection."""
    if len(arguments)>12 or len(set(arguments))!=len(arguments) or type(maximum_models) is not int or not 1<=maximum_models<=4096:
        raise ValueError('Unsupported graph or enumeration bound')
    ids={v:i for i,v in enumerate(arguments)}
    if any(len(e)!=2 or any(x not in ids for x in e) for e in attacks):raise ValueError('Invalid attack endpoint')
    import clingo
    program='\n'.join([f'arg({i}).' for i in ids.values()]+[f'att({ids[a]},{ids[b]}).' for a,b in attacks])
    program+='\n{selected(X)} :- arg(X).\nattacked(Y) :- selected(X),att(X,Y).\n'
    program+=':- selected(X), selected(Y), att(X,Y).\n:- arg(X), not selected(X), not attacked(X).\n#show selected/1.\n'
    ctl=clingo.Control(['0','--warn=none']);ctl.add('base',[],program);ctl.ground([('base',[])])
    extensions=[]
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            if len(extensions)>=maximum_models:
                handle.cancel();return {'extensions':extensions,'complete':False,'status':'ENUMERATION_LIMIT','program':program}
            extensions.append(sorted(arguments[s.arguments[0].number] for s in model.symbols(shown=True)))
        result=handle.get()
    return {'extensions':sorted(extensions),'complete':bool(result.exhausted),'status':'COMPLETE' if result.exhausted else 'UNKNOWN',
            'program':program,'legal_premises_verified':False}


def cvc5_compare(left,right,names,timeout_ms=3000):
    """Independent encoder for Boolean RuleIR bodies under T/F/U states.

    Conflict, scope, arithmetic, dates and binding alignment are outside this
    function's contract. Each factual value has disjoint true/false indicators.
    """
    if not names or len(names)>12 or len(set(names))!=len(names) or not 1<=timeout_ms<=30000:
        raise ValueError('Invalid domain or timeout')
    import cvc5
    from cvc5 import Kind as K
    tm=cvc5.TermManager();solver=cvc5.Solver(tm)
    solver.setLogic('QF_UF');solver.setOption('produce-models','true');solver.setOption('tlimit-per',str(timeout_ms))
    variables={n:(tm.mkConst(tm.getBooleanSort(),f'x{i}t'),tm.mkConst(tm.getBooleanSort(),f'x{i}f')) for i,n in enumerate(names)}
    term=lambda k,*xs:tm.mkTerm(k,*xs)
    for t,f in variables.values():solver.assertFormula(term(K.NOT,term(K.AND,t,f)))
    def encode(node,depth=0):
        if depth>32:raise ValueError('Expression depth')
        op=node['op']
        if op=='fact':return variables[node['name']]
        if op=='literal' and node['type']=='bool' and type(node['value']) is bool:
            return tm.mkBoolean(node['value']),tm.mkBoolean(not node['value'])
        if op=='not':
            t,f=encode(node['arg'],depth+1);return f,t
        if op in ('all','any') and node['args']:
            pairs=[encode(n,depth+1) for n in node['args']]
            if len(pairs)==1:return pairs[0]
            kt,kf=(K.AND,K.OR) if op=='all' else (K.OR,K.AND)
            return term(kt,*(p[0] for p in pairs)),term(kf,*(p[1] for p in pairs))
        raise ValueError('UNSUPPORTED_BOOLEAN_FRAGMENT')
    try: a,b=encode(left),encode(right)
    except (ValueError,KeyError,TypeError) as exc:
        return {'status':'UNSUPPORTED','reason':str(exc),'equivalence_established':False}
    solver.assertFormula(term(K.OR,term(K.DISTINCT,a[0],b[0]),term(K.DISTINCT,a[1],b[1])))
    result=solver.checkSat()
    status='EQUIVALENT_WITHIN_DOMAIN' if result.isUnsat() else 'DIFFERENT' if result.isSat() else 'UNKNOWN'
    witness=None
    if result.isSat():
        witness={n:('T' if solver.getValue(v[0]).getBooleanValue() else 'F' if solver.getValue(v[1]).getBooleanValue() else 'U') for n,v in variables.items()}
    return {'status':status,'witness':witness,'domain':{n:['T','F','U'] for n in names},
            'scope':'Boolean body only; fact bindings assumed identical; conflict excluded',
            'equivalence_established':result.isUnsat(),'legal_correctness_established':False,'release_eligible':False}
