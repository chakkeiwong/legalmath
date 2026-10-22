"""Revalidate sealed010 once; never regenerate its successful candidate."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as authority_digest
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor.contracts import digest
from scripts import prospectus_bes_cash_flow as b

REVIEW=REL+'/reviews/bes-cash-flow-211'
PLAN='docs/plans/prospectus-bes-cash-flow-validation-2026-10-17.md'
CANDIDATE=b.SOURCE+'/attempt-010'
PREVIOUS_REVIEW=REL+'/reviews/bes-cash-flow-210'
TEST='tests/prospectus/test_bes_cash_flow_revalidation.py'
ROUTER='src/legalmath/prospectus/build_contract.py'
METHODS=('scripts/prospectus_bes_cash_flow_revalidation.py',TEST,ROUTER)
SELECTOR={'version':'bes-cash-flow-retained-validation.v1','candidate':CANDIDATE,
    'preparation_seconds':30,'validation_seconds':180,'cumulative_seconds':1560,
    'old010_admission_to_rejection_charge_seconds':250,'new_extraction_OCR_network_GPU':0,
    'candidate_regeneration':False,'incremental_bytes':32*1024**2,'cumulative_bytes':200*1024**2,
    'reserve_bytes':262144}

def verify_method_parity(expected,current):
    b.require(set(expected)==set(current),'Protected method inventory changed')
    b.require({k:v for k,v in expected.items() if k!=ROUTER}==
              {k:v for k,v in current.items() if k!=ROUTER},'Protected substantive010 method changed')

def prior_cost(root):
    events=[e for e in Authority(root).events() if e.get('attempt')==CANDIDATE]
    first=next(e for e in events if e['kind']=='ADMIT')
    last=next(e for e in reversed(events) if e['kind']=='REJECT')
    elapsed=(datetime.fromisoformat(last['at'])-datetime.fromisoformat(first['at'])).total_seconds()
    b.require(last['reason']=='Cumulative command/acceptance-validation time ceiling' and 0<=elapsed<=250,
              'Original rejection or conservative timing bound differs')
    failed=read(root/b.SOURCE/'attempt-009/run-manifest.json')
    prep=read(root/PREVIOUS_REVIEW/'preparation.json')['seconds']
    return {'seconds':948.8160658078269+prep+failed['wall_seconds']+250,
        'historical003_008_seconds':948.8160658078269,'preparation_through210_seconds':prep,
        'failed009_seconds':failed['wall_seconds'],'actual010_admit_to_reject_interval_seconds':elapsed,
        'charged010_interval_seconds':250,'candidate010_seconds_included_not_added':
        read(root/CANDIDATE/'run-manifest.json')['wall_seconds'],
        'timing_kind':'Conservative whole010 interval includes candidate, acceptance and intervening idle time',
        'exclusions':'Older unknown time, agent authoring/reading and historical startup exclusions remain disclosed'}

def protected(root):
    old=read(root/PREVIOUS_REVIEW/'frozen.json')
    verify_method_parity(old['methods'],{n:file_hash(root/n) for n in old['methods']})
    b.require(old['inputs']=={n:file_hash(root/n) for n in old['inputs']},'Protected original210 source changed')
    candidate=root/CANDIDATE;outputs=read(candidate/'outputs.json')
    b.require(outputs=={n:file_hash(candidate/n) for n in outputs},'Sealed010 output changed')
    r,m=read(candidate/'result.json'),read(candidate/'run-manifest.json')
    b.require(r['status']=='PASS' and m['status']=='PASS' and r['task_complete'] is False
              and r['whole_program_complete'] is False,'Original candidate did not pass finite checks')
    b.require(m['methods']==old['methods'] and m['data_version']==old['inputs'],'Candidate identities differ')
    checked_tests(candidate/'tests.xml',182)
    return old,outputs

def storage(root,attempt,enforce=True):
    inherited=b.storage(root,attempt,enforce=False)
    extra={root/n for n in (METHODS[0],TEST,PLAN)}
    extra|={p for folder in (root/REVIEW,root/CANDIDATE,root/REL/'continuation-reviews/bes-cash-flow-211-record')
            for p in folder.rglob('*') if p.is_file()}
    extra|={root/REL/'proposals'/('bes-cash-flow-211'+suffix) for suffix in ('.json','-review.json')}
    count=sum(p.stat().st_size for p in extra if p.is_file())
    result={**inherited,'new_bytes':inherited['new_bytes']+count,'combined_bytes':inherited['combined_bytes']+count}
    if enforce:
        b.require(result['new_bytes']<SELECTOR['incremental_bytes']-SELECTOR['reserve_bytes']
            and result['combined_bytes']<SELECTOR['cumulative_bytes']-SELECTOR['reserve_bytes'],
            'Cumulative211 retention ceiling')
    return result

def validate_submission(root,attempt,task):
    root,attempt=Path(root),Path(attempt);started=time.monotonic();passed=False
    old_handler=signal.getsignal(signal.SIGALRM)
    def expired(_s,_f):raise ValueError('Retained acceptance180second ceiling')
    signal.signal(signal.SIGALRM,expired);signal.alarm(180)
    try:
        b.require(task['id']=='source-bes-dep-07' and task.get('cash_flow_revalidation')==SELECTOR,'Wrong reviewed211 task')
        frozen=read(root/REVIEW/'frozen.json')
        b.require(frozen['methods']=={n:file_hash(root/n) for n in METHODS},'Reviewed211 method changed')
        b.require(set(frozen['inputs'])|set(METHODS)|{REVIEW+'/frozen.json'}<=set(task['inputs']),'Unbound211 evidence')
        b.require(frozen['inputs']=={n:file_hash(root/n) for n in frozen['inputs']},'Frozen211 source changed')
        protected(root)
        b.require(read(attempt/'candidate-reference.json')=={'path':CANDIDATE,
            'outputs_sha256':file_hash(root/CANDIDATE/'outputs.json')},'Candidate reference changed')
        result=read(attempt/'result.json')
        b.require(result['status']=='PASS' and result['scope']=='RETAINED_CANDIDATE_REQUIRES_SUBSTANTIVE_VALIDATION'
            and result['task_complete'] is False and result['whole_program_complete'] is False,'Reference package promotes candidate')
        candidate=root/CANDIDATE;ps=b.products(root);profile=read(candidate/'profile.json')
        b.require(digest(profile)==digest(b.make_profile(root,ps['P1']['payload']['graph'])),'Actual profile differs')
        baseline=b.load(root/b.NORMAL/'candidate-answer.json.gz');revised=b.updated(ps,profile)
        actual=b.service.consume(revised,root,mode='frozen',include_artifacts=True)
        b.verify_answer(actual,baseline,revised);delta=b.load(candidate/'normal-answer-delta.json.gz')
        b.require(digest({**baseline,**delta})==digest(actual),'Sealed delta differs from current actual answer')
        fixture=b.load(root/b.FIXTURE)
        b.require(digest(fixture['original_units'])==digest(b.load(root/b.PRIOR/'source-units.json.gz'))
            and digest(fixture['original_reading'])==digest(b.load(root/b.PRIOR/'profile.json.gz')['reading']),
            'Independent original-source fixture changed')
        independent=b.verify_review(actual[b.production.ADDED],profile,ps['P1']['payload']['graph'],
            fixture['original_reading'],fixture['original_units'],root)
        b.require(read(candidate/'verification.json')==independent
            and read(candidate/'controls.json')==b.controls(root,fixture),'Retained independent checks differ')
        spec=read(candidate/'composition.json')
        b.require(spec['normal_answer_sha256']==digest(actual)
            and spec['normal_baseline']==b.NORMAL+'/candidate-answer.json.gz'
            and spec['normal_baseline_file_sha256']==file_hash(root/spec['normal_baseline'])
            and spec['prior_composition']==b.PRIOR+'/answer-composition.json'
            and spec['prior_composition_file_sha256']==file_hash(root/spec['prior_composition'])
            and spec['complete_prior_answer_preserved'] is True and spec['large_answer_copies']==0,'Composition identity differs')
        del actual,baseline,ps,revised
        prior=b.reconstruct(root,spec['prior_composition'])
        b.require(digest(prior)==spec['prior_answer_sha256']
            and digest({**prior,b.production.ADDED:delta[b.production.ADDED]})==spec['complete_composed_answer_sha256'],
            'Complete prior answer not preserved')
        costs=prior_cost(root);prep=read(root/REVIEW/'preparation.json')['seconds'];elapsed=time.monotonic()-started
        print(json.dumps({'stage':'substantive-validation-complete','seconds':elapsed,
            'prior_charged_seconds':costs['seconds'],'preparation_seconds':prep,
            'cumulative_charged_seconds':costs['seconds']+prep+elapsed,'relations':8,'adverse_refusals':42}),flush=True)
        b.require(prep<=30 and elapsed<=180 and costs['seconds']+prep+elapsed<=1560,'Reviewed211 clock ceiling')
        storage(root,attempt);passed=True
        return True
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,old_handler)
        print(json.dumps({'stage':'retained-validation-clock','seconds':time.monotonic()-started,'passed':passed}),flush=True)

def prepare():
    start=time.monotonic();folder=ROOT/REVIEW;folder.mkdir(parents=True,exist_ok=True)
    old,outputs=protected(ROOT);costs=prior_cost(ROOT)
    with (folder/'tests.log').open('x') as log:
        subprocess.run([sys.executable,'-m','pytest',TEST,'tests/prospectus/test_build_contract.py','-q',
            '--junitxml='+str(folder/'tests.xml')],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),
            'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1'},timeout=20,stdout=log,stderr=subprocess.STDOUT,check=True)
    preparation={'seconds':time.monotonic()-start,'status':'PASS','cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'command':[sys.executable,'-m','scripts.prospectus_bes_cash_flow_revalidation','prepare'],
        'prior_cost':costs,'accounting_exclusions':'Later proposal/freeze hashing and agent authoring excluded; all preparation tests charged'}
    b.require(preparation['seconds']<=30,'Preparation211 time ceiling')
    write(folder/'preparation.json',preparation,exclusive=True)
    auth=Authority(ROOT);program,tasks,_=auth.spec();b.require(program['revision']==210,'Wrong211 baseline')
    inputs=set(old['inputs'])|set(old['methods'])|{CANDIDATE+'/outputs.json',PREVIOUS_REVIEW+'/frozen.json',PLAN,REVIEW+'/preparation.json'}
    inputs|={CANDIDATE+'/'+n for n in outputs}
    frozen={'methods':{n:file_hash(ROOT/n) for n in METHODS},'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)},
        'selector':SELECTOR,'protected_substantive_methods_equal':True,'only_allowed_old_method_change':ROUTER}
    write(folder/'frozen.json',frozen,exclusive=True)
    state=storage(ROOT,ROOT/b.SOURCE/'attempt-011')
    b.require(state['combined_bytes']+12*1024**2+262144<200*1024**2,'211 support/admission forecast exceeds retention')
    write(folder/'preflight.json',{**state,'forecast_bytes':12*1024**2,'prior_cost':costs},exclusive=True)
    proposal=deepcopy(program);proposal['revision']=211
    task=next(t for t in proposal['tasks'] if t['id']=='source-bes-dep-07')
    task.update(dossier=PLAN,cash_flow_revalidation=SELECTOR,timeout_seconds=210,
        reason='Revalidate sealed successful010 once with reviewed180second acceptance bound; preserve rejected receipt and substantive tests, clock and source history.')
    task['inputs']=sorted(set(task['inputs'])|inputs|set(METHODS)|{REVIEW+'/frozen.json',REVIEW+'/preflight.json'})
    proposal['budgets'][task['budget_key']]['maximum_new_attempts']=11
    review={'baseline':authority_digest(program),'changes':['Single retained010 result replay; no candidate regeneration',
        'Explicit180second validation and1560second cumulative clock; storage unchanged; all rejected receipts retained',
        'Actual acceptance timing printed before enforcement and record command clock retained'],
        'skeptical_audit':{'verdict':'PASS_AFTER_RESOURCE_PLAN_REPAIR','plan':PLAN,
            'findings':['010 passed substantive candidate checks but acceptance exceeded60seconds',
                '250seconds conservatively charges whole010 admit-to-reject interval including candidate; no double counting',
                'Source/parser/consumer/oracle and prior tests match210 exactly; only named build router dispatch changes',
                'Full current frozen consumer and every predecessor comparison still required; no PASS-only shortcut',
                'Original source task and general build remain incomplete']},
        'evidence_contract':{'question':'Does sealed010 pass unchanged substantive verification under a measured feasible clock?',
            'baseline':b.NORMAL+'/candidate-answer.json.gz','primary':'Actual consumer equality, independent original reading,42controls and whole008 composition',
            'promotion_veto':'Source/answer/unknown/authority mismatch or any accepted adverse case',
            'continuation_veto':'Protected method drift, invalid source or180second validation/1560second cumulative/200MiB storage',
            'explanatory':['runtime','test/control counts','sizes'],'not_concluded':['source authenticity','correction','general discovery','original task or build completion'],
            'artifacts':b.SOURCE+'/attempt-011'},'scope_unchanged':True,'budget_unchanged':False,
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':10,'new_maximum':11,
            'retained_attempts':[e['attempt'] for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']],
            'reason':'Reproduced acceptance resource-plan failure; successful candidate retained without regeneration',
            'next_discriminating_check':'One actual retained-candidate validation under180seconds with full original-source/answer checks',
            'stop_condition':'Same substantive checks;180seconds acceptance/1560seconds cumulative/200MiB storage; no unchanged retry',
            'same_scope_authorization':'User asks refresh and continue general build; no external opinion or scope change'}}
    write(ROOT/REL/'proposals/bes-cash-flow-211.json',proposal,exclusive=True)
    write(ROOT/REL/'proposals/bes-cash-flow-211-review.json',review,exclusive=True)
    print(json.dumps({'stage':'prepared211','seconds':preparation['seconds'],'prior_charged_seconds':costs['seconds'],
        'charged_bytes_before_proposal':state['combined_bytes'],'substantive_methods_unchanged':True}),flush=True)

def stage(attempt_name):
    auth=Authority(ROOT);attempt=auth.path(attempt_name);admission=read(attempt/'admission.json')
    program,tasks,_=auth.spec();task=tasks['source-bes-dep-07']
    b.require(admission['task_spec']==task and admission['program_sha256']==authority_digest(program)
        and admission['binding']==auth.binding(task) and task['cash_flow_revalidation']==SELECTOR,'Unchanged211 admission required')
    protected(ROOT);storage(ROOT,attempt)
    write(attempt/'candidate-reference.json',{'path':CANDIDATE,'outputs_sha256':file_hash(ROOT/CANDIDATE/'outputs.json')},exclusive=True)
    write(attempt/'result.json',{'task':task['id'],'status':'PASS','scope':'RETAINED_CANDIDATE_REQUIRES_SUBSTANTIVE_VALIDATION',
        'task_complete':False,'whole_program_complete':False,'candidate':CANDIDATE,
        'meaning':'Reference integrity staged; authority must run substantive validator before finite acceptance'},exclusive=True)
    write(attempt/'run-manifest.json',{'git_commit':admission['git_commit'],'command':[sys.executable,'-m',
        'scripts.prospectus_bes_cash_flow_revalidation','stage','--attempt',attempt_name],
        'environment':{'python':sys.version,'executable':sys.executable,'PYTHONPATH':str(ROOT/'src')},
        'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'N/A; deterministic',
        'methods':read(ROOT/REVIEW/'frozen.json')['methods'],'data_version':file_hash(ROOT/CANDIDATE/'outputs.json'),
        'prior_cost':prior_cost(ROOT),'plan':PLAN,'result':attempt_name+'/RESULT.md'},exclusive=True)
    (attempt/'RESULT.md').write_text('# Retained candidate awaiting substantive acceptance\n\nThe010 candidate remains sealed; its original acceptance rejection is retained. This package stages its exact reference for one current frozen-consumer and independent-source replay. Reference integrity alone does not establish acceptance.\n\n| Decision | Primary criterion | Veto | Uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n| Stage retained010 | Pending full replay | Enforced by named validator | Original source correction unresolved | Record through bounded wrapper | Original task and build incomplete |\n\nThe acceptance command receipt outside this sealed package records actual runtime and authority verdict. Original source limits and red-team findings remain in010/RESULT.md.\n')
    write(attempt/'outputs.json',{p.name:file_hash(p) for p in attempt.iterdir() if p.is_file() and p.name!='outputs.json'},exclusive=True)
    print(json.dumps({'stage':'reference-staged','attempt':attempt_name,'candidate_regenerated':False}))

def record(attempt_name):
    folder=ROOT/REL/'continuation-reviews/bes-cash-flow-211-record';folder.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();error=None;result=None
    try:
        with (folder/'command.log').open('x') as log:
            result=subprocess.run([sys.executable,'-m','scripts.prospectus_control','record','--attempt',attempt_name],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=210,check=False)
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    event=next(e for e in reversed(Authority(ROOT).events()) if e.get('attempt')==attempt_name)
    receipt={'wall_seconds':time.monotonic()-start,'exit_code':result.returncode if result else None,'error':error,
        'authority_kind':event['kind'],'reason':event.get('reason'),'build_acceptances':event.get('build_acceptances',[]),
        'event_sha256':event['sha256'],'command_log_sha256':file_hash(folder/'command.log')}
    write(folder/'receipt.json',receipt,exclusive=True)
    print(json.dumps(receipt))
    return 0 if event['kind'] in ('RECORD','ACCEPT') and 'individual-cash-flow' in event.get('build_acceptances',[]) else 1

def main():
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','stage','record']);parser.add_argument('--attempt');a=parser.parse_args()
    if a.action=='prepare':prepare();return 0
    if not a.attempt:parser.error('--attempt is required')
    if a.action=='stage':stage(a.attempt);return 0
    return record(a.attempt)

if __name__=='__main__':raise SystemExit(main())
