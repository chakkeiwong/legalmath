"""Single-use checked adoption and continuation of common capacity.

No arbitrary commands or paths are accepted. The recorded predecessor settles
before code changes. All live actions retain the original grant and deadline.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'
STAGE = WORK/'staging'
BASE = ROOT/'artifacts/legal-mission-control/2026-10-13/master'
OLD = ROOT/'artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry'
PROGRAM = ROOT/'docs/implementation/legal-mission-control/integration-master.json'
MISSION = ROOT/'docs/implementation/legal-mission-control/mission.json'
PLAN = ROOT/'docs/plans/legal-integration-master-2026-10-13.md'
REVIEW = ROOT/'docs/plans/legal-common-capacity-interface-2026-10-20.md'
DEADLINE = datetime.fromisoformat('2026-10-20T18:55:16+00:00')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.writing')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha256(path.read_bytes()).hexdigest())


def require(ok, why):
    if not ok:
        raise ValueError(why)


def verify(pointer):
    path = (ROOT/pointer['path']).resolve()
    require(path.is_relative_to(ROOT) and ref(path) == pointer, 'Changed reviewed file: ' + pointer['path'])
    return path


def identity(pid):
    try:
        fields = Path('/proc/'+str(pid)+'/stat').read_text().rsplit(') ',1)[1].split()
        return None if fields[0] == 'Z' else dict(pid=pid, start=fields[19])
    except (OSError, IndexError):
        return None


def alive(process):
    return bool(process) and identity(process['pid']) == process


def checked_manifest():
    manifest = read(WORK/'deployment-manifest.json')
    require(manifest['profile'] == 'common-capacity-deployment.v1', 'Unknown deployment manifest')
    require(manifest['deadline_utc'] == DEADLINE.isoformat() and manifest['provider_calls_added'] == 0, 'Changed authority')
    for pointer in manifest['evidence']:
        verify(pointer)
    require(len({r['target'] for r in manifest['writes']}) == len(manifest['writes']), 'Duplicate deployment target')
    require({r['target'] for r in manifest['writes']} == set(read(WORK/'implementation-files.json')) | {str(PLAN.relative_to(ROOT))},
        'Deployment differs from reviewed implementation scope')
    for row in manifest['writes']:
        target = (ROOT/row['target']).resolve()
        require(target.is_relative_to(ROOT) and not set(target.relative_to(ROOT).parts) & {'.git','.codex','.agents','.aws'},
            'Unsafe deployment target')
        require(row['replacement']['path'] == str((STAGE/row['target']).relative_to(ROOT)), 'Foreign staged replacement')
        require(row['before'] is None or row['before']['path'] == row['target'], 'Foreign deployment baseline')
        verify(row['replacement'])
    return manifest


def status():
    result = dict(deployment_registered=(WORK/'registration.json').exists(),
        predecessor_alive=alive(read(OLD/'execution/worker.json')['process']),
        predecessor_result=(OLD/'execution/result.json').exists(),
        live_deadline_utc=DEADLINE.isoformat(), live_deadline_expired=datetime.now(timezone.utc) >= DEADLINE)
    if not result['predecessor_alive'] and not result['predecessor_result']:
        result['process_visibility'] = 'UNKNOWN: absent from this /proc view; trusted identity check required'
    for name in ('armed','continuation-state','continuation-result'):
        path = WORK/(name+'.json')
        if path.exists(): result[name] = read(path)
    return result


def settled(manifest):
    require(ref(PROGRAM) == manifest['predecessor_program'], 'A different master revision is active')
    require(read(OLD/'execution/worker.json')['process'] == manifest['predecessor_worker'], 'Predecessor identity changed')
    if alive(manifest['predecessor_worker']):
        return False
    active = read(OLD/'execution/active-command.json')
    require(not alive(active['process']), 'A predecessor child is still active')
    require((OLD/'execution/result.json').exists(), 'Predecessor died without a completion record; reconcile first')
    result = read(OLD/'execution/result.json')
    require(len(result['commands']) == 4, 'Predecessor wrapper is incomplete')
    for command in result['commands']:
        verify(command['stdout']); verify(command['stderr'])
    state = read(BASE/'execution-state.json')
    require(not any(row['status'] == 'RUNNING' for row in state['tasks'].values()), 'Unsettled master owner remains')
    reserved = []
    for path in (OLD/'live').rglob('dispatch.json'):
        for key,row in read(path)['calls'].items():
            if row['status'] == 'RESERVED': reserved.append(dict(path=str(path.relative_to(ROOT)), key=key))
    require(not reserved, 'Uncertain predecessor dispatches require reconciliation: ' + json.dumps(reserved))
    for path in (OLD/'live').rglob('product-binding.json'):
        require(read(path)['status'] != 'RESERVED', 'Uncertain predecessor native action: ' + str(path))
    return True


def checkpoints():
    program = read(PROGRAM)
    for question in ('p10','p14','evidence','gatecoin'):
        prepared = read(ROOT/program['candidate_capacity_retry']['checkpoints'][question]['path'])
        calls = {}
        folder = OLD/'live'/question/'product/calls'
        for key in ('candidates-'+question, 'criticism-'+question):
            directory = folder/key
            if not (directory/'result.json').exists(): continue
            result = read(directory/'result.json')
            row = {name:ref(directory/(name+'.json')) for name in ('request','schema','result')}
            if result['status'] == 'VALIDATED':
                row['mode'] = 'VALIDATED'
            elif question == 'p14' and key == 'criticism-p14' and result.get('error') == 'E_RESOURCE_LIMIT':
                row.update(mode='OUTPUT_BUDGET_REVALIDATION', reference_binding=ref(directory/'reference-binding.json'),
                    transport_manifest=ref(BASE/'provider-evidence/3449-38a69a1728a57217/manifest.json'))
            elif result['status'] == 'FAILED' and result.get('error') not in ('E_RESOURCE_LIMIT','E_DEPENDENCY'):
                row['mode'] = 'RETAINED_FAILURE'
            else:
                continue
            calls[key] = row
        common = dict(profile='common-capacity-checkpoint.v1', input_hash=prepared['input_hash'], calls=calls)
        save(WORK/'checkpoints'/(question+'.json'), common)
        for arm in sorted((OLD/'live/arms'/question).glob('*')):
            if not arm.is_dir() or not (arm/'calls/dispatch.json').exists(): continue
            journal = read(arm/'calls/dispatch.json')
            require(journal['input_hash'] == prepared['input_hash'], 'Arm input changed')
            retained = dict(calls)
            retry = []
            for key, entry in journal['calls'].items():
                require(entry['status'] != 'RESERVED', 'Uncertain arm call ' + key)
                directory = arm/'calls'/key
                result = read(directory/'result.json')
                row = {name:ref(directory/(name+'.json')) for name in ('request','schema','result')}
                row['dispatch'] = ref(arm/'calls/dispatch.json')
                if result['status'] == 'VALIDATED':
                    row['mode'] = 'VALIDATED'
                elif result['status'] == 'FAILED' and result.get('error') in ('E_RESOURCE_LIMIT','E_DEPENDENCY'):
                    # Only the reviewed changed-capacity/service continuation
                    # can retry these. Semantic failures remain exact failures.
                    retry.append(dict(key=key, result=row['result'], reason=result.get('reason')))
                    continue
                else:
                    row['mode'] = 'RETAINED_FAILURE'
                retained[key] = row
            native = []
            for path in sorted((arm/'native').rglob('product-binding.json')):
                previous = read(path)
                require(previous['status'] != 'RESERVED', 'Uncertain native action ' + str(path))
                if previous['status'] == 'COMPLETED':
                    native.append(dict(kind=previous['binding']['kind'], binding=ref(path),
                        result=ref(path.with_name('product-result.json'))))
            save(WORK/'checkpoints/arms'/question/(arm.name+'.json'), dict(common,
                calls=retained, native=native, reviewed_missing_calls=retry))


def adopt():
    manifest = checked_manifest()
    if (WORK/'adoption.json').exists():
        require(read(WORK/'adoption.json')['status'] == 'APPLIED', 'Partial adoption requires review')
        require(read(WORK/'adoption.json')['manifest'] == ref(WORK/'deployment-manifest.json'), 'Changed adopted manifest')
        require(all(ref(ROOT/r['target'])['sha256'] == r['replacement']['sha256'] for r in manifest['writes']),
            'Adopted implementation changed')
        return dict(adopted=True, reused=True)
    require(settled(manifest), 'Predecessor is still running')
    with ExitStack() as stack:
        # The exact supervisor lock location is read from the current route.
        sys.path[:0] = [str(ROOT), str(ROOT/'src')]
        from scripts.legal_integration_phased_live import LIVE
        for path in (OLD/'execution/worker.lock', ROOT/LIVE/'supervisor.lock',
                BASE/'execution-state.run.lock', MISSION.with_name('mission.execution.lock'), BASE/'execution-state.lock'):
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(settled(manifest), 'Predecessor changed while taking locks')
        for row in manifest['writes']:
            path = ROOT/row['target']
            require((ref(path) if path.exists() else None) == row['before'], 'Production file changed: ' + row['target'])
        archives = []
        paths = {PROGRAM, BASE/'execution-state.json', MISSION, BASE/'current-binding.json',
                 BASE/'live-calls.json', BASE/'live-grant.json', PLAN}
        paths |= {ROOT/r['target'] for r in manifest['writes'] if r['before'] is not None}
        for source in sorted(paths):
            destination = WORK/'before'/source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source,destination)
            archives.append(dict(previous=ref(source), archive=ref(destination)))
        save(WORK/'baseline.json', dict(profile='common-capacity-predecessor.v1',
            at_utc=datetime.now(timezone.utc).isoformat(), prior_detours=59, running_owners=0,
            calls=len(read(BASE/'live-calls.json')['calls']), archived=archives,
            predecessor_result=ref(OLD/'execution/result.json')))
        checkpoints()
        save(WORK/'adoption.json', dict(status='PREPARED', manifest=ref(WORK/'deployment-manifest.json')))
        for row in manifest['writes']:
            target, source = ROOT/row['target'], ROOT/row['replacement']['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name+'.capacity-installing')
            temporary.write_bytes(source.read_bytes())
            temporary.replace(target)
        require(all(ref(ROOT/r['target'])['sha256'] == r['replacement']['sha256'] for r in manifest['writes']),
            'Adoption verification failed')
        save(WORK/'adoption.json', dict(status='APPLIED', manifest=ref(WORK/'deployment-manifest.json'),
            at_utc=datetime.now(timezone.utc).isoformat()))
    return dict(adopted=True, new_live_calls=0)


def command(label, argv):
    folder = WORK/'continuation'
    folder.mkdir(exist_ok=True)
    result_path = folder/(label+'.json')
    if result_path.exists():
        result = read(result_path)
        require(result['command'] == argv, 'Continuation command changed')
        verify(result['stdout']); verify(result['stderr'])
        return result
    state_path = WORK/'continuation-state.json'
    if state_path.exists():
        previous = read(state_path)
        require(previous.get('stage') != label or previous.get('process') is None,
            'Interrupted or active continuation command must be reconciled before redispatch: ' + label)
    started = datetime.now(timezone.utc).isoformat()
    with (folder/(label+'.stdout')).open('w') as out, (folder/(label+'.stderr')).open('w') as err:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err)
        save(WORK/'continuation-state.json', dict(stage=label, command=argv, process=identity(child.pid), started_at_utc=started))
        code = child.wait()
    result = dict(command=argv, exit_code=code, started_at_utc=started, ended_at_utc=datetime.now(timezone.utc).isoformat(),
        stdout=ref(folder/(label+'.stdout')), stderr=ref(folder/(label+'.stderr')))
    save(result_path, result)
    return result


def worker():
    with (WORK/'continuation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = dict(status='RUNNING', commands=[], integration_complete=False)
        try:
            manifest = checked_manifest()
            if not (WORK/'adoption.json').exists():
                while not settled(manifest):
                    save(WORK/'continuation-state.json', dict(stage='WAITING_FOR_PREDECESSOR',
                        worker=manifest['predecessor_worker'], observed_at_utc=datetime.now(timezone.utc).isoformat(),
                        live_deadline_utc=DEADLINE.isoformat()))
                    time.sleep(30)
            adopt()
            for label, argv in (
                ('register', ['.venv-context/bin/python','scripts/legal_integration_master.py','gap-refresh']),
                ('refresh', ['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                ('verify', ['.venv-context/bin/python','scripts/legal_integration_master.py','verify'])):
                row = command(label, argv); result['commands'].append(row)
                require(row['exit_code'] == 0, label + ' refused; retained stderr identifies the prerequisite')
            if datetime.now(timezone.utc) < DEADLINE:
                result['commands'].append(command('live', ['.venv-context/bin/python','scripts/legal_integration_master.py','live']))
            else:
                result['live_dispatch'] = 'BLOCKED_EXISTING_DEADLINE_EXPIRED'
            for label, argv in (
                ('ready', ['.venv-context/bin/python','scripts/legal_integration_master.py','run']),
                ('final-refresh', ['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                ('final-verify', ['.venv-context/bin/python','scripts/legal_integration_master.py','verify'])):
                result['commands'].append(command(label, argv))
            result['status'] = ('CHECKPOINT' if all(r['exit_code'] == 0 for r in result['commands'])
                else 'BLOCKED')
            if result['status'] == 'BLOCKED':
                result['reason'] = 'One or more commands failed; exact stdout/stderr retained; independent local work completed'
        except Exception as exc:
            result.update(status='BLOCKED', reason=str(exc))
        result['ended_at_utc'] = datetime.now(timezone.utc).isoformat()
        save(WORK/'continuation-result.json', result)
        save(WORK/'continuation-state.json', dict(stage=result['status'], reason=result.get('reason'),
            result=ref(WORK/'continuation-result.json')))
        return result


def arm():
    checked_manifest()
    with (WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (WORK/'armed.json').exists():
            previous = read(WORK/'armed.json')
            require(previous['manifest'] == ref(WORK/'deployment-manifest.json'), 'Changed armed manifest')
            if alive(previous['process']):
                return dict(previous, already_running=True)
            require(not (WORK/'continuation-result.json').exists(), 'Continuation already settled; review its result')
            state = read(WORK/'continuation-state.json') if (WORK/'continuation-state.json').exists() else {}
            require(not alive(state.get('process')), 'Continuation child is still active')
            save(WORK/('interrupted-'+str(previous['process']['pid'])+'.json'),previous)
        with (WORK/'continuation.log').open('ab') as log:
            child = subprocess.Popen(['.venv-context/bin/python','scripts/legal_common_capacity_deploy.py','_worker'],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        value = dict(process=identity(child.pid), manifest=ref(WORK/'deployment-manifest.json'),
            started_at_utc=datetime.now(timezone.utc).isoformat())
        save(WORK/'armed.json', value)
        return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status','adopt','arm','_worker'])
    args = parser.parse_args()
    print(json.dumps({'status':status,'adopt':adopt,'arm':arm,'_worker':worker}[args.action](), indent=2))
