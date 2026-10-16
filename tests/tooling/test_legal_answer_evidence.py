"""Actual v5 regressions and adversarial evidence-reference controls; zero calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import answer_evidence as evidence
from legalmath.interpretation.assurance.legal_locators import build_index, validate_citation
from scripts import legal_mission_answer_tools_recovery as old

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-12/answer-tools-repair'


def read(name):
    return json.loads((BASE / name).read_text())


def request():
    original = read('requests/baseline.review.json')
    return evidence.review_request(original, original['proposed_answer'])


def result(req):
    def field(r):
        if r.get('case_id'):
            return next(k for k, v in req['evidence']['fields'].items()
                        if v['role'] == 'CASE' and v['case_id'] == r['case_id'])
        return next(
            k for k, v in req['evidence']['fields'].items() if v['role'] == 'ANSWER' and v['question_id'] in r['question_ids'])
    packet = req['context'].get('source_packet')
    quote = [{'unit_id': packet['units'][0]['unit_id'], 'quote': packet['units'][0]['text']}] if packet else []
    return {'binding_hash': req['binding_hash'], 'verdict': 'PASS_WITH_LIMITS',
            'findings': [{'id': r['id'], 'status': 'PRESERVED', 'reason': 'Reference control only.',
                         'source_support': quote,
                         'references': [evidence.full_reference(req['evidence'], field(r))]}
                        for r in req['requirements']]}


def test_actual_old_validator_accepts_empty_preserved_quotes_but_new_rejects():
    raw = read('responses/baseline.review.json')['value']
    for row in raw['obligation_findings']:
        row['answer_quote'] = ''
    old.validate_review(raw, read('requests/baseline.review.json'))
    req = request(); new = result(req)
    new['findings'][0]['references'] = []
    with pytest.raises(LegalMathError):
        evidence.validate_review(new, req)


def test_actual_old_validator_accepts_cross_field_quote_but_span_cannot():
    req = read('requests/baseline.review.json')
    raw = read('responses/baseline.review.json')['value']
    fields = req['proposed_answer']['answers']
    raw['obligation_findings'][0]['answer_quote'] = fields[0]['answer'][-30:] + '\n' + fields[1]['answer'][:30]
    old.validate_review(raw, req)
    new = request(); fid = next(k for k, v in new['evidence']['fields'].items() if v['path'] == ['answers', 0, 'answer'])
    with pytest.raises(LegalMathError):
        evidence.resolve(new['answer'], new['evidence'], {'field_id': fid, 'start': len(fields[0]['answer']) - 30,
                                                        'end': len(fields[0]['answer']) + 31})


@pytest.mark.parametrize('fault', ['empty', 'negative', 'bool', 'foreign', 'changed_answer', 'catalog'])
def test_reference_controls(fault):
    req = request(); row = result(req)['findings'][0]['references'][0]
    if fault == 'empty': row['end'] = 0
    if fault == 'negative': row['start'] = -1
    if fault == 'bool': row['start'] = False
    if fault == 'foreign': row['field_id'] = 'missing'
    if fault == 'changed_answer': req['answer']['answers'][0]['answer'] += ' altered'
    if fault == 'catalog': req['evidence']['fields'][row['field_id']]['text'] += ' altered'
    with pytest.raises(LegalMathError):
        evidence.resolve(req['answer'], req['evidence'], row)


def test_qualifications_can_be_cited_but_do_not_alone_establish_preservation():
    req = request(); value = result(req)
    fid = next(k for k, v in req['evidence']['fields'].items() if v['role'] == 'QUALIFICATION')
    value['findings'][0]['references'] = [evidence.full_reference(req['evidence'], fid)]
    with pytest.raises(LegalMathError): evidence.validate_review(value, req)
    value['findings'][0]['status'] = 'UNRESOLVED'; value['verdict'] = 'UNRESOLVED'
    evidence.validate_review(value, req)


def test_verdict_cannot_hide_wrong_case_or_question_and_cases_stay_separate():
    answer = read('responses/baseline.answer.json')['value']
    case = answer['case_assessments'][0]
    req = evidence.review_request({}, answer, [{'id': case['case_id'], 'kind': 'case', 'case_id': case['case_id']}])
    fid = next(k for k, v in req['evidence']['fields'].items() if v['role'] == 'ANSWER')
    value = {'binding_hash': req['binding_hash'], 'verdict': 'PASS_WITH_LIMITS',
             'findings': [{'id': case['case_id'], 'status': 'PRESERVED', 'reason': 'Control',
                           'source_support': [], 'references': [evidence.full_reference(req['evidence'], fid)]}]}
    with pytest.raises(LegalMathError): evidence.validate_review(value, req)
    value['findings'][0].update(status='WRONG', references=[])
    with pytest.raises(LegalMathError): evidence.validate_review(value, req)
    value['verdict'] = 'REPAIR_REQUIRED'
    evidence.validate_review(value, req)


def test_unicode_and_repeated_text_use_exact_field_coordinates():
    answer = {'answers': [{'question_id': 'p14', 'answer': '要求 α 要求 α'}]}
    cat = evidence.catalog(answer); fid = next(iter(cat['fields']))
    assert evidence.resolve(answer, cat, {'field_id': fid, 'start': 5, 'end': 9})['quote'] == '要求 α'


def source_index():
    packet = read('common.json')['source_packet']
    path = ROOT / 'docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json'
    doc = json.loads(path.read_text())
    ids = [u['unit_id'] for u in packet['units'] if u['unit_id'].startswith('d3b41d4d7e61c.')]
    return packet, build_index(packet, doc['html'], source_ref={'path': str(path.relative_to(ROOT)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, unit_ids=ids)


def test_retained_p19_p20_and_footnote_attachment_are_source_bound():
    packet, index = source_index()
    unit = next(u for u in packet['units'] if 'at least one competent staff' in u['text'])
    validate_citation(packet, index, unit_id=unit['unit_id'], quote='at least one competent staff', locator='P19')
    with pytest.raises(LegalMathError):
        validate_citation(packet, index, unit_id=unit['unit_id'], quote='at least one competent staff', locator='P20')
    assert {'from': 'P14', 'to': 'FN5'} in index['footnote_links']
    assert {'from': 'P10', 'to': 'FN1'} in index['footnote_links']
    para11 = next(r['text'] for r in index['records'] if r['locator'] == 'P11')
    # Typography is not an authority for deleting substantive source text.
    assert 'proper record' in para11.lower()


def test_explicit_list_numbering_and_ambiguous_restarts():
    packet = {'units': [{'unit_id': 'u', 'text': 'Staff.'}]}
    index = build_index(packet, '<ol start="19"><li>Staff.</li><li value="23">End.</li></ol>', source_ref={}, unit_ids=['u'])
    assert index['units']['u']['locators'] == ['P19']
    with pytest.raises(LegalMathError):
        build_index(packet, '<ol><li>A</li></ol><ol><li>B</li></ol>', source_ref={}, unit_ids=['u'])
