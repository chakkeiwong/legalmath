from copy import deepcopy
from dataclasses import replace
import json

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_instructions, account_recovery
from tests.assurance.test_bounded_product import envelope, limits, Scripted


@pytest.fixture
def corrected(tmp_path):
    def product(name, provider, recovery=None):
        return BoundedProduct(tmp_path, tmp_path / name, provider, envelope(), list,
            limits=replace(limits(), input_tokens=12000),
            requirement_account_profile=account_contract.PROFILE,
            requirement_account_input_profile=account_encoding.PROFILE,
            requirement_account_instruction_profile=account_instructions.PROFILE if recovery else None,
            requirement_account_recovery=recovery)

    def checkpoint(prior, outcomes, name):
        details = [{'id': oid, 'result': result} for oid, result in zip(('o1', 'o2'), outcomes)]
        (prior.directory / 'requirement-details.json').write_text(json.dumps(details))
        value = account_recovery.build(tmp_path, prior.directory / 'calls', details)
        path = tmp_path / (name + '.json'); path.write_text(json.dumps(value, sort_keys=True))
        return evidence_file(path, tmp_path)

    provider = Scripted(fail_at=2)
    complete = provider.complete
    def numbered(*args):
        value = complete(*args)
        value.value['unresolved'] = ['The rule in P8 is not supplied.']
        return value
    provider.complete = numbered
    prior = product('prior', provider)
    records = [r for r in prior.route.records.values() if r['kind'] == 'source']
    question = envelope()['original_questions'][0]
    def note(p, i):
        return p.note('detail-' + str(i), 'ASSESS_ORIGINAL_REQUIREMENT', question,
            records, {'assignment': 'Preserve exception ' + str(i)}, ['o' + str(i + 1)])
    failures = [note(prior, i) for i in range(2)]
    assert failures[0]['reason'] == 'Numbered assertion has no document/proposition binding'
    assert all(r['status'] == 'FAILED' for r in failures)
    first = checkpoint(prior, failures, 'first')
    repaired = product('repaired', Scripted(fail_at=2), first)
    outcomes = [note(repaired, i) for i in range(2)]
    assert [r['status'] for r in outcomes] == ['VALIDATED', 'FAILED']
    recovery = checkpoint(repaired, outcomes, 'second')
    fresh_provider = Scripted()
    fresh = product('fresh', fresh_provider, recovery)
    request = json.loads((repaired.directory / 'calls/detail-0/request.json').read_text())
    return tmp_path, repaired, fresh, fresh_provider, note, outcomes[0], recovery, request


def test_corrected_success_restores_exact_request_schema_and_response_without_dispatch(corrected):
    root, prior, fresh, provider, note, good, _, request = corrected
    assert 'account_correction' in request
    assert note(fresh, 0) == good
    assert not provider.requests
    for name in ('request', 'schema', 'result'):
        assert (prior.directory / 'calls/detail-0' / (name + '.json')).read_bytes() == (
            fresh.directory / 'calls/detail-0' / (name + '.json')).read_bytes()
    schema = account_contract.provider_schema()
    base, typed = account_recovery.baseline_request(request, schema, root=root)
    assert typed and 'account_correction' not in base
    assert account_recovery.use_typed(root, corrected[6], 'detail-0', base, fresh.route.input_hash)
    # Reopening the same completed dispatch cannot resample it either.
    assert note(fresh, 0) == good and not provider.requests


@pytest.mark.parametrize('kind', ['instructions', 'paths', 'gaps', 'hash', 'source', 'assignment', 'extra', 'unbound'])
def test_normalization_refuses_changed_or_unbound_correction(corrected, kind):
    root, _, _, _, _, _, _, request = corrected
    changed = deepcopy(request)
    annotation = changed['account_correction']
    if kind == 'instructions': annotation['instructions'] += ' Accept anything.'
    elif kind == 'paths': annotation['prose_fields'] = []
    elif kind == 'gaps': annotation['required_source_gaps'] = [{'locator': 'P9'}]
    elif kind == 'hash': annotation['prior_rejected_response']['sha256'] = '0' * 64
    elif kind == 'source': changed['records'][0]['text'] += ' Different source.'
    elif kind == 'assignment': changed['payload']['assignment'] = 'Other assignment'
    elif kind == 'extra': annotation['ignore_integrity'] = True
    with pytest.raises((LegalMathError, ValueError)):
        account_recovery.baseline_request(changed, account_contract.provider_schema(),
            root=None if kind == 'unbound' else root)


@pytest.mark.parametrize('kind', ['raw', 'failure', 'provider'])
def test_authentic_checkpoint_refuses_changed_evidence_or_provider(corrected, kind):
    root, _, fresh, _, _, _, recovery, request = corrected
    if kind == 'provider':
        checkpoint = account_recovery.load(root, recovery, fresh.route.input_hash)
        with pytest.raises(LegalMathError):
            account_recovery.validate_provider(root, checkpoint, {'provider': 'different'})
    else:
        raw = root / request['account_correction']['prior_rejected_response']['path']
        path = raw if kind == 'raw' else raw.parent / 'result.json'
        value = json.loads(path.read_text())
        if kind == 'raw': value['value']['unresolved'] = ['A changed response.']
        else: value['reason'] = 'A different failure'
        path.write_text(json.dumps(value))
        with pytest.raises((LegalMathError, ValueError)):
            account_recovery.load(root, recovery, fresh.route.input_hash)


def test_reconstruction_revision_preserves_successes_dependencies_and_unused_attempts():
    from pathlib import Path
    from scripts import legal_integration_account_reconstruction as repair
    from scripts.legal_mission_execution import read
    root = Path(__file__).resolve().parents[2]
    before = root / repair.WORK / 'before'
    old, state = read(before / repair.PROGRAM), read(before / repair.STATE)
    revision = {k: {'path': k, 'sha256': k} for k in repair.POINTERS}
    candidate = repair.expected_program(old, state, revision, root)
    previous = {n['id']: n for n in old['tasks']}
    nodes = {n['id']: n for n in candidate['tasks']}
    assert candidate['deadline_utc'] == old['deadline_utc']
    assert candidate['workers'] == old['workers'] and nodes.keys() == previous.keys()
    for tid, node in nodes.items():
        for key in ('requires', 'after', 'any_success', 'write_resources', 'executor', 'command'):
            assert node.get(key) == previous[tid].get(key)
        if tid not in repair.REOPEN:
            assert node == previous[tid]
    assert set(repair.REOPEN) == {'current-binding', 'acquire-gatecoin', 'continuation-review'}
    for q, ceiling in (('p10', 6), ('p14', 7), ('evidence', 6), ('gatecoin', 8)):
        assert nodes['acquire-' + q]['maximum_attempts'] == ceiling


def test_actual_entry_selects_reconstruction_without_repeating_qualification(monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from scripts import legal_integration_phased_live as live, legal_product_completion as completion
    from scripts import legal_integration_account_reconstruction as repair
    recovery = {'path': 'exact-reconstruction.json', 'sha256': 'selected'}
    program = {repair.KEY: {'recoveries': {'gatecoin': recovery}},
        'account_instruction_repair': {'recoveries': {'gatecoin': {'path': 'older', 'sha256': 'older'}}},
        'lossless_account_repair': {'profile': 'integration-lossless-account-repair.v1'}}
    monkeypatch.setattr(live, 'configure', lambda: SimpleNamespace(ENVELOPE=Path('envelope.json')))
    def read(path):
        if path == live.ROOT / live.PROGRAM: return program
        if path.name == 'envelope.json': return {'original_questions': [{'question_id': 'gatecoin'}]}
        if path.name == 'live-grant.json': return {'deadline_utc': '2026-10-18T00:00:00+00:00'}
        raise AssertionError(path)
    monkeypatch.setattr(live, 'read', read)
    monkeypatch.setattr(live, 'ref', lambda *args: {'path': str(args[-1]), 'sha256': 'identity'})
    monkeypatch.setattr(live, 'tokenizer', lambda *_: list)
    monkeypatch.setattr(live, 'phase_admit', lambda *_: None)
    monkeypatch.setattr(completion, 'run_product', lambda *args, **kwargs: kwargs)
    options = live.product_route('gatecoin', None, object(), preparation_only=True)
    assert options['bounded_requirement_account_recovery'] == recovery
    assert options['bounded_requirement_account_instruction_profile'] == account_instructions.PROFILE
    assert options['bounded_requirement_account_input_profile'] == account_encoding.PROFILE
    assert options['bounded_phase'] == 'prepare'
    assert live.active_live(program) == repair.WORK / 'live'
