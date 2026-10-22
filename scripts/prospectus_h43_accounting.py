"""One reviewed metadata-budget repair; source operations stay unchanged."""
from copy import deepcopy
from datetime import datetime, timezone
import json, signal, sys, time
from scripts import prospectus_h43_source as source
from legalmath.prospectus.execution_authority import Authority, CODE, digest

ROOT,AUTH=source.ROOT,source.AUTH
OLD_PREP,OLD_HERE=source.PREP,source.HERE
OLD_PLAN,OLD_METHOD=source.PLAN,source.METHOD
PREP=AUTH/'reviews/h43-accounting-320'
HERE=AUTH/'attempts/basf-references/attempt-059'
PLAN='docs/plans/prospectus-h43-accounting-2026-10-19.md'
METHOD='scripts/prospectus_h43_accounting.py'
read,save,sha,rel=source.read,source.save,source.sha,source.rel


def previous():
    start=read(OLD_PREP/'accounting-start.json')
    seconds=start['prior']['combined_measured_seconds']+0.798026769
    for folder in (OLD_PREP,OLD_HERE):
        for p in folder.glob('stages/*/result.json'):seconds+=read(p)['wall_seconds']
    paths={p for d in (OLD_PREP,OLD_HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (OLD_PLAN,OLD_METHOD));paths.add(AUTH/'revisions/0319.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<12600 and size<2044*1024**2
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'prior_scope':'All026–057 and office costs plus058 metadata and failed command',
        'unmeasured_authoring_and_older_time':'UNKNOWN'}


def close_failed():
    source.frozen();assert not (OLD_HERE/'outputs.json').exists()
    assert not (OLD_HERE/'stages/local/started.json').exists()
    save(OLD_HERE/'failed-local-command.json',{'command':['.venv/bin/python','-m','scripts.prospectus_h43_source','local'],
        'exit_code':1,'wall_seconds':0.798026769,'measurement_source':'retained exec tool result',
        'error':'AssertionError in costs: incremental metadata exceeds16MiB',
        'local_stage_started':False,'source_requests_started':0})
    save(OLD_HERE/'result.json',{'status':'PASS','task':'basf-references','trial_status':'FAIL',
        'result_kind':'RETAINED_PREPARATION_FAILURE','original_task_complete':False,
        'candidate_evaluated':False,'production_changed':False,'resources':previous(),
        'failure_class':'OUR_METADATA_FORECAST','reviewed_repair':PLAN,
        'next_action':'One changed40MiB metadata forecast with unchanged combined ceilings and original source contract'})
    (OLD_HERE/'RESULT.md').write_text('''# H43 source work did not start

The local command stopped at its resource preflight. The16MiB incremental
forecast omitted a second roughly10.5MB immutable program copy plus admission
metadata. No source request, local content search or product change occurred.
This is our budget-estimation defect, not evidence against a package or law.
All frozen inputs and prior costs remain. The reviewed accounting plan permits
one changed forecast, not a retry with unchanged assumptions.

|Decision|Criterion|Veto|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain failed preparation|Source work unevaluated|Incremental forecast invalid|H43 source and historical applicability|Single reviewed accounting repair|Candidate failure or legal closure|
''')
    save(OLD_HERE/'outputs.json',{str(p.relative_to(OLD_HERE)):sha(p) for p in OLD_HERE.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'PASS','retained_trial':'FAIL','candidate_evaluated':False,'resources':previous()}


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+extra
    for d in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in d.glob(pattern))
    paths={p for d in (PREP,HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN,METHOD));paths.add(AUTH/'revisions/0320.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<12600 and size<2044*1024**2
    assert seconds-start['prior']['combined_measured_seconds']<118
    assert size-start['prior']['combined_bytes']<40*1024**2
    requests=sum(len(list(d.glob('requests/*/started.json'))) for d in (OLD_HERE,HERE));assert requests<=2
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'new_GETs':requests,'maximum_new_GETs':2,'historical_GETs_reset':False,
        'unmeasured_authoring_and_older_time':'UNKNOWN'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==319
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==58 and [e['kind'] for e in events if e.get('attempt')==rel(OLD_HERE)][-1]=='RECORD'
    save(PREP/'accounting-start.json',{'prior':previous(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    bindings={n:sha(ROOT/n) for n in (*CODE,PLAN,METHOD,OLD_METHOD,OLD_PLAN)}
    bindings.update(read(OLD_PREP/'freeze.json')['bindings'])
    bindings[rel(OLD_HERE/'outputs.json')]=sha(OLD_HERE/'outputs.json')
    bindings[rel(PREP/'accounting-start.json')]=sha(PREP/'accounting-start.json')
    save(PREP/'freeze.json',{'bindings':bindings,'source_operations_unchanged':True})
    proposal=deepcopy(program);proposal['revision']=320
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=PLAN,
        reason='Repair reproduced H43 metadata forecast once, then execute unchanged source investigation',
        h43_accounting={'review':rel(PREP),'failed_attempt':rel(OLD_HERE),'additional_bytes':40*1024**2,
            'combined_seconds':12600,'combined_bytes':2048*1024**2,'further_harness_retry_allowed':False})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=59
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=320
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=digest(task),
            next_action='Execute unchanged H43 source investigation after measured metadata correction',
            stop_condition='59 admissions;30s stages;two total H43 GETs;no further harness retry;combined12600s/2048MiB')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+118,'bytes':costs()['combined_bytes']+40*1024**2}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Retain failed058 metadata forecast','One changed forecast; source method unchanged'],
        'skeptical_audit':{'verdict':'PASS','review':PLAN,'forecast':forecast},
        'evidence_contract':read(OLD_PREP/'review.json')['evidence_contract'],
        'budget_revision':{'budget_key':'basf-references','previous_maximum':58,'new_maximum':59,
            'retained_attempts':attempts,'reason':'058 source work stopped before execution by omitted duplicated authority metadata',
            'next_discriminating_check':'Actual admitted metadata fits explicit40MiB forecast before unchanged source operations',
            'stop_condition':'No further H43 harness retry;two total GETs;combined12600s/2048MiB',
            'same_scope_authorization':'User requests continued internal build and ordinary local repairs'},
        'resource_revision':{'old_incremental_bytes':16*1024**2,'new_incremental_bytes':40*1024**2,
            'combined_bounds_unchanged':True,'all_failed_costs_retained':True,'GET_allowance_unchanged':True}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':320,'forecast':forecast}


def main():
    stage=sys.argv[1]
    if stage=='close-failed':print(json.dumps(close_failed()));return
    source.PREP=PREP;source.HERE=HERE;source.PLAN=PLAN;source.METHOD=METHOD;source.costs=costs
    if stage=='prepare':source.prepare=prepare
    source.main()


if __name__=='__main__':main()
