"""Source-authority010 regression through actual P1–P5 consumers."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/shell-source-chain-380'
BASE = AUTH / 'attempts/finance-conventions/attempt-013'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def same(left, right):
    assert digest(left) == digest(right)


def products(request, graph):
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)},
                      {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    return {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
            'P5': service.financial_product(p1, p2, p3)}


@pytest.fixture(scope='module')
def compared_products():
    path = AUTH / 'reviews/shell-maturity-361/global-plain-packet.json.gz'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == read(PREP / 'input-bindings.json')[str(path.relative_to(ROOT))]
    packet = read(path)
    legacy = products(packet['request'], packet['graph'])
    request = deepcopy(packet['request'])
    request['contract_source_chain'] = {'version': 'shell-contract-source-chain.v1'}
    return legacy, products(request, packet['graph'])


def rebind(values, payload):
    result = deepcopy(values)
    bundle = result['P1']['payload']['request']['bundle']
    result['P2'] = service.seal('P2', bundle, {'P1': result['P1']['sha256']}, payload)
    result['P3'] = service.seal('P3', bundle,
        {'P1': result['P1']['sha256'], 'P2': result['P2']['sha256']}, result['P3']['payload'])
    result['P4'] = service.seal('P4', bundle,
        {'P1': result['P1']['sha256'], 'P3': result['P3']['sha256']}, result['P4']['payload'])
    result['P5'] = service.seal('P5', bundle,
        {'P2': result['P2']['sha256'], 'P3': result['P3']['sha256']}, result['P5']['payload'])
    return result


def test_actual_consumer_preserves_complete_legacy_answer(compared_products):
    legacy, _ = compared_products
    answer = service.consume(legacy, ROOT, mode='frozen')
    same(answer, read(BASE / 'ordinary/global-plain-answer.json.gz'))
    same(legacy['P5'], read(BASE / 'ordinary/global-plain-P5.json.gz'))
    assert 'contract_source_chain' not in answer


def test_actual_consumer_delivers_review_and_preserves_questions(compared_products):
    legacy, reviewed = compared_products
    before = digest(reviewed)
    answer = service.consume(reviewed, ROOT, mode='frozen')
    baseline = read(BASE / 'ordinary/global-plain-answer.json.gz')
    same(answer['questions'], baseline['questions'])
    same(reviewed['P2']['payload']['assembly'], legacy['P2']['payload']['assembly'])
    same(reviewed['P5']['payload'], legacy['P5']['payload'])
    same(answer['contract_source_chain'], reviewed['P2']['payload']['contract_source_chain'])
    assert answer['mode'] == 'ASSISTED'
    assert answer['contract_source_chain']['legal_applicability_established'] is False
    assert answer['contract_source_chain']['trustee_history']['actual_succession_established'] is False
    assert digest(reviewed) == before


@pytest.mark.parametrize('defect', ['succession', 'publication', 'agreement', 'precedence',
                                   'false-as-zero', 'qualifier', 'omitted'])
def test_actual_consumer_refuses_rehashed_report(compared_products, defect):
    _, reviewed = compared_products
    payload = deepcopy(reviewed['P2']['payload'])
    report = payload['contract_source_chain']
    if defect == 'succession':
        report['trustee_history']['actual_succession_established'] = True
    elif defect == 'publication':
        report['edition_link']['historical_publication'] = '2020-08-13'
    elif defect == 'agreement':
        report['onward_documents'].pop()
    elif defect == 'precedence':
        report['precedence']['condition'] = 'ALWAYS'
    elif defect == 'false-as-zero':
        report['legal_applicability_established'] = 0
    elif defect == 'qualifier':
        report['sources']['conditions_and_agreements'].pop()
    else:
        payload.pop('contract_source_chain')
    with pytest.raises(ValueError, match='source-chain'):
        service.consume(rebind(reviewed, payload), ROOT, mode='frozen')


def test_actual_consumer_refuses_unsolicited_report(compared_products):
    legacy, reviewed = compared_products
    payload = deepcopy(legacy['P2']['payload'])
    payload['contract_source_chain'] = deepcopy(reviewed['P2']['payload']['contract_source_chain'])
    with pytest.raises(ValueError, match='source-chain'):
        service.consume(rebind(legacy, payload), ROOT, mode='frozen')
