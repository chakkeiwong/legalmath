from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json

import pytest
from jsonschema import ValidationError

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance.phased import (
    account_contract, account_encoding, account_input, account_instructions, account_recovery,
)
from tests.assurance.test_bounded_product import envelope, limits, Scripted
from tests.assurance.test_lossless_account_recovery import fixture


@pytest.mark.parametrize('profile', [None, account_input.PROFILE, account_encoding.PROFILE])
def test_account_guidance_matches_wire_and_preserves_source_assignment(tmp_path, profile):
    _, original = fixture(tmp_path)
    old = account_contract.select(original, input_profile=profile)
    new = account_contract.select(original, input_profile=profile,
        instruction_profile=account_instructions.PROFILE)
    legacy = prepare(old, account_contract.provider_schema())
    candidate = prepare(new, account_contract.provider_schema())
    assert legacy['schema'] == candidate['schema']
    assert account_recovery.baseline_request(new, account_contract.provider_schema())[0] == original
    before, after = deepcopy(legacy['request']), deepcopy(candidate['request'])
    for value in (before, after):
        for key in ('instructions', 'response_reference_instructions', 'account_instruction_profile'):
            value.pop(key, None)
    assert before == after
    guidance = candidate['request']['response_reference_instructions']
    assert 'open_dependencies' not in guidance and 'findings' not in guidance
    assert 'exactly condition and consequence' in guidance
    considered = candidate['schema']['properties']['considered']
    slots = {key: spec['enum'][0] for key, spec in considered['properties'].items()}
    assert json.dumps(slots, separators=(',', ':')) in guidance
    assert ('an integer from 0' in guidance) == (profile == account_encoding.PROFILE)
    response = {'conclusion': 'The duty depends on consent.',
        'support': [{'span_id': 0 if profile == account_encoding.PROFILE else 's0'}],
        'contrary': [], 'assumptions': [], 'unresolved': ['Client facts remain unknown.'],
        'alternatives': [], 'considered': slots, 'source_gaps': [], 'assertion_bindings': []}
    decoded = resolve(response, candidate, maximum_bytes=100000)
    assert decoded['considered'] == original['required_considered']
    for mutation in ('root', 'alternative', 'considered', 'citation'):
        invalid = deepcopy(response)
        if mutation == 'root': invalid['open_dependencies'] = []
        elif mutation == 'alternative':
            invalid['alternatives'] = [{'condition': 'If consent', 'consequence': 'Conditional', 'support': []}]
        elif mutation == 'considered': invalid['considered'] = list(slots.values())
        else: invalid['support'][0]['span_id'] = 'made-up-span'
        with pytest.raises((LegalMathError, ValidationError)):
            resolve(invalid, candidate, maximum_bytes=100000)


def test_legacy_wire_bytes_and_seven_actual_rejected_outputs_are_unchanged():
    from scripts.legal_integration_account_instruction_repair import replay_request, corrected_request
    root = Path(__file__).resolve().parents[2]
    work = root / 'artifacts/legal-mission-control/2026-10-15/qualification-continuation/live/common'
    checked, rejected = 0, 0
    for path in sorted(work.glob('*/calls/*/reference-binding.json')):
        retained = json.loads(path.read_text())
        request, schema = replay_request(retained), retained['original_schema']
        assert prepare(request, schema) == retained
        assert corrected_request(retained)['records'] == request['records']
        checked += 1
        response_path = path.parent / 'wire-response.json'
        if not response_path.exists(): continue
        response = json.loads(response_path.read_text())['value']
        result = json.loads((path.parent / 'result.json').read_text())
        if result['status'] != 'FAILED': continue
        with pytest.raises((LegalMathError, ValidationError)):
            resolve(response, retained, maximum_bytes=2000000)
        rejected += 1
    assert checked == 19 and rejected == 7


@pytest.mark.parametrize('typed', [False, True])
def test_new_guidance_reuses_success_under_its_exact_original_contract(tmp_path, typed):
    options = {'requirement_account_profile': account_contract.PROFILE} if typed else {}
    prior = BoundedProduct(tmp_path, tmp_path / 'prior', Scripted(fail_at=2), envelope(), list,
        limits=replace(limits(), input_tokens=12000), **options)
    records = [r for r in prior.route.records.values() if r['kind'] == 'source']
    question = envelope()['original_questions'][0]
    good = prior.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {}, ['o1'])
    failed = prior.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {}, ['o2'])
    details = [{'id': 'o1', 'result': good}, {'id': 'o2', 'result': failed}]
    (prior.directory / 'requirement-details.json').write_text(json.dumps(details))
    manifest = account_recovery.build(tmp_path, prior.directory / 'calls', details)
    from scripts.legal_mission_execution import save, ref
    save(tmp_path / 'recovery.json', manifest)
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path / 'next', provider, envelope(), list,
        limits=replace(limits(), input_tokens=12000), requirement_account_profile=account_contract.PROFILE,
        requirement_account_instruction_profile=account_instructions.PROFILE,
        requirement_account_recovery=ref(tmp_path, 'recovery.json'))
    assert product.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, {}, ['o1']) == good
    assert not provider.requests
    assert (product.directory / 'calls/detail-0/request.json').read_bytes() == (
        prior.directory / 'calls/detail-0/request.json').read_bytes()


def test_reviewed_reopening_keeps_dependencies_and_deferred_attempt_limits():
    from scripts import legal_integration_account_instruction_repair as repair
    from scripts.legal_mission_execution import read
    root = Path(__file__).resolve().parents[2]
    before_dir = root / repair.WORK / 'before'
    old, state = read(before_dir / repair.PROGRAM), read(before_dir / repair.STATE)
    revision = {k: {'path': k, 'sha256': k} for k in repair.POINTERS}
    candidate = repair.expected_program(old, state, revision, root)
    assert candidate['deadline_utc'] == old['deadline_utc']
    assert candidate['workers'] == old['workers']
    previous = {n['id']: n for n in old['tasks']}
    nodes = {n['id']: n for n in candidate['tasks']}
    assert nodes.keys() == previous.keys()
    for tid, node in nodes.items():
        for field in ('requires', 'after', 'any_success', 'write_resources', 'executor', 'command'):
            assert node.get(field) == previous[tid].get(field)
        if tid not in repair.REOPEN:
            assert node == previous[tid]
    assert nodes['acquire-p10']['maximum_attempts'] == nodes['acquire-evidence']['maximum_attempts'] == 6
    assert nodes['acquire-p14']['maximum_attempts'] == nodes['acquire-gatecoin']['maximum_attempts'] == 7
    assert 'corpus-qualification' not in repair.REOPEN
    assert 'semantic-preflight' not in repair.REOPEN


def test_replay_refuses_changed_source_and_schema():
    from scripts import legal_integration_account_instruction_repair as repair
    from scripts.legal_mission_execution import read
    root = Path(__file__).resolve().parents[2]
    retained = read(root / repair.PREVIOUS / 'live/common/gatecoin/calls/detail-90-part-0-part-1/reference-binding.json')
    for kind in ('source', 'schema'):
        changed = deepcopy(retained)
        if kind == 'source': changed['original_request']['records'][0]['text'] += ' altered'
        else: changed['original_schema']['additionalProperties'] = True
        with pytest.raises((ValueError, LegalMathError)):
            repair.replay_request(changed)


def test_live_product_entry_receives_instructions_and_latest_recovery(monkeypatch):
    from types import SimpleNamespace
    from scripts import legal_integration_phased_live as live, legal_product_completion as completion
    from scripts import legal_integration_account_instruction_repair as repair
    recovery = {'path': 'current-recovery.json', 'sha256': 'current'}
    program = {repair.KEY: {'recoveries': {'gatecoin': recovery}},
        'lossless_account_repair': {'profile': 'integration-lossless-account-repair.v1'}}
    monkeypatch.setattr(live, 'configure', lambda: SimpleNamespace(ENVELOPE=Path('envelope.json')))
    def read(path):
        if path == live.ROOT / live.PROGRAM: return program
        if path.name == 'envelope.json': return {'original_questions': [{'id': 'gatecoin'}]}
        if path.name == 'live-grant.json': return {'deadline_utc': '2026-10-18T00:00:00+00:00'}
        raise AssertionError(path)
    monkeypatch.setattr(live, 'read', read)
    monkeypatch.setattr(live, 'ref', lambda *args: {'path': str(args[-1]), 'sha256': 'identity'})
    monkeypatch.setattr(live, 'tokenizer', lambda *_: list)
    monkeypatch.setattr(live, 'phase_admit', lambda *_: None)
    monkeypatch.setattr(completion, 'run_product', lambda *args, **kwargs: kwargs)
    options = live.product_route('gatecoin', None, object(), preparation_only=True)
    assert options['bounded_requirement_account_instruction_profile'] == account_instructions.PROFILE
    assert options['bounded_requirement_account_input_profile'] == account_encoding.PROFILE
    assert options['bounded_requirement_account_recovery'] == recovery
    assert options['bounded_phase'] == 'prepare'
