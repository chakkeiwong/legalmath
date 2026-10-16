"""Acceptance decisions must preserve evidence without forcing tool adoption."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from scripts.legal_integration_acceptance import (
    TOOLS, QUESTIONS, validate_applicability, validate_evaluation, validate_inventory,
    evaluation_summary,
)
from scripts.legal_integration_master import task, MasterExecution
from scripts.legal_mission_execution import save, ref, validate_program, digest


def proof(root):
    save(root / 'proof.json', {'retained': 'synthetic boundary, target and scope evidence'})
    return ref(root, 'proof.json')


def matrix(root, decision='applicable'):
    evidence = proof(root)
    value = {'profile': 'legal-tool-applicability.v1', 'pairs': [
        {'question': q, 'tool': t, 'decision': decision, 'mechanism': 'fixture mechanism',
         'reason': 'fixture scope', 'required_target': 'fixture target', 'question_impact': 'conditional',
         'reopen_when': 'target changes', 'evidence': [evidence], 'reviewed': True,
         'boundary_evidence': [evidence], 'target_evidence': [evidence], 'warrant_review': [evidence]}
        for q in QUESTIONS for t in TOOLS]}
    save(root / 'pairs.json', value)
    return value


def evaluated(root):
    matrix(root)
    evidence = [ref(root, 'proof.json')]
    return {'id': 'bm25', 'fully_integrated': False,
        'evaluation_completion': {'status': 'evaluated', 'scope': 'original questions',
            'reason': 'evaluated without adoption', 'reopen_when': 'new target', 'evidence': evidence,
            'reviewed': True, 'question_impact': 'no observed benefit',
            'applicability': ref(root, 'pairs.json')},
        'evaluation': {'route': 'actual_product', 'matched_inputs': True, 'finding': 'no_benefit',
            'baseline': evidence, 'candidate': evidence, 'assessment': evidence,
            'input_bindings': {'baseline': 'same', 'candidate': 'same'},
            'questions': dict.fromkeys(QUESTIONS, 'fixture question')},
        'stages': {name: {'level': level, 'evidence': evidence} for name, level in (
            ('product_invocation', 'live'), ('downstream_delivery', 'live'),
            ('negative_and_unsupported', 'controlled'), ('answer_contribution', 'evaluated'))}}


def test_evaluation_does_not_imply_adoption(tmp_path):
    tool = evaluated(tmp_path)
    result = evaluation_summary([tool], tmp_path)
    assert result['selected_tools_fully_evaluated'] == 1
    assert result['selected_tools_fully_integrated'] == 0
    assert not result['all_selected_tool_dispositions_complete']


@pytest.mark.parametrize('fault', ['inputs', 'evidence', 'delivery', 'coverage', 'applicability'])
def test_unsupported_evaluation_never_closes(tmp_path, fault):
    tool = evaluated(tmp_path)
    if fault == 'inputs': tool['evaluation']['input_bindings']['candidate'] = 'changed'
    if fault == 'evidence': tool['evaluation']['assessment'] = []
    if fault == 'delivery': tool['stages']['downstream_delivery']['level'] = 'controlled'
    if fault == 'coverage': tool['evaluation']['questions'].pop('gatecoin')
    if fault == 'applicability':
        matrix(tmp_path, 'target_required')
        tool['evaluation_completion']['applicability'] = ref(tmp_path, 'pairs.json')
    with pytest.raises(ValueError): validate_evaluation(tool, tmp_path)


def test_reviewed_scope_rejection_is_neither_effect_nor_integration(tmp_path):
    tool = evaluated(tmp_path)
    matrix(tmp_path, 'not_applicable')
    tool['evaluation_completion'].update(status='rejected', applicability=ref(tmp_path, 'pairs.json'),
        applicability_evidence=[ref(tmp_path, 'pairs.json')],
        boundary_and_fallback_evidence=[ref(tmp_path, 'proof.json')], contribution_assessed=False)
    result = validate_evaluation(tool, tmp_path)
    assert result == {'status': 'rejected', 'closed': True, 'effect_evaluated': False}
    tool['fully_integrated'] = True
    with pytest.raises(ValueError): validate_evaluation(tool, tmp_path)


@pytest.mark.parametrize('fault', ['omission', 'duplicate', 'unreviewed', 'unwarranted'])
def test_pair_register_cannot_hide_missing_work(tmp_path, fault):
    value = matrix(tmp_path, 'not_applicable')
    if fault == 'omission': value['pairs'].pop()
    if fault == 'duplicate': value['pairs'][0] = deepcopy(value['pairs'][1])
    if fault == 'unreviewed': value['pairs'][0]['reviewed'] = False
    if fault == 'unwarranted':
        value['pairs'][0]['decision'] = 'applicable'
        value['pairs'][0]['warrant_review'] = []
    with pytest.raises(ValueError): validate_applicability(value, tmp_path)


def test_inventory_dispositions_preserve_ids_and_require_factual_conditions(tmp_path):
    evidence = [proof(tmp_path)]
    rows = [{'kind': 'obligation', 'id': 'o', 'disposition': 'external_fact', 'reason': 'unknown conduct',
        'evidence': evidence, 'reviewed': True, 'question_impact': 'conditional responsibility',
        'review_evidence': evidence, 'reopen_when': 'conduct evidence supplied',
        'conditional_answer': 'If action was adequate under the applicable standard...',
        'evidence_request': 'Provide the dated control review and incident record.'}]
    doc = {'profile': 'legal-original-inventory-review.v1', 'records': rows}
    validate_inventory(doc, ['o'], [], tmp_path)
    rows[0].pop('conditional_answer')
    with pytest.raises(ValueError): validate_inventory(doc, ['o'], [], tmp_path)
    with pytest.raises(ValueError): validate_inventory(doc, ['o', 'missing'], [], tmp_path)


def execution(root):
    tasks = [task('acquire-p10', agent=True), task('source'), task('downstream', ['acquire-p10']),
             task('assessment', after=['acquire-p10'])]
    program = {'profile': 'legal-mission-execution.v1', 'workers': 2,
        'deadline_utc': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        'protected_evidence': [], 'artifact_directory': 'out', 'tasks': tasks}
    save(root / 'program.json', program)
    return MasterExecution(root, 'program.json', 'state.json')


def test_preflight_failure_does_not_consume_attempt_or_block_independent_work(tmp_path):
    run = execution(tmp_path)
    run.block_before_dispatch('acquire-p10', 'Semantic prerequisite failed', [proof(tmp_path)])
    view = MasterExecution(tmp_path, 'program.json', 'state.json').summary()
    assert view['tasks']['acquire-p10']['attempts_used'] == 0
    assert set(view['ready']) == {'source', 'assessment'}
    assert view['tasks']['downstream']['status'] == 'DEPENDENCY_BLOCKED'
    save(tmp_path / 'proof.json', {'tampered': True})
    assert run.summary()['tasks']['acquire-p10']['status'] == 'INVALID'


def test_shared_veto_survives_restart_and_leaves_source_work_ready(tmp_path):
    run = execution(tmp_path)
    run.record_continuation_veto('E_AUTHORITY', 'Binding changed', [proof(tmp_path)], ['acquire-p10'])
    view = MasterExecution(tmp_path, 'program.json', 'state.json').summary()
    assert view['tasks']['acquire-p10']['status'] == 'BLOCKED'
    assert view['tasks']['acquire-p10']['attempts_used'] == 0
    assert 'source' in view['ready']
    with pytest.raises(ValueError): run.start('acquire-p10')


def test_reviewed_retry_of_undispatched_work_records_its_first_attempt(tmp_path):
    run = execution(tmp_path)
    run.block_before_dispatch('acquire-p10', 'Prerequisite unavailable', [proof(tmp_path)])
    run.retry('acquire-p10', 'Prerequisite repaired and reviewed')
    assert run.start('acquire-p10') == 1
    with run.locked() as state:
        assert 'dispatch_status' not in state['tasks']['acquire-p10']
        assert len(state['tasks']['acquire-p10']['attempts']) == 1
        assert state['events'][0]['action'] == 'PREREQUISITE_BLOCKED'


def test_fourth_attempt_requires_bound_prior_state_and_local_scope(tmp_path):
    run = execution(tmp_path)
    program = deepcopy(run.program)
    program['tasks'][1]['maximum_attempts'] = 4
    program['acceptance_revision'] = {'attempt_ceilings': {'source': 4}, 'review': proof(tmp_path)}
    with pytest.raises(ValueError): validate_program(program, tmp_path)


def test_reviewed_migration_accepts_one_local_attempt_but_not_extra_live_authority(tmp_path):
    run = execution(tmp_path)
    before = deepcopy(run.program)
    for row in before['tasks']:
        row['maximum_attempts'] = 3
    save(tmp_path / 'old-program.json', before)
    old_state = {'program_hash': digest(before), 'tasks': {
        t['id']: {'attempts': [{}, {}, {}], 'status': 'FAILED'} for t in before['tasks']}}
    save(tmp_path / 'old-state.json', old_state)
    revised = deepcopy(before)
    revised['tasks'][1]['maximum_attempts'] = 4
    revised['acceptance_revision'] = {'profile': 'legal-acceptance-revision.v1',
        'additional_consolidated_revision': 1, 'prior_detours': 20, 'live_calls_added': 0,
        'user_instruction': 'synthetic reviewed local authorization', 'review': proof(tmp_path),
        'prior_program': ref(tmp_path, 'old-program.json'), 'prior_state': ref(tmp_path, 'old-state.json'),
        'attempt_ceilings': {'source': 4}, 'reopened_nodes': ['source']}
    validate_program(revised, tmp_path)
    save(tmp_path / 'revised.json', revised)
    reset = deepcopy(old_state)
    reset['program_hash'] = digest(revised)
    reset['tasks']['source']['attempts'] = []
    save(tmp_path / 'reset-state.json', reset)
    with pytest.raises(ValueError, match='Historical attempts changed'):
        MasterExecution(tmp_path, 'revised.json', 'reset-state.json').summary()
    invalid = deepcopy(revised)
    invalid['acceptance_revision']['reopened_nodes'] = ['acquire-p10']
    invalid['acceptance_revision']['attempt_ceilings'] = {'acquire-p10': 4}
    invalid['tasks'][0]['maximum_attempts'] = 4
    with pytest.raises(ValueError): validate_program(invalid, tmp_path)
    revised['deadline_utc'] = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    with pytest.raises(ValueError): validate_program(revised, tmp_path)


def test_campaign_preflight_blocks_only_the_failed_question(tmp_path):
    from scripts.legal_integration_campaign import block_failed_preflight
    run = execution(tmp_path)
    outcomes = {q: {'passed': q != 'p10'} for q in QUESTIONS}
    block_failed_preflight(run, outcomes, True, [proof(tmp_path)])
    assert run.summary()['tasks']['acquire-p10']['attempts_used'] == 0
    assert 'source' in run.summary()['ready']


def test_dormant_campaign_helper_routes_to_binding_preparation(tmp_path, monkeypatch):
    from scripts import legal_integration_reopening as reopening
    from scripts import legal_integration_reopening_live as live
    monkeypatch.setattr(live, 'prepare_binding', lambda: {'checked': 'dispatch-free'})
    assert reopening.local_node('campaign', tmp_path) == {'checked': 'dispatch-free'}


def test_local_acceptance_revision_cannot_reuse_consumed_live_binding(monkeypatch):
    from scripts import legal_integration_campaign as campaign
    monkeypatch.setattr(campaign, 'read', lambda path: {'acceptance_revision': {'live_calls_added': 0}})
    def forbidden():
        raise AssertionError('Unqualified revision reached a live provider')
    monkeypatch.setattr(campaign, 'provider', forbidden)
    with pytest.raises(ValueError, match='no qualified live binding'):
        campaign.live()


def test_real_adverse_review_can_establish_harm_but_broken_review_cannot():
    from scripts.legal_integration_campaign import validate_effect
    class Evaluator:
        def citations(self, value, sources):
            assert value['support'][0]['quote'] == 'Source rule'
    baseline = {'answer': {'value': {'conclusion': 'Conditional'}}, 'review_accepted': True}
    review = {'status': 'VALIDATED', 'value': {'verdict': 'REJECT', 'issues': ['Lost condition'],
                                            'support': [{'quote': 'Source rule'}]}}
    candidate = {'answer': {'value': {'conclusion': 'Unconditional'}}, 'review_accepted': False,
                 'reviews': [review], 'tools': [{'id': 'tool-formal', 'value': {'status': 'PASS'}}]}
    value = {'effect': 'harmful', 'baseline_quote': 'Conditional', 'candidate_quote': 'Unconditional',
             'support': [{'quote': 'Source rule'}], 'unresolved': []}
    validate_effect(value, baseline, candidate, Evaluator(), [])
    for invalid in ({'status': 'FAILED'}, {'status': 'VALIDATED', 'value': {'verdict': 'REJECT', 'support': []}}):
        broken = {**candidate, 'reviews': [invalid]}
        with pytest.raises(ValueError): validate_effect(value, baseline, broken, Evaluator(), [])
