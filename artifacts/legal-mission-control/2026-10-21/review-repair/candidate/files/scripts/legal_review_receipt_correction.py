"""Amend R2 without resetting an original task, call or repair allowance."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import signal
import time

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = Path('artifacts/legal-mission-control/2026-10-21/review-repair')
HERE = WORK/'candidate'
RUNTIME = WORK/'continued-live'
KEY = 'receipt_correction'
CHANGED = ('scripts/legal_review_repair.py', 'scripts/legal_integration_phased_live.py',
    'src/legalmath/interpretation/assurance/phased/review_repair.py')
ADDED = ('scripts/legal_review_receipt_correction.py',
    'src/legalmath/interpretation/assurance/phased/review_receipts.py',
    'tests/assurance/test_review_receipts.py', 'tests/tooling/test_review_receipt_correction.py')


def mapped(rows, *, mission=False):
    excluded = {str(STATE), str(BASE/'current-binding.json'), str(BASE/'live-calls.json'),
        str(BASE/'live-grant.json'), str(DOC/'mission.json')}
    if not mission:
        excluded.add(str(PROGRAM))
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
        for r in rows if r['previous']['path'] not in excluded}


def expected_program(old, correction, root, plan_reference):
    rows=read(root/correction['baseline']['path'])['archived']
    value = historical_projection(old, mapped(rows))
    value['review_repair'][KEY] = correction
    value['protected_evidence'] += [correction[k] for k in ('review','result','baseline','seed')]
    value['protected_evidence'] += list(correction['implementation'].values())
    value['protected_evidence'].append(plan_reference)
    return value


def validate(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    correction = program['review_repair'][KEY]
    require(correction['profile'] == 'source-review-receipt-correction.v1'
        and correction['runtime'] == str(RUNTIME) and correction['calls_added'] == 0
        and correction['attempts_added'] == 0 and correction['detours_added'] == 0,
        'Unreviewed receipt correction')
    require(set(correction['implementation']) == set(CHANGED+ADDED), 'Changed R2 correction scope')
    for name in ('review','result','baseline','seed','prior_program','prior_state','prior_binding'):
        verify(root, correction[name])
    for item in correction['implementation'].values(): verify(root,item)
    baseline=read(root/correction['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed R2 predecessor bytes')
        verify(root,row['archive'])
    require(baseline['settled'] is True,
        'Receipt correction lacks its settled predecessor')
    held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    require(correction['prior_program']==held[str(PROGRAM)]
        and correction['prior_state']==held[str(STATE)]
        and correction['prior_binding']==held[str(BASE/'current-binding.json')],
        'Receipt correction changed predecessor')
    old=read(root/correction['prior_program']['path'])
    require(KEY not in old['review_repair'], 'Duplicate R2 correction')
    with historical_evidence(root,mapped(baseline['archived'])):
        validate_program(old,root)
    result=read(root/correction['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['legal_acceptance'] is False,
        'R2 correction lacks passing local evidence')
    for item in result['evidence']: verify(root,item)
    require(program == expected_program(old,correction,root,plan_reference),
        'R2 correction changed graph, attempts, authority or unrelated program')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def validate_history(program,state,root):
    correction=program['review_repair'][KEY]
    before=read(root/correction['prior_state']['path'])
    require(state['events'][:len(before['events'])] == before['events'], 'Lost R2 event history')
    for tid,row in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']), 'Lost R2 owner attempt')
        for a,b in zip(row['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()), 'Changed original attempt '+tid)
        if row['status']=='SUCCEEDED':
            require(current==row,'Successful task changed during R2 continuation')


def seed_runtime(root,source,destination,provider):
    """Copy exact settled dispatches; rebuild phase contracts under new binding."""
    root,source,destination=Path(root),Path(source),Path(destination)
    from types import SimpleNamespace
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.bounded_context import Limits
    require(source!=destination and not destination.exists(), 'Runtime seed must have a new destination')
    files=[]
    for identity in sorted(source.rglob('identity.json')):
        product=identity.parent
        journal=product/'calls/dispatch.json'
        if not journal.exists(): continue
        saved=read(journal)
        product_identity=read(identity)
        require(not any('repair-review-' in key for key in saved['calls']),
            'Cannot migrate an invalid-review pass already started')
        checker=BoundDispatch(provider,product/'calls',SimpleNamespace(limits=Limits(**product_identity['limits'])))
        if product_identity.get('common_capacity_profile'): checker.capacity_manager=True
        require(not any(r['status']=='RESERVED' for r in saved['calls'].values()), 'Uncertain seed dispatch')
        for key,row in saved['calls'].items():
            require(Path(key).name==key, 'Unsafe seed dispatch key')
            folder=product/'calls'/key
            request,schema,result=(read(folder/name) for name in ('request.json','schema.json','result.json'))
            require(row['identity']==checker.request_identity(request,schema)
                and row['result_hash']==digest(result) and row['status']==result['status'],
                'Changed seed dispatch')
        paths=[identity,product/'source-store.json',journal]
        paths += [p for p in sorted((product/'calls').rglob('*')) if p.is_file()
            and p!=journal and p.suffix not in ('.lock','.tmp')]
        for path in paths:
            require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'Foreign seed file')
            target=destination/path.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream: stream.write(path.read_bytes())
            require(ref(root,path)['sha256']==ref(root,target)['sha256'], 'Seed copy changed')
            files.append(dict(source=ref(root,path),copy=ref(root,target),mutable=path==journal))
    require(files,'No settled product dispatches to seed')
    return dict(profile='exact-settled-dispatch-seed.v1',files=files,
        source=str(source.relative_to(root)),destination=str(destination.relative_to(root)),
        phase_contracts_copied=False,provider_calls=0)


def settle_once(root=ROOT, *, expected=None):
    """Try a settled-call boundary; never signal a provider or uncertain owner."""
    from scripts.legal_mission_execution import process_identity
    root=Path(root)
    owner=read(root/WORK/'worker.json')['process']
    require(expected is not None and owner==expected and process_identity(owner['pid'])==owner,
        'Worker identity changed or is not visible in this context')
    with ExitStack() as stack:
        try:
            locks=[root/STATE.with_suffix('.lock'),root/WORK/'service/service-worker.lock']
            journals=sorted((root/WORK/'live').rglob('calls/dispatch.json'))
            locks += [p.with_name('dispatch.lock') for p in journals]
            for path in locks:
                handle=stack.enter_context(path.open('a'))
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(settled=False,reason='Owner is executing; boundary not acquired')
        state=read(root/STATE)
        active={tid:r for tid,r in state['tasks'].items() if r['status']=='RUNNING'}
        require(set(active)=={'baseline-gatecoin'} and active['baseline-gatecoin']['live_supervisor']==owner
            and len(active['baseline-gatecoin']['attempts'])==4, 'Different active task at R2 handover')
        circuit=read(root/WORK/'service/service-circuit.json')
        if circuit['open'] or circuit.get('half_open_reserved'):
            return dict(settled=False,reason='Service recovery still owns its request')
        for path in journals:
            calls=read(path)['calls']
            if any(r['status']=='RESERVED' for r in calls.values()):
                return dict(settled=False,reason='Request dispatch still reserved')
            require(not any('repair-review-' in k for k in calls), 'Invalid-review pass already started')
        children=Path(f'/proc/{owner["pid"]}/task/{owner["pid"]}/children')
        if children.read_text().strip():
            return dict(settled=False,reason='Worker has a child; no signal sent')
        before=ref(root,BASE/'live-calls.json')
        stopped=False
        try:
            os.kill(owner['pid'],signal.SIGSTOP)
            stopped=True
            for _ in range(100):
                fields=Path(f'/proc/{owner["pid"]}/stat').read_text().rsplit(') ',1)[1].split()
                if fields[0] in ('T','t'): break
                time.sleep(.01)
            require(fields[0] in ('T','t') and process_identity(owner['pid'])==owner
                and not children.read_text().strip() and ref(root,BASE/'live-calls.json')==before,
                'Worker did not reach a stable settled boundary')
            evidence=dict(settled=True,process=owner,at_utc=datetime.now(timezone.utc).isoformat(),
                task='baseline-gatecoin',attempt=4,ledger=before,provider_children=[],reserved_dispatches=0,
                dispatches=[ref(root,p) for p in journals],calls=len(read(root/BASE/'live-calls.json')['calls']),
                reason='Controlled implementation handover after a settled call; retain RUNNING reservation')
            save(root/HERE/'handover.json',evidence)
            os.kill(owner['pid'],signal.SIGTERM)
            os.kill(owner['pid'],signal.SIGCONT)
            stopped=False
            for _ in range(100):
                if process_identity(owner['pid']) is None: break
                time.sleep(.05)
            require(process_identity(owner['pid']) is None,'Supervisor did not exit; no deployment authorized')
            evidence['supervisor_ended']=True
            save(root/HERE/'handover.json',evidence)
            return evidence
        finally:
            if stopped: os.kill(owner['pid'],signal.SIGCONT)


def freeze(root=ROOT):
    root=Path(root)
    require(not (root/HERE/'baseline.json').exists(),'R2 predecessor already frozen')
    ended=read(root/HERE/'handover.json')
    from scripts.legal_mission_execution import process_alive
    require(ended['supervisor_ended'] and not process_alive(ended['process']), 'Handover owner remains alive')
    rows=[]
    paths=[*CHANGED,str(PLAN),str(PROGRAM),str(STATE),str(DOC/'mission.json'),
        str(BASE/'current-binding.json'),str(BASE/'live-calls.json'),str(BASE/'live-grant.json'),
        str(WORK/'worker.json'),str(WORK/'service/service-circuit.json'),str(WORK/'service/service-recovery.json')]
    for relative in paths:
        archive=HERE/'before'/relative
        target=root/archive
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream: stream.write((root/relative).read_bytes())
        rows.append(dict(previous=ref(root,relative),archive=ref(root,archive)))
    require(ref(root,BASE/'live-calls.json')==ended['ledger'],'Calls changed after handover')
    from scripts.legal_integration_campaign import provider
    seed=seed_runtime(root,root/WORK/'live',root/RUNTIME,provider())
    save(root/HERE/'seed.json',seed)
    baseline=dict(settled=True,archived=rows,handover=ref(root,HERE/'handover.json'),
        seed=ref(root,HERE/'seed.json'),calls=ended['calls'],attempts_added=0,detours_added=0)
    save(root/HERE/'baseline.json',baseline)
    return baseline


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import LIVE
    from scripts.legal_integration_repair_execution import validate_staged_mission
    journal=HERE/'registration.json'
    with ExitStack() as stack:
        for path in (WORK/'worker.lock',LIVE/'supervisor.lock',WORK/'live/supervisor.lock',
                RUNTIME/'supervisor.lock',WORK/'service/service-worker.lock',
                STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED': finish_transaction(ROOT,journal)
            require(read(ROOT/PROGRAM)['review_repair'].get(KEY),'Different receipt correction registered')
            return dict(registered=True,resumed=True)
        baseline=read(ROOT/HERE/'baseline.json')
        held={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'],'R2 predecessor changed: '+str(path))
        old,state=read(ROOT/PROGRAM),read(ROOT/STATE)
        correction=dict(profile='source-review-receipt-correction.v1',runtime=str(RUNTIME),
            calls_added=0,attempts_added=0,detours_added=0,
            review=ref(ROOT,HERE/'review.md'),result=ref(ROOT,HERE/'result.json'),
            baseline=ref(ROOT,HERE/'baseline.json'),seed=ref(ROOT,HERE/'seed.json'),
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],
            prior_binding=held[str(BASE/'current-binding.json')],
            implementation={p:ref(ROOT,p) for p in CHANGED+ADDED})
        program=expected_program(old,correction,ROOT,ref(ROOT,PLAN))
        validate(program,ROOT,ref(ROOT,PLAN))
        stage=HERE/'registration-stage'
        now=datetime.now(timezone.utc).isoformat()
        state['program_hash']=digest(program)
        state['events'].append(dict(task_id=None,action='REVIEW_RECEIPT_CORRECTION',at_utc=now,
            review=correction['review'],attempts_added=0,calls_added=0))
        save(ROOT/stage/'program.json',program)
        save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        previous=read(ROOT/BASE/'current-binding.json')
        binding=deepcopy(previous)
        binding['bindings']=historical_projection(binding['bindings'],mapped(baseline['archived'],mission=True))
        binding['program']=pointer
        binding['bindings'] += [pointer,ref(ROOT,PLAN),correction['review'],correction['result'],
            correction['baseline'],correction['seed'],*correction['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in baseline['archived']
            if (r['previous']['path'],r['previous']['sha256']) not in known]
        binding['receipt_correction']=correction['review']
        binding['predecessor']=correction['prior_binding']
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mapped(baseline['archived'],mission=True))
        master=mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'):
                master[key]=deepcopy(program[key])
        master.update(program=pointer,plan=ref(ROOT,PLAN),review_repair=program['review_repair'])
        reason='Resume Gatecoin attempt 4 with authenticated malformed-review repair and bounded diagnostics; continue independent original owners.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='review-receipt-correction-2026-10-21',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,correction['review'],correction['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/HERE/'registration-check.json',validate_staged_mission(ROOT,stage,mission,62))
        # Validate actual provider authority with staged program/binding and no dispatch.
        from unittest.mock import patch
        from scripts.legal_integration_campaign import provider
        targets={ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        rt,rb=Path.read_text,Path.read_bytes
        with patch.object(Path,'read_text',lambda path,*a,**k:rt(targets.get(path,path),*a,**k)), \
             patch.object(Path,'read_bytes',lambda path,*a,**k:rb(targets.get(path,path),*a,**k)):
            require(len(provider().check()['calls'])==baseline['calls'],'R2 authority changed charges')
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,calls_added=0,attempts_added=0,detours_added=0,resume_task='baseline-gatecoin',attempt=4)
