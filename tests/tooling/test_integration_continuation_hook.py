"""Continuation behavior with real processes, locks and the production DAG engine.

The isolated master's provider is a local fixture: these tests make no external
calls and do not claim legal or model quality.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import pytest

from scripts import legal_integration_continuation as hook
from scripts.legal_mission_execution import Execution, Refused, read, ref, save


MASTER_FIXTURE = '''
from pathlib import Path
import json, os, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.legal_mission_execution import Execution,read,save,ref
from scripts.legal_integration_continuation import PROGRAM,STATE
class MasterExecution(Execution):
    def sync_mission(self): pass
def result(tid,output):
    evidence=ROOT/(tid+'-evidence.txt');evidence.write_text('actual local fixture result')
    save(output,{'task_id':tid,'status':'FAILED' if tid.startswith('fail-') else 'SUCCEEDED',
        'conclusion':'Retained fixture outcome','next_action':'Continue independent work',
        'evidence':[ref(ROOT,evidence)]})
if __name__=='__main__':
    action=sys.argv[1]
    with (ROOT/'actions.jsonl').open('a') as out: out.write(json.dumps({'action':action,'pid':os.getpid()})+'\\n')
    if action=='worker':result(sys.argv[2],Path(sys.argv[3]));sys.exit(0)
    if action=='verify':sys.exit(0)
    execution=MasterExecution(ROOT,PROGRAM,STATE)
    if action=='run':execution.run()
    elif action=='live':
        while (ROOT/'hold-live').exists():time.sleep(.01)
        if (ROOT/'fail-live').exists():sys.exit(7)
        for tid in execution.summary()['ready']:
            if execution.tasks[tid]['executor']!='agent':continue
            execution.start(tid);output=ROOT/(tid+'-result.json');result(tid,output);execution.finish(tid,output)
'''

CONTROL_FIXTURE = '''
from pathlib import Path
import json,os,sys
def validate(mission,tools,root):
    assert mission['current_task']=='product-contribution'
    assert len({r['id'] for r in mission['history']})==len(mission['history'])
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    with (root/'actions.jsonl').open('a') as out:out.write(json.dumps({'action':sys.argv[1],'pid':os.getpid()})+'\\n')
    if (root/('fail-gate-'+sys.argv[1])).exists():sys.exit(2)
    print('{}')
'''


def task(name, *, agent=False, requires=(), after=()):
    return {'id': name, 'executor': 'agent' if agent else 'command', 'kind': 'source_analysis',
            'requires': list(requires), 'after': list(after), 'maximum_attempts': 1,
            'write_resources': [name], 'priority': 1, 'inputs': [], 'question_ids': ['p10'],
            'acceptance': 'Retained result', 'deliverable': 'Retained result',
            **({} if agent else {'command': ['.venv/bin/python',
                 'scripts/legal_integration_master.py', 'worker', name, '{result}'], 'timeout_seconds': 10})}


def fixture_root(tmp_path, tasks=None):
    root = tmp_path
    (root / 'scripts').mkdir()
    for name in ('legal_integration_continuation.py', 'legal_mission_execution.py'):
        shutil.copyfile(hook.ROOT / 'scripts' / name, root / 'scripts' / name)
    # Exercise the public detached entrypoint with only its polling interval
    # shortened; command selection, process/lock ownership and receipts are real.
    copied_hook = root / hook.SCRIPT
    copied_hook.write_text(copied_hook.read_text().replace('POLL_SECONDS = 15\n', 'POLL_SECONDS = 0.02\n'))
    (root / 'scripts/legal_integration_master.py').write_text(MASTER_FIXTURE)
    (root / 'scripts/legal_mission_control.py').write_text(CONTROL_FIXTURE)
    for env in ('.venv', '.venv-context'):
        (root / env / 'bin').mkdir(parents=True)
        (root / env / 'bin/python').symlink_to(sys.executable)
    tasks = tasks if tasks is not None else [task('baseline-p10', agent=True)]
    deadline = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save(root / hook.PROGRAM, {'profile': 'legal-mission-execution.v1', 'workers': 2,
         'deadline_utc': deadline, 'protected_evidence': [], 'artifact_directory': 'results', 'tasks': tasks})
    execution = Execution(root, hook.PROGRAM, hook.STATE)
    with execution.locked() as state:
        save(root / hook.STATE, state)
    save(root / hook.BASE / 'live-grant.json', {'approved': True, 'deadline_utc': deadline, 'maximum_calls': 10})
    save(root / hook.BASE / 'live-calls.json', {'calls': []})
    save(root / hook.MISSION, {'current_task': 'product-contribution', 'history': []})
    save(root / 'docs/implementation/legal-mission-control/tools.json', {})
    save(root / hook.WORK / 'registration.json', {
        'profile': 'integration-continuation-hook.v1', 'commands': hook.COMMANDS,
        'pid_namespace': hook.pid_namespace(),
        'protected': [ref(root, hook.PROGRAM), ref(root, hook.SCRIPT), ref(root, hook.BASE/'live-grant.json')],
        'predecessor_processes': [], 'writer_locks': [], 'maximum_drains': 20,
        'attempts_reset': False, 'calls_added': 0, 'deadline_extended': False})
    return root


def wait_for(predicate, timeout=10):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(.01)
    raise AssertionError('Timed out waiting for isolated test process')


def journal(root):
    path = root / hook.WORK / 'journal.json'
    return read(path) if path.exists() else {}


def spawn(root, code=None):
    code = code or 'from scripts.legal_integration_continuation import Hook; Hook(poll=.02).watch()'
    return subprocess.Popen([sys.executable, '-c', code], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def completed(process):
    out, err = process.communicate(timeout=20)
    assert process.returncode == 0, (out, err)


def actions(root, name):
    path = root / 'actions.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines() if json.loads(line)['action'] == name] if path.exists() else []


def test_failure_drains_independent_original_nodes_and_completion_review(tmp_path):
    root = fixture_root(tmp_path, [task('fail-p10'), task('native-p14'),
        task('blocked-p10', agent=True, requires=['fail-p10']),
        task('baseline-p14', agent=True, requires=['native-p14']),
        task('continuation-review', after=['blocked-p10', 'baseline-p14'])])
    # A failed predecessor's receipt is a completion dependency, not a veto.
    save(root / hook.PREDECESSOR / 'worker-result.json', {'live_exit_code': 7, 'preflight_passed': True})
    completed(spawn(root))
    state = read(root / hook.STATE)
    assert state['tasks']['fail-p10']['status'] == 'FAILED'
    assert state['tasks']['native-p14']['status'] == 'SUCCEEDED'
    assert state['tasks']['baseline-p14']['status'] == 'SUCCEEDED'
    assert state['tasks']['continuation-review']['status'] == 'SUCCEEDED'
    assert not state['tasks']['blocked-p10']['attempts']
    result = read(root / hook.WORK / 'result.json')
    assert result['status'] == 'BLOCKED' and not result['integration_complete']
    assert result['predecessor_result'] == ref(root, hook.PREDECESSOR/'worker-result.json')
    assert len(actions(root, 'live')) == 1 and len(actions(root, 'run')) == 2
    assert len(actions(root, 'refresh')) == 4


def test_predecessor_lock_blocks_dispatch_until_release_without_success_requirement(tmp_path):
    root = fixture_root(tmp_path)
    manifest_path = root / hook.WORK / 'registration.json'
    manifest = read(manifest_path); manifest['writer_locks'] = ['old-writer.lock']; save(manifest_path, manifest)
    with hook.locked(root/'old-writer.lock'):
        process = spawn(root)
        try:
            wait_for(lambda: journal(root).get('status') == 'WAITING_PREDECESSOR')
            assert not actions(root, 'live') and not actions(root, 'refresh')
        except BaseException:
            process.kill(); process.communicate(); raise
    completed(process)
    assert len(actions(root, 'live')) == 1


def test_restart_adopts_running_step_without_duplicate_dispatch(tmp_path):
    root = fixture_root(tmp_path)
    (root/'hold-live').touch()
    first = spawn(root)
    try:
        wait_for(lambda: actions(root, 'live'))
        first.kill(); first.communicate()
        second = spawn(root)
        try:
            wait_for(lambda: journal(root).get('process', {}).get('pid') == second.pid)
            assert len(actions(root, 'live')) == 1
            (root/'hold-live').unlink()
            completed(second)
        finally:
            if second.poll() is None:second.kill();second.communicate()
        assert len(actions(root, 'live')) == 1
        assert read(root/hook.STATE)['tasks']['baseline-p10']['status'] == 'SUCCEEDED'
    finally:
        if (root/'hold-live').exists():(root/'hold-live').unlink()
        if first.poll() is None:first.kill();first.communicate()


def test_restart_between_receipt_and_cursor_commit_does_not_relaunch(tmp_path):
    root = fixture_root(tmp_path)
    crash = '''
import os
from scripts.legal_integration_continuation import Hook
original=Hook.publish
def publish(self,j,status,**fields):
    original(self,j,status,**fields)
    if status=='ACTION_SETTLED' and j['steps'][j['active_step']]['action']=='live':os._exit(91)
Hook.publish=publish
Hook(poll=.02).watch()
'''
    first = spawn(root, crash)
    first.communicate(timeout=15)
    assert first.returncode == 91
    saved = journal(root)
    assert 'active_step' in saved and saved['steps'][saved['active_step']]['result']['exit_code'] == 0
    completed(spawn(root))
    assert len(actions(root, 'live')) == 1
    assert len(actions(root, 'refresh')) == 2


def test_failed_runner_refreshes_and_does_not_spin_on_unchanged_frontier(tmp_path):
    root = fixture_root(tmp_path)
    (root/'fail-live').touch()
    completed(spawn(root))
    assert len(actions(root, 'live')) == 1
    assert len(actions(root, 'refresh')) == 2
    result = read(root/hook.WORK/'result.json')
    assert 'unchanged frontier' in result['additional_blockers']['baseline-p10']
    assert not read(root/hook.STATE)['tasks']['baseline-p10']['attempts']


def test_changed_binding_or_common_gate_failure_prevents_all_dispatch(tmp_path):
    root = fixture_root(tmp_path)
    (root/'fail-gate-admit').touch()
    completed(spawn(root))
    assert not actions(root, 'live')
    assert read(root/hook.WORK/'result.json')['additional_blockers']['gates'][0]['action'] == 'admit'
    (root/hook.PROGRAM).write_text('{}')
    with pytest.raises(Refused, match='Changed evidence'):
        hook.Hook(root).manifest()


def test_pid_reuse_and_unreadable_identity_are_not_mistaken_for_live_or_dead(monkeypatch):
    actual = hook.identity(os.getpid())
    assert hook.alive(actual)
    assert not hook.alive({'pid': os.getpid(), 'start': str(int(actual['start']) + 1)})
    def denied(*args, **kwargs):raise PermissionError('test restriction')
    monkeypatch.setattr(Path, 'read_text', denied)
    with pytest.raises(Refused, match='Uncertain process identity'):
        hook.alive(actual)


def test_wrong_pid_namespace_cannot_arm_or_mistake_hidden_workers_for_dead(tmp_path):
    root = fixture_root(tmp_path)
    manifest = read(root/hook.WORK/'registration.json')
    manifest['pid_namespace'] = 'pid:[0]'
    save(root/hook.WORK/'registration.json', manifest)
    result = subprocess.run([sys.executable, str(hook.SCRIPT), 'arm'], cwd=root,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode != 0 and 'Different PID namespace' in result.stderr
    assert not (root/hook.WORK/'journal.json').exists()
    observed = public(root, 'status')
    assert observed['alive'] is None and 'different PID namespace' in observed['process_visibility']
    assert not actions(root, 'live')


def test_expired_or_exhausted_live_does_not_block_local_ready_work():
    view = {'tasks': {'native-p14': {'status':'READY','attempts_used':0,'maximum_attempts':1,'executor':'command'},
                     'baseline-p10': {'status':'READY','attempts_used':0,'maximum_attempts':1,'executor':'agent'},
                     'acquire-evidence': {'status':'READY','attempts_used':7,'maximum_attempts':7,'executor':'agent'}}}
    grant = {'approved':True,'deadline_utc':'2000-01-01T00:00:00+00:00','maximum_calls':10}
    action,key,_ = hook.selection(view,grant,0,[])
    assert action == 'run'
    action,_,blocked = hook.selection(view,grant,0,[['run',key]])
    assert action is None and 'expired' in blocked['baseline-p10'] and 'exhausted' in blocked['acquire-evidence']
    grant['deadline_utc']='2100-01-01T00:00:00+00:00'
    assert 'call ceiling' in hook.selection(view,grant,10,[['run',key]])[2]['baseline-p10']


def test_unknown_external_outcome_still_allows_local_retention_and_never_replays(tmp_path):
    root = fixture_root(tmp_path)
    instance = hook.Hook(root, poll=.01)
    saved = instance.journal()
    folder = root/hook.WORK/'steps/0000-live'
    save(folder/'intent.json', {'action':'live','command':hook.COMMANDS['live'],
        'at_utc':'2000-01-01T00:00:00+00:00','registration':ref(root,instance.manifest_path),'index':0})
    row = {'path':str(folder.relative_to(root)),'action':'live'}
    result = instance.step_outcome(row)
    assert result['unknown_outcome'] and not actions(root,'live')
    view = {'tasks': {'native-p14': {'status':'READY','attempts_used':0,'maximum_attempts':1,'executor':'command'},
                     'baseline-p10': {'status':'READY','attempts_used':0,'maximum_attempts':1,'executor':'agent'}}}
    grant = read(root/hook.BASE/'live-grant.json')
    action,key,_ = hook.selection(view,grant,0,[],external_uncertain=True)
    assert action == 'run'
    assert 'reconciliation' in hook.selection(view,grant,0,[['run',key]],external_uncertain=True)[2]['baseline-p10']


def test_single_watcher_and_receipt_writer_are_exclusive(tmp_path):
    root = fixture_root(tmp_path)
    instance = hook.Hook(root)
    with hook.locked(instance.directory/'watch.lock'):
        with pytest.raises(BlockingIOError):instance.watch()
    with hook.locked(instance.directory/'action.lock'):
        assert hook.lock_busy(instance.directory/'action.lock')


def test_inherited_action_lock_survives_receipt_writer_death(tmp_path):
    root = fixture_root(tmp_path)
    (root/'hold-live').touch()
    watcher = spawn(root)
    writer = command = None
    try:
        wait_for(lambda: actions(root,'live'))
        saved = journal(root); row = saved['steps'][saved['active_step']]
        folder = root/row['path']
        writer = read(folder/'worker.json')['process']
        command = read(folder/'command.json')['process']
        os.kill(writer['pid'],signal.SIGKILL)
        wait_for(lambda: not hook.alive(writer))
        assert hook.alive(command) and hook.lock_busy(root/hook.WORK/'action.lock')
        assert hook.Hook(root).step_outcome(row) is None
        assert len(actions(root,'live')) == 1
    finally:
        if (root/'hold-live').exists():(root/'hold-live').unlink()
        if watcher.poll() is None:watcher.kill()
        watcher.communicate()
        if command and hook.alive(command):
            wait_for(lambda: not hook.alive(command))


def public(root, action):
    result = subprocess.run([sys.executable, str(hook.SCRIPT), action], cwd=root,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_public_arm_is_detached_idempotent_and_records_installation(tmp_path):
    root = fixture_root(tmp_path)
    manifest = read(root/hook.WORK/'registration.json')
    manifest['writer_locks'] = ['predecessor.lock']
    save(root/hook.WORK/'registration.json', manifest)
    # Installation retains the actual reviewed receipt; no provider fixture.
    save(root/hook.REVIEW, {'verdict': 'PASS', 'provider_calls': 0})
    with hook.locked(root/'predecessor.lock'):
        armed = public(root, 'arm')
        pid = armed['process']['pid']
        try:
            assert armed['alive'] and armed['status'] == 'WAITING_PREDECESSOR'
            assert os.getsid(pid) == pid
            assert public(root, 'arm')['process'] == armed['process']
            assert public(root, 'record')['recorded']
            assert len(read(root/hook.MISSION)['history']) == 1
        except BaseException:
            os.kill(pid, signal.SIGKILL)
            raise
    wait_for(lambda: (root/hook.WORK/'finalization.json').exists())
    wait_for(lambda: not hook.alive(armed['process']))
    assert public(root, 'arm')['status'] == 'SETTLED'
    assert len(actions(root, 'live')) == 1
    assert len(read(root/hook.MISSION)['history']) == 2


def test_finalization_failure_is_retained_and_restart_never_redispatches(tmp_path):
    root = fixture_root(tmp_path)
    (root/'fail-gate-refresh').touch()
    # Common gate failure yields a terminal blocker, then final refresh fails.
    first = subprocess.run([sys.executable, str(hook.SCRIPT), 'watch'], cwd=root,
                           capture_output=True, text=True, timeout=15)
    assert first.returncode != 0
    assert journal(root)['status'] == 'ERROR'
    assert (root/hook.WORK/'result.json').exists()
    assert list((root/hook.WORK).glob('error-*.json'))
    assert not (root/hook.WORK/'finalization.json').exists()
    assert len(read(root/hook.MISSION)['history']) == 1
    (root/'fail-gate-refresh').unlink()
    public(root, 'arm')
    wait_for(lambda: (root/hook.WORK/'finalization.json').exists())
    assert journal(root)['status'] == 'BLOCKED'
    assert not actions(root, 'live')
    assert len(read(root/hook.MISSION)['history']) == 1
    assert len(actions(root, 'refresh')) == 3
