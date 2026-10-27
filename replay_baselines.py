"""Deterministic local replays; no provider dispatch or legal promotion."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import sys
sys.path[:0] = [str(Path(__file__).parent/'src'), str(Path(__file__).parent)]
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer, require
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, BoundDispatch
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance import bounded_references as refs
from legalmath.interpretation.assurance.phased import context_disposition, context_references, warrant_references
from legalmath.interpretation.assurance.phased import correction_input, review_repair
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from legalmath.interpretation.assurance.legal_locators import verify_index

ROOT=Path('/home/chakwong/python/legalmath')
BASE=ROOT/'artifacts/legal-mission-control/2026-10-24/window-continuation/service-inheritance/live/arms'
OUT=ROOT/'artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair'
def read(p): return json.loads(p.read_text())
def ref(p): return {'path':str(p.relative_to(ROOT)), 'sha256':sha256(p.read_bytes()).hexdigest()}
def save(name,value):
    p=OUT/name
    if p.exists(): require(read(p)==value,'Refuse changed replay output: '+name)
    else: p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def outcome(fn):
    try: return {'status':'VALIDATED','value':fn()}
    except Exception as e: return {'status':'FAILED','error':getattr(e,'code',type(e).__name__),
        'reason':str(getattr(e,'details',None) or e)}
def product(q):
    base=BASE/q/'baseline'; identity=read(base/'identity.json')
    route=object.__new__(ContextRoute); route.records=read(base/'source-store.json')
    require(digest(route.records)==identity['store_hash'],'Changed source store')
    route.envelope=route.reconstruct(); require(digest(route.envelope)==identity['input_hash'],'Changed source envelope')
    route.units={u['unit_id']:u for u in route.envelope['source_packet']['units']}
    route.input_hash=identity['input_hash']; route.limits=Limits(**identity['limits'])
    route.encode=tokenizer(ROOT/'.localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken')
    for index in route.envelope.get('legal_indexes',[]):
        verify_index(route.envelope['source_packet'],index,root=ROOT,expected_index_hash=index['index_hash'])
    p=object.__new__(BoundedProduct); p.root=ROOT; p.route=route
    return p,base
def assert_request(p,request,q):
    require(request['input_hash']==p.route.input_hash,'Changed question input')
    for r in request['records']:
        require(r==p.route.records.get(r['id']),'Changed delivered source')
        require(q in p.acquisition_questions(r),'Foreign question source')
def check_warrant(p,request,value):
    assert_request(p,request,'p14')
    return review_repair.validate_warrant(p,value,request['payload']['issues'],
        request['required_considered'][0],request['records'],request['payload']['answer'],explicit_target=True)

def warrants():
    p,base=product('p14'); rows=[]; adverse=[]
    for folder in sorted((base/'calls').iterdir()):
        if not folder.name.startswith('warrant-') or not (folder/'result.json').exists():continue
        retained=read(folder/'result.json')
        if retained.get('reason')!='Need waiver quotation is absent from the actual answer':continue
        request=read(folder/'request.json'); raw=read(folder/'raw.json')['value']; schema=read(folder/'schema.json')
        before=outcome(lambda:check_warrant(p,request,raw))
        wire=deepcopy(read(folder/'wire-response.json')['value'])
        proposal=deepcopy(request); proposal[warrant_references.FIELD]=warrant_references.PROFILE
        binding=refs.prepare(proposal,schema)
        for d in wire['decisions']: d['answer_evidence']={'answer_field':d['answer_evidence']['path']}
        decoded_result=outcome(lambda:refs.resolve(wire,binding,maximum_bytes=p.route.limits.decoded_output_bytes))
        decoded=decoded_result.get('value')
        if decoded is not None:
            expected=deepcopy(raw)
            for d in expected['decisions']:
                d['answer_evidence']=context_references.selections(proposal)[d['answer_evidence']['path']]
            require(decoded==expected,'Warrant simulation changed more than exact quotation')
            after=outcome(lambda:check_warrant(p,proposal,decoded))
        else:
            after=decoded_result
        rows.append({'call':folder.name,'request':ref(folder/'request.json'),'raw':ref(folder/'raw.json'),
            'retained_result':ref(folder/'result.json'),'baseline':before,'simulation':after,
            'dispositions':[d['disposition'] for d in raw['decisions']],
            'only_answer_quote_replaced':True,'legal_acceptance':False})
        if not adverse and decoded is not None:
            for damage in ('foreign_quote','changed_target','missing_support','lost_issue','necessary_missing_evidence'):
                bad=deepcopy(decoded); d=bad['decisions'][0]
                if damage=='foreign_quote':d['answer_evidence']['quote']='Invented exact quotation.'
                elif damage=='changed_target':d['correction_target']='DEPENDENCY_ONLY'
                elif damage=='missing_support':d['support']=[]
                elif damage=='lost_issue':bad['decisions']=[]
                else:d['blocking_source_gaps']=deepcopy(raw['source_gaps'][:1])
                if damage=='necessary_missing_evidence' and not d['blocking_source_gaps']:continue
                test=outcome(lambda:check_warrant(p,proposal,bad))
                require(test['status']=='FAILED','Adverse warrant passed: '+damage)
                adverse.append({'damage':damage,**test})
    require(len(rows)==20,'Changed P14 quotation-failure population')
    result={'kind':'LOCAL_WARRANT_PROTOCOL_SIMULATION','provider_calls':0,'rows':rows,
        'counts':dict(Counter(r['simulation']['status'] for r in rows)), 'adverse_controls':adverse}
    save('p14-warrant-replay-final.json',result); print('P14',result['counts'],flush=True)

def gatecoin():
    p,base=product('gatecoin'); folder=base/'calls/audit-context-disposition-gatecoin-32ac9ac15b66bae6e6868d04'
    request=read(folder/'request.json'); raw=read(folder/'raw.json')['value']; shape=read(folder/'schema.json')
    def check(value,req):
        assert_request(p,req,'gatecoin'); v=req['payload']
        return context_disposition.validate(p,'gatecoin',value,v['answer'],v['item'],
            v['prior_needs'],req['records'],v['source_delivery_failures'])
    before=outcome(lambda:check(raw,request)); proposal=deepcopy(request)
    proposal[context_references.FIELD]=context_references.PROFILE
    wire=deepcopy(read(folder/'wire-response.json')['value'])
    for d in wire['need_dispositions']:d['answer_evidence']={'answer_field':d['answer_evidence']['path']}
    def simulate():
        value=refs.resolve(wire,refs.prepare(proposal,shape),maximum_bytes=p.route.limits.decoded_output_bytes)
        for field in ('verdict','reason','issues','support','source_gaps','considered'):
            require(value[field]==raw[field],'Changed Gatecoin substantive field '+field)
        check(value,proposal)
        return {'verdict':value['verdict'],'retained_needs':len(proposal['payload']['prior_needs']),
            'decoded_context_needs':len(value['context_needs'])}
    result={'request':ref(folder/'request.json'),'raw':ref(folder/'raw.json'),
        'baseline':before,'simulation':outcome(simulate),'provider_calls':0,'legal_acceptance':False}
    save('gatecoin-context-replay.json',result); print('Gatecoin context',result['simulation']['status'],flush=True)
    capacity=base/'capacity/correction-gatecoin'
    request=load_exact(capacity/'request.json'); shape=load_exact(capacity/'schema.json')
    provider=object.__new__(BoundedCodexProvider)
    provider.encode=p.route.encode; provider.limits=p.route.limits
    provider.routing={'model':'gpt-6.1-sol','provider':'openai','fields':{}}
    provider.executable='codex-measurement-only-never-executed'
    dispatch=object.__new__(BoundDispatch); dispatch.route=p.route; dispatch.provider=provider; dispatch.capacity_manager=None
    before=outcome(lambda:dispatch.measure(request,shape))
    selected=deepcopy(request); selected[correction_input.FIELD]=correction_input.PROFILE
    after=outcome(lambda:dispatch.measure(selected,shape))
    plain=refs.prepare(request,shape); packed=refs.prepare(selected,shape)
    restored=correction_input.expand(packed['request']); restored.pop(correction_input.FIELD)
    require(restored==plain['request'] and packed['schema']==plain['schema'],'Changed correction input/schema')
    require(before['status']=='FAILED' and before['error']=='E_RESOURCE_LIMIT','Capacity baseline changed')
    result={'request':ref(capacity/'request.json'),'schema':ref(capacity/'schema.json'),
        'baseline':before,'candidate':after,'exact_expansion_equal':True,'response_schema_equal':True,
        'source_gap_occurrences':len(request['payload']['retained_source_gaps']),
        'unique_gap_values':len(packed['request'][correction_input.TABLE]['values']),
        'provider_calls':0,'legal_acceptance':False}
    save('gatecoin-correction-capacity.json',result); print('Gatecoin capacity',after,flush=True)

if __name__=='__main__':
    warrants(); gatecoin()
