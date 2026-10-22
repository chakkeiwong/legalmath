"""The source-batching correction cannot erase attempts or unrelated vetoes."""
from copy import deepcopy

import pytest
from scripts import legal_retained_acquisition_repair as repair
from scripts.legal_mission_execution import save, ref, Refused


def setup(root):
    old = dict(tasks=[dict(id=name, maximum_attempts=2, inputs=[], deliverable='prior')
        for name in ('baseline-gatecoin', 'acquire-p14', 'baseline-p10', 'corpus-qualification')],
        protected_evidence=[], deadline_utc='2026-10-24T02:19:15+00:00', global_call_ceiling=8100)
    defect = dict(code='E_INTEGRITY', reason=repair.REASON, scope=['baseline-gatecoin','baseline-p10'])
    unrelated = dict(code='E_INTEGRITY', reason='Independent evidence failure', scope=['corpus-qualification'])
    before = dict(tasks={t['id']: dict(status='FAILED', attempts=[{'number':1},{'number':2}]) for t in old['tasks']},
        events=[{'action':'retained'}], continuation_vetoes=[defect, unrelated],
        resolved_continuation_vetoes=[{'veto':'older'}])
    before['tasks']['acquire-p14']['status'] = 'SUCCEEDED'
    before['tasks']['baseline-p10'] = dict(status='PENDING', attempts=[])
    save(root/'before.json', before)
    save(root/repair.PLAN, {'plan':'local test'})
    revision = dict(prior_state=ref(root,'before.json'), implementation={}, review={'review':'exact'},
        result={'result':'exact'}, baseline={}, resolved_vetoes=[defect])
    program = repair.expected_program(old, revision, root, plan_reference={})
    return old, before, program


def test_single_failed_owner_retry_preserves_history_and_independent_work(tmp_path):
    old, before, program = setup(tmp_path)
    after = repair.project_state(before, program, 'now')
    repair.validate_state_history(program, after, tmp_path)
    assert next(t for t in program['tasks'] if t['id'] == 'baseline-gatecoin')['maximum_attempts'] == 3
    assert after['tasks']['baseline-gatecoin']['status'] == 'PENDING'
    assert all(after['tasks'][tid]['attempts'] == row['attempts'] for tid, row in before['tasks'].items())
    for tid in ('acquire-p14','baseline-p10','corpus-qualification'):
        assert after['tasks'][tid] == before['tasks'][tid]
    assert after['continuation_vetoes'] == [before['continuation_vetoes'][1]]
    assert program['global_call_ceiling'] == old['global_call_ceiling']
    assert program['deadline_utc'] == old['deadline_utc']


@pytest.mark.parametrize('mutation', ['running','attempt','success','veto','resolution','event'])
def test_lost_history_or_active_worker_refused(tmp_path, mutation):
    old, before, program = setup(tmp_path)
    if mutation == 'running':
        before['tasks']['baseline-p10']['status'] = 'RUNNING'
        with pytest.raises(Refused):
            repair.project_state(before, program, 'now')
        return
    after = repair.project_state(before, program, 'now')
    if mutation == 'attempt': after['tasks']['baseline-gatecoin']['attempts'].pop()
    elif mutation == 'success': after['tasks']['acquire-p14']['status'] = 'PENDING'
    elif mutation == 'veto': after['continuation_vetoes'].clear()
    elif mutation == 'resolution': after['resolved_continuation_vetoes'].pop()
    else: after['events'][0]['action'] = 'changed'
    with pytest.raises(Refused):
        repair.validate_state_history(program, after, tmp_path)


def test_five_minute_authority_uses_sealed_predecessor_not_changed_live_bytes(tmp_path):
    from scripts.legal_mission_execution import historical_evidence, verify
    for name in ('program.json','binding.json'):
        save(tmp_path/name, {'original':True})
        before = ref(tmp_path, name)
        save(tmp_path/('old-'+name), {'original':True})
        archive = ref(tmp_path, 'old-'+name)
        save(tmp_path/name, {'reviewed_successor':True})
        current = ref(tmp_path, name)
        with historical_evidence(tmp_path, {(name,before['sha256']):archive}):
            verify(tmp_path, before)
            verify(tmp_path, current)
        save(tmp_path/name, {'unreviewed':True})
        with historical_evidence(tmp_path, {(name,before['sha256']):archive}):
            with pytest.raises(Refused): verify(tmp_path, current)
