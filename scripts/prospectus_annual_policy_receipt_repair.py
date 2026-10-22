"""One reviewed task-attribution repair; never rewrite rejected source evidence."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from scripts import prospectus_annual_policy_submission as prior
from legalmath.prospectus.execution_authority import Authority,digest,file_hash
from legalmath.prospectus.execution_workers import validate

AUTH,SOURCE=prior.AUTH,prior.SOURCE
PREP=AUTH/'reviews/annual-policy-receipt-442'
OLD=prior.HERE
HERE=SOURCE/'attempt-018'
TASK=prior.TASK
PLAN='docs/plans/prospectus-annual-policy-receipt-repair-2026-10-22.md'
SELF='scripts/prospectus_annual_policy_receipt_repair.py'
read,save,require=prior.read,prior.save,prior.require
rel=prior.rel


def usage():
    value=prior.costs()
    files={p for folder in (PREP,HERE) if folder.exists() for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update([ROOT/PLAN,ROOT/SELF,AUTH/'revisions/0442.json'])
    value['new_bytes']+=sum(p.stat().st_size for p in files if p.is_file())
    # Prior costs already include history and current program growth since441.
    extra=sum(read(p).get('seconds',0) for p in PREP.glob('commands/*.json'))
    value['new_seconds']+=extra
    value['cumulative_charged_seconds']+=extra
    value['cumulative_bytes']=read(AUTH/'reviews/annual-basis-440/post-record.json')['costs']['cumulative_bytes']+value['new_bytes']
    value['recovery_seconds']=extra
    value['allowed']=value['allowed'] and extra<30 and value['new_seconds']<600 and value['cumulative_charged_seconds']<2960 and value['new_bytes']+2*1024**2<160*1024**2 and value['cumulative_bytes']+2*1024**2<600*1024**2
    return value


def evidence(a):
    event=next(e for e in reversed(a.events()) if e.get('attempt')==rel(OLD))
    require(event['kind']=='REJECT' and event['reason']=='Worker result failed or belongs to another task','Exact rejected receipt required')
    require(a.retained_evidence_valid(event),'Rejected evidence corrupted')
    frozen=read(prior.PREP/'freeze.json')
    require(all(file_hash(ROOT/p)==h for p,h in frozen['evidence'].items()),'Original frozen evidence changed')
    require(prior.inventory(ROOT/'src/legalmath')==frozen['package']==prior.inventory(OLD/'installed-package/legalmath'),'Production/installed package changed')
    for part in prior.work.PARTS:
        require(read(prior.WORK/('candidate-'+part)/'result.json')==read(OLD/('ordinary-'+part)/'result.json')==read(OLD/('installed-'+part)/'result.json'),'Substantive part mismatch')
    require(read(OLD/'ordinary-answer/answer-delta.json.gz')==read(OLD/'installed-answer/answer-delta.json.gz')==read(prior.WORK/'candidate-answer/answer-delta.json.gz'),'Complete answer delta mismatch')
    from scripts.prospectus_english_applicability_program import check_runtime
    check_runtime(frozen['runtime'],frozen['runtime_files'])
    return event


def prepare():
    a=Authority(ROOT)
    old,tasks,_=a.spec()
    require(old['revision']==441 and not PREP.exists() and not HERE.exists(),'Fresh recovery only')
    event=evidence(a)
    result=read(OLD/'result.json')
    require(result.get('status')=='PASS' and 'task' not in result,'Exact missing task defect required')
    cases={'original-malformed':result,'corrected-partial':{**result,'task':TASK},
           'wrong-task':{**result,'task':'not-source09'},'failed-status':{**result,'task':TASK,'status':'FAIL'}}
    checks=[]
    for name,case in cases.items():
        folder=PREP/'preflight'/name
        save(folder/'result.json',case)
        try:
            disposition=validate(ROOT,folder,tasks[TASK])
        except ValueError as exc:
            require(name!='corrected-partial' and str(exc)=='Worker result failed or belongs to another task','Unexpected validator refusal')
            checks.append({'case':name,'rejected':True,'reason':str(exc)})
        else:
            require(name=='corrected-partial' and disposition is False,'Generic validator improperly accepted task')
            checks.append({'case':name,'partial_record_only':True})
    save(PREP/'preflight.json',{'status':'PASS','checks':checks,'original_rejection':event})
    proposal=deepcopy(old)
    proposal['revision']=442
    task=next(t for t in proposal['tasks'] if t['id']==TASK)
    task.update(dossier=PLAN,pre_admission_review=PLAN,receipt_repair_review=rel(PREP/'preflight.json'),
        reason='One changed receipt recovery: retain verified017product evidence with explicit original task attribution; original scope remains partial')
    extra=[PLAN,SELF,rel(PREP/'preflight.json'),rel(OLD/'outputs.json'),rel(OLD/'result.json'),
           rel(prior.PREP/'record-projection.json'),rel(prior.PREP/'record-projection.log')]
    task['inputs']=sorted(set(task['inputs'])|set(extra))
    attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==TASK]
    require(len(attempts)==old['budgets'][TASK]['maximum_new_attempts']==17,'Retain17admissions')
    proposal['budgets'][TASK]['maximum_new_attempts']=18
    routes=read(ROOT/old['continuation_review']['routes'])
    routes['baseline_revision']=442
    row=next(r for r in routes['tasks'] if r['task']==TASK)
    row.update(task_sha256=digest(task),dossier=PLAN,phase=0,
        next_action='Record corrected partial receipt referencing unchanged017evidence, then continue original remaining annual policies and numerical notes.',
        stop_condition='One receipt recovery consumes441changed recovery;18cumulative admissions;same2960seconds600MiB;no repeated product trials.')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({p:file_hash(ROOT/p) for p in extra+[rel(PREP/'routes.json')]})
    review={'baseline':digest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Correct missing task attribution through new receipt referencing sealed rejected evidence'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'actual_validator_preflight':rel(PREP/'preflight.json')},
        'evidence_contract':{'primary':'Correct partial task attribution with complete retained substantive evidence unchanged',
            'baseline':rel(OLD),'promotion_veto':['Changed source/product evidence','Wrong task/status'],
            'continuation_veto':['Invalid authority','Spent cumulative bound'],'not_concluded':['Original task acceptance','New product trial']},
        'budget_revision':{'budget_key':TASK,'previous_maximum':17,'new_maximum':18,'retained_attempts':attempts,
            'reason':'One permitted changed recovery for reproduced local receipt omission; no runtime/storage increase',
            'next_discriminating_check':'Actual validator of corrected018receipt before seal and actual RECORD event',
            'stop_condition':{'recovery_seconds':30,'new_seconds':600,'cumulative_seconds':2960,'new_bytes':160*1024**2,'cumulative_bytes':600*1024**2,'changed_recovery_consumed':True},
            'same_scope_authorization':'Continue original build and bounded repair; sealed rejection retained'}}
    size=lambda v:len(json.dumps(v,indent=2,ensure_ascii=False).encode())
    forecast=usage()['new_bytes']+2*size(proposal)+size(review)+size(task)+2*1024**2
    require(forecast+2*1024**2<160*1024**2 and read(AUTH/'reviews/annual-basis-440/post-record.json')['costs']['cumulative_bytes']+forecast+2*1024**2<600*1024**2,'Recovery storage forecast exceeds unchanged bound')
    save(PREP/'forecast.json',{'new_bytes':forecast,'limits_unchanged':True})
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'REVIEWED','preflight':checks}


def seal():
    a=Authority(ROOT)
    program,tasks,_=a.spec()
    require(program['revision']==442 and read(HERE/'admission.json')['binding']==a.binding(tasks[TASK]),'Current442admission required')
    require(next(e for e in reversed(a.events()) if e.get('task')==TASK)['kind']=='ADMIT','Recovery terminal already')
    event=evidence(a)
    original=read(OLD/'result.json')
    result={**original,'task':TASK,'plan':PLAN,'costs':usage(),
        'receipt_repair':{'original_attempt':rel(OLD),'original_event':event['sha256'],'outputs_sha256':file_hash(OLD/'outputs.json'),
            'change':'ADD_MISSING_TASK_ID','product_trials_repeated':False},'task_complete':False,'whole_program_complete':False}
    save(HERE/'result.json',result)
    require(validate(ROOT,HERE,tasks[TASK]) is False,'Correct receipt must be partial only')
    save(HERE/'evidence-reference.json',{'original_event':event,'outputs_manifest':rel(OLD/'outputs.json'),
        'result':rel(OLD/'RESULT.md'),'coverage':rel(OLD/'COVERAGE.md'),'preflight':rel(PREP/'preflight.json'),
        'all_candidate_current_installed_parts_equal':True,'source_runtime_package_bindings_unchanged':True})
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],'command':sys.argv,
        'environment':'Existing CPU offline Python; no product trial rerun','random_seeds':'N/A deterministic',
        'plan':PLAN,'original_run_manifest':rel(OLD/'run-manifest.json'),'result':rel(HERE/'RESULT.md')})
    for name,text in {'RESULT.md':'# Corrected partial receipt\n\nThe original017 result omitted its task ID and was rejected. The new receipt names source-bes-dep-09 and references the unchanged sealed017 results. The actual generic validator confirms partial retention only. Every source/package/runtime binding, seven candidate/current/installed results and complete answer deltas were rechecked. No product test was rerun. This is our receipt-writer defect, not a fundamental package defect. The rejected attempt and all failure evidence remain intact. The single changed recovery is consumed.\n\n| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |\n|---|---|---|---|---|---|\n| Retain corrected partial receipt | Task/status match; source evidence unchanged | Validator and evidence checks pass | Original finite supplied-interpretation limits remain | Continue remaining original policies and notes | Original task or master-program completion |\n',
        'COVERAGE.md':'# Coverage unchanged\n\nSee the immutable source09 attempt-017/COVERAGE.md. This receipt correction adds no source meaning or coverage. At least72 original required pages lack interpreted readings;14BES dependencies and Q3 PARTIAL remain.\n'}.items():
        with (HERE/name).open('x') as stream:
            stream.write(text)
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):file_hash(p) for p in HERE.rglob('*') if p.is_file()})
    require(usage()['allowed'],'Recovery ceiling')
    return {'status':'SEALED_CORRECTED_RECEIPT'}


def record():
    argv=[str(ROOT/'.venv/bin/python'),'-B','-m','scripts.prospectus_control','record','--attempt',rel(HERE)]
    start=time.monotonic()
    with (PREP/'record.log').open('x') as log:
        try:
            code=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=60).returncode
        except subprocess.TimeoutExpired:
            code=-1
    save(PREP/'record-projection.json',{'argv':argv,'exit_code':code,'seconds':time.monotonic()-start,'role':'AUTHORITY_RECORD_AND_VIEW'})
    a=Authority(ROOT)
    event=next(e for e in reversed(a.events()) if e.get('attempt')==rel(HERE))
    valid=a.retained_evidence_valid(event)
    save(PREP/'post-record.json',{'event':event,'costs':usage(),'retained_evidence_valid':valid})
    require(event['kind']=='RECORD' and valid,'Inspect terminal event; no repeated recovery')
    return {'status':'RECORDED','event':event['sha256']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','seal','record','usage'])
    args=parser.parse_args()
    started=time.monotonic()
    try:
        result=globals()[args.action]()
    except Exception as exc:
        if args.action in ('prepare','seal'):
            save(PREP/'commands'/(args.action+'-failed.json'),{'argv':sys.argv,'exit_code':1,'seconds':time.monotonic()-started,'error':str(exc)})
        raise
    if args.action in ('prepare','seal'):
        save(PREP/'commands'/(args.action+'.json'),{'argv':sys.argv,'exit_code':0,'seconds':time.monotonic()-started})
    print(json.dumps({**result,'costs':usage()}),flush=True)
