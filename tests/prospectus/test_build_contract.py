"""Delivery scope is explicit and executable without erasing historical tasks."""
from copy import deepcopy

import pytest

from legalmath.prospectus.build_contract import check, check_revision, project, validate_submission, DEFERRED
from legalmath.prospectus.execution_authority import file_hash


@pytest.fixture
def program(tmp_path):
    direction = tmp_path / 'direction.md'
    direction.write_text('Build first; no external opinion or receiver; portability deferred.\n')
    return {'tasks': [{'id': t} for t in ['reasoning-corpus', *DEFERRED]],
            'build_contract': {'version': 'general-build.v1',
                'authorization': {'path': 'direction.md', 'sha256': file_hash(direction)},
                'required_tasks': ['reasoning-corpus'], 'deferred_tasks': dict(DEFERRED),
                'real_case': 'AFTER_GENERAL_BUILD', 'external_opinion_required': False,
                'cdm_receiver': None, 'portability': 'DEFERRED',
                'claim': 'CONDITIONAL_CORRECTNESS_IN_DECLARED_SUPPORTED_DOMAIN'}}


def test_delivery_scope_requires_user_direction_and_full_task_partition(program, tmp_path):
    check(program, tmp_path)
    assert project(program, set())['complete'] is False
    state = project(program, {'reasoning-corpus'})
    assert state['complete'] is True and state['deferred_tasks_accepted'] is False
    assert len(program['tasks']) == 7
    changed = deepcopy(program)
    changed['tasks'].append({'id': 'unaccounted-source'})
    with pytest.raises(ValueError, match='disposition'):
        check(changed, tmp_path)
    (tmp_path / 'direction.md').write_text('Altered direction\n')
    with pytest.raises(ValueError, match='authorization'):
        check(program, tmp_path)


@pytest.mark.parametrize('field,value', [('external_opinion_required', True),
                                       ('cdm_receiver', 'invented-receiver'),
                                       ('real_case', 'DONE'), ('portability', 'REQUIRED_NOW')])
def test_unrequested_prerequisites_cannot_silently_return(program, tmp_path, field, value):
    program['build_contract'][field] = value
    with pytest.raises(ValueError):
        check(program, tmp_path)


def test_review_distinguishes_original_inventory_from_changed_delivery(program):
    old = {'tasks': program['tasks']}
    with pytest.raises(ValueError, match='scope change'):
        check_revision(old, program, {'scope_unchanged': True})
    check_revision(old, program, {'delivery_scope_changed': True,
        'delivery_authorization': program['build_contract']['authorization'],
        'original_obligations_preserved': True})


def test_deferral_does_not_remove_a_requirement_arbitrarily(program, tmp_path):
    program['build_contract']['required_tasks'] = []
    with pytest.raises(ValueError):
        check(program, tmp_path)


def test_build_first_defers_actual_reader_cohort_without_accepting_it(program, tmp_path):
    from legalmath.prospectus.build_contract import BUILD_FIRST_DEFERRED
    program['tasks'].append({'id': 'independent-packet', 'handler': 'agent'})
    contract = program['build_contract']
    contract.update(version='general-build.v3', criteria={},
                    deferred_tasks=dict(BUILD_FIRST_DEFERRED))
    check(program, tmp_path)
    result = project(program, {'reasoning-corpus'})
    assert result['complete'] is True
    assert result['deferred_tasks']['independent-packet'] == 'EXTERNAL_READER_COHORT_NOT_BUILD_CRITERION'
    assert result['deferred_tasks_accepted'] is False
    contract['required_tasks'].append('independent-packet')
    with pytest.raises(ValueError, match='disposition'):
        check(program, tmp_path)


def scoped(program):
    program['tasks'][0] = {'id': 'basf-references', 'handler': 'agent'}
    contract = program['build_contract']
    contract.update(version='general-build.v2', required_tasks=['basf-references'], criteria={
        'basf-references': [
            {'id': 'pension-rounding', 'basis': 'NAMED_CONDITIONAL_CHECK',
             'validator': 'pension-rounding.v1', 'description': 'Conditional pension arithmetic only'},
            {'id': 'remaining-reference-coverage', 'basis': 'ORIGINAL_TASK_ACCEPTANCE',
             'validator': None, 'description': 'All remaining original reference requirements'}]})
    return program


def test_verified_component_preserves_pending_original_requirement(program, tmp_path):
    scoped(program)
    check(program, tmp_path)
    result = project(program, set(), {'basf-references': ['pension-rounding']})
    assert result['complete'] is False
    assert len(result['verified_criteria']) == len(result['pending_criteria']) == 1
    assert result['original_tasks_accepted_by_build_criteria'] is False
    assert project(program, {'basf-references'}, {'basf-references': ['pension-rounding']})['complete'] is True


@pytest.mark.parametrize('mutation', ['omit', 'wrong-validator', 'wrong-task', 'external'])
def test_conditional_acceptance_cannot_launder_a_requirement(program, tmp_path, mutation):
    scoped(program)
    rows = program['build_contract']['criteria']['basf-references']
    if mutation == 'omit':
        rows.pop()
    elif mutation == 'wrong-validator':
        rows[0]['validator'] = 'arbitrary-pass.v1'
    elif mutation == 'wrong-task':
        rows[0]['id'] = 'complete-everything'
    else:
        program['tasks'][0]['handler'] = 'external'
    with pytest.raises(ValueError):
        check(program, tmp_path)


def test_bes_cash_flow_check_never_closes_original_source_task(program, tmp_path):
    program['tasks'][0]={'id':'source-bes-dep-07','handler':'agent'}
    program['build_contract'].update(version='general-build.v2',required_tasks=['source-bes-dep-07'],criteria={
        'source-bes-dep-07':[
            {'id':'individual-cash-flow','basis':'NAMED_CONDITIONAL_CHECK','validator':'bes-cash-flow.v1',
             'description':'Finite original bilingual arithmetic and consumer'},
            {'id':'remaining-source-coverage','basis':'ORIGINAL_TASK_ACCEPTANCE','validator':None,
             'description':'All original source obligations remain'}]})
    check(program,tmp_path)
    state=project(program,set(),{'source-bes-dep-07':['individual-cash-flow']})
    assert len(state['verified_criteria'])==1 and len(state['pending_criteria'])==1
    assert not state['complete'] and not state['original_tasks_accepted_by_build_criteria']


def test_explicit_submission_scope_does_not_award_unchecked_criteria(program, tmp_path, monkeypatch):
    from scripts import prospectus_pension_reconciliation as validator
    scoped(program)
    task = program['tasks'][0]
    called = []
    monkeypatch.setattr(validator, 'validate_submission', lambda *args: called.append(args) or True)
    task['build_criteria_scope'] = []
    check(program, tmp_path)
    assert validate_submission(tmp_path, tmp_path, task, program) == [] and not called
    assert len(project(program, set())['pending_criteria']) == 2
    task['build_criteria_scope'] = ['pension-rounding']
    assert validate_submission(tmp_path, tmp_path, task, program) == ['pension-rounding']
    assert len(called) == 1
    monkeypatch.setattr(validator, 'validate_submission', lambda *args: False)
    with pytest.raises(ValueError, match='did not pass'):
        validate_submission(tmp_path, tmp_path, task, program)
    del task['build_criteria_scope']
    with pytest.raises(ValueError, match='did not pass'):
        validate_submission(tmp_path, tmp_path, task, program)


@pytest.mark.parametrize('scope', ['pension-rounding', None, ['unknown'], ['remaining-reference-coverage'],
                                  ['pension-rounding', 'pension-rounding'], [{}]])
def test_invalid_submission_scope_refused_at_check_and_submission(program, tmp_path, scope):
    scoped(program)
    task = program['tasks'][0]
    task['build_criteria_scope'] = scope
    with pytest.raises(ValueError, match='Submission scope'):
        check(program, tmp_path)
    with pytest.raises(ValueError, match='Submission scope'):
        validate_submission(tmp_path, tmp_path, task, program)
