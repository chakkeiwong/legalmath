from copy import deepcopy
from pathlib import Path
import json
import pytest
from jsonschema import validate as validate_schema, ValidationError
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased import account_contract, group_review
from tests.assurance.test_bounded_product import envelope, limits, Scripted


@pytest.mark.parametrize('mutation', [None, 'numbered-prose', 'foreign-quote'])
def test_provider_schema_simplification_keeps_local_account_vetoes(tmp_path, mutation):
    class Provider(Scripted):
        def complete(self, request, schema, settings):
            assert 'pattern' not in schema['$defs']['AccountProse']
            result = super().complete(request, schema, settings)
            if mutation == 'numbered-prose':
                result.value['conclusion'] = 'Paragraph 10 proves compliance.'
            elif mutation == 'foreign-quote':
                result.value['support'][0]['quote'] = 'Invented legal source.'
            return result
    product = BoundedProduct(tmp_path, tmp_path / 'account', Provider(), envelope(), list,
        limits=limits(), requirement_account_profile=account_contract.PROFILE)
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    result = product.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', envelope()['original_questions'][0],
        records, {'assignment': 'Preserve the exception.'}, ['o1'])
    assert result['status'] == ('VALIDATED' if mutation is None else 'FAILED')


def decision(locators):
    return {'analyses': [{'analysis_id': 'a', 'decision': {'verdict': 'UNRESOLVED',
        'reason': 'The incorporated schedule is needed.', 'support': [], 'issues': ['Missing schedule.'],
        'source_gaps': [], 'assertion_bindings': [], 'context_needs': [{'kind': 'SOURCE_TEXT',
            'reason': 'Need the priority terms.', 'record_ids': [], 'locators': locators,
            'query': 'The incorporated emergency schedule'}]}}],
        'assignments': {'item': {'analysis_id': 'a'}}}


def test_context_schema_rejects_fake_document_but_allows_textual_need():
    value = decision([{'index_hash': 'NO_INDEXED_SOURCE_AVAILABLE', 'locator': 'P14'}])
    validate_schema(value, group_review.schema(['item']))  # Historical schema unchanged.
    with pytest.raises(ValidationError):
        validate_schema(value, group_review.schema(['item'], legal_indexes=[]))
    validate_schema(decision([]), group_review.schema(['item'], legal_indexes=[]))
    indexes = [{'index_hash': 'actual-document'}]
    with pytest.raises(ValidationError):
        validate_schema(value, group_review.schema(['item'], legal_indexes=indexes))
    value['analyses'][0]['decision']['context_needs'][0]['locators'][0]['index_hash'] = 'actual-document'
    validate_schema(value, group_review.schema(['item'], legal_indexes=indexes))
    from legalmath.interpretation.assurance.bounded_product import TEXT
    assert TEXT == {'type': 'string', 'minLength': 1}
    assert 'enum' not in group_review.schema(['item'])['$defs']['Decision']['properties']['reason']


def test_strict_historical_account_and_review_schemas_unchanged():
    root = Path(__file__).resolve().parents[2]
    work = root / 'artifacts/legal-mission-control/2026-10-15/account-continuation/live'
    actual = json.loads((work / 'account-qualification/largest-actual/calls/account-protocol/schema.json').read_text())
    assert account_contract.schema() == actual
    simplified = account_contract.provider_schema()
    simplified['$defs']['AccountProse']['pattern'] = account_contract.PROSE_PATTERN
    assert simplified == actual
    folder = next((work / 'reviewer-qualification/calls').glob('supported-*'))
    request = json.loads((folder / 'request.json').read_text())
    assert group_review.schema(request['required_considered']) == json.loads((folder / 'schema.json').read_text())


def test_new_master_revision_never_increases_acquisition_attempts():
    from scripts.legal_integration_master import task
    from scripts.legal_integration_schema_repair import expected_program, REOPEN
    nodes = [task(t, agent=t in ('semantic-preflight', 'account-qualification')) for t in REOPEN]
    nodes += [task('acquire-p14', ['account-qualification'], agent=True)]
    nodes[-1]['maximum_attempts'] = 5
    old = {'tasks': nodes, 'protected_evidence': []}
    before = {'tasks': {n['id']: {'attempts': [{}, {}, {}, {}]} for n in nodes}}
    pointer = {'path': 'evidence', 'sha256': 'retained'}
    revision = {k: pointer for k in ('review', 'baseline', 'local_review', 'qualification_inputs', 'positive_replay')}
    result = expected_program(old, before, revision, None, plan_reference=pointer)
    assert result['tasks'][-1] == nodes[-1]
    assert result['tasks'][2]['requires'] == []  # No reviewer dependency added.
    assert old['tasks'] == nodes


def test_schema_revision_uses_new_output_and_preserves_source_root(monkeypatch):
    from scripts import legal_integration_phased_live as live
    from scripts.legal_integration_schema_repair import WORK
    assert live.active_live({'response_schema_repair': {}, 'account_capacity_repair': {'active': True}}) != WORK / 'live'
    assert live.active_live({'response_schema_repair': {'active': True}}) == WORK / 'live'
    assert live.LIVE != WORK / 'live'
