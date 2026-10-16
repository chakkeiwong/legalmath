from copy import deepcopy

import pytest

from scripts.legal_mission_execution import Execution, Refused, digest, ref, save, validate_program
from tests.tooling.test_legal_mission_execution import task, setup, finish


def revised(root):
    execution = setup(root, [task('runtime'), task('product'), task('acquire-p10')])
    execution.start('runtime'); finish(execution, 'runtime', 'FAILED')
    prior = deepcopy(execution.program)
    state = __import__('json').loads((root/'state.json').read_text())
    save(root/'previous-program.json', prior); save(root/'previous-state.json', state)
    (root/'review.md').write_text('Reviewed local repair, no live allowance or deadline change.')
    changed = deepcopy(prior)
    changed['remaining_work_revision'] = {'profile': 'legal-remaining-work-revision.v1',
        'prior_detours': 21, 'additional_consolidated_revision': 1, 'live_calls_added': 0,
        'user_instruction': 'Refresh review and execute', 'review': ref(root, 'review.md'),
        'prior_program': ref(root, 'previous-program.json'), 'prior_state': ref(root, 'previous-state.json'),
        'reopened_nodes': ['runtime'], 'attempt_ceilings': {'runtime': 2}, 'archives': []}
    validate_program(changed, root)
    return changed, state


@pytest.mark.parametrize('fault', ['deadline', 'attempt', 'live', 'population', 'renewal'])
def test_reviewed_revision_cannot_hide_resource_or_population_changes(tmp_path, fault):
    changed, state = revised(tmp_path)
    if fault == 'deadline': changed['deadline_utc'] = '2101-01-01T00:00:00+00:00'
    if fault == 'attempt': changed['tasks'][1]['maximum_attempts'] = 3
    if fault == 'live':
        changed['remaining_work_revision']['reopened_nodes'].append('acquire-p10')
        changed['remaining_work_revision']['attempt_ceilings']['acquire-p10'] = 1
    if fault == 'population': changed['tasks'].pop()
    if fault == 'renewal':
        previous = deepcopy(changed)
        save(tmp_path/'renewed.json', previous)
        changed['remaining_work_revision']['prior_program'] = ref(tmp_path, 'renewed.json')
    with pytest.raises(Refused): validate_program(changed, tmp_path)


def test_historical_attempt_prefix_and_independent_readiness_survive(tmp_path):
    changed, state = revised(tmp_path)
    save(tmp_path/'program.json', changed)
    state['program_hash'] = digest(changed)
    state['tasks']['runtime'] = {'status': 'PENDING', 'attempts': state['tasks']['runtime']['attempts']}
    save(tmp_path/'state.json', state)
    execution = Execution(tmp_path, 'program.json', 'state.json')
    assert set(execution.summary()['ready']) == {'runtime', 'product', 'acquire-p10'}
    state['tasks']['runtime']['attempts'] = []
    save(tmp_path/'state.json', state)
    with pytest.raises(Refused, match='Historical attempts'): execution.summary()


def test_current_register_keeps_history_and_prefers_reviewed_continuation():
    from scripts.legal_integration_acceptance import current_register
    program = {'acceptance_revision': {'inventory': {'path': 'old.json'}}}
    assert current_register(program, 'inventory') == {'path': 'old.json'}
    program['remaining_work_revision'] = {'inventory': {'path': 'current.json'}}
    assert current_register(program, 'inventory') == {'path': 'current.json'}
    assert program['acceptance_revision']['inventory'] == {'path': 'old.json'}


def test_source_packet_change_rebuilds_exact_quote_positions_without_population_change():
    from scripts.legal_integration_remaining import rebuild_quote_locations
    from legalmath.interpretation.assurance.bounded_context import citation_dependencies
    from tests.assurance.test_bounded_product import envelope
    value = envelope()
    text = value['source_packet']['units'][0]['text']
    value['answer_acceptance']['original_readings'] = [{'id': 'reading-1', 'citations': [
        {'unit_id': value['source_packet']['units'][0]['unit_id'], 'quote': text}]}]
    value = rebuild_quote_locations(value)
    value['source_packet']['units'].append({'unit_id': 'supplement', 'text': 'New evidence.'})
    assert any(r['reason'] == 'STALE_QUOTATION_INDEX' for r in citation_dependencies(value)[1])
    repaired = rebuild_quote_locations(value)
    dependencies, unresolved = citation_dependencies(repaired)
    assert not unresolved and dependencies
    assert repaired['answer_acceptance']['original_readings'] == value['answer_acceptance']['original_readings']
    assert repaired['answer_acceptance']['acceptance_obligations'] == value['answer_acceptance']['acceptance_obligations']
    assert repaired['source_packet'] == value['source_packet']


def test_final_diagnostic_updates_display_without_promoting_or_rewriting_attempt(tmp_path):
    from scripts.legal_integration_master import current_qualification_view
    save(tmp_path/'capacity.json', {'request_failures': [], 'semantic_preservation': 'UNQUALIFIED'})
    source = {'path': 'source.json', 'sha256': 'fixture'}
    save(tmp_path/'verification.json', {'source': source, 'questions': {'p10': {
        '_node_status': 'BLOCKED', '_conclusion': 'Capacity repaired; live semantics unqualified.',
        'capacity': ref(tmp_path, 'capacity.json')}}})
    program = {'remaining_work_revision': {'source_revision': source,
        'final_verification': ref(tmp_path, 'verification.json')}}
    view = {'tasks': {'qualify-p10': {'status': 'BLOCKED', 'reason': '8 capacity failures', 'attempts_used': 4}},
            'blocked': {'qualify-p10': '8 capacity failures'}}
    shown = current_qualification_view(tmp_path, program, deepcopy(view))
    assert shown['tasks']['qualify-p10']['status'] == 'BLOCKED'
    assert shown['tasks']['qualify-p10']['attempts_used'] == 4
    assert shown['tasks']['qualify-p10']['recorded_attempt_reason'] == '8 capacity failures'
    assert shown['blocked']['qualify-p10'] == 'Capacity repaired; live semantics unqualified.'
    assert view['tasks']['qualify-p10']['reason'] == '8 capacity failures'
    assert current_qualification_view(tmp_path, program, shown)['tasks']['qualify-p10']['recorded_attempt_reason'] == '8 capacity failures'
    program['remaining_work_revision']['source_revision'] = {'path': 'different'}
    with pytest.raises(Refused): current_qualification_view(tmp_path, program, view)
