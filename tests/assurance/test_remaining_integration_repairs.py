from copy import deepcopy
from dataclasses import replace
import json

import pytest

from legalmath.canonical import canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.legal_locators import build_index
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def indexed_product(tmp_path):
    original = envelope()
    packet = original['source_packet']
    indexes = []
    for unit in packet['units']:
        path = tmp_path / (unit['unit_id'] + '.html')
        path.write_text('<ol start="10"><li>' + unit['text'] + '</li></ol>')
        indexes.append(build_index(packet, path.read_text(), source_ref=evidence_file(path, tmp_path),
                                   unit_ids=[unit['unit_id']], root=tmp_path))
    original['legal_indexes'] = indexes
    return BoundedProduct(tmp_path, tmp_path/'p', Scripted(), original, list, limits=limits()), indexes


def test_assertion_cannot_borrow_paragraph_from_other_document_or_other_field(tmp_path):
    product, indexes = indexed_product(tmp_path)
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    quote = {'record_id': records[0]['id'], 'quote': records[0]['text'], 'locator': 'P10'}
    value = {'conclusion': 'Paragraph 10 conditions the duty on a request.', 'support': [quote],
             'assertion_bindings': [{'path': '/conclusion', 'index_hash': indexes[0]['index_hash'], 'citation': quote}]}
    product.citations(value, records)
    wrong = deepcopy(value)
    wrong['assertion_bindings'][0]['index_hash'] = indexes[1]['index_hash']
    with pytest.raises(LegalMathError): product.citations(wrong, records)
    wrong = deepcopy(value)
    wrong['alternatives'] = [{'condition': 'Paragraph 10 establishes an unconditional duty.'}]
    with pytest.raises(LegalMathError) as caught: product.citations(wrong, records)
    assert 'document/proposition' in caught.value.details
    wrong = deepcopy(value); wrong['assertion_bindings'] = []
    with pytest.raises(LegalMathError): product.citations(wrong, records)


class DependencyProvider(Scripted):
    def complete(self, request, schema, settings):
        result = super().complete(request, schema, settings)
        if request['task'] == 'READ_SOURCE':
            for row in result.value['records']:
                row['open_dependencies'] = ['Does the remote consent exception defeat the duty?']
        return result


def test_discovered_dependency_retrieves_remote_source_and_reaches_interaction_review(tmp_path):
    provider = DependencyProvider()
    product = BoundedProduct(tmp_path, tmp_path/'p', provider, envelope(), list, limits=limits())
    investigation = product.investigate()
    assert len(investigation['discovered_dependencies']) == 2  # two readers deduplicated
    resolution = [r for r in provider.requests if r['task'] == 'RESOLVE_SOURCE_DEPENDENCY']
    assert resolution and all({r['unit_id'] for r in req['records']} == {'source.a', 'source.b'} for req in resolution)
    assert all(row['disposition'] == 'UNRESOLVED' for row in investigation['discovered_dependencies'])
    answer = product.answer(investigation)
    assert any(r['task'] == 'AUDIT_WITHIN_QUESTION_DEPENDENCY' for r in provider.requests)
    assert not answer['all_question_reviews_accepted']


def test_dependency_limit_retains_every_unprocessed_dependency(tmp_path):
    provider = DependencyProvider()
    product = BoundedProduct(tmp_path, tmp_path/'p', provider, envelope(), list,
                             limits=replace(limits(), dependency_requests=1))
    result = product.investigate()
    assert len(result['discovered_dependencies']) == 2
    assert sum(r['result']['status'] == 'FAILED' for r in result['discovered_dependencies']) == 1
    assert result['question_acquisition_complete']['p14']  # conditional work remains possible


def test_compact_wire_and_expanded_quotes_have_separate_bounds_and_next_input_is_compacted(tmp_path):
    class ReferenceProvider:
        live = False
        reference_transport = True
        def complete(self, request, schema, settings):
            full = max(request['response_spans'], key=lambda row: row['end_codepoint'] - row['start_codepoint'])
            return Completion({'conclusion': 'Conditional.', 'support': [{'span_id': full['span_id']}] * 12,
                'contrary': [], 'assumptions': [], 'unresolved': ['Unknown facts.'], 'alternatives': [],
                'considered': [], 'source_gaps': [], 'assertion_bindings': []}, {})
    original = envelope()
    original['source_packet']['units'][0]['text'] = 'Unique passage with a remote exception. ' * 25 + 'End.'
    lim = replace(limits(), chunk_tokens=2000, overlap_tokens=100, output_bytes=2000,
                  output_tokens=2000, decoded_output_bytes=30000, decoded_output_tokens=30000,
                  input_tokens=40000)
    product = BoundedProduct(tmp_path, tmp_path/'p', ReferenceProvider(), original, list, limits=lim)
    record = next(r for r in product.route.records.values() if r['kind'] == 'source')
    result = product.note('expanded', 'ANSWER_ORIGINAL_QUESTION', original['original_questions'][0], [record], None, [])
    assert result['status'] == 'VALIDATED'
    assert result['output_measurement']['decoded_bytes'] > lim.output_bytes
    request = product.request('AUDIT_ANSWER_AGAINST_SOURCE', 'Question', [record], payload=result['value'])
    prepared = prepare(request, NOTE)
    assert len(canonical(prepared['request'])) < len(canonical(request))
    assert prepared['request']['payload']['support'][0]['quote']['source_slice']['start_codepoint'] == 0
    limited = BoundedProduct(tmp_path, tmp_path/'small', ReferenceProvider(), original, list,
                              limits=replace(lim, decoded_output_bytes=3000))
    failed = limited.note('expanded', 'ANSWER_ORIGINAL_QUESTION', 'Question', [record], None, [])
    assert failed['status'] == 'FAILED' and failed['error'] == 'E_RESOURCE_LIMIT'


def test_correction_requires_valid_adverse_review_and_preserves_original(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'p', provider, envelope(), list, limits=limits(), maximum_corrections=1)
    record = next(r for r in product.route.records.values() if r['kind'] == 'source')
    answer = product.note('original', 'ANSWER_ORIGINAL_QUESTION', 'Question', [record], None, [])
    rejected = {'status': 'VALIDATED', 'value': {'verdict': 'REJECT', 'issues': ['The condition was lost.'],
                  'support': answer['value']['support']}}
    before = len(provider.requests)
    same, _, details = product.correct_answer('p14', 'Question', answer,
        [rejected, {'status': 'FAILED'}], [], [])
    assert same == answer and details['status'] == 'NOT_ATTEMPTED' and len(provider.requests) == before
    candidate, reviews, retained = product.correct_answer('p14', 'Question', answer, [rejected], [], [])
    assert retained['original_answer'] == answer and retained['original_reviews'] == [rejected]
    assert len([r for r in provider.requests if r['task'] == 'CORRECT_REVIEWED_ANSWER']) == 1
    assert reviews and all(r['value']['verdict'] == 'UNRESOLVED' for r in reviews)
    assert (tmp_path/'p/correction-p14-original.json').exists()


def test_native_content_identity_changes_on_edit_addition_and_deletion(tmp_path):
    from scripts.legal_native_identity import content_identity
    (tmp_path/'package.py').write_text('version = 1')
    baseline = content_identity([tmp_path])
    (tmp_path/'package.py').write_text('version = 2')
    changed = content_identity([tmp_path]); assert changed != baseline
    (tmp_path/'extra.py').write_text('new module')
    added = content_identity([tmp_path]); assert added != changed
    (tmp_path/'extra.py').unlink()
    assert content_identity([tmp_path]) == changed


def test_reviewed_requirement_overlay_adds_p14_without_rewriting_original(tmp_path):
    original = envelope()
    original['original_questions'].append({'question_id': 'p10', 'text': 'Responsibility'})
    original['answer_acceptance']['acceptance_obligations'][0]['question_ids'] = ['p10']
    original['requirement_question_ids'] = {'obligation:o1': ['p10', 'p14']}
    product = BoundedProduct(tmp_path, tmp_path/'p', Scripted(), original, list, limits=limits())
    obligation = product.route.records['obligation:o1']
    assert product.applicable(obligation, 'p14') and product.applicable(obligation, 'p10')
    assert obligation['value']['question_ids'] == ['p10']
    product.route.envelope['requirement_question_ids']['obligation:o1'] = ['p14']
    with pytest.raises(LegalMathError): product.requirement_questions(obligation)


def test_full_wire_measurement_splits_readings_without_losing_records(tmp_path, monkeypatch):
    product = BoundedProduct(tmp_path, tmp_path/'p', Scripted(), envelope(), list,
        limits=replace(limits(), records_per_request=8))
    measure = product.dispatch.measure
    def framed(request, schema):
        if len(request.get('records', [])) > 1:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Reference table exceeds wire budget')
        return measure(request, schema)
    monkeypatch.setattr(product.dispatch, 'measure', framed)
    packets, blocked = product.reading_packets()
    assert not blocked
    for reader in ('reader-1', 'reader-2'):
        ids = [r['id'] for p in packets if p['request']['reader'] == reader for r in p['request']['records']]
        assert set(ids) == {r['id'] for r in product.route.records.values() if r['kind'] == 'source'}
        assert len(ids) == len(set(ids))
    assert all(len(p['request']['records']) == 1 for p in packets)
