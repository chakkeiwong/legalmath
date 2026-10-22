"""Real retained denominators and the named acceptance boundary refuse forgeries."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.prospectus_reasoning_acceptance_evidence import (
    SOLVER, load, same, same_records, same_solver_records, solver_requirements,
)
from scripts.prospectus_reasoning_acceptance import ROOT, validate_submission, checked_stages
from legalmath.prospectus.execution_acceptance import check_task


@pytest.fixture(scope='module')
def original():
    return load(ROOT / SOLVER / 'source-record.json.gz')


def test_original_solver_evidence_satisfies_declared_requirements(original):
    solver_requirements(original, original)


@pytest.mark.parametrize('attack', ['replace-case', 'duplicate-control', 'false-source', 'missing-product'])
def test_retained_totals_cannot_replace_actual_cases_and_source(original, attack):
    changed = deepcopy(original)
    if attack == 'replace-case':
        changed['cases'][-1] = deepcopy(changed['cases'][0])
    elif attack == 'duplicate-control':
        changed['controls'][-1] = deepcopy(changed['controls'][0])
    elif attack == 'false-source':
        changed['source_sha256'] = '0' * 64
    else:
        changed['products'].pop()
    with pytest.raises(ValueError):
        solver_requirements(changed, original)


def test_complete_evidence_comparison_rejects_omission_and_unrelated_changes(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    left.mkdir(); right.mkdir()
    (left / 'a.json').write_text('{"unknown_actual_fact":null}')
    with pytest.raises(ValueError, match='inventory'):
        same_records(left, right)
    (right / 'a.json').write_text('{"unknown_actual_fact":true}')
    with pytest.raises(ValueError, match='mismatch'):
        same_records(left, right)


@pytest.mark.parametrize('left,right', [(False, 0), (True, 1), (1, 1.0),
    ({'questions': [{'complete': False}]}, {'questions': [{'complete': 0}]}),
    ([False, True], [0, 1])])
def test_json_type_substitutions_are_not_equal_evidence(left, right):
    with pytest.raises(ValueError, match='mismatch'):
        same(left, right, 'typed complete answer')


def test_nonunique_actual_witnesses_are_verified_not_compared_as_unique():
    folder = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/reasoning-witness-repair-263'
    first, second = load(folder / 'replay-0.json.gz'), load(folder / 'replay-1.json.gz')
    assert first != second
    same_solver_records(first, second)
    altered = deepcopy(second)
    row = next(r for r in altered['cases'] if r['id'] == 'synthetic/13/all/true')
    row['result']['witnesses']['true']['f0'] = False
    with pytest.raises(ValueError, match='observation'):
        same_solver_records(first, altered)


@pytest.mark.parametrize('status', ['FAIL', 'RUNNING', None])
def test_top_level_pass_cannot_hide_failed_or_incomplete_stage(tmp_path, status):
    stage = tmp_path / 'stages/validate'; stage.mkdir(parents=True)
    (stage / 'started.json').write_text('{}')
    (stage / 'result.json').write_text(json.dumps({'status': status, 'error': None}))
    (tmp_path / 'result.json').write_text(json.dumps({'task': 'reasoning-corpus', 'status': 'PASS',
        'scope': 'FINITE_ENGINEERING_ONLY', 'source_meaning_proved': False, 'whole_program_complete': False}))
    with pytest.raises(ValueError, match='Failed reasoning stage'):
        validate_submission(ROOT, tmp_path, {'id': 'reasoning-corpus', 'evidence_attempt': 'prior'})


def test_missing_final_stage_cannot_be_accepted(tmp_path):
    stage = tmp_path / 'stages/validate'; stage.mkdir(parents=True)
    (stage / 'started.json').write_text('{}')
    with pytest.raises(ValueError, match='Incomplete'):
        checked_stages(tmp_path, ['validate'])


def test_validator_cannot_be_assigned_to_source_meaning_or_external_task():
    for task_id, stream, handler in [('basf-meanings', 'assisted', 'agent'),
                                      ('reasoning-corpus', 'engineering', 'external')]:
        with pytest.raises(ValueError):
            check_task({'id': task_id, 'stream': stream, 'handler': handler,
                        'validator': 'conditional-reasoning-current.v1'})


@pytest.mark.parametrize('change', [{'task': 'basf-meanings'}, {'status': 'FAIL'},
    {'scope': 'LEGAL_TRUTH'}, {'source_meaning_proved': True}, {'whole_program_complete': True}])
def test_submission_refuses_cross_task_failure_and_promoted_scope(tmp_path, change):
    result = {'task': 'reasoning-corpus', 'status': 'PASS', 'scope': 'FINITE_ENGINEERING_ONLY',
              'source_meaning_proved': False, 'whole_program_complete': False, **change}
    (tmp_path / 'result.json').write_text(json.dumps(result))
    with pytest.raises(ValueError, match='scope/result'):
        validate_submission(ROOT, tmp_path, {'id': 'reasoning-corpus'})
