"""A local maintenance package cannot renew provider or owner allowances."""
from copy import deepcopy
import pytest
from scripts import legal_integration_repair_execution as repair
from scripts.legal_mission_execution import ref, save, digest, Refused


def fixture(root, monkeypatch):
    old = {'tasks': [{'id': 'acquire-p14', 'maximum_attempts': 10}],
           'deadline_utc': 'retained', 'global_call_ceiling': 8100, 'protected_evidence': [],
           repair.KEY: {'repair_ids': ['R' + str(i) for i in range(1, 11)],
                        'cumulative_additional_attempts': 19}}
    before = {'program_hash': digest(old), 'tasks': {'acquire-p14': {'status': 'FAILED', 'attempts': []}}}
    paths = {str(repair.PROGRAM): old, str(repair.STATE): before,
             str(repair.BASE / 'current-binding.json'): {'scope': 'old'},
             str(repair.BASE / 'live-calls.json'): {'calls': ['retained']}}
    held, rows = {}, []
    for name, value in paths.items():
        path = root / 'before' / name
        save(path, value)
        held[name] = ref(root, path)
        rows.append({'previous': {'path': name, 'sha256': held[name]['sha256']}, 'archive': held[name]})
    baseline = {'prior_detours': 50, 'calls': 2359, 'running_owners': 0,
                'reserved_dispatches': 0, 'archived': rows}
    save(root / 'baseline.json', baseline)
    save(root / 'result.json', dict(verdict='PASS', provider_calls=0, ledger_unchanged=True,
                                    legal_acceptance=False, evidence=[]))
    save(root / 'review.json', {'reviewed': True})
    implementation = {}
    for name in repair.LOCAL_MUTATED:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Reviewed local implementation or plan.')
        if name != str(repair.PLAN):
            implementation[name] = ref(root, path)
    revision = dict(profile='integration-post-r10-local-refresh.v1', user_instruction=repair.LOCAL_USER,
        work=str(repair.LOCAL_WORK), prior_detours=50, additional_consolidated_revision=1,
        live_calls_added=0, additional_task_attempts=0, additional_transport_replacements=0,
        attempts_reset=False, reopened_nodes=[], baseline=ref(root, 'baseline.json'),
        review=ref(root, 'review.json'), result=ref(root, 'result.json'), implementation=implementation,
        prior_program=held[str(repair.PROGRAM)], prior_state=held[str(repair.STATE)],
        prior_binding=held[str(repair.BASE / 'current-binding.json')],
        prior_ledger=held[str(repair.BASE / 'live-calls.json')])
    # This test isolates the outer amendment; real predecessor validation is
    # exercised by the staged actual campaign check before registration.
    monkeypatch.setattr(repair, 'validate_program', lambda value, root: None)
    return old, revision, repair.expected_local_refresh(old, revision, root)


def test_local_amendment_preserves_original_tasks_and_limits(tmp_path, monkeypatch):
    old, revision, program = fixture(tmp_path, monkeypatch)
    assert repair.validate_local_refresh(program, tmp_path) == {'acquire-p14': 10}
    assert program['tasks'] == old['tasks']
    assert program['global_call_ceiling'] == old['global_call_ceiling']
    assert program[repair.KEY] == old[repair.KEY]


@pytest.mark.parametrize('field,value', [
    ('live_calls_added', 1), ('additional_task_attempts', 1),
    ('additional_transport_replacements', 1), ('attempts_reset', True),
    ('reopened_nodes', ['acquire-p14']), ('prior_detours', 0),
    ('user_instruction', 'continue forever'),
])
def test_local_amendment_cannot_grant_live_work(tmp_path, monkeypatch, field, value):
    old, revision, program = fixture(tmp_path, monkeypatch)
    program['local_refresh'][field] = value
    with pytest.raises(Refused): repair.validate_local_refresh(program, tmp_path)


@pytest.mark.parametrize('field', ['attempts', 'deadline', 'ceiling', 'historical_repairs'])
def test_local_amendment_cannot_hide_graph_or_budget_changes(tmp_path, monkeypatch, field):
    old, revision, program = fixture(tmp_path, monkeypatch)
    if field == 'attempts': program['tasks'][0]['maximum_attempts'] += 1
    elif field == 'deadline': program['deadline_utc'] = 'renewed'
    elif field == 'ceiling': program['global_call_ceiling'] += 1
    else: program[repair.KEY]['repair_ids'] = []
    with pytest.raises(Refused): repair.validate_local_refresh(program, tmp_path)


def test_changed_historical_archive_blocks_local_adoption(tmp_path, monkeypatch):
    old, revision, program = fixture(tmp_path, monkeypatch)
    (tmp_path / revision['prior_state']['path']).write_text('{}')
    with pytest.raises(Refused): repair.validate_local_refresh(program, tmp_path)
