from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased import group_review
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def test_conditional_review_still_refuses_acceptance_with_needed_context(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path / 'review', Scripted(), envelope(), list, limits=limits())
    record = next(r for r in product.route.records.values() if r['kind'] == 'source')
    decision = {'verdict': 'ACCEPT', 'reason': 'The conditional claim follows; actual consent remains unknown.',
        'support': [{'record_id': record['id'], 'quote': record['text'], 'locator': ''}],
        'issues': [], 'source_gaps': [], 'assertion_bindings': [], 'context_needs': []}
    value = {'analyses': [{'analysis_id': 'conditional', 'decision': decision}],
        'assignments': {'item': {'analysis_id': 'conditional'}}}
    assert group_review.validate(product, 'p14', value, ['item'], [record])['item']['decision']['verdict'] == 'ACCEPT'
    decision['context_needs'] = [{'kind': 'CLIENT_FACT', 'reason': 'Needed to judge the claim itself.',
        'record_ids': [], 'locators': [], 'query': ''}]
    with pytest.raises(LegalMathError) as failure:
        group_review.validate(product, 'p14', value, ['item'], [record])
    assert failure.value.details == 'Accepted review retains necessary context'
    decision['verdict'] = 'UNRESOLVED'
    assert group_review.validate(product, 'p14', value, ['item'], [record])['item']['decision']['context_needs']


@pytest.mark.parametrize('preparation', [True, False])
def test_master_public_route_selects_recovery_and_original_source_independently(tmp_path, monkeypatch, preparation):
    from scripts import legal_integration_phased_live as live, legal_product_completion as public
    from scripts.legal_integration_account_repair import WORK
    from legalmath.interpretation.assurance.phased import account_contract, account_input
    value = envelope()
    recovery = {'path': 'frozen-p14.json', 'sha256': 'original-successes'}
    program = {'account_capacity_repair': {'recoveries': {'p14': recovery}}}
    def read(path):
        if path == tmp_path / live.PROGRAM:
            return program
        if path.name == 'live-grant.json':
            return {'deadline_utc': '2026-10-18T19:03:39.626294+00:00'}
        return value
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    monkeypatch.setattr(live, 'read', read)
    monkeypatch.setattr(live, 'configure', lambda: SimpleNamespace(ENVELOPE=live.Path('source.json')))
    monkeypatch.setattr(live, 'tokenizer', lambda p: list)
    monkeypatch.setattr(live, 'ref', lambda root, p: {'path': str(p), 'sha256': 'binding'})
    seen = {}
    def capture(*args, **kwargs):
        seen.update(args=args, kwargs=kwargs)
        return {'passed': True}
    monkeypatch.setattr(public, 'run_product', capture)
    assert live.product_route('p14', None, object(), preparation_only=preparation) == {'passed': True}
    kwargs = seen['kwargs']
    assert kwargs['bounded_requirement_account_profile'] == account_contract.PROFILE
    assert kwargs['bounded_requirement_account_input_profile'] == account_input.PROFILE
    assert kwargs['bounded_requirement_account_recovery'] == recovery
    assert kwargs['bounded_envelope'] is value and kwargs['active_questions'] == ['p14']
    assert kwargs['bounded_execution'] == 'phased'
    assert kwargs['bounded_acquisition_ref']['path'] == str(live.LIVE / 'acquisition/investigation.json')
    assert kwargs['shared_prefix'] == (None if preparation else tmp_path / WORK / 'live/common/p14/calls')


def test_account_graph_keeps_reviewer_failure_independent():
    from scripts.legal_integration_account_repair import expected_program, REOPEN
    from scripts.legal_integration_master import task
    nodes = [task('current-binding'), task('semantic-preflight', ['current-binding'], agent=True),
        task('continuation-review', after=['semantic-preflight'])]
    nodes += [task('acquire-' + q, ['current-binding'], agent=True) for q in ('p10', 'p14', 'evidence', 'gatecoin')]
    old = {'tasks': nodes, 'protected_evidence': []}
    before = {'tasks': {n['id']: {'attempts': [{}, {}, {}, {}]} for n in nodes}}
    reference = {'path': 'review.md', 'sha256': 'unchanged'}
    revision = {k: reference for k in ('review', 'baseline', 'local_review', 'population', 'qualification_inputs')}
    new = expected_program(old, before, revision, None, plan_reference=reference)
    table = {n['id']: n for n in new['tasks']}
    assert table['account-qualification']['requires'] == ['current-binding']
    for q in ('p10', 'p14', 'evidence', 'gatecoin'):
        node = table['acquire-' + q]
        assert node['requires'] == ['current-binding', 'account-qualification']
        assert node['maximum_attempts'] == 5
    assert old['tasks'] == nodes


@pytest.mark.parametrize('mutation', [None, 'grant', 'scope', 'predecessor', 'changed-bytes'])
def test_shared_service_scope_survives_multiple_bound_amendments(tmp_path, mutation):
    from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    def retain(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return evidence_file(path, tmp_path)
    original_review = {'path': 'original-review.md', 'sha256': 'original'}
    scope = retain('scope.json', {'grant_hash': 'grant', 'review': original_review})
    initial = {'phase_service_scope': scope, 'grant_hash': 'grant', 'review': original_review}
    first = retain('first.json', initial)
    middle = {**initial, 'review': {'path': 'middle.md', 'sha256': 'middle'},
        'predecessor': first, 'phase_service_predecessor': first}
    if mutation == 'grant':
        middle['grant_hash'] = 'changed'
    elif mutation == 'scope':
        middle['phase_service_scope'] = {**scope, 'sha256': 'changed'}
    elif mutation == 'predecessor':
        middle['predecessor'] = {**first, 'sha256': 'changed'}
    second = retain('second.json', middle)
    current = {**initial, 'review': {'path': 'new.md', 'sha256': 'new'},
        'predecessor': second, 'phase_service_predecessor': second}
    retain('current-binding.json', current)
    stage = retain('stage.json', {'service_scope': scope, 'grant_hash': 'grant'})
    retain('current-stage.json', stage)
    if mutation == 'changed-bytes':
        (tmp_path / 'first.json').write_text('{}')
    allowance = CampaignAllowance(tmp_path, {}, root=tmp_path)
    if mutation:
        with pytest.raises(LegalMathError):
            allowance.service_scope()
    else:
        assert allowance.service_scope()[0] == scope
