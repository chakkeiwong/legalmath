"""Finish frozen integration controls without replaying completed028 stages."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts import prospectus_definition_integration as prior
from scripts import prospectus_definition_integration_oracle as oracle
from scripts.prospectus_typed_delta import changes, apply, equal
from legalmath.prospectus.successor.contracts import digest

AUTH, BASE = prior.AUTH, prior.HERE
PREP = AUTH/'reviews/definition-controls-288'
HERE = AUTH/'attempts/basf-references/attempt-029'
METHOD = 'scripts/prospectus_definition_controls.py'
PLAN = 'docs/plans/prospectus-definition-controls-2026-10-18.md'
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
STAGES = tuple('controls-'+str(i) for i in range(1,oracle.BATCHES))+('reconcile','seal')


def close_partial():
    started=time.monotonic()
    prior.frozen()
    assert not (BASE/'outputs.json').exists()
    complete = [s for s in oracle.STAGES if (BASE/'stages'/s/'result.json').exists()]
    assert complete == list(oracle.STAGES[:17])
    assert all(read(BASE/'stages'/s/'result.json')['status']=='PASS' for s in complete)
    cost = prior.costs()
    rate = read(BASE/'stages/controls-0/result.json')['wall_seconds']
    projected = cost['cumulative026_028_measured_seconds']+23*rate
    assert projected > 1800
    result = {'status':'PASS','task':'basf-references','result_kind':'PARTIAL_DEFINITION_INTEGRATION',
        'full_trial_complete':False,'original_task_complete':False,'completed_stages':complete,
        'remaining_stages':list(STAGES),'complete_ordinary_answers_checked':3,
        'actual_upstream_refusals':7,'actual_consumer_refusals':4,
        'remaining_consumer_controls':len(oracle.CONTROLS)-4,'resources':cost,
        'observed_first_batch_seconds':rate,'projected_cumulative_seconds':projected,
        'candidate_rejected':False,'reason':'Observed batch cost exceeds original finite time forecast',
        'next_action':'Reviewed cumulative resource continuation; never repeat completed stages',
        'reviewed_continuation_plan':PLAN}
    save(BASE/'result.json',result)
    save(BASE/'run-manifest.json',{'commands':[read(BASE/'stages'/s/'started.json')['command'] for s in complete],
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'data_version':sha(prior.SOURCE/'bound-inventory.json.gz'),'random_seeds':'N/A deterministic',
        'wall_time':cost,'plan':prior.PLAN,'result':rel(BASE/'result.json'),
        'partial_continuation_plan':PLAN,'candidate_changes':False})
    with (BASE/'RESULT.md').open('x') as stream:
        stream.write('''# Definition integration: partial trial retained

Three complete ordinary product/answer comparisons passed, including exact
absent-profile agreement.72 regressions,8 interval examples,9 malformed inputs,
7 upstream refusals and4 ordinary consumer controls passed. The other89 consumer
controls are not evaluated. All62 readings remain unresolved.

The observed58.18-second four-control batch makes the original cumulative1800s
time forecast infeasible. Stop this admission before exhaustion; preserve all
completed evidence and continue only after an explicit reviewed cumulative
extension. No candidate failure or external-package limitation was observed.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain partial integration evidence | Three complete answers pass;89 controls unrun | No candidate veto; resource forecast requires repair | Remaining adversarial behavior and governing meaning | Reviewed unchanged-control continuation | Completed trial, legal correctness or finished build |

The strongest alternative explanation remains shared source-reading error.
Passing transport tests cannot establish governing interpretation. The new
resource review preserves all prior costs and immutable methods.
''')
    save(BASE/'stages/close-partial/result.json',{'status':'PASS','wall_seconds':time.monotonic()-started,
        'command':['.venv/bin/python','-m','scripts.prospectus_definition_controls','close-partial']})
    save(BASE/'outputs.json',{str(p.relative_to(BASE)):sha(p) for p in BASE.rglob('*')
                             if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'PASS','partial_sealed':True,'candidate_rejected':False,
            'remaining_consumer_controls':len(oracle.CONTROLS)-4}


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_028_measured_seconds']+extra
    for d in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in d.glob(pattern))
    paths={p for d in (PREP,HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/p for p in (METHOD,PLAN))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0288.json')
    size=start['prior_resources']['cumulative026_028_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds < 3600 and size < 156*1024**2, 'Reviewed cumulative026–029 resources exhausted'
    return {'cumulative026_029_measured_seconds':seconds,'cumulative026_029_bytes':size,
        'seconds_bound':3600,'bytes_bound_including_4MiB_reserve':160*1024**2,
        'prior_costs_reset':False,'historical_manual_controller_seconds':'UNKNOWN',
        'prior_snapshot_sha256':sha(PREP/'accounting-start.json')}


def prepare():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program=read(AUTH/'program.json')
    assert program['revision']==287
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==28
    assert next(e for e in reversed(events) if e.get('attempt')==rel(BASE))['kind']=='RECORD'
    save(PREP/'accounting-start.json',{'prior_resources':prior.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    bindings={p:sha(ROOT/p) for p in (*CODE,METHOD,PLAN)}
    bindings.update(read(prior.PREP/'freeze.json')['bindings'])
    bindings.update({rel(BASE/'outputs.json'):sha(BASE/'outputs.json'),
                     rel(PREP/'accounting-start.json'):sha(PREP/'accounting-start.json')})
    save(PREP/'freeze.json',{'bindings':bindings,'prior_freeze_sha256':sha(prior.PREP/'freeze.json')})
    proposal=deepcopy(program)
    proposal['revision']=288
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN,pre_admission_review=PLAN,
        reason='Finish89 frozen consumer controls after measured runtime feasibility repair; preserve all028 comparisons',
        definition_control_continuation={'prior':rel(BASE),'review':rel(PREP),'method':METHOD,
            'remaining_controls':len(oracle.CONTROLS)-4,'cumulative_seconds':3600,
            'cumulative_bytes_including_reserve':160*1024**2,'candidate_changes':False})
    proposal['budgets']['basf-references']['maximum_new_attempts']=29
    routes=read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision']=288
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(dossier=PLAN,task_sha256=authority_digest(task),
                next_action='Finish frozen89 consumer controls, reconcile with028, record and refresh; then source reasoning',
                stop_condition='29 admissions;180s stages;cumulative026–0293600s/160MiB with4MiB reserve;no repeated completed stages')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Retain partial028; finish exactly89 pending controls without changing production or expectations',
            'Explicit cumulative time1800 to3600s and storage128 to160MiB;4MiB reserve retained'],
        'skeptical_audit':{'verdict':'PASS','review':PLAN,'observed_resource_trigger':rel(BASE/'result.json')},
        'evidence_contract':{'primary':'All93 original actual refusals plus three complete028 answer comparisons',
            'promotion_veto':['Accepted forgery','Wrong exception origin','Changed protected answers'],
            'continuation_veto':['Corrupt evidence','Method drift','Missing result','Cumulative limit'],
            'not_concluded':['Legal correctness','General recall','Whole-build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':28,'new_maximum':29,
            'retained_attempts':attempts,'reason':'Measured58.18s batch invalidated original runtime forecast',
            'next_discriminating_check':'Remaining89 unchanged actual ordinary-consumer forgery refusals',
            'stop_condition':'180s stages;3600s cumulative;160MiB including4MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continued general build; routine local resource revision'},
        'resource_revision':{'prior_seconds':1800,'new_seconds':3600,'prior_bytes':128*1024**2,
            'new_bytes':160*1024**2,'reserve_bytes':4*1024**2,'prior_costs_retained':True},
        'original_obligations_preserved':True,'resources':costs()}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':288,'resources':costs()}


def frozen():
    from legalmath.prospectus.execution_authority import Authority, digest as authority_digest
    admission=read(HERE/'admission.json')
    assert authority_digest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,checksum in read(PREP/'freeze.json')['bindings'].items():
        assert sha(ROOT/name)==checksum,name
    for name,checksum in read(BASE/'outputs.json').items():
        assert sha(BASE/name)==checksum,name
    for row in read(prior.PREP/'installation.json')['files']:
        assert sha(ROOT/row['target'])==row['after_sha256']


def controls(batch):
    from legalmath.prospectus.successor import service
    assert 1<=batch<oracle.BATCHES
    p,_=prior.retained('assisted-products')
    original=digest(p)
    base_path=BASE/'assisted-products.json.gz'
    cases=list(oracle.CONTROLS)[batch*oracle.BATCH_SIZE:(batch+1)*oracle.BATCH_SIZE]
    for case in cases:
        bad=oracle.reseal(p,oracle.mutation(case,p))
        actual_digest=digest(bad)
        assert actual_digest!=original,'Adverse control made no change'
        delta=changes(p,bad)
        equal(apply(p,delta),bad,'Lossy adverse retention')
        path=HERE/('control-'+case+'.json.gz')
        save(path,{'base':{'path':rel(base_path),'file_sha256':sha(base_path),'products_sha256':original},
                   'products_delta':delta,'products_sha256':actual_digest})
        retained=read(path)
        assert sha(ROOT/retained['base']['path'])==retained['base']['file_sha256']
        restored=apply(p,retained['products_delta'])
        assert digest(restored)==retained['products_sha256']
        equal(restored,bad,'Serialized adverse retention changed input')
        expected_error,function,module=oracle.CONTROLS[case]
        try:
            service.consume(restored,ROOT,mode='frozen')
        except ValueError as exc:
            save(HERE/('controls/'+case+'-actual.json'),{'type':type(exc).__name__,'message':str(exc)})
            receipt=oracle.refusal(exc,expected_error,function,module)
            save(HERE/('controls/'+case+'.json'),{'case':case,'validly_resealed':True,
                'forged_products_sha256':actual_digest,'original_products_sha256':original,**receipt})
        else:
            raise ValueError('Validly resealed definition forgery accepted: '+case)
    return {'status':'PASS','batch':batch,'actual_consumer_refusals':len(cases),'validly_resealed':True}


def reconcile():
    original=read(BASE/'result.json')
    assert original['full_trial_complete'] is False
    total=original['actual_consumer_refusals']
    for stage in STAGES[:-2]:
        result=read(HERE/'stages'/stage/'result.json')
        assert result['status']=='PASS'
        total+=result['actual_consumer_refusals']
    assert total==len(oracle.CONTROLS)
    case_refs={}
    for i,case in enumerate(oracle.CONTROLS):
        base=BASE if i<4 else HERE
        receipt=read(base/('controls/'+case+'.json'))
        expected_error,function,module=oracle.CONTROLS[case]
        assert receipt['message']==expected_error and receipt['type']=='ValueError'
        assert receipt['origin']['module']==module and receipt['origin']['function']==function
        assert receipt['validly_resealed'] is True
        path=base/('control-'+case+'.json.gz')
        case_refs[case]={'products':rel(path),'products_file_sha256':sha(path),
            'receipt':rel(base/('controls/'+case+'.json'))}
    for label in oracle.LABELS:
        comparison=read(BASE/(label+'-comparison.json'))
        assert comparison['complete_products_equal'] and comparison['complete_answer_equal']
    spec,_=oracle.validate_sources()
    original_refs=read(prior.SOURCE/'reconciliation.json.gz')
    assert len(original_refs['original_reference_ledger']['records'])==60
    assert len(original_refs['statutory_updated_reference_ledger']['records'])==60
    save(HERE/'reconciliation.json.gz',{'original_reconciliation':read(prior.LEXICAL/'reconciliation.json.gz'),
        'source_records':[{**r,'ordinary_dependency':oracle.PREFIX+r['id'],
            'governing_scope_admitted':False,'meaning_admitted':False} for r in spec['records']],
        'all_control_evidence':case_refs,'original_reference_records':60,'original_definition_records':62,
        'denominator_replaced':False,'known_misses':spec['known_misses'],'original_task_complete':False})
    return {'status':'PASS','actual_consumer_refusals':total,'complete_ordinary_answers_checked':3,
        'actual_upstream_refusals':7,'original_reference_records':60,'source_records':62,
        'original_task_complete':False,'scope_admitted':False,'meaning_admitted':False}


def seal():
    result={**read(HERE/'stages/reconcile/result.json'),'task':'basf-references',
        'result_kind':'FINITE_DEFINITION_SOURCE_TO_ANSWER_INTEGRATION','full_trial_complete':True,
        'resources':costs(),'prior_attempt':rel(BASE),'prior_outputs_sha256':sha(BASE/'outputs.json'),
        'next_action':'Source-reasoned governing-scope and missing-definition continuation',
        'remaining':['Governing scopes and meanings','Missing definitions and provenance gaps',
                     'Historical statutory application','Original acceptance and general discovery']}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'prior_commands_manifest':rel(BASE/'run-manifest.json'),'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU; GPU intentionally hidden','random_seeds':'N/A deterministic',
        'data_version':sha(prior.SOURCE/'bound-inventory.json.gz'),'wall_time':result['resources'],
        'plan':PLAN,'result':rel(HERE/'result.json'),'method_freeze':sha(PREP/'freeze.json')})
    with (HERE/'RESULT.md').open('x') as stream:
        stream.write('''# Finite definition integration checked through ordinary answers

All three complete answer comparisons,7 source/profile refusals and93 actual
consumer refusals pass across sealed028 and029. Changed products had valid
hashes; the ordinary consumer reconstructed evidence and refused the specified
change at the required origin. All62 source readings and610 authored use
associations remain present, with governing meaning unresolved. Financial and
statutory payloads remain unchanged; absent input reproduces complete025.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain finite assisted integration | Three complete answers and93 actual refusals pass | No integration veto | Same-agent readings, governing scope, missing definitions and historical law | Source-reasoned scope continuation | General recall, legal correctness or whole-build completion |

The implementation gap was disconnected definition evidence and incomplete
subquestion verification. The planning gap was an insufficient measured-time
allowance; its explicit revision retained all earlier costs and completed
evidence. Neither finding establishes a fundamental external-package limitation.
The strongest alternative explanation is shared source-reading error; contrary
source reasoning can overturn a reading without disproving transport.
''')
    return {'status':'PASS','full_trial_complete':True,'original_task_complete':False,'resources':costs()}


def main():
    assert len(sys.argv)==2
    stage=sys.argv[1]
    if stage=='remaining':
        # One foreground supervisor, with a fresh180s alarm inside each child.
        # A saved start without PASS is a refusal to rerun, never a retry.
        for pending in STAGES:
            folder=HERE/'stages'/pending
            if (folder/'result.json').exists():
                assert read(folder/'result.json')['status']=='PASS'
                continue
            assert not (folder/'started.json').exists(),'Pending/failed stage must be reviewed: '+pending
            actual=subprocess.run([sys.executable,'-m','scripts.prospectus_definition_controls',pending],
                cwd=ROOT,timeout=195)
            if actual.returncode:
                raise SystemExit(actual.returncode)
        return
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Definition control stage bound')))
    signal.alarm(180)
    if stage=='close-partial':
        print(json.dumps(close_partial()))
        return
    if stage=='prepare':
        started=time.monotonic()
        result=prepare()
        save(PREP/'stages/prepare/result.json',{**result,'wall_seconds':time.monotonic()-started})
        print(json.dumps(result))
        return
    assert stage in STAGES
    if stage=='reconcile':
        required=STAGES[:-2]
    elif stage=='seal':
        required=('reconcile',)
    else:
        required=()
    for item in required:
        assert read(HERE/'stages'/item/'result.json')['status']=='PASS'
    folder=HERE/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged stage retry refused'
    costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_controls',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Definition control stage bound')))
    signal.alarm(180)
    try:
        frozen()
        result=controls(int(stage.split('-')[1])) if stage.startswith('controls-') else globals()[stage]()
        frozen()
        costs(time.monotonic()-started)
        result['wall_seconds']=time.monotonic()-started
        save(folder/'result.json',result)
        if stage=='seal':
            save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    main()
