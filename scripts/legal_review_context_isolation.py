"""Preserve the active P14 run while isolating fresh context classifications."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_review_receipt_correction import mapped as previous_mapping

HERE = Path('artifacts/legal-mission-control/2026-10-23/p14-corrected-context')
DEPLOYMENT = Path('artifacts/legal-mission-control/2026-10-23/p14-deployment')
SOURCE = DEPLOYMENT/'live'
RUNTIME = DEPLOYMENT/'context-isolated-live'
REVIEW = Path('docs/plans/p14-corrected-context-isolation-2026-10-23.md')
KEY = 'context_isolation'
CHANGED = ('src/legalmath/interpretation/assurance/phased/context_disposition.py',
    'scripts/legal_review_deployment.py', 'scripts/legal_mission_control.py',
    'src/legalmath/interpretation/assurance/phased/review_repair.py')
ADDED = ('scripts/legal_review_context_isolation.py',
    'tests/assurance/test_corrected_context_disposition.py',
    'tests/tooling/test_review_context_isolation.py',
    'tests/assurance/test_context_pointer_warrant_targets.py')


def archive_rows(root, baseline):
    additional=read(Path(root)/HERE/'additional-before.json')
    rows=baseline['archived']+additional['archived']
    require(len({r['previous']['path'] for r in rows})==len(rows),'Repeated context archive')
    return rows


def mapped(rows, *, mission=False):
    # Mutable service ledgers are archived as evidence, not rewritten in old
    # programs. Identical old snapshots may already have a different archive.
    allowed = set(CHANGED) | ({str(PROGRAM)} if mission else set())
    return previous_mapping([r for r in rows if r['previous']['path'] in allowed], mission=mission)


def settle():
    """No signal unless all dispatches are settled and the exact owner is idle."""
    from scripts.legal_mission_execution import process_identity, process_alive
    receipt = ROOT/HERE/'handover.json'
    if receipt.exists():
        saved = read(receipt)
        require(saved.get('supervisor_ended') and not process_alive(saved['process']),
            'Incomplete prior handover requires inspection')
        return saved
    owner = read(ROOT/DEPLOYMENT/'worker.json')['process']
    require(read(ROOT/DEPLOYMENT/'armed.json')['process'] == owner
        and process_identity(owner['pid']) == owner, 'Deployment supervisor identity changed')
    with ExitStack() as stack:
        journals = sorted((ROOT/SOURCE).rglob('calls/dispatch.json'))
        paths = [ROOT/STATE.with_suffix('.lock'), ROOT/DOC/'mission.execution.lock',
            ROOT/DEPLOYMENT/'service/service-worker.lock',
            ROOT/DEPLOYMENT/'service/service-circuit.lock'] + [p.with_name('dispatch.lock') for p in journals]
        try:
            for path in paths:
                handle = stack.enter_context(path.open('a'))
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(settled=False, reason='State or provider is active; no signal sent')
        state = read(ROOT/STATE)
        require(state['tasks']['baseline-p14']['status'] == 'RUNNING'
            and len(state['tasks']['baseline-p14']['attempts']) == 5
            and state['tasks']['baseline-p14'].get('live_supervisor') == owner,
            'P14 left the reviewed continuation boundary')
        require(all(r.get('master_live') and r.get('live_supervisor') and
            (r['live_supervisor'] == owner or not process_alive(r['live_supervisor']))
            for r in state['tasks'].values() if r['status'] == 'RUNNING'),
            'Another active owner prevents handover')
        if any(r['status'] == 'RESERVED' for p in journals for r in read(p)['calls'].values()):
            return dict(settled=False, reason='Reserved dispatch remains; no signal sent')
        circuit = read(ROOT/DEPLOYMENT/'service/service-circuit.json')
        if circuit.get('open', True) or any(circuit.get(key) for key in
                ('half_open_reserved', 'half_open_request_hash', 'half_open_schema_hash')):
            return dict(settled=False, reason='Service recovery is not settled; no signal sent')
        children = Path(f'/proc/{owner["pid"]}/task/{owner["pid"]}/children')
        if children.read_text().strip():
            return dict(settled=False, reason='Supervisor has a child; no signal sent')
        before = ref(ROOT, BASE/'live-calls.json')
        stopped = False
        try:
            os.kill(owner['pid'], signal.SIGSTOP)
            stopped = True
            for _ in range(100):
                fields = Path(f'/proc/{owner["pid"]}/stat').read_text().rsplit(') ', 1)[1].split()
                if fields[0] in ('T', 't'):
                    break
                time.sleep(.01)
            require(fields[0] in ('T', 't') and process_identity(owner['pid']) == owner
                and not children.read_text().strip() and ref(ROOT, BASE/'live-calls.json') == before
                and sorted((ROOT/SOURCE).rglob('calls/dispatch.json')) == journals
                and read(ROOT/DEPLOYMENT/'service/service-circuit.json') == circuit,
                'Supervisor did not reach a stable idle boundary')
            value = dict(settled=True, process=owner, at_utc=datetime.now(timezone.utc).isoformat(),
                ledger=before, calls=len(read(ROOT/BASE/'live-calls.json')['calls']),
                dispatches=[ref(ROOT, p) for p in journals], reserved_dispatches=0,
                provider_children=[], service_settled=True,
                circuit=ref(ROOT, DEPLOYMENT/'service/service-circuit.json'),
                reason='Reviewed corrected-context classification repair')
            save(receipt, value)
            os.kill(owner['pid'], signal.SIGTERM)
            os.kill(owner['pid'], signal.SIGCONT)
            stopped = False
            for _ in range(100):
                if not process_alive(owner):
                    break
                time.sleep(.05)
            require(not process_alive(owner), 'Supervisor did not end')
            value['supervisor_ended'] = True
            save(receipt, value)
            return value
        finally:
            if stopped:
                os.kill(owner['pid'], signal.SIGCONT)


def freeze():
    from scripts.legal_mission_execution import process_alive
    from scripts.legal_review_timeout_correction import verify_orphans
    require(not (ROOT/HERE/'baseline.json').exists(), 'Context predecessor already frozen')
    ended = read(ROOT/HERE/'handover.json')
    require(ended['supervisor_ended'] and not process_alive(ended['process']), 'Supervisor remains active')
    require(ref(ROOT, BASE/'live-calls.json') == ended['ledger'], 'Charges changed after handover')
    require(ended['service_settled'] and ref(ROOT, DEPLOYMENT/'service/service-circuit.json') == ended['circuit'],
        'Service recovery changed after handover')
    for pointer in ended['dispatches']:
        verify(ROOT, pointer)
    verify_orphans(ROOT, read(ROOT/STATE), ROOT/SOURCE)
    paths = [*CHANGED, str(PROGRAM), str(STATE), str(DOC/'mission.json'),
        str(BASE/'current-binding.json'), str(BASE/'live-calls.json'), str(BASE/'live-grant.json'),
        str(DEPLOYMENT/'worker.json'), str(DEPLOYMENT/'armed.json'),
        str(DEPLOYMENT/'service/service-circuit.json'), str(DEPLOYMENT/'service/service-recovery.json')]
    archived = []
    for relative in paths:
        archive = HERE/'before'/relative
        (ROOT/archive).parent.mkdir(parents=True, exist_ok=True)
        with (ROOT/archive).open('xb') as stream:
            stream.write((ROOT/relative).read_bytes())
        archived.append(dict(previous=ref(ROOT, relative), archive=ref(ROOT, archive)))
    value = dict(settled=True, handover=ref(ROOT, HERE/'handover.json'), archived=archived,
        calls=ended['calls'], service_charges=len(read(ROOT/DEPLOYMENT/'service/service-recovery.json')['charges']),
        at_utc=datetime.now(timezone.utc).isoformat())
    save(ROOT/HERE/'baseline.json', value)
    return value


def seed():
    """Authenticate and retain settled calls; new requests keep their normal gates."""
    from types import SimpleNamespace
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.bounded_context import Limits
    from scripts.legal_integration_campaign import provider
    require(not (ROOT/HERE/'seed.json').exists(), 'Context seed already exists')
    baseline = read(ROOT/HERE/'baseline.json')
    require(ref(ROOT, BASE/'live-calls.json') == read(ROOT/HERE/'handover.json')['ledger'],
        'Calls changed before seeding')
    service = provider()
    service.check()
    old = read(ROOT/PROGRAM)['review_repair']['deployment']
    checkpoints = deepcopy(old['arm_checkpoints'])
    imported = []
    for journal in sorted((ROOT/SOURCE/'arms').glob('*/*/calls/dispatch.json')):
        directory = journal.parent.parent
        qid, arm = directory.parent.name, directory.name
        require(qid in checkpoints and arm in checkpoints[qid], 'Unreviewed arm checkpoint')
        checkpoint = deepcopy(read(ROOT/checkpoints[qid][arm]['path']))
        identity, saved = read(directory/'identity.json'), read(journal)
        require(checkpoint['input_hash'] == saved['input_hash'], 'Changed seeded input')
        checker = BoundDispatch(service, directory/'calls',
            SimpleNamespace(limits=Limits(**identity['limits'])))
        if identity.get('common_capacity_profile'):
            checker.capacity_manager = True
        for key, row in saved['calls'].items():
            require(Path(key).name == key and row['status'] != 'RESERVED', 'Unsettled seed request')
            folder = directory/'calls'/key
            pointers = {name: ref(ROOT, folder/(name+'.json')) for name in ('request','schema','result')}
            pointers['dispatch'] = ref(ROOT, journal)
            request, schema, result = [read(ROOT/pointers[name]['path']) for name in ('request','schema','result')]
            require(row['identity'] == checker.request_identity(request, schema)
                and row['result_hash'] == digest(result) and row['status'] == result['status'],
                'Seed request or result differs from its authenticated journal')
            require(result['status'] in ('VALIDATED','FAILED'), 'Unknown seed result status')
            require(not result.get('continuation_veto'), 'Seed contains an unresolved continuation veto')
            value = {**pointers, 'mode': 'VALIDATED' if result['status']=='VALIDATED' else 'RETAINED_FAILURE'}
            if key in checkpoint['calls']:
                require(read(ROOT/checkpoint['calls'][key]['result']['path']) == result,
                    'Seed would replace an earlier result')
            checkpoint['calls'][key] = value
            imported.append(dict(question=qid, arm=arm, key=key, status=result['status'], **pointers))
        target = HERE/'checkpoints'/qid/(arm+'.json')
        save(ROOT/target, checkpoint)
        checkpoints[qid][arm] = ref(ROOT, target)
    value = dict(arm_checkpoints=checkpoints, imported=imported, provider_calls=0,
        baseline=ref(ROOT,HERE/'baseline.json'), calls=baseline['calls'],
        historical_decisions_unchanged=True, failed_results_retained=True)
    save(ROOT/HERE/'seed.json', value)
    return dict(imported_calls=len(imported), provider_calls=0)


def expected_revision(old, isolation):
    value = deepcopy(old['review_repair']['deployment'])
    value.update(runtime=str(RUNTIME), result=isolation['result'],
        arm_checkpoints=isolation['arm_checkpoints'], context_isolation=isolation)
    value['implementation'].update({p:isolation['implementation'][p] for p in CHANGED})
    return value


def validate(program, root):
    from scripts.legal_mission_execution import validate_program
    root = Path(root)
    revision = program['review_repair']['deployment']
    isolated = revision[KEY]
    require(isolated['profile']=='corrected-context-isolation.v1'
        and isolated['runtime']==str(RUNTIME) and isolated['prior_detours']==63
        and isolated['additional_consolidated_revision']==1
        and isolated['calls_added']==isolated['attempts_added']==isolated['service_replacements_added']==0,
        'Changed corrected-context scope or allowance')
    require(set(isolated['implementation'])==set(CHANGED+ADDED), 'Changed isolation implementation')
    for key in ('review','result','baseline','additional_baseline','seed','prior_program','prior_state','prior_binding'):
        verify(root, isolated[key])
    for pointer in isolated['implementation'].values():
        verify(root, pointer)
    baseline = read(root/isolated['baseline']['path'])
    require(baseline['settled'], 'Context successor lacks a settled predecessor')
    verify(root, baseline['handover'])
    handover = read(root/baseline['handover']['path'])
    require(handover['supervisor_ended'] and handover['service_settled'],
        'Context predecessor did not end at settled service')
    require(isolated['additional_baseline']==ref(root,HERE/'additional-before.json'),'Changed extra archive')
    rows=archive_rows(root,baseline)
    held = {r['previous']['path']:r['archive'] for r in rows}
    for row in rows:
        require(row['previous']['sha256']==row['archive']['sha256'], 'Changed isolation predecessor bytes')
        verify(root, row['archive'])
    for key, path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')):
        require(isolated[key]==held[str(path)], 'Wrong isolation predecessor '+key)
    require(handover['circuit']['sha256'] == held[str(DEPLOYMENT/'service/service-circuit.json')]['sha256']
        and handover['ledger']['sha256'] == held[str(BASE/'live-calls.json')]['sha256'],
        'Handover differs from frozen ledgers')
    old = read(root/isolated['prior_program']['path'])
    require(KEY not in old['review_repair']['deployment'], 'Repeated context-isolation allowance')
    with historical_evidence(root, mapped(rows)):
        validate_program(old, root)
    require(revision==expected_revision(old,isolated), 'Unreviewed deployment change')
    result = read(root/isolated['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['legal_acceptance'] is False,
        'Isolation lacks passing local checks')
    for pointer in result['evidence']:
        verify(root,pointer)
    seeded = read(root/isolated['seed']['path'])
    require(seeded['provider_calls']==0 and seeded['historical_decisions_unchanged']
        and seeded['failed_results_retained'] and seeded['arm_checkpoints']==isolated['arm_checkpoints']
        and seeded['baseline']==isolated['baseline'], 'Changed isolation call seed')
    verify(root,seeded['warrant_target_followup'])
    followup=read(root/seeded['warrant_target_followup']['path'])
    require(followup['profile']=='reviewed-warrant-target-followup.v1'
        and followup['provider_calls']==0 and followup['legal_acceptance'] is False
        and followup['review']==isolated['review']
        and followup['excluded_issue_occurrences']==7
        and set(followup['retained_warrant_keys'])==set(followup['retained']),
        'Changed reviewed warrant target scope')
    for pointers in followup['retained'].values():
        for pointer in pointers.values(): verify(root,pointer)
    for rule in followup['exclusions'].values():
        verify(root,rule['result'])
        require(digest(read(root/rule['result']['path'])['value'])==rule['value_hash']
            and rule['disposition']=='EXCLUDE_FROM_ANSWER_CORRECTION_ONLY',
            'Changed non-answer exclusion evidence')
    for pointers in seeded['arm_checkpoints'].values():
        for pointer in pointers.values():
            verify(root,pointer)
    for row in seeded['imported']:
        for key in ('request','schema','result','dispatch'):
            verify(root,row[key])
        result = read(root/row['result']['path'])
        recorded = read(root/row['dispatch']['path'])['calls'][row['key']]
        require(recorded['status']==result['status']==row['status']
            and recorded['result_hash']==digest(result), 'Changed imported result')


def project_state(before, program, now):
    value = deepcopy(before)
    value['program_hash'] = digest(program)
    value['events'].append(dict(action='CORRECTED_CONTEXT_ISOLATED',task_id='baseline-p14',at_utc=now,
        review=program['review_repair']['deployment'][KEY]['review'],
        calls_added=0,attempts_added=0,service_replacements_added=0,attempts_reset=False))
    return value


def validate_history(program, state, root):
    revision = program['review_repair']['deployment'][KEY]
    before = read(Path(root)/revision['prior_state']['path'])
    require(state['events'][:len(before['events'])]==before['events'], 'Lost context predecessor events')
    for tid, row in before['tasks'].items():
        current = state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']), 'Lost context predecessor attempt')
        for a,b in zip(row['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()), 'Changed context predecessor attempt '+tid)
        if row['status']=='SUCCEEDED':
            require(current==row, 'Successful independent task changed')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])),
        'Lost context predecessor veto')


def register():
    from scripts import legal_review_deployment as deployment
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_review_timeout_correction import verify_orphans
    journal = HERE/'registration.json'
    with ExitStack() as stack:
        for path in (DEPLOYMENT/'worker.lock',HERE/'worker.lock',
                DEPLOYMENT/'service/service-worker.lock',SOURCE/'supervisor.lock',RUNTIME/'supervisor.lock',
                STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            finish_transaction(ROOT,journal)
            return dict(registered=True,resumed=True)
        baseline=read(ROOT/HERE/'baseline.json')
        rows=archive_rows(ROOT,baseline)
        held={r['previous']['path']:r['archive'] for r in rows}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json',
                DEPLOYMENT/'service/service-recovery.json',DEPLOYMENT/'service/service-circuit.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'], 'Changed context boundary '+str(path))
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        verify_orphans(ROOT,before,ROOT/SOURCE)
        isolated=dict(profile='corrected-context-isolation.v1',runtime=str(RUNTIME),
            prior_detours=63,additional_consolidated_revision=1,calls_added=0,attempts_added=0,
            service_replacements_added=0,review=ref(ROOT,REVIEW),result=ref(ROOT,HERE/'local-result.json'),
            baseline=ref(ROOT,HERE/'baseline.json'),seed=ref(ROOT,HERE/'seed.json'),
            additional_baseline=ref(ROOT,HERE/'additional-before.json'),
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            implementation={p:ref(ROOT,p) for p in CHANGED+ADDED},
            arm_checkpoints=read(ROOT/HERE/'seed.json')['arm_checkpoints'])
        revised=expected_revision(old,isolated)
        # Rebuild the same deployment from its original sealed predecessor.
        # The immediate predecessor is additionally authenticated by isolation.validate.
        ancestor=read(ROOT/revised['prior_program']['path'])
        program=deployment.expected_program(ancestor,revised,ROOT,ref(ROOT,PLAN))
        deployment.validate(program,ROOT,ref(ROOT,PLAN))
        now=datetime.now(timezone.utc).isoformat()
        state=project_state(before,program,now)
        deployment.validate_history(program,state,ROOT)
        stage=HERE/'registration-stage'
        save(ROOT/stage/'program.json',program)
        save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        binding=deepcopy(read(ROOT/BASE/'current-binding.json'))
        binding['bindings']=historical_projection(binding['bindings'],mapped(rows,mission=True))
        binding.update(program=pointer,context_isolation=isolated,predecessor=isolated['prior_binding'])
        binding['bindings'] += [pointer,ref(ROOT,PLAN),*[isolated[k] for k in (
            'review','result','baseline','additional_baseline','seed','prior_program','prior_state','prior_binding')],
            *isolated['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in rows
            if (r['previous']['path'],r['previous']['sha256']) not in known]
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mapped(rows,mission=True))
        master=mission['integration_master']
        master.update(program=pointer,plan=ref(ROOT,PLAN),review_repair=program['review_repair'])
        reason=('Resume the same P14 attempt with exact settled calls preserved and fresh corrected-review needs '
            'isolated from original classifications; continue independent original owners without added authority.')
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='p14-corrected-context-isolation-2026-10-23',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,isolated['review'],isolated['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/HERE/'registration-check.json',validate_staged_mission(ROOT,stage,mission,64))
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,calls_added=0,attempts_added=0,service_replacements_added=0,detours=64)


if __name__=='__main__':
    import argparse, json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['settle','freeze','seed','register'])
    parser.add_argument('--wait-seconds',type=int,default=0,choices=range(0,51),
        metavar='0..50',help='For settle only: poll the same nonblocking checks for at most 50 seconds.')
    args=parser.parse_args()
    parser.error('--wait-seconds requires settle') if args.wait_seconds and args.action!='settle' else None
    end=time.monotonic()+args.wait_seconds
    while True:
        result=globals()[args.action]()
        if args.action!='settle' or result.get('settled') or time.monotonic()>=end:
            break
        time.sleep(min(.2,max(0,end-time.monotonic())))
    print(json.dumps(result,indent=2))
