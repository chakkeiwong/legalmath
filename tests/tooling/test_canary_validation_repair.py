"""Exact retained service responses exercise revalidation without resampling."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import legal_integration_canary_validation as repair
from scripts import legal_integration_current_live as live
from scripts.legal_mission_execution import read, save, ref, Refused, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance import integration_contract


@pytest.fixture
def replay_path():
    with TemporaryDirectory(prefix='test-replay-', dir=repair.ROOT/repair.WORK) as directory:
        yield Path(directory)


@pytest.fixture
def replay(monkeypatch):
    campaign = live.activate()
    service = campaign.provider()
    def forbid(*args, **kwargs):
        raise AssertionError('Revalidation must not dispatch or charge a model call')
    monkeypatch.setattr(type(service), 'complete', forbid)
    monkeypatch.setattr(type(service.allowance), 'reserve', forbid)
    receipt = read(repair.ROOT/repair.WORK/'retained-canaries.json')
    reference = ref(repair.ROOT, repair.WORK/'retained-canaries.json')
    return campaign, service, receipt, reference


def test_exact_eight_responses_pass_without_new_calls(replay, replay_path):
    _, service, _, reference = replay
    before = (repair.ROOT/repair.BASE/'live-calls.json').read_bytes()
    outcomes = repair.revalidate(service, replay_path, reference)
    assert set(outcomes) == set(repair.QUESTIONS)
    assert all(row['passed'] for row in outcomes.values())
    assert all(row[k]['status'] == 'VALIDATED' for row in outcomes.values() for k in ('reading', 'review'))
    assert (repair.ROOT/repair.BASE/'live-calls.json').read_bytes() == before


def test_original_review_schema_order_reconstructs_exact_binding(replay):
    campaign, _, receipt, _ = replay
    files = receipt['calls']['canary-review-p10']
    values = {key: read(repair.ROOT/value['path']) for key, value in files.items()}
    assert values['schema'] == campaign.AUDIT
    assert prepare(values['request'], values['schema']) != values['reference-binding']
    assert prepare(values['request'], campaign.AUDIT) == values['reference-binding']


def test_decoded_canary_keeps_wire_limit_for_direct_provider(replay, replay_path):
    campaign, service, receipt, _ = replay
    inputs = read(repair.ROOT/receipt['inputs']['p10']['path'])
    raw = read(repair.ROOT/receipt['calls']['canary-read-p10']['raw']['path'])
    product = campaign.session(replay_path, service, maximum=8)
    campaign.validate_canary_read(product, inputs['reading'], raw['value'])
    direct = SimpleNamespace(route=product.route, provider=SimpleNamespace(reference_transport=False))
    with pytest.raises(LegalMathError) as caught:
        campaign.validate_canary_read(direct, inputs['reading'], raw['value'])
    assert caught.value.details == 'Response exceeds declared budget'


@pytest.mark.parametrize('fault', ['source', 'request', 'schema', 'binding', 'wire', 'coverage', 'quote', 'receipt', 'provider-schema'])
def test_tampering_refuses_only_affected_question(replay, monkeypatch, replay_path, fault):
    _, service, receipt, reference = replay
    original = integration_contract.read_evidence
    files = receipt['calls']['canary-read-p10']
    selected = {'request': 'request', 'schema': 'schema', 'binding': 'reference-binding',
                'wire': 'wire-response', 'coverage': 'raw', 'quote': 'raw', 'receipt': 'provider-receipt'}
    def intercepted(item, root, **kwargs):
        value = original(item, root, **kwargs)
        if fault == 'source' and item == reference:
            value['source']['sha256'] = '0'*64
        elif fault in selected and item == files[selected[fault]]:
            if fault == 'request': value['task'] = 'WRONG_TASK'
            elif fault == 'schema': value['required'] = []
            elif fault == 'binding': value['binding'] = '0'*64
            elif fault == 'wire': value['value'] = {}
            elif fault == 'coverage': value['value']['records'] = []
            elif fault == 'quote':
                value['value']['records'][0]['findings'][0]['support'][0]['quote'] = 'Fabricated quotation'
            elif fault == 'receipt': value['allowance_slot'] += 1
        return value
    monkeypatch.setattr(integration_contract, 'read_evidence', intercepted)
    if fault == 'provider-schema':
        original_read = repair.read
        target = (repair.ROOT/files['provider-receipt']['path']).parent/'schema.json'
        def wrong_schema(path):
            value = original_read(path)
            return {} if path == target else value
        monkeypatch.setattr(repair, 'read', wrong_schema)
    if fault == 'source':
        with pytest.raises(Refused, match='source changed'):
            repair.revalidate(service, replay_path, reference)
    else:
        outcomes = repair.revalidate(service, replay_path, reference)
        assert not outcomes['p10']['passed']
        expected = {'request': 'request/schema/provider changed', 'schema': 'request/schema/provider changed',
                    'binding': 'reference expansion changed', 'wire': 'required property',
                    'coverage': 'decoded output differs', 'quote': 'decoded output differs',
                    'receipt': 'provider receipt differs', 'provider-schema': 'provider request/schema differs'}
        assert expected[fault] in outcomes['p10']['reason']
        assert all(outcomes[q]['passed'] for q in repair.QUESTIONS if q != 'p10')


@pytest.fixture(scope='module')
def candidate():
    root, work = repair.ROOT, repair.WORK
    baseline = read(root/work/'baseline.json')
    refs = {row['previous']['path']: row['archive'] for row in baseline['archived']}
    directory = work/'test-registration'
    local = directory/'local-review.json'
    save(root/local, {'verdict': 'PASS', 'provider_calls': 0,
                     'evidence': [ref(root, repair.REVIEW)], 'scope': 'Offline candidate only'})
    old = read(root/refs[str(repair.PROGRAM)]['path'])
    revision = {'profile': 'integration-canary-validation-repair.v1', 'prior_detours': 33,
        'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
        'user_instruction': repair.USER, 'review': ref(root, repair.REVIEW),
        'baseline': ref(root, work/'baseline.json'), 'local_review': ref(root, local),
        'canaries': ref(root, work/'retained-canaries.json'),
        'checkpoints': old['retry_delay_repair']['checkpoints'],
        'semantic_stage_maximum': old['retry_delay_repair']['semantic_stage_maximum'],
        'prior_program': refs[str(repair.PROGRAM)], 'prior_state': refs[str(repair.STATE)],
        'prior_binding': refs[str(repair.BASE/'current-binding.json')],
        'prior_ledger': refs[str(repair.BASE/'live-calls.json')],
        'reopened_nodes': list(repair.REOPEN),
        'service_recovery_policy': deepcopy(repair.SERVICE_CONTINUATION_POLICY)}
    before = read(root/revision['prior_state']['path'])
    program = repair.expected_program(historical_projection(old, repair.archives(baseline['archived'])),
                                     before, revision, root)
    state = deepcopy(before)
    for tid in repair.REOPEN:
        state['tasks'][tid].update(status='PENDING', reason='Offline candidate')
        for key in ('result', 'dispatch_status', 'prerequisite_evidence', 'shared_scope'):
            state['tasks'][tid].pop(key, None)
    state['program_hash'] = digest(program)
    return directory, program, state, before


def test_repair_preserves_semantic_success_and_all_attempts(candidate):
    directory, program, state, before = candidate
    save(repair.ROOT/directory/'program.json', program)
    save(repair.ROOT/directory/'state.json', state)
    execution = repair.MasterExecution(repair.ROOT, directory/'program.json', directory/'state.json')
    with execution.locked() as saved:
        assert all(saved['tasks'][tid]['attempts'] == row['attempts'] for tid, row in before['tasks'].items())
        assert saved['tasks']['semantic-preflight'] == before['tasks']['semantic-preflight']
    view = execution.classify(state)
    assert not any(row['status'] == 'INVALID' for row in view.values())
    assert view['current-binding']['status'] == 'READY'
    assert view['semantic-preflight']['status'] == 'SUCCEEDED'
    assert all(view[tid]['maximum_attempts'] == 4 and view[tid]['attempts_used'] == 3 for tid in repair.ACQUIRE)
    failed = deepcopy(state)
    failed['tasks']['current-binding']['status'] = 'BLOCKED'
    assert execution.classify(failed)['continuation-review']['status'] == 'READY'


@pytest.mark.parametrize('fault', ['deadline', 'calls', 'semantic', 'acquisition', 'sources', 'retry'])
def test_program_refuses_unreviewed_extensions(candidate, fault):
    _, base, _, _ = candidate
    program = deepcopy(base)
    revision = program['canary_validation_repair']
    tasks = {task['id']: task for task in program['tasks']}
    if fault == 'deadline': program['deadline_utc'] = '2100-01-01T00:00:00+00:00'
    elif fault == 'calls': revision['live_calls_added'] = 1
    elif fault == 'semantic': tasks['semantic-preflight']['maximum_attempts'] += 1
    elif fault == 'acquisition': tasks['acquire-p10']['maximum_attempts'] += 1
    elif fault == 'sources': tasks['ownership-handbook']['acceptance'] = 'Ignore ownership'
    else: revision['service_recovery_policy']['per_request_replacements'] += 1
    with pytest.raises(Refused): validate_program(program, repair.ROOT)
