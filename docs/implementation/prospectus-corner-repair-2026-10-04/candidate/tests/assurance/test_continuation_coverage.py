from copy import deepcopy
import json

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import single_reader as sr
from legalmath.interpretation.assurance.issue_limits import IssueLimits
from tests.search.support import FunctionProvider
from .test_round16 import scoped_fixture
from .test_continuation_references import encode_quotes


def fixture():
    p, _, r, q, _ = scoped_fixture()
    for i, text in enumerate(['Except the\u00a0following class.', 'Footnote: the exception has a condition.',
                              'Table continues: a second duty.', 'Annex: the old edition is superseded.']):
        p['units'].append({'unit_id': 'unit.'+str(i), 'text': text, 'locator': 'structural fixture', 'span': None, 'normative': True})
    other = {**deepcopy(q['candidate']), 'control_id': 'second.duty', 'question': 'Has the second duty been performed?',
             'source_evidence': [{'unit_id': p['units'][-1]['unit_id'], 'quote': p['units'][-1]['text']}]}
    interpretation = {'reading': r['candidate'], 'reading_question_id': q['candidate']['control_id'],
                      'questions': [q['candidate'], other], 'uncertainty': ['Question inventory is a proposed interpretation.']}
    return p, interpretation


def response(packet, interpretation, *, revise=False):
    def respond(req):
        task = req['task']; current = req.get('interpretation', interpretation)
        evidence = lambda unit: {'unit_id': unit['unit_id'], 'quote': unit['text']}
        if task == 'SINGLE_INTERPRETATION': value = interpretation
        elif task == 'SINGLE_UNIT_COVERAGE':
            units = [u for u in packet['units'] if u['unit_id'] in req['required_unit_ids']]
            value = {'packet_hash': digest(packet), 'interpretation_hash': digest(current), 'units': [
                {'unit_id': u['unit_id'], 'disposition': 'QUESTIONS', 'question_ids': [current['questions'][0]['control_id']],
                 'related_unit_ids': [packet['units'][-1]['unit_id']], 'evidence': [evidence(u)],
                 'rationale': 'Synthetic boundary dependency remains visible.'} for u in units],
                'concerns': [{'concern_id': 'concern.'+str(i), 'question_ids': [current['questions'][1]['control_id']],
                    'related_unit_ids': [u['unit_id'], packet['units'][0]['unit_id']] if u != packet['units'][0] else [u['unit_id']],
                    'evidence': [evidence(u)], 'explanation': 'Keep the exception, second question and edition uncertainty.'}
                    for i, u in enumerate(units)]}
        else:
            new = None
            if revise and 'revision' not in current['reading']['assumptions']:
                new = deepcopy(current); new['reading']['assumptions'].append('revision')
            value = {'packet_hash': digest(packet), 'interpretation_hash': digest(current),
                'coverage_hash': digest(req['coverage']),
                'concerns': [{'concern_id': c['concern_id'], 'status': 'RETAINED_UNRESOLVED', 'evidence': [],
                              'rationale': 'Unresolved fixture qualification.'} for c in req['coverage']['concerns']],
                'questions': [{'question_id': q['control_id'], 'question_hash': digest(q),
                               'status': 'EXECUTABLE_PROPOSAL' if q['control_id'] == current['reading_question_id'] else 'UNRESOLVED',
                               'rationale': 'The single expression only proposes an answer to its exact question.'} for q in current['questions']],
                'revised_interpretation': new, 'remaining_uncertainty': ['No source entailment was established by this fixture.']}
        return encode_quotes(value, req['source_references'])
    return respond


def test_split_complete_source_and_reconcile_all_cross_piece_concerns(tmp_path):
    p, i = fixture(); provider = FunctionProvider(response(p, i))
    result = sr.run(p, provider, tmp_path, maximum_units=2)
    assert result['execution_complete'] and len(provider.requests) == 5
    assert [r['unit_id'] for r in result['coverage'][0]['units']] == [u['unit_id'] for u in p['units']]
    assert len(result['reconciliations'][0]['concerns']) == len(p['units'])
    assert result['reconciliations'][0]['questions'][1]['status'] == 'UNRESOLVED'
    assert all(r['source_packet'] == p for r in provider.requests)
    assert result['legal_correctness'] == 'NOT_ESTABLISHED'
    sr.run(p, provider, tmp_path, maximum_units=2)
    assert len(provider.requests) == 5


def test_revision_invalidates_every_coverage_piece_and_preserves_old_reading(tmp_path):
    p, i = fixture(); provider = FunctionProvider(response(p, i, revise=True))
    result = sr.run(p, provider, tmp_path, maximum_units=2)
    assert result['execution_complete'] and len(result['interpretations']) == 2
    assert len(provider.requests) == 9
    assert result['coverage'][0]['interpretation_hash'] != result['coverage'][1]['interpretation_hash']
    assert 'revision' not in result['interpretations'][0]['reading']['assumptions']
    assert all(r['status'] == 'RETAINED_UNRESOLVED' for r in result['reconciliations'][1]['concerns'])


def test_compacted_transport_keeps_original_output_identity_and_every_source_text(tmp_path):
    p,i=fixture();provider=FunctionProvider(response(p,i))
    result=sr.run(p,provider,tmp_path,maximum_units=2,transport_profile='compact-locators.v2')
    assert result['execution_complete']
    for req in provider.requests:
        assert req['output_identity_contract']['packet_hash']==digest(p)
        assert req['source_references']['packet_hash']==digest(req['source_packet'])
        if 'interpretation' in req:
            assert req['output_identity_contract']['question_hashes'] == {
                q['control_id']: digest(q) for q in req['interpretation']['questions']}
        assert [(u['unit_id'],u['text'],u['normative']) for u in req['source_packet']['units']]==[
            (u['unit_id'],u['text'],u['normative']) for u in p['units']]
    assert result['coverage'][0]['packet_hash']==digest(p)
    assert result['reconciliations'][0]['coverage_hash']==digest(result['coverage'][0])


def test_transport_hash_cannot_replace_original_packet_identity(tmp_path):
    p,i=fixture();base=response(p,i)
    def wrong(req):
        value=base(req)
        if req['task']=='SINGLE_UNIT_COVERAGE':value['packet_hash']=req['source_references']['packet_hash']
        return value
    result=sr.run(p,FunctionProvider(wrong),tmp_path,transport_profile='compact-locators.v2')
    assert not result['execution_complete'] and result['stopped']['error']=='E_REFERENCE'
    assert not result['coverage']


def test_actual_263_unit_source_initial_request_fits_without_dropping_text():
    from pathlib import Path
    from legalmath.canonical import canonical
    root=Path(__file__).resolve().parents[2]
    tasks=json.loads((root/'artifacts/assurance-successor/2026-09-28/study-source-freeze.json').read_text())['tasks']
    p=next(t['packet'] for t in tasks if len(t['packet']['units'])==263)
    request={'source_packet':p,'task':'SINGLE_INTERPRETATION','instructions':sr.CONVENTION+sr.GRAMMAR}
    compact=sr.transport_request(request,'compact-locators.v2')
    wire,_,_=sr.source_references.prepare(compact,sr.Interpretation.model_json_schema())
    assert len(canonical(wire))<200000
    assert [(u['unit_id'],u['text']) for u in wire['source_packet']['units']]==[(u['unit_id'],u['text']) for u in p['units']]
    assert wire['output_identity_contract']['packet_hash']==digest(p)


@pytest.mark.parametrize('mutation', ['unit_missing', 'unit_duplicate', 'source', 'reading', 'concern_missing',
    'question_missing', 'wrong_question', 'question_hash', 'coverage_hash', 'relabel_question'])
def test_detached_coverage_and_same_type_question_substitution_rejected(tmp_path, mutation):
    p, i = fixture(); provider = FunctionProvider(response(p, i)); out = tmp_path/'source'
    result = sr.run(p, provider, out, maximum_units=2)
    cov = deepcopy(result['coverage'][0]); global_value = deepcopy(result['reconciliations'][0])
    pieces = json.loads((out/'coverage-revision-0.json').read_text())
    if mutation == 'unit_missing': pieces[0]['units'].pop()
    elif mutation == 'unit_duplicate': pieces[0]['units'][1] = deepcopy(pieces[0]['units'][0])
    elif mutation == 'source': p['units'][0]['text'] += ' Amendment'
    elif mutation == 'reading': i['reading']['statement'] += ' Changed question'
    elif mutation == 'concern_missing': global_value['concerns'].pop()
    elif mutation == 'question_missing': global_value['questions'].pop()
    elif mutation == 'wrong_question': global_value['questions'][1]['status'] = 'EXECUTABLE_PROPOSAL'
    elif mutation == 'question_hash': global_value['questions'][0]['question_hash'] = '0'*64
    elif mutation == 'coverage_hash': global_value['coverage_hash'] = '0'*64
    else:
        global_value['revised_interpretation'] = deepcopy(i)
        global_value['revised_interpretation']['questions'][0]['question'] = 'Another Boolean question'
    with pytest.raises(LegalMathError):
        sr.merge_coverage(p, i, cov['partition'], pieces)
        sr.validate_reconciliation(global_value, p, i, cov)


def test_reading_revision_ceiling_never_reports_stale_coverage_complete(tmp_path):
    p, i = fixture(); provider = FunctionProvider(response(p, i, revise=True))
    result = sr.run(p, provider, tmp_path, maximum_units=2, maximum_revisions=1)
    assert not result['execution_complete'] and len(result['remaining_units']) == len(p['units'])
    assert result['stopped']['error'] == 'E_RESOURCE_LIMIT'


def test_repartition_cannot_replenish_source_issue_spending_or_deadline(tmp_path, monkeypatch):
    limits = IssueLimits(tmp_path/'limits.json', {'source': 'unchanged'})
    for _ in range(3): limits.reserve(['a', 'b'], 'a'*64)
    with pytest.raises(LegalMathError): limits.reserve(['b'], 'b'*64)
    assert limits.report()['b']['spent'] == 3
    limits.reserve(['unrelated'], 'c'*64)
    import legalmath.interpretation.assurance.issue_limits as module
    now = limits.report()['unrelated']['started_ms']
    monkeypatch.setattr(module.time, 'time_ns', lambda: (now + 86400001)*1000000)
    with pytest.raises(LegalMathError): limits.reserve(['unrelated'], 'd'*64)


def test_inherited_exhausted_issue_is_not_reset_by_new_response_protocol(tmp_path):
    limits = IssueLimits(tmp_path/'limits.json', {'source': 'same'}, inherited={
        'unit': {'spent': 3, 'started_ms': 0, 'evidence_hash': 'a'*64}})
    with pytest.raises(LegalMathError): limits.reserve(['unit'], 'b'*64)
    assert limits.report()['unit']['spent'] == 3
