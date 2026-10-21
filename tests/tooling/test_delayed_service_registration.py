"""The new timing instruction cannot renew tasks, calls, failures or deadlines."""
from copy import deepcopy
import pytest
from scripts import legal_integration_delayed_service as delayed
from scripts.legal_mission_execution import (
    ref, save, digest, Refused, historical_evidence, merged_historical_archives,
)


def fixture(root, monkeypatch):
    tasks = [{'id': tid, 'maximum_attempts': maximum} for tid, maximum in
        [('acquire-p10', 7), ('acquire-evidence', 6), ('acquire-p14', 10), ('baseline-p10', 2)]]
    old = {'tasks': tasks, 'protected_evidence': [], 'deadline_utc': 'retained',
        'global_call_ceiling': 8100, 'local_refresh': {'completed': True},
        'repair_execution': {'repair_ids': ['R' + str(n) for n in range(1, 11)],
                             'cumulative_additional_attempts': 19}}
    states = {n['id']: {'status': 'BLOCKED', 'dispatch_status': 'NOT_DISPATCHED',
        'attempts': [{'number': i} for i in range(1, n['maximum_attempts'])]}
        for n in tasks[:2]}
    states['acquire-p14'] = {'status': 'FAILED', 'attempts': [{'number': i} for i in range(1, 11)]}
    states['baseline-p10'] = {'status': 'PENDING', 'attempts': []}
    before = {'program_hash': digest(old), 'tasks': states, 'events': []}
    paths = {str(delayed.PROGRAM): old, str(delayed.STATE): before,
        str(delayed.BASE / 'current-binding.json'): {'old_scope': 'retained'},
        str(delayed.BASE / 'live-calls.json'): {'calls': ['retained']},
        str(delayed.BASE / 'live-grant.json'): {'deadline': 'retained'}}
    held, rows = {}, []
    for name, value in paths.items():
        save(root / 'before' / name, value)
        held[name] = ref(root, root / 'before' / name)
        rows.append({'previous': {'path': name, 'sha256': held[name]['sha256']}, 'archive': held[name]})
    baseline = dict(prior_detours=51, calls=2359, running_owners=0, reserved_dispatches=0, archived=rows)
    save(root / 'baseline.json', baseline)
    save(root / 'review.json', {'reviewed': True})
    save(root / 'result.json', dict(verdict='PASS', provider_calls=0, ledger_unchanged=True,
        legal_acceptance=False, evidence=[]))
    implementation = {}
    for name in delayed.MUTATED:
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Reviewed delayed-retry implementation or plan.')
        if name != str(delayed.PLAN): implementation[name] = ref(root, path)
    revision = dict(profile='integration-delayed-service.v1', user_instruction=delayed.USER,
        work=str(delayed.WORK), prior_detours=51, additional_consolidated_revision=1,
        live_calls_added=0, additional_task_attempts=0, additional_transport_replacements=24,
        service_recovery_policy=deepcopy(delayed.SERVICE_DELAYED_POLICY), attempts_reset=False,
        reopened_nodes=list(delayed.REOPEN), baseline=ref(root, 'baseline.json'),
        review=ref(root, 'review.json'), result=ref(root, 'result.json'), implementation=implementation,
        prior_program=held[str(delayed.PROGRAM)], prior_state=held[str(delayed.STATE)],
        prior_binding=held[str(delayed.BASE / 'current-binding.json')],
        prior_ledger=held[str(delayed.BASE / 'live-calls.json')],
        prior_grant=held[str(delayed.BASE / 'live-grant.json')])
    # Isolate the outer policy here. The staged real mission validates every
    # actual predecessor before its registration transaction can commit.
    monkeypatch.setattr(delayed, 'validate_program', lambda value, root: None)
    return old, before, delayed.expected_program(old, revision, root)


def test_reopens_only_existing_unused_independent_attempts(tmp_path, monkeypatch):
    old, before, program = fixture(tmp_path, monkeypatch)
    assert delayed.validate_revision(program, tmp_path) == {n['id']: n['maximum_attempts'] for n in old['tasks']}
    state = delayed.project_state(before, program, 'now')
    delayed.validate_state_history(program, state, tmp_path)
    assert program['tasks'] == old['tasks']
    for tid in delayed.REOPEN:
        assert state['tasks'][tid]['status'] == 'PENDING'
        assert state['tasks'][tid]['attempts'] == before['tasks'][tid]['attempts']
    assert state['tasks']['acquire-p14'] == before['tasks']['acquire-p14']
    state['tasks']['baseline-p10'] = {'status': 'RUNNING', 'attempts': [{'number': 1}]}
    delayed.validate_state_history(program, state, tmp_path)


@pytest.mark.parametrize('field,value', [('live_calls_added', 1), ('additional_task_attempts', 1),
    ('additional_transport_replacements', 25), ('attempts_reset', True),
    ('reopened_nodes', ['acquire-p14']), ('prior_detours', 0), ('user_instruction', 'forever')])
def test_timing_instruction_cannot_expand_authority(tmp_path, monkeypatch, field, value):
    _, _, program = fixture(tmp_path, monkeypatch)
    program[delayed.KEY][field] = value
    with pytest.raises(Refused): delayed.validate_revision(program, tmp_path)


@pytest.mark.parametrize('fault', ['attempts', 'deadline', 'calls', 'repairs', 'expired_owner'])
def test_rejects_hidden_resource_or_graph_changes(tmp_path, monkeypatch, fault):
    _, before, program = fixture(tmp_path, monkeypatch)
    if fault == 'attempts': program['tasks'][0]['maximum_attempts'] += 1
    elif fault == 'deadline': program['deadline_utc'] = 'renewed'
    elif fault == 'calls': program['global_call_ceiling'] += 1
    elif fault == 'repairs': program['repair_execution']['repair_ids'] = []
    else:
        before['tasks']['acquire-p10']['attempts'].append({'number': 7})
        with pytest.raises(Refused): delayed.project_state(before, program, 'now')
        return
    with pytest.raises(Refused): delayed.validate_revision(program, tmp_path)


def test_settled_failure_and_spent_attempts_cannot_disappear(tmp_path, monkeypatch):
    _, before, program = fixture(tmp_path, monkeypatch)
    state = delayed.project_state(before, program, 'now')
    state['tasks']['acquire-p14']['status'] = 'PENDING'
    with pytest.raises(Refused): delayed.validate_state_history(program, state, tmp_path)
    state = delayed.project_state(before, program, 'now')
    state['tasks']['acquire-p10']['attempts'].pop()
    with pytest.raises(Refused): delayed.validate_state_history(program, state, tmp_path)


def test_nested_predecessor_projection_inherits_exact_outer_archive_aliases(tmp_path):
    (tmp_path / 'source.py').write_text('new bytes')
    (tmp_path / 'before').mkdir()
    (tmp_path / 'before/source.py').write_text('retained predecessor bytes')
    source = ref(tmp_path, 'source.py')
    archived = ref(tmp_path, 'before/source.py')
    outer = {(source['path'], archived['sha256']): archived}

    with historical_evidence(tmp_path, outer):
        composed = merged_historical_archives(tmp_path, {})
        assert composed == outer

        (tmp_path / 'other.py').write_text('other current bytes')
        (tmp_path / 'before/other.py').write_text('other retained bytes')
        other = ref(tmp_path, 'other.py')
        other_archive = ref(tmp_path, 'before/other.py')
        composed = merged_historical_archives(
            tmp_path, {(other['path'], other_archive['sha256']): other_archive})
        assert composed == {
            **outer,
            (other['path'], other_archive['sha256']): other_archive,
        }

        (tmp_path / 'different-alias.py').write_text('retained predecessor bytes')
        conflict = ref(tmp_path, 'different-alias.py')
        with pytest.raises(Refused, match='Conflicting historical evidence archive'):
            merged_historical_archives(
                tmp_path, {(source['path'], conflict['sha256']): conflict})
