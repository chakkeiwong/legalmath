"""Adverse controls for the one-time completion of registered repair 42."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from scripts.legal_mission_execution import Execution, Refused, save

HELPER = Path(__file__).resolve().parents[2] / 'artifacts/legal-mission-control/2026-10-15/account-reconstruction/complete_registration.py'
spec = importlib.util.spec_from_file_location('complete_reconstruction_registration', HELPER)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def state_and_veto():
    scope = ['acquire-p10']
    veto = {'code': 'E_INTEGRITY', 'reason': repair.REASON,
            'evidence': [deepcopy(repair.VETO_EVIDENCE)], 'scope': scope}
    return {'program_hash': 'unchanged', 'tasks': {'acquire-p10': {'status': 'PENDING', 'attempts': [{'number': 1}]}},
            'events': [{'action': 'PRIOR'}], 'continuation_vetoes': [veto]}, scope


@pytest.mark.parametrize('field,value', [('code', 'E_AUTHORITY'), ('reason', 'Another failure'),
    ('scope', ['other']), ('evidence', [{'path': 'foreign', 'sha256': 'unknown'}])])
def test_changed_or_unbound_veto_is_refused(field, value):
    state, scope = state_and_veto()
    state['continuation_vetoes'][0][field] = value
    with pytest.raises(Refused, match='Exact reviewed veto'):
        repair.project(state, scope, {}, 'now')


def test_history_and_foreign_vetoes_are_preserved_and_apply_still_blocks(tmp_path):
    state, scope = state_and_veto()
    marker = tmp_path / 'other.json'
    marker.write_text('{}')
    from scripts.legal_mission_execution import ref
    foreign = [{'code': code, 'reason': 'Unrepaired ' + code, 'evidence': [ref(tmp_path, marker)], 'scope': scope}
               for code in ('E_AUTHORITY', 'E_INTEGRITY')]
    state['continuation_vetoes'] += foreign
    before = deepcopy(state)
    projected = repair.project(state, scope, {'path': 'review', 'sha256': 'fixed'}, 'now')
    assert state == before
    assert projected['tasks'] == before['tasks']
    assert projected['events'][:-1] == before['events']
    assert projected['continuation_vetoes'] == foreign
    assert projected['resolved_continuation_vetoes'][-1]['veto'] == before['continuation_vetoes'][0]
    node = {'id': scope[0], 'executor': 'agent', 'requires': [], 'after': [], 'inputs': [],
        'maximum_attempts': 2, 'write_resources': scope, 'priority': 1, 'question_ids': ['p10'],
        'acceptance': 'Original evidence', 'deliverable': 'result.json'}
    program = {'profile': 'legal-mission-execution.v1', 'workers': 1, 'deadline_utc': '2100-01-01T00:00:00+00:00',
               'protected_evidence': [], 'tasks': [node]}
    save(tmp_path / 'program.json', program)
    engine = Execution(tmp_path, 'program.json', 'state.json')
    assert engine.classify(projected)[scope[0]]['status'] == 'BLOCKED'


def test_running_owner_or_duplicate_resolution_is_refused():
    state, scope = state_and_veto()
    state['tasks'][scope[0]]['status'] = 'RUNNING'
    with pytest.raises(Refused, match='owner is running'):
        repair.project(state, scope, {}, 'now')
    state['tasks'][scope[0]]['status'] = 'PENDING'
    projected = repair.project(state, scope, {}, 'now')
    with pytest.raises(Refused, match='Exact reviewed veto'):
        repair.project(projected, scope, {}, 'again')
