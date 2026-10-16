"""The same-master repair keeps historical outcomes and exact finite limits."""
from copy import deepcopy

import pytest

from scripts.legal_integration_service_continuation import (
    ROOT, BASE, PROGRAM, STATE, DELAY_WORK, DELAY_REVIEW, REOPEN, USER,
    SERVICE_CONTINUATION_POLICY, expected_delay_program, delay_archives)
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_mission_execution import read, save, ref, validate_program, Refused
from legalmath.canonical import digest


@pytest.fixture(scope='module')
def candidate():
    baseline = read(ROOT/DELAY_WORK/'baseline.json')
    refs = {row['previous']['path']: row['archive'] for row in baseline['archived']}
    directory = DELAY_WORK/'test-registration'
    local = directory/'local-review.json'
    save(ROOT/local, {'verdict': 'PASS', 'provider_calls': 0,
                     'evidence': [ref(ROOT, DELAY_REVIEW)], 'scope': 'Offline candidate only'})
    budget = read(ROOT/DELAY_WORK/'resume-budget.json')
    revision = {'profile': 'integration-retry-delay-repair.v1', 'prior_detours': 32,
        'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
        'user_instruction': USER, 'review': ref(ROOT, DELAY_REVIEW),
        'baseline': ref(ROOT, DELAY_WORK/'baseline.json'), 'local_review': ref(ROOT, local),
        'checkpoints': ref(ROOT, DELAY_WORK/'checkpoints.json'),
        'resume_budget': ref(ROOT, DELAY_WORK/'resume-budget.json'),
        'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
        'prior_binding': refs[str(BASE/'current-binding.json')], 'prior_ledger': refs[str(BASE/'live-calls.json')],
        'reopened_nodes': list(REOPEN), 'semantic_stage_maximum': budget['semantic_stage_maximum'],
        'service_recovery_policy': deepcopy(SERVICE_CONTINUATION_POLICY)}
    before = read(ROOT/revision['prior_state']['path'])
    program = expected_delay_program(historical_projection(read(ROOT/revision['prior_program']['path']),
        delay_archives(baseline['archived'])), before, revision, ROOT)
    state = deepcopy(before)
    for tid in REOPEN:
        state['tasks'][tid].update(status='PENDING', reason='Offline candidate')
        state['tasks'][tid].pop('result', None)
    state['program_hash'] = digest(program)
    return directory, program, state, before


def test_repair_preserves_source_owners_and_runs_review_after_failure(candidate):
    from scripts.legal_integration_master import MasterExecution
    directory, program, state, before = candidate
    validate_program(program, ROOT)
    save(ROOT/directory/'program.json', program)
    save(ROOT/directory/'state.json', state)
    execution = MasterExecution(ROOT, directory/'program.json', directory/'state.json')
    with execution.locked() as saved:
        for tid, row in before['tasks'].items():
            assert saved['tasks'][tid]['attempts'] == row['attempts']
    view = execution.classify(state)
    assert not any(row['status'] == 'INVALID' for row in view.values())
    assert view['current-binding']['status'] == 'READY'
    assert all(view[tid]['status'] == 'SUCCEEDED' for tid in
               ('ownership-2023', 'ownership-2025', 'ownership-handbook'))
    failed = deepcopy(state)
    failed['tasks']['current-binding']['status'] = 'BLOCKED'
    assert execution.classify(failed)['continuation-review']['status'] == 'READY'


@pytest.mark.parametrize('fault', ['deadline', 'calls', 'attempts', 'acquisition', 'sources', 'retry', 'budget'])
def test_repair_refuses_unreviewed_extensions(candidate, fault):
    _, base, _, _ = candidate
    program = deepcopy(base)
    revision = program['retry_delay_repair']
    tasks = {task['id']: task for task in program['tasks']}
    if fault == 'deadline':
        program['deadline_utc'] = '2100-01-01T00:00:00+00:00'
    elif fault == 'calls':
        revision['live_calls_added'] = 1
    elif fault == 'attempts':
        tasks['semantic-preflight']['maximum_attempts'] += 1
    elif fault == 'acquisition':
        tasks['acquire-p10']['maximum_attempts'] += 1
    elif fault == 'sources':
        tasks['ownership-handbook']['acceptance'] = 'Ignore ownership'
    elif fault == 'retry':
        revision['service_recovery_policy']['per_request_replacements'] += 1
    else:
        revision['semantic_stage_maximum'] += 1
    with pytest.raises(Refused):
        validate_program(program, ROOT)
