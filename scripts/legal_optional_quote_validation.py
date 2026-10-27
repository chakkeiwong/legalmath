"""Fixed, history-preserving successor for optional answer-quotation checks."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence, process_identity, process_alive
from scripts.legal_integration_acceptance_revision import historical_projection

KEY = 'optional_quote_validation'
HERE = Path('artifacts/legal-mission-control/2026-10-23/p14-optional-quote')
OLD_WORK = Path('artifacts/legal-mission-control/2026-10-23/p14-corrected-context/requested-owner')
SOURCE = Path('artifacts/legal-mission-control/2026-10-23/p14-deployment/context-isolated-live')
RUNTIME = HERE/'live'
REVIEW = Path('docs/plans/p14-optional-quotation-integrity-2026-10-23.md')
SELF = 'scripts/legal_optional_quote_validation.py'
TEST = 'tests/tooling/test_optional_quote_validation.py'
PRODUCT = 'src/legalmath/interpretation/assurance/phased/context_disposition.py'
CHANGED = (PRODUCT, 'scripts/legal_review_repair.py', 'scripts/legal_integration_phased_live.py',
           'scripts/legal_mission_control.py', 'scripts/legal_review_deployment.py')
ADDED = (SELF, TEST)
SELECTED = ('baseline-p14','baseline-gatecoin','tool-gatecoin-bm25')
CORRECTED_KEY = 'audit-context-disposition-p14-f27ee3e41f98d678fc3e4711'
CORRECTED_HASHES = {
    'request': ('638813e894b97484513da68af84c131bb791b5c28bf0f5d1eac76981f5c55f32',
                '9331cb0fa6a7ba60fbb7642708753d5c3cceea85fb1af8921d6a19d429012277'),
    'schema': ('31e5044df3901a081ca4a0d4a0b4e88543af9ba5c5e2dca8a4c97a18fcc0ff42',
               'f73ebf935b64ca859964ccdd4eddc9c35d8799f4532e822465d7ace4f181b6f8'),
    'result': ('15ca0291cd98e7f2cced4b4f0f5708d71c0f1c215ddb0c4e42ca4d71bb157c64',
               '9c6e2adcef9d57f4a3a7b26ccdc7bafa409d8e7dd60d39fb267ecb1f21a31d62'),
}

def now():
    return datetime.now(timezone.utc).isoformat()

def mapping(rows, mission=False):
    allowed = set(CHANGED) | ({str(PROGRAM)} if mission else set())
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
            for r in rows if r['previous']['path'] in allowed}

def expected_program(old, revision, root, plan_reference):
    rows = read(root/revision['baseline']['path'])['archived']
    value = historical_projection(old, mapping(rows))
    value['review_repair'][KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('review','result','baseline','seed')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference)
    return value

def validate(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    root = Path(root)
    revision = program['review_repair'][KEY]
    require(revision['profile']=='optional-answer-quotation-validation.v1'
        and revision['runtime']==str(RUNTIME) and revision['prior_detours']==64
        and revision['additional_consolidated_revision']==1
        and revision['calls_added']==revision['attempts_added']==revision['service_replacements_added']==0,
        'Changed optional-quotation scope or allowance')
    require(set(revision['implementation'])==set(CHANGED+ADDED),'Changed quotation implementation scope')
    for name in ('review','result','baseline','seed','prior_program','prior_state','prior_binding'):
        verify(root,revision[name])
    for pointer in revision['implementation'].values(): verify(root,pointer)
    baseline=read(root/revision['baseline']['path'])
    require(baseline['settled'],'Quotation successor lacks settled predecessor')
    verify(root,baseline['handover'])
    handover=read(root/baseline['handover']['path'])
    require(handover['supervisor_ended'] and handover['service_settled'], 'Unsettled quotation handover')
    held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed historical bytes')
        verify(root,row['archive'])
    for name,path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')):
        require(revision[name]==held[str(path)],'Wrong quotation predecessor '+name)
    require(held[str(BASE/'live-calls.json')]['sha256']==handover['ledger']['sha256'], 'Wrong handover ledger')
    old=read(root/revision['prior_program']['path'])
    require(KEY not in old['review_repair'],'Repeated quotation revision')
    with historical_evidence(root,mapping(baseline['archived'])):
        validate_program(old,root)
    result=read(root/revision['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and not result['legal_acceptance'],
        'Quotation tests did not pass')
    for pointer in result['evidence']: verify(root,pointer)
    seed=read(root/revision['seed']['path'])
    require(seed['provider_calls']==0 and seed['historical_decisions_unchanged']
        and seed['failed_results_retained'] and seed['arm_checkpoints']==revision['arm_checkpoints']
        and seed['baseline']==revision['baseline'],'Changed quotation seed')
    for pointer in [p for arms in seed['arm_checkpoints'].values() for p in arms.values()]: verify(root,pointer)
    for row in seed['imported']:
        for name in ('request','schema','result','dispatch'): verify(root,row[name])
        value=read(root/row['result']['path'])
        dispatch=read(root/row['dispatch']['path'])['calls'][row['key']]
        require(dispatch['result_hash']==digest(value) and dispatch['status']==value['status']==row['status'],
            'Changed imported quotation result')
    for row in seed.get('superseded_failed_contracts', []):
        require(checkpoint_predecessor(root,row['question'],row['arm'],row['key'],
            row['previous'],row['current'])==row,'Changed corrected-contract history')
    require(program==expected_program(old,revision,root,plan_reference), 'Unreviewed graph, authority or content change')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def validate_history(program,state,root):
    before=read(Path(root)/program['review_repair'][KEY]['prior_state']['path'])
    require(state['events'][:len(before['events'])]==before['events'],'Lost prior quotation events')
    require(set(state['tasks'])==set(before['tasks']),'Changed task set')
    for tid,row in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']),'Lost attempts')
        for old,new in zip(row['attempts'],current['attempts']):
            require(all(new.get(k)==v for k,v in old.items()),'Changed retained attempt '+tid)
        if row['status']=='SUCCEEDED': require(row==current,'Changed successful independent task')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])),
        'Lost continuation veto')

def verify_preparation():
    value=read(ROOT/HERE/'preparation.json')
    require(value['program']==ref(ROOT,PROGRAM) and value['binding']==ref(ROOT,BASE/'current-binding.json'),
        'Program changed since preparation')
    for pointer in value['current_files']+value['candidates']+[value['review']]: verify(ROOT,pointer)
    return value

def prepare():
    require(not (ROOT/HERE/'preparation.json').exists(),'Quotation preparation already exists')
    def replace_once(text,old,new):
        require(text.count(old)==1,'Candidate patch anchor is not unique')
        return text.replace(old,new)
    outputs={path:(ROOT/path).read_text() for path in CHANGED}
    old="        need, disposition = row['original_need'], result['disposition']\n"
    new=old+("        evidence = result['answer_evidence']\n"
        "        if evidence['path'] or evidence['quote']:\n"
        "            from legalmath.errors import LegalMathError\n"
        "            try:\n"
        "                answer_quote(answer, evidence['path'], evidence['quote'])\n"
        "            except LegalMathError as exc:\n"
        "                require(False, 'Invalid response answer quotation: ' + str(exc.details or exc), 'E_SCHEMA')\n")
    outputs[PRODUCT]=replace_once(outputs[PRODUCT],old,new)
    path='scripts/legal_review_repair.py'
    old="    revision = program[KEY]\n    if revision.get('deployment'):\n"
    new="    revision = program[KEY]\n    if revision.get('optional_quote_validation'):\n        from scripts.legal_optional_quote_validation import validate\n        return validate(program, root, plan_reference)\n    if revision.get('deployment'):\n"
    outputs[path]=replace_once(outputs[path],old,new)
    old="def validate_state_history(program, state, root):\n"
    new=old+"    if program[KEY].get('optional_quote_validation'):\n        from scripts.legal_optional_quote_validation import validate_history as check_quote_history\n        check_quote_history(program, state, root)\n"
    outputs[path]=replace_once(outputs[path],old,new)
    path='scripts/legal_integration_phased_live.py'
    old="    if program.get('review_repair'):\n        if program['review_repair'].get('deployment'):\n"
    new="    if program.get('review_repair'):\n        if program['review_repair'].get('optional_quote_validation'):\n            return Path(program['review_repair']['optional_quote_validation']['runtime'])\n        if program['review_repair'].get('deployment'):\n"
    outputs[path]=replace_once(outputs[path],old,new)
    old="    directory=ROOT/common if preparation_only else ROOT/route_live/'arms'/q/(tool or 'baseline')\n"
    new="            if repaired.get('optional_quote_validation'):\n                options['bounded_capacity_checkpoint'] = repaired['optional_quote_validation']['arm_checkpoints'].get(q, {}).get(\n                    tool or 'baseline', options['bounded_capacity_checkpoint'])\n"+old
    outputs[path]=replace_once(outputs[path],old,new)
    path='scripts/legal_review_deployment.py'
    old="def worker_directory():\n"
    new=old+"    if read(ROOT/PROGRAM)['review_repair'].get('optional_quote_validation'):\n        from scripts.legal_optional_quote_validation import HERE as quotation\n        return quotation\n"
    outputs[path]=replace_once(outputs[path],old,new)
    path='scripts/legal_mission_control.py'
    old="    else:\n        master_state = None\n    require(mission[\"current_task\"] in tasks, \"No current substantive task\")\n"
    new="            quotation = review_repair.get('optional_quote_validation')\n            if quotation:\n                require(quotation.get('profile') == 'optional-answer-quotation-validation.v1'\n                    and quotation.get('prior_detours') == detours == 64\n                    and quotation.get('additional_consolidated_revision') == 1\n                    and quotation.get('calls_added') == quotation.get('attempts_added') == quotation.get('service_replacements_added') == 0,\n                    'Unreviewed optional answer-quotation repair')\n                require(any(r['id'] == 'p14-optional-quotation-integrity-2026-10-23'\n                    and quotation['review'] in r['result_evidence'] for r in history),\n                    'Quotation repair lacks reviewed history')\n                detours += 1\n"+old
    outputs[path]=replace_once(outputs[path],old,new)
    for path,body in outputs.items():
        target=ROOT/HERE/'candidate'/path
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream: stream.write(body)
        compile(body,str(target),'exec')
    value=dict(at_utc=now(),program=ref(ROOT,PROGRAM),binding=ref(ROOT,BASE/'current-binding.json'),
        review=ref(ROOT,REVIEW),current_files=[ref(ROOT,p) for p in CHANGED+ADDED],
        candidates=[ref(ROOT,HERE/'candidate'/p) for p in CHANGED],provider_calls=0)
    save(ROOT/HERE/'preparation.json',value)
    return dict(prepared=len(outputs),provider_calls=0)

def owner_children(owner):
    return Path(f'/proc/{owner["pid"]}/task/{owner["pid"]}/children').read_text().strip()

def owner_state(owner):
    return Path(f'/proc/{owner["pid"]}/stat').read_text().rsplit(') ',1)[1].split()[0]

def settle_once():
    verify_preparation()
    result=ROOT/HERE/'handover.json'
    if result.exists():
        value=read(result)
        require(value.get('supervisor_ended') and not process_alive(value['process']),'Incomplete prior handover')
        return value
    tests=read(ROOT/HERE/'local-result.json')
    require(tests['verdict']=='PASS' and tests['provider_calls']==0,'Local checks pending')
    for pointer in tests['evidence']: verify(ROOT,pointer)
    owner=read(ROOT/OLD_WORK/'worker.json')['process']
    require(read(ROOT/OLD_WORK/'armed.json')['process']==owner and process_identity(owner['pid'])==owner,
        'Different active supervisor')
    binding=read(ROOT/BASE/'current-binding.json')
    service=ROOT/Path(binding['phase_service_scope']['path']).parent
    with ExitStack() as stack:
        journals=sorted((ROOT/SOURCE).rglob('calls/dispatch.json'))
        paths=[ROOT/STATE.with_suffix('.lock'),ROOT/DOC/'mission.execution.lock',service/'service-worker.lock',
            service/'service-circuit.lock',(ROOT/BASE/'live-calls.json').with_suffix('.lock')]
        paths += [p.with_name('dispatch.lock') for p in journals]
        try:
            for path in paths:
                path.parent.mkdir(parents=True,exist_ok=True)
                handle=stack.enter_context(path.open('a'))
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(settled=False,reason='Shared state/provider busy; no signal')
        state=read(ROOT/STATE)
        current=state['tasks']['baseline-p14']
        require(current['status']=='RUNNING' and len(current['attempts'])==5
            and current['live_supervisor']==owner,'P14 left retained attempt')
        require(all(r.get('master_live') and r.get('live_supervisor') and
            (r['live_supervisor']==owner or not process_alive(r['live_supervisor']))
            for r in state['tasks'].values() if r['status']=='RUNNING'),'Unknown other owner')
        if any(r['status']=='RESERVED' for p in journals for r in read(p)['calls'].values()):
            return dict(settled=False,reason='Reserved dispatch; no signal')
        circuit=read(service/'service-circuit.json')
        if circuit.get('open',True) or any(circuit.get(k) for k in ('half_open_reserved','half_open_request_hash','half_open_schema_hash')):
            return dict(settled=False,reason='Service recovery unsettled; no signal')
        if owner_children(owner): return dict(settled=False,reason='Provider child; no signal')
        ledger=ref(ROOT,BASE/'live-calls.json')
        stopped=False
        try:
            os.kill(owner['pid'],signal.SIGSTOP); stopped=True
            for _ in range(100):
                if owner_state(owner) in ('T','t'): break
                time.sleep(.01)
            require(owner_state(owner) in ('T','t') and process_identity(owner['pid'])==owner
                and not owner_children(owner) and ref(ROOT,BASE/'live-calls.json')==ledger
                and read(service/'service-circuit.json')==circuit
                and sorted((ROOT/SOURCE).rglob('calls/dispatch.json'))==journals,'Idle boundary changed after stop')
            verify_preparation()
            value=dict(settled=True,process=owner,at_utc=now(),ledger=ledger,
                calls=len(read(ROOT/BASE/'live-calls.json')['calls']),service_settled=True,
                service=str(service.relative_to(ROOT)),dispatches=[ref(ROOT,p) for p in journals],
                reserved_dispatches=0,provider_children=[])
            save(result,value)
            os.kill(owner['pid'],signal.SIGTERM); os.kill(owner['pid'],signal.SIGCONT); stopped=False
            for _ in range(100):
                if not process_alive(owner): break
                time.sleep(.05)
            require(not process_alive(owner),'Supervisor did not end')
            value['supervisor_ended']=True; save(result,value)
            return value
        finally:
            if stopped: os.kill(owner['pid'],signal.SIGCONT)

def settle():
    end=time.monotonic()+50
    while True:
        value=settle_once()
        if value.get('settled') or time.monotonic()>=end: return value
        time.sleep(.2)

def checkpoint_predecessor(root, qid, arm, key, previous, current):
    root=Path(root)
    for entry in (previous,current):
        for name in ('request','schema','result','dispatch'): verify(root,entry[name])
    old,new=read(root/previous['result']['path']),read(root/current['result']['path'])
    if old==new: return None
    require((qid,arm,key)==('p14','baseline',CORRECTED_KEY),
        'Unreviewed checkpoint collision')
    require(previous['mode']=='RETAINED_FAILURE' and old['status']=='FAILED'
        and new['status']=='VALIDATED' and not old.get('continuation_veto')
        and not new.get('continuation_veto'),'Invalid corrected-contract transition')
    for name,hashes in CORRECTED_HASHES.items():
        require((previous[name]['sha256'],current[name]['sha256'])==hashes,
            'Changed exact corrected-contract '+name)
    return dict(question=qid,arm=arm,key=key,previous=deepcopy(previous),current=deepcopy(current))

def freeze_seed():
    from types import SimpleNamespace
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.bounded_context import Limits
    from scripts.legal_integration_campaign import provider
    verify_preparation()
    handover=read(ROOT/HERE/'handover.json')
    require(handover['supervisor_ended'] and not process_alive(handover['process']),'Supervisor still active')
    require(ref(ROOT,BASE/'live-calls.json')==handover['ledger'],'Charges changed after handover')
    for pointer in handover['dispatches']: verify(ROOT,pointer)
    paths=[*CHANGED,str(PROGRAM),str(STATE),str(DOC/'mission.json'),str(BASE/'current-binding.json'),
        str(BASE/'live-calls.json'),str(BASE/'live-grant.json'),str(OLD_WORK/'worker.json'),str(OLD_WORK/'armed.json'),
        handover['service']+'/service-circuit.json',handover['service']+'/service-recovery.json']
    if (ROOT/HERE/'baseline.json').exists():
        baseline=read(ROOT/HERE/'baseline.json')
        require(baseline['settled'] and baseline['handover']==ref(ROOT,HERE/'handover.json')
            and [r['previous']['path'] for r in baseline['archived']]==paths,
            'Changed partial seeding baseline')
        for row in baseline['archived']:
            verify(ROOT,row['previous']);verify(ROOT,row['archive'])
            require(row['previous']['sha256']==row['archive']['sha256'],'Changed partial archive')
    else:
        archived=[]
        for path in paths:
            target=HERE/'before'/path; (ROOT/target).parent.mkdir(parents=True,exist_ok=True)
            with (ROOT/target).open('xb') as out: out.write((ROOT/path).read_bytes())
            archived.append(dict(previous=ref(ROOT,path),archive=ref(ROOT,target)))
        baseline=dict(settled=True,handover=ref(ROOT,HERE/'handover.json'),archived=archived,
            calls=handover['calls'],service_charges=len(read(ROOT/handover['service']/'service-recovery.json')['charges']),at_utc=now())
        save(ROOT/HERE/'baseline.json',baseline)
    service=provider(); service.check()
    checkpoints=deepcopy(read(ROOT/PROGRAM)['review_repair']['deployment']['arm_checkpoints'])
    imported=[];superseded=[]
    for journal in sorted((ROOT/SOURCE/'arms').glob('*/*/calls/dispatch.json')):
        directory=journal.parent.parent; qid,arm=directory.parent.name,directory.name
        require(qid in checkpoints and arm in checkpoints[qid],'Unknown arm')
        checkpoint=deepcopy(read(ROOT/checkpoints[qid][arm]['path']))
        identity,saved=read(directory/'identity.json'),read(journal)
        require(checkpoint['input_hash']==saved['input_hash'],'Changed seeded input')
        checker=BoundDispatch(service,directory/'calls',SimpleNamespace(limits=Limits(**identity['limits'])))
        if identity.get('common_capacity_profile'): checker.capacity_manager=True
        for key,row in saved['calls'].items():
            require(Path(key).name==key and row['status']!='RESERVED','Uncertain seed call')
            folder=directory/'calls'/key
            pointers={n:ref(ROOT,folder/(n+'.json')) for n in ('request','schema','result')}
            pointers['dispatch']=ref(ROOT,journal)
            request,schema,result=[read(ROOT/pointers[n]['path']) for n in ('request','schema','result')]
            require(row['identity']==checker.request_identity(request,schema) and row['result_hash']==digest(result)
                and row['status']==result['status'] and result['status'] in ('VALIDATED','FAILED')
                and not result.get('continuation_veto'),'Changed or vetoed seed result')
            if key in checkpoint['calls']:
                previous=checkpoint_predecessor(ROOT,qid,arm,key,checkpoint['calls'][key],pointers)
                if previous: superseded.append(previous)
            checkpoint['calls'][key]={**pointers,'mode':'VALIDATED' if result['status']=='VALIDATED' else 'RETAINED_FAILURE'}
            imported.append(dict(question=qid,arm=arm,key=key,status=result['status'],**pointers))
        target=HERE/'checkpoints'/qid/(arm+'.json')
        if (ROOT/target).exists():
            require(read(ROOT/target)==checkpoint,'Changed partial checkpoint')
        else: save(ROOT/target,checkpoint)
        checkpoints[qid][arm]=ref(ROOT,target)
    seed=dict(arm_checkpoints=checkpoints,imported=imported,superseded_failed_contracts=superseded,provider_calls=0,
        baseline=ref(ROOT,HERE/'baseline.json'),historical_decisions_unchanged=True,failed_results_retained=True)
    save(ROOT/HERE/'seed.json',seed)
    return dict(imported=len(imported),provider_calls=0,calls_preserved=baseline['calls'])

def install():
    prepared=verify_preparation()
    handover=read(ROOT/HERE/'handover.json')
    require(handover['supervisor_ended'] and not process_alive(handover['process']),'Unsafe install boundary')
    require(ref(ROOT,BASE/'live-calls.json')==handover['ledger'],'Calls changed before install')
    seed=read(ROOT/HERE/'seed.json'); require(seed['provider_calls']==0,'Seed dispatched a call')
    for path in CHANGED:
        destination=ROOT/path; source=ROOT/HERE/'candidate'/path
        require(not destination.is_symlink() and not source.is_symlink(),'Symlink installation refused')
        temporary=destination.with_name(destination.name+'.quotation-installing')
        with temporary.open('xb') as out: out.write(source.read_bytes())
        temporary.chmod(destination.stat().st_mode & 0o777)
        temporary.replace(destination)
    save(ROOT/HERE/'installation.json',dict(installed=[ref(ROOT,p) for p in CHANGED+ADDED],
        preparation=ref(ROOT,HERE/'preparation.json'),at_utc=now(),provider_calls=0))
    return dict(installed=len(CHANGED),provider_calls=0,registration_pending=True)

def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_review_timeout_correction import verify_orphans
    journal=HERE/'registration.json'
    with ExitStack() as stack:
        for path in (OLD_WORK/'worker.lock',HERE/'worker.lock',STATE.with_suffix('.run.lock'),
                DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a')); fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            finish_transaction(ROOT,journal); return dict(registered=True,resumed=True)
        baseline=read(ROOT/HERE/'baseline.json'); rows=baseline['archived']
        held={r['previous']['path']:r['archive'] for r in rows}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'],'Boundary changed '+str(path))
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        verify_orphans(ROOT,before,ROOT/SOURCE)
        revision=dict(profile='optional-answer-quotation-validation.v1',runtime=str(RUNTIME),prior_detours=64,
            additional_consolidated_revision=1,calls_added=0,attempts_added=0,service_replacements_added=0,
            review=ref(ROOT,REVIEW),result=ref(ROOT,HERE/'local-result.json'),baseline=ref(ROOT,HERE/'baseline.json'),
            seed=ref(ROOT,HERE/'seed.json'),prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],
            prior_binding=held[str(BASE/'current-binding.json')],implementation={p:ref(ROOT,p) for p in CHANGED+ADDED},
            arm_checkpoints=read(ROOT/HERE/'seed.json')['arm_checkpoints'])
        program=expected_program(old,revision,ROOT,ref(ROOT,PLAN))
        state=deepcopy(before); state['program_hash']=digest(program)
        state['events'].append(dict(action='OPTIONAL_QUOTATION_VALIDATION',task_id='baseline-p14',at_utc=now(),
            review=revision['review'],calls_added=0,attempts_added=0,attempts_reset=False))
        stage=HERE/'registration-stage'
        save(ROOT/stage/'program.json',program); save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        binding=deepcopy(read(ROOT/BASE/'current-binding.json'))
        binding['bindings']=historical_projection(binding['bindings'],mapping(rows,mission=True))
        binding.update(program=pointer,optional_quote_validation=revision,predecessor=revision['prior_binding'])
        binding['bindings'] += [pointer,ref(ROOT,PLAN),*[revision[k] for k in ('review','result','baseline','seed')],
            *revision['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in rows if (r['previous']['path'],r['previous']['sha256']) not in known]
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mapping(rows,mission=True))
        mission['integration_master'].update(program=pointer,plan=ref(ROOT,PLAN),review_repair=program['review_repair'])
        reason='Reject false optional answer quotations, retain affected original unresolved decisions and continue independent context/correction work under the same attempts and authority.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='p14-optional-quotation-integrity-2026-10-23',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',recorded_at_utc=now(),decision=reason,
            next_task='product-contribution',next_task_reason=reason,result_evidence=[pointer,revision['review'],revision['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/HERE/'registration-check.json',validate_staged_mission(ROOT,stage,mission,65))
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,detours=65,calls_added=0,attempts_added=0)

def worker():
    from scripts.legal_review_timeout_correction import verify_orphans
    from scripts.legal_review_repair import live as drain
    spec=importlib.util.spec_from_file_location('p14_retained_owner',ROOT/OLD_WORK.parent/'requested_owner.py')
    selected=importlib.util.module_from_spec(spec); spec.loader.exec_module(selected)
    with (ROOT/HERE/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(ROOT/HERE/'worker.json',dict(process=process_identity(os.getpid()),at_utc=now()))
        try:
            verify_orphans(ROOT,read(ROOT/STATE),ROOT/RUNTIME)
            execution=MasterExecution(ROOT,PROGRAM,STATE)
            for tid in SELECTED:
                save(ROOT/HERE/(tid+'.started.json'),dict(at_utc=now(),task_id=tid))
                save(ROOT/HERE/(tid+'.result.json'),selected.run_selected(execution,tid))
            save(ROOT/HERE/'live-result.json',drain())
        except BaseException as exc:
            import traceback
            save(ROOT/HERE/'worker-error.json',dict(error=type(exc).__name__,reason=str(getattr(exc,'details',None) or exc),
                traceback=traceback.format_exc(),at_utc=now()))
            raise
        finally:
            steps=[]
            for action in ('refresh','status'):
                command=([str(ROOT/'.venv/bin/python'),'scripts/legal_mission_control.py',action] if action=='refresh'
                    else [str(ROOT/'.venv-context/bin/python'),'scripts/legal_integration_master.py',action])
                with (ROOT/HERE/(action+'.stdout')).open('w') as out,(ROOT/HERE/(action+'.stderr')).open('w') as err:
                    code=subprocess.call(command,cwd=ROOT,stdout=out,stderr=err)
                steps.append(dict(command=command,exit_code=code))
            save(ROOT/HERE/'finished.json',dict(steps=steps,at_utc=now(),integration_complete=False))

def arm():
    from scripts.legal_integration_campaign import provider
    with (ROOT/HERE/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/HERE/'armed.json'
        if path.exists():
            saved=read(path); require(process_alive(saved['process']),'Prior worker ended; inspect before restart')
            return dict(already_running=True,**saved)
        require(read(ROOT/HERE/'registration.json')['status']=='COMMITTED','Quotation registration pending')
        handover=read(ROOT/HERE/'handover.json')
        require(handover['supervisor_ended'] and not process_alive(handover['process']),'Old supervisor active')
        provider().check()
        with (ROOT/HERE/'worker.log').open('a') as log:
            process=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(ROOT/SELF),'worker'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        identity=process_identity(process.pid); require(identity is not None,'Worker exited at startup')
        value=dict(process=identity,at_utc=now()); save(path,value); return value

def status():
    result=dict(at_utc=now(),receipts={p.name:read(p) for p in (ROOT/HERE).glob('*.json')
        if p.name in ('armed.json','worker.json','worker-error.json','finished.json','registration-check.json')})
    worker=result['receipts'].get('worker.json')
    if worker:
        result['process_identity_matches']=process_alive(worker['process'])
        if result['process_identity_matches']:
            result['children']=owner_children(worker['process']); result['process_state']=owner_state(worker['process'])
    ledger=read(ROOT/BASE/'live-calls.json'); result['calls']=len(ledger['calls']);result['ceiling']=ledger['maximum']
    binding=read(ROOT/BASE/'current-binding.json'); service=ROOT/Path(binding['phase_service_scope']['path']).parent
    recovery=read(service/'service-recovery.json'); result['recovery_charges']=len(recovery['charges'])
    result['recovery_ceiling']=recovery['maximum']
    circuit=read(service/'service-circuit.json')
    result['circuit']={k:circuit.get(k) for k in ('open','half_open_reserved','resumed_at_utc')}
    return result

if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','settle','freeze_seed','install','register','arm','worker','status'])
    args=parser.parse_args()
    print(json.dumps(globals()[args.action](),indent=2))
