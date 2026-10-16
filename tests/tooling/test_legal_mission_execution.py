"""Behavioral graph tests: failed branches cannot end independent execution."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import threading

import pytest

from scripts.legal_mission_execution import Execution, Refused, digest, ref, save, validate_program


def task(tid, **kwargs):
    return {'id': tid, 'executor': 'agent', 'kind': 'source_analysis',
        'requires': [], 'after': [], 'any_success': [], 'inputs': [],
        'maximum_attempts': 2, 'write_resources': [tid], 'priority': 1,
        'question_ids': ['p10'], 'acceptance': 'Retained substantive result',
        'deliverable': 'An evidence-backed result', **kwargs}


def setup(tmp_path, tasks):
    value = {'profile': 'legal-mission-execution.v1', 'workers': 2,
        'deadline_utc': '2100-01-01T00:00:00+00:00', 'protected_evidence': [],
        'artifact_directory': 'artifacts', 'tasks': tasks}
    save(tmp_path/'program.json', value)
    return Execution(tmp_path, 'program.json', 'state.json')


def finish(execution, tid, status='SUCCEEDED'):
    path = execution.root/(tid+'-evidence.txt')
    path.write_text('Retained result for '+tid)
    output = execution.root/(tid+'-result.json')
    save(output, {'task_id': tid, 'status': status, 'conclusion': 'Actual result '+status,
        'next_action': 'Continue ready work', 'evidence': [ref(execution.root, path)]})
    execution.finish(tid, output)


def test_failure_blocks_only_descendants_and_final_review_can_still_run(tmp_path):
    execution=setup(tmp_path,[task('a'),task('b'),task('a-child',requires=['a']),
        task('b-child',requires=['b']),task('review',after=['a-child','b-child'])])
    execution.start('a');finish(execution,'a','FAILED')
    assert execution.summary()['ready']==['b']
    execution.start('b');finish(execution,'b')
    assert execution.summary()['ready']==['b-child']
    execution.start('b-child');finish(execution,'b-child')
    execution.start('review');finish(execution,'review')
    state=execution.summary()
    assert state['execution']=='BLOCKED' and not state['ready']
    assert set(state['blocked'])=={'a','a-child'}


def test_recovery_unlocks_dependant_without_erasing_failure(tmp_path):
    execution=setup(tmp_path,[task('first'),task('repair',when_failed='first'),
        task('answer',any_success=[['first','repair']])])
    execution.start('first');finish(execution,'first','FAILED')
    assert execution.summary()['ready']==['repair']
    execution.start('repair');finish(execution,'repair')
    execution.start('answer');finish(execution,'answer')
    assert execution.summary()['tasks']['first']['status']=='FAILED'
    assert execution.summary()['tasks']['answer']['status']=='SUCCEEDED'
    assert execution.summary()['execution']=='COMPLETE'
    assert execution.summary()['recovered']=={'first':'repair'}


def test_unused_recovery_is_inactive_and_empty_command_queue_keeps_agent_work(tmp_path):
    execution=setup(tmp_path,[task('a'),task('repair',when_failed='a'),task('b',requires=['a'])])
    assert execution.run()['execution']=='WORK_REMAINS'
    execution.start('a');finish(execution,'a')
    assert execution.summary()['tasks']['repair']['status']=='INACTIVE'
    assert execution.run()['ready']==['b']


def test_restart_never_reexecutes_success_or_resets_interrupted_attempts(tmp_path):
    execution=setup(tmp_path,[task('a'),task('b',requires=['a'])])
    execution.start('a');finish(execution,'a')
    execution=Execution(tmp_path,'program.json','state.json')
    assert execution.summary()['ready']==['b']
    with pytest.raises(Refused):execution.start('a')
    execution.start('b');execution.interrupt('b','Worker was interrupted; output inspected')
    execution=Execution(tmp_path,'program.json','state.json')
    execution.retry('b','Repair identified and source corrected')
    assert execution.start('b')==2
    finish(execution,'b','FAILED')
    with pytest.raises(Refused,match='ceiling'):execution.retry('b','More')


def test_stale_input_is_branch_blocker_and_stale_result_invalidates_children(tmp_path):
    source=tmp_path/'source.txt';source.write_text('old')
    execution=setup(tmp_path,[task('a',inputs=[ref(tmp_path,source)]),task('b'),task('child',requires=['a'])])
    execution.start('a');finish(execution,'a')
    execution.start('child');finish(execution,'child')
    source.write_text('changed')
    view=execution.summary()
    assert view['tasks']['a']['status']==view['tasks']['child']['status']=='INVALID'
    assert view['ready']==['b']


def test_global_evidence_and_cycle_fail_before_dispatch(tmp_path):
    execution=setup(tmp_path,[task('a',requires=['b']),task('b')])
    program=deepcopy(execution.program);program['tasks'][1]['requires']=['a']
    with pytest.raises(Refused,match='Cyclic'):validate_program(program,tmp_path)
    marker=tmp_path/'grant.json';marker.write_text('{}')
    program=deepcopy(execution.program);program['protected_evidence']=[ref(tmp_path,marker)]
    marker.write_text('changed')
    with pytest.raises(Refused,match='Changed evidence'):validate_program(program,tmp_path)


def test_conflicting_writes_and_duplicate_starts_are_refused(tmp_path):
    execution=setup(tmp_path,[task('a',write_resources=['source']),task('b',write_resources=['source']),task('c')])
    execution.start('a')
    with pytest.raises(Refused,match='busy'):execution.start('b')
    with pytest.raises(Refused,match='not ready'):execution.start('a')
    execution.start('c');finish(execution,'c')
    finish(execution,'a')
    execution.start('b')


def test_deadline_prevents_dispatch_but_does_not_delete_results(tmp_path):
    execution=setup(tmp_path,[task('a')])
    execution.program['deadline_utc']='2000-01-01T00:00:00+00:00'
    save(tmp_path/'program.json',execution.program)
    execution=Execution(tmp_path,'program.json','state.json')
    assert execution.summary()['execution']=='DEADLINE_REACHED'
    with pytest.raises(Refused,match='deadline'):execution.start('a')


def test_changed_definition_cannot_reset_state(tmp_path):
    execution=setup(tmp_path,[task('a')]);execution.start('a')
    program=read_json(tmp_path/'program.json');program['tasks'][0]['maximum_attempts']=3
    save(tmp_path/'program.json',program)
    with pytest.raises(Refused,match='migration'):Execution(tmp_path,'program.json','state.json').summary()


def read_json(path):
    return json.loads(path.read_text())


def test_real_command_loop_drains_other_branch_after_failure_and_resumes(tmp_path):
    binary=tmp_path/'.venv/bin/python';binary.parent.mkdir(parents=True);binary.symlink_to(sys.executable)
    worker=tmp_path/'worker.py'
    worker.write_text('''import hashlib,json,pathlib,sys
tid,output,mode=sys.argv[1:]
output=pathlib.Path(output)
if mode=="fail": raise SystemExit(7)
if mode=="empty": raise SystemExit(0)
evidence=output.with_name("evidence.txt");evidence.write_text(tid)
output.write_text(json.dumps({"task_id":tid,"status":"SUCCEEDED","conclusion":"checked "+tid,
"next_action":"Continue ready tasks","evidence":[{"path":str(evidence.relative_to(pathlib.Path.cwd())),
"sha256":hashlib.sha256(evidence.read_bytes()).hexdigest()}]}))
''')
    def command(tid,mode='ok',**kw):
        return task(tid,executor='command',command=['.venv/bin/python','worker.py',tid,'{result}',mode],timeout_seconds=10,**kw)
    execution=setup(tmp_path,[command('broken','fail'),command('independent'),command('child',requires=['independent']),
        command('repair',when_failed='broken'),command('after-repair',any_success=[['broken','repair']]),
        command('empty','empty'),task('reasoning')])
    view=execution.run()
    assert view['tasks']['broken']['status']==view['tasks']['empty']['status']=='FAILED'
    assert all(view['tasks'][t]['status']=='SUCCEEDED' for t in ['independent','child','repair','after-repair'])
    assert view['ready']==['reasoning'] and view['execution']=='WORK_REMAINS'
    before=read_json(tmp_path/'state.json')
    execution.run()
    assert read_json(tmp_path/'state.json')==before


def test_concurrent_claims_have_one_winner(tmp_path):
    execution=setup(tmp_path,[task('a')]);results=[]
    def claim():
        try:results.append(execution.start('a'))
        except Refused:results.append('refused')
    threads=[threading.Thread(target=claim) for _ in range(2)]
    for t in threads:t.start()
    for t in threads:t.join()
    assert sorted(str(x) for x in results)==['1','refused']


def test_changed_completion_outcome_invalidates_report(tmp_path):
    execution=setup(tmp_path,[task('a'),task('child',requires=['a']),task('report',after=['child'])])
    execution.start('a');finish(execution,'a','FAILED')
    execution.start('report');finish(execution,'report')
    execution.retry('a','Review found a repair')
    assert execution.summary()['tasks']['report']['status']=='INVALID'


def test_input_change_while_running_cannot_be_committed_success(tmp_path):
    source=tmp_path/'source.txt';source.write_text('before')
    execution=setup(tmp_path,[task('a',inputs=[ref(tmp_path,source)])])
    execution.start('a');source.write_text('after')
    with pytest.raises(Refused,match='Changed evidence'):finish(execution,'a')
    finish(execution,'a','FAILED')


def test_dead_command_is_interrupted_without_redispatch(tmp_path):
    execution=setup(tmp_path,[task('a',executor='command',command=['.venv/bin/python','worker.py'],timeout_seconds=10),task('b')])
    execution.start('a')
    with execution.locked() as state:
        state['tasks']['a']['attempts'][-1]['supervisor']={'pid':99999999,'start':'0'}
        save(execution.state_path,state)
    execution.run()
    view=execution.summary()
    assert view['tasks']['a']['status']=='INTERRUPTED'
    assert view['ready']==['b']
    assert view['tasks']['a']['attempts_used']==1


def test_worker_setup_exception_does_not_cancel_independent_work(tmp_path):
    execution=setup(tmp_path,[task('a',executor='command',command=['.venv/bin/python','missing.py'],timeout_seconds=10),task('b')])
    (tmp_path/'artifacts/a/attempt-1').mkdir(parents=True)
    view=execution.run()
    assert view['tasks']['a']['status']=='FAILED'
    assert view['ready']==['b']


def test_invalid_running_input_remains_active_and_completion_report_waits(tmp_path):
    source=tmp_path/'source.txt';source.write_text('before')
    execution=setup(tmp_path,[task('a',inputs=[ref(tmp_path,source)]),task('report',after=['a'])])
    execution.start('a');source.write_text('after')
    view=execution.summary()
    assert view['running']==['a'] and view['execution']=='WORK_REMAINS'
    assert view['tasks']['report']['status']=='WAITING'


def test_pending_mission_refresh_prevents_false_completion_and_retries_without_task(tmp_path,monkeypatch):
    execution=setup(tmp_path,[task('a')]);execution.start('a');finish(execution,'a')
    with execution.locked() as state:
        state['mission_sync_error']='temporary refresh failure';save(execution.state_path,state)
    assert execution.summary()['execution']=='WORK_REMAINS'
    calls=[]
    def sync():
        calls.append('sync')
        with execution.locked() as state:
            del state['mission_sync_error'];save(execution.state_path,state)
    monkeypatch.setattr(execution,'sync_mission',sync)
    assert execution.run()['execution']=='COMPLETE'
    assert calls==['sync'] and execution.summary()['tasks']['a']['attempts_used']==1


def test_valid_completed_orphan_is_adopted_without_repeat(tmp_path):
    execution=setup(tmp_path,[task('a',executor='command',command=['.venv/bin/python','missing.py'],timeout_seconds=10)])
    execution.start('a')
    folder=tmp_path/'artifacts/a/attempt-1';folder.mkdir(parents=True)
    evidence=folder/'evidence.txt';evidence.write_text('Actual retained result')
    save(folder/'result.json',{'task_id':'a','status':'SUCCEEDED','conclusion':'Worker finished',
        'next_action':'Continue','evidence':[ref(tmp_path,evidence)]})
    with execution.locked() as state:
        state['tasks']['a']['attempts'][-1]['supervisor']={'pid':99999999,'start':'0'}
        save(execution.state_path,state)
    assert execution.run()['execution']=='COMPLETE'
    assert execution.summary()['tasks']['a']['attempts_used']==1


def test_live_orphan_not_interrupted_or_redispatched(tmp_path):
    from scripts.legal_mission_execution import process_identity
    import os
    execution=setup(tmp_path,[task('a',executor='command',command=['.venv/bin/python','missing.py'],timeout_seconds=10)])
    execution.start('a')
    with execution.locked() as state:
        attempt=state['tasks']['a']['attempts'][-1]
        attempt['supervisor']={'pid':99999999,'start':'0'};attempt['worker']=process_identity(os.getpid())
        save(execution.state_path,state)
    assert execution.run()['running']==['a']


def test_unexpected_worker_exception_cannot_cancel_independent_future(tmp_path,monkeypatch):
    execution=setup(tmp_path,[task(t,executor='command',command=['.venv/bin/python','missing.py'],timeout_seconds=10) for t in ('a','b')])
    def command(tid,attempt):
        if tid=='a':raise RuntimeError('Unexpected setup failure')
        finish(execution,tid)
    monkeypatch.setattr(execution,'command',command)
    view=execution.run()
    assert view['tasks']['a']['status']=='INTERRUPTED'
    assert view['tasks']['b']['status']=='SUCCEEDED'
