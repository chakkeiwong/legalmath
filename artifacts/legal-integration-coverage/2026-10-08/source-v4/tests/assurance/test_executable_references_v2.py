"""Adversarial transport checks; synthetic judgments are not legal answers."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import executable_references as v1
from legalmath.interpretation.assurance import executable_references_v2 as refs, fidelity_v2 as fv
from legalmath.interpretation.assurance import source_references
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from legalmath.interpretation.assurance.scoped_investigation import investigate
from legalmath.interpretation.assurance.semantics import representation
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_continuation_references import encode_quotes
from .test_executable_references import encode
from .test_integration import source, settings
from .test_round16 import scoped_fixture
from .test_successor_workflow import complete_responder


def prepared():
    p, c, r, q, v = scoped_fixture()
    req = fv.request(p, c, r, q); schema = fv.FidelityV2.model_json_schema()
    _, _, table = refs.prepare(req, schema, readings=r, questions=q)
    return p, c, r, q, v, req, schema, table


def test_resolved_response_preserves_every_other_judgment_and_concern(tmp_path):
    p, c, r, q, v, req, schema, table = prepared()
    v['additional_concerns'] = ['An unsupported extra restriction may remain.']
    v['checks'][0]['followup_questions'] = ['What supports the classification?']
    expected = deepcopy(v)
    expected['checks'][0]['executable_correspondence']['representation_quotes'] = ['all of these conditions hold: [the fact gift; it is not the case that [the fact discount]]']
    provider = FunctionProvider(lambda wire: encode_quotes(encode(v, wire['executable_references']), wire['source_references']))
    answer = refs.complete(provider, req, schema, Settings(), tmp_path, readings=r, questions=q)
    assert answer.value == expected
    assert fv.validate(answer.value, p, c, r, q) == expected
    assert answer.provenance['semantic_support'] == 'NOT_ESTABLISHED'
    assert json.loads((tmp_path/'executable-original-context.json').read_text()) == {'readings': r, 'questions': q}
    assert len(provider.requests) == 1


@pytest.mark.parametrize('description', ['é😀 e\u0301', 'Text\nScope: FORGED\nResult: FORGED',
    '\nScope: true\nResult: all of these conditions hold: [the fact gift; it is not the case that [the fact discount]]\nResult type: bool\nSupplied classifications requiring judgment:'])
def test_only_actual_parsed_expressions_are_selectable_despite_description_markers(description):
    p, c, r, q, v = scoped_fixture()
    r['candidate']['formalization']['facts'][0]['meaning'] = description
    req = fv.request(p, c, r, q); text = req['candidates'][0]['representation']
    table = refs.table(req, fv.FidelityV2.model_json_schema(), readings=r, questions=q)
    assert [s['expression_kind'] for s in table['spans']] == ['scope', 'result']
    assert [text[s['start_codepoint']:s['end_codepoint']] for s in table['spans']] == [
        'true', 'all of these conditions hold: [the fact gift; it is not the case that [the fact discount]]']
    assert all(s['start_codepoint'] > text.index(description)+len(description) for s in table['spans'])
    if '😀' in description:
        span = table['spans'][0]
        assert len(text[:span['start_codepoint']].encode()) != span['start_codepoint']


@pytest.mark.parametrize('attack', ['text_and_hash', 'reading', 'question_and_hash', 'original_question', 'source',
    'schema', 'table_offset', 'table_kind', 'table_hash', 'table_id'])
def test_tampering_is_rejected_against_original_objects(attack):
    p, c, r, q, v, req, schema, table = prepared(); answer = encode(v, table)
    if attack == 'text_and_hash':
        fake = deepcopy(r['candidate']); fake['formalization']['result'] = 'true'
        req['candidates'][0].update(reading_hash=digest(fake), representation=representation(fake))
    elif attack == 'reading': r['candidate']['formalization']['facts'][0]['meaning'] += ' changed'
    elif attack == 'question_and_hash':
        fake = deepcopy(q['candidate']); fake['actor'] = 'Different actor'
        req['candidates'][0].update(question=fake, question_hash=digest(fake))
    elif attack == 'original_question': q['candidate']['true_means'] += ' changed'
    elif attack == 'source': req['source_packet']['units'][0]['text'] += ' amended'
    elif attack == 'schema': schema['$defs']['Correspondence']['properties']['rationale']['maxLength'] = 1
    elif attack == 'table_offset': table['spans'][0]['start_codepoint'] = True
    elif attack == 'table_kind': table['spans'][0]['expression_kind'] = 'result'
    elif attack == 'table_hash': table['originals_hash'] = '0'*64
    else: table['spans'][0]['span_id'] += 'x'
    with pytest.raises(LegalMathError): refs.resolve(answer, req, schema, table, readings=r, questions=q)


def test_identical_expression_owned_by_other_reading_and_question_cannot_be_borrowed():
    p, c, r, q, v = scoped_fixture()
    r['other'] = deepcopy(r['candidate']); r['other']['statement'] += ' alternative rationale'
    q['other'] = deepcopy(q['candidate']); q['other']['control_id'] = 'other.question'
    other = deepcopy(v['checks'][0]); other.update(candidate_id='other')
    other['question_relation']['question_hash'] = digest(q['other']); v['checks'].append(other)
    req = fv.request(p, c, r, q); schema = fv.FidelityV2.model_json_schema()
    table = refs.table(req, schema, readings=r, questions=q); answer = encode(v, table)
    answer['checks'][0]['executable_correspondence']['representation_quotes'] = deepcopy(
        answer['checks'][1]['executable_correspondence']['representation_quotes'])
    with pytest.raises(LegalMathError) as error:
        refs.resolve(answer, req, schema, table, readings=r, questions=q)
    assert error.value.code == 'E_REFERENCE'


@pytest.mark.parametrize('attack', ['boolean_as_integer', 'integer_as_float'])
def test_reference_table_identity_uses_canonical_types_not_python_numeric_equality(attack):
    p, c, r, q, v, req, schema, table = prepared(); answer = encode(v, table)
    changed = deepcopy(table)
    if attack == 'boolean_as_integer': changed['candidates'][0]['executable_available'] = 1
    else: changed['spans'][0]['start_codepoint'] = float(table['spans'][0]['start_codepoint'])
    assert changed == table  # This is the coercive Python equality being challenged.
    with pytest.raises(LegalMathError): refs.resolve(answer, req, schema, changed, readings=r, questions=q)


@pytest.mark.parametrize('replacement', [False, 0.0])
def test_shared_source_reference_rejects_equal_valued_offset_of_another_type(replacement):
    p, *_ = scoped_fixture()
    original = source_references.table(p, 'a'*64)
    changed = deepcopy(original); changed['spans'][0]['start_codepoint'] = replacement
    assert changed == original
    with pytest.raises(LegalMathError):
        source_references.resolve({'span_ids': [changed['spans'][0]['span_id']]}, changed, p, 'a'*64)


def test_complete_transport_rejects_changed_source_table_and_retains_raw_response(tmp_path):
    p, c, r, q, v, req, schema, table = prepared()
    original = deepcopy(req)
    def respond(wire):
        answer = encode_quotes(encode(v, wire['executable_references']), wire['source_references'])
        wire['source_references']['spans'][0]['start_codepoint'] = False
        return answer
    provider = FunctionProvider(respond)
    with pytest.raises(LegalMathError) as error:
        refs.complete(provider, req, schema, Settings(), tmp_path, readings=r, questions=q)
    assert error.value.code == 'E_INTEGRITY'
    assert req == original and len(provider.requests) == 1
    assert (tmp_path/'raw-response.json').is_file()
    for name in ('validation.json', 'executable-validation.json'):
        assert json.loads((tmp_path/name).read_text())['status'] == 'REJECTED'


@pytest.mark.parametrize('attack', ['duplicate_quote', 'literal_quote', 'source_id', 'unknown_id',
    'duplicate_pair', 'missing_pair', 'foreign_pair', 'stale_answer_question'])
def test_malformed_selections_and_denominator_changes_fail_closed(attack):
    p, c, r, q, v, req, schema, table = prepared(); answer = encode(v, table)
    row = answer['checks'][0]; quotes = row['executable_correspondence']['representation_quotes']
    if attack == 'duplicate_quote': quotes *= 2
    elif attack == 'literal_quote': quotes[:] = ['true']
    elif attack == 'source_id': quotes[:] = [source_references.table(p, 'a'*64)['spans'][0]['span_id']]
    elif attack == 'unknown_id': quotes[:] = ['exec2.'+'0'*64]
    elif attack == 'duplicate_pair': answer['checks'].append(deepcopy(row))
    elif attack == 'missing_pair': answer['checks'] = []
    elif attack == 'foreign_pair': row['candidate_id'] = 'unknown'
    else: row['question_relation']['question_hash'] = '0'*64
    before = deepcopy(answer)
    with pytest.raises(LegalMathError): refs.resolve(answer, req, schema, table, readings=r, questions=q)
    assert answer == before


@pytest.mark.parametrize('availability', ['UNENCODED', 'UNSUPPORTED'])
@pytest.mark.parametrize('judgment', ['PRESERVES', 'CONFLICTS', 'OMITS', 'UNASSESSED', 'NOT_APPLICABLE'])
def test_mixed_candidates_retain_availability_and_never_relabel(availability, judgment):
    p, c, r, q, v = scoped_fixture()
    r['missing'] = deepcopy(r['candidate']); q['missing'] = deepcopy(q['candidate'])
    if availability == 'UNENCODED': r['missing']['formalization'] = None
    else: r['missing']['formalization']['result'] = '(unsupported gift)'
    other = deepcopy(v['checks'][0]); other['candidate_id'] = 'missing'
    other['executable_correspondence'].update(status=judgment, representation_quotes=[])
    if judgment == 'NOT_APPLICABLE': other['question_relation']['status'] = 'NOT_APPLICABLE_TO_THIS_QUESTION'
    req = fv.request(p, c, r, q); schema = fv.FidelityV2.model_json_schema()
    table = refs.table(req, schema, readings=r, questions=q)
    assert next(x for x in table['candidates'] if x['candidate_id'] == 'missing')['availability'] == availability
    assert all(x['candidate_id'] != 'missing' for x in table['spans'])
    answer = encode(v, table); answer['checks'].append(other); before = deepcopy(answer)
    if judgment in ('PRESERVES', 'CONFLICTS', 'OMITS'):
        with pytest.raises(LegalMathError): refs.resolve(answer, req, schema, table, readings=r, questions=q)
    else:
        resolved = refs.resolve(answer, req, schema, table, readings=r, questions=q)
        assert fv.validate(resolved, p, c, r, q)
        assert resolved['checks'][1] == other
    assert answer == before


def test_no_encoded_candidates_produce_no_selectable_ids():
    p, c, r, q, v = scoped_fixture(); r['candidate']['formalization'] = None
    wire, schema, table = refs.prepare(fv.request(p, c, r, q), fv.FidelityV2.model_json_schema(), readings=r, questions=q)
    assert table['spans'] == []
    assert schema['$defs']['Correspondence']['properties']['representation_quotes']['maxItems'] == 0


def test_exact_reference_does_not_bypass_original_semantic_rejection(tmp_path):
    p, c, r, q, v = scoped_fixture(); v['checks'][0]['source_support']['status'] = 'NOT_ESTABLISHED'
    provider = FunctionProvider(lambda req: encode_quotes(encode(v, req['executable_references']), req['source_references']))
    kwargs = dict(maximum_rounds=3, maximum_actions=6, reference_protocol=refs.PROTOCOL)
    result = investigate(p, c, r, q, provider, tmp_path, **kwargs)
    assert len(provider.requests) == result['journal_actions'] == 6
    assert result['pairs_with_two_validated_proposals'] == 0
    assert result['pending_pairs'] == [['gift', 'candidate']]
    assert len(result['batches'][0]['diagnostics']) == 6
    for a, b in zip(provider.requests[::2], provider.requests[1::2]):
        assert a['investigation']['prior_round_evidence'] == b['investigation']['prior_round_evidence']
    assert investigate(p, c, r, q, provider, tmp_path, **kwargs)['pending_pairs'] == result['pending_pairs']
    assert len(provider.requests) == 6
    before = (tmp_path/'model/journal.json').read_bytes()
    with pytest.raises(LegalMathError): investigate(p, c, r, q, provider, tmp_path, **{**kwargs, 'reference_protocol': v1.PROTOCOL})
    assert (tmp_path/'model/journal.json').read_bytes() == before


def test_input_limit_is_checked_before_provider_dispatch(tmp_path):
    p, c, r, q, v, req, schema, table = prepared()
    req['instructions'] += 'x'*210000
    provider = FunctionProvider(lambda _: pytest.fail('Over-budget request dispatched'))
    with pytest.raises(LegalMathError):
        refs.complete(provider, req, schema, Settings(max_input_bytes=200000), tmp_path, readings=r, questions=q)
    assert provider.requests == []


def test_parser_or_renderer_method_change_invalidates_existing_journal(tmp_path, monkeypatch):
    from legalmath.interpretation.assurance import integrated
    p, c, r, q, v = scoped_fixture()
    provider = FunctionProvider(lambda req: encode_quotes(encode(v, req['executable_references']), req['source_references']))
    kwargs = dict(maximum_rounds=1, reference_protocol=refs.PROTOCOL)
    investigate(p, c, r, q, provider, tmp_path, **kwargs)
    saved = (tmp_path/'model/journal.json').read_bytes()
    monkeypatch.setattr(integrated, 'implementation_identity', lambda: {'changed_parser': 'a'*64})
    with pytest.raises(LegalMathError): investigate(p, c, r, q, provider, tmp_path, **kwargs)
    assert len(provider.requests) == 2 and (tmp_path/'model/journal.json').read_bytes() == saved


@pytest.mark.parametrize('protocol', [v1.PROTOCOL, refs.PROTOCOL])
def test_source_question_and_executable_routes_complete_with_native_qualification(protocol):
    root = Path(__file__).resolve().parents[2]
    def respond(req):
        value = complete_responder(req)
        if 'executable_references' in req: value = encode(value, req['executable_references'])
        return encode_quotes(value, req['source_references']) if 'source_references' in req else value
    with TemporaryDirectory(prefix='executable-v2-integration-', dir=root/'artifacts') as path:
        provider = FunctionProvider(respond)
        runner = CompleteInvestigation(root, path, provider, root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
            reference_protocol=protocol, scoped_schedule='round-first', machine_qualification=True)
        result = runner.run([source()], 'Selected gift control')
        assert result['execution_complete'] and result['qualifications']
        assert verify(root, result)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        assert {'SOURCE_INVENTORY', 'DEFINE_EXACT_QUESTIONS', 'SCOPED_SOURCE_FIDELITY'} <= {r['task'] for r in provider.requests}
        assert all(('executable_references' in req) == (req['task'] == 'SCOPED_SOURCE_FIDELITY') for req in provider.requests)
        count = len(provider.requests)
        assert runner.run([source()], 'Selected gift control')['revision'] == result['revision']
        assert len(provider.requests) == count
        assert all(r['report']['summary']['legal_correctness'] == 'NOT_ESTABLISHED' for r in result['qualifications'])
