"""Reviewed source-based continuation of original BASF office task."""
from copy import deepcopy
from pathlib import Path
import json
import os
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority,REL,read,write,digest,file_hash
from legalmath.prospectus.successor import service
from scripts.prospectus_calendar_evidence import load,require

PLAN='docs/plans/prospectus-agent-notice-window-2026-10-17.md'
REVIEW=REL+'/reviews/agent-window-237'
ORIGINAL=REL+'/attempts/basf-office/attempt-002'
PRIOR=REL+'/attempts/reasoning-corpus/attempt-008'
CHANGED=['src/legalmath/prospectus/successor/calendar_facts.py']
BOUNDS={'preparation_seconds':60,'stage_seconds':110,'incremental_seconds':600,
    'new_bytes':64*1024**2,'reserve_bytes':2*1024**2,'test_starts':1,'native_calls':0,'gpu_calls':0}


def main():
    tick=time.monotonic();signal.alarm(60)
    a=Authority(ROOT);old,tasks,_=a.spec()
    require(old['revision']==236,'Wrong active revision')
    folder=ROOT/REVIEW;folder.mkdir(parents=True,exist_ok=False)
    write(folder/'started.json',{'command':['.venv/bin/python','scripts/prospectus_agent_window_prepare.py']},exclusive=True)
    events=a.events();history=[]
    for path in (ORIGINAL,PRIOR):
        e=next(e for e in reversed(events) if e.get('attempt')==path and e['kind'] in {'RECORD','ACCEPT','REJECT'})
        require(a.retained_evidence_valid(e),'Retained source/result changed')
        history.append({'attempt':path,'kind':e['kind'],'outputs_sha256':file_hash(ROOT/path/'outputs.json')})
    sources=read(ROOT/ORIGINAL/'source-review.json')
    for name,h in sources['images'].items():require(file_hash(ROOT/name)==h,'Original image changed')
    reading=next(r for r in read(ROOT/ORIGINAL/'agent-source-readings.json') if r['id']=='basf-agents:effectiveness-reference')
    require(reading['agent_reading']['notice_window_days']==[30,45] and reading['agent_reading']['insolvency_immediate_effect'] is True,'Wrong source clause')
    write(folder/'selected-source.json',reading,exclusive=True)
    before={str(p.relative_to(ROOT)):file_hash(p) for p in (ROOT/'src/legalmath').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    require(len(before)==452,'Wrong source baseline')
    write(folder/'before-methods.json',before,exclusive=True)
    for name in CHANGED:
        dest=folder/'before'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as out:out.write((ROOT/name).read_bytes())
    base=REL+'/attempts/law-applicability/attempt-008'
    ps=load(ROOT/base/'common-products.json.gz')
    data=load(ROOT/base/'cases/boundary-no-registration.json.gz')['input']
    data['calendar_facts'][0]['operator']='LE'
    try:service.law_product(ps['P1'],ps['P3'],law_input=data)
    except ValueError as error:require(str(error)=='Unexpected or missing fields','Unexpected missing-operator failure')
    else:raise ValueError('Upper-bound gap not reproduced')
    write(folder/'review.json',{'verdict':'PASS','original_images':sources['images'],'history':history,
        'source_read':'Original base124 image plus exact retained selected sentence/source pieces',
        'target':'NECESSARY_NOTICE_PRECONDITION_ONLY','unsupported_operator':'LE',
        'counterexample':'45 days plus1 microsecond is less than46 days but exceeds45 days',
        'production_before':452,'allowed_changed':CHANGED,'historical_unmeasured_seconds':'UNKNOWN'},exclusive=True)
    admissions=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-office']
    require(len(admissions)==old['budgets']['basf-office']['maximum_new_attempts']==2,'Wrong cumulative budget')
    new=deepcopy(old);new['revision']=237
    t=next(t for t in new['tasks'] if t['id']=='basf-office')
    require(not set(CHANGED)&set(t['inputs']),'Unexpected live mutable input')
    t.update(dossier=PLAN,reason='Compute inclusive30-to45-day source notice window and conditional insolvency exception without asserting actual effectiveness',
        agent_window={'version':'agent-window.v1','review':REVIEW,'bounds':BOUNDS,'allowed_changed':CHANGED,'whole_task_complete':False})
    support=[PLAN,str(Path(__file__).relative_to(ROOT)),ORIGINAL+'/source-review.json',ORIGINAL+'/agent-source-readings.json',
        PRIOR+'/outputs.json',*sources['images']]
    support += [str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file()]
    t['inputs']=sorted(set(t['inputs'])|set(support))
    new['budgets']['basf-office']['maximum_new_attempts']=3
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=237
    for row in routes['tasks']:
        if row['task']=='basf-office':row.update(phase=0,mode='local',task_sha256=digest(t),dossier=PLAN,remaining=t['reason'],
            next_action='Implement admitted GE/LE calendar operator, run source-bound notice and old full-answer consumers, record/refresh.',stop_condition=BOUNDS)
        elif row['task']=='reasoning-corpus':row.update(phase=3,remaining='008 recorded136 source-bound subset-minimal proofs,4096 independent cases and40 unchanged legacy answers; broader reasoning remains incomplete.',
            next_action='Preserve completed optional finite explanation evidence; inspect distinct reasoning limits and later installed validation.')
    route=REL+'/closure-routes-2026-10-17-agent-window-237.json'
    write(ROOT/route,routes,exclusive=True);new['continuation_review'].update(plan=PLAN,routes=route)
    for n in (PLAN,route,str(Path(__file__).relative_to(ROOT))):new['continuation_review']['bindings'][n]=file_hash(ROOT/n)
    review={'baseline':digest(old),'changes':t['reason'],'scope_unchanged':True,'budget_unchanged':False,
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'source_review':REVIEW+'/review.json'},'evidence_contract':PLAN,
        'budget_revision':{'budget_key':'basf-office','previous_maximum':2,'new_maximum':3,'retained_attempts':admissions,
            'reason':t['reason'],'next_discriminating_check':'Exact upper/lower boundaries,insolvency branch and80 prior full explanation consumers',
            'stop_condition':BOUNDS,'same_scope_authorization':'User-directed general build, source-based conditional proof without external-adviser prerequisite'}}
    a.validate_program(new)
    write(ROOT/REL/'proposals/agent-window-237.json',new,exclusive=True)
    write(ROOT/REL/'proposals/agent-window-237-review.json',review,exclusive=True)
    write(folder/'preparation-time.json',{'seconds':time.monotonic()-tick},exclusive=True)
    print(json.dumps({'revision_prepared':237,'retained_admissions':2,'seconds':time.monotonic()-tick}))
    signal.alarm(0)


if __name__=='__main__':main()
