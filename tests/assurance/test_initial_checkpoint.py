from copy import deepcopy
import json

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from tests.assurance.test_bounded_product import Scripted, envelope, limits


def initial(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'initial', provider, envelope(), list, limits=limits())
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    result = product.note('answer-p14', 'ANSWER_ORIGINAL_QUESTION', 'Question', records, None, [])
    path = tmp_path/'checkpoint.json'
    directory = product.directory/'calls'
    manifest = {'profile': 'bounded-initial-checkpoint.v1', 'input_hash': product.route.input_hash,
        'dispatch': evidence_file(directory/'dispatch.json', tmp_path), 'calls': {'answer-p14': {
            k: evidence_file(directory/'answer-p14'/(k+'.json'), tmp_path)
            for k in ('request','schema','result')}}}
    save(path, manifest)
    return product, result, records, path, manifest


def test_only_exact_initial_response_is_reused_and_correction_review_is_fresh(tmp_path):
    _, result, records, path, _ = initial(tmp_path)
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'fresh', provider, envelope(), list, limits=limits(),
        retained_initial=evidence_file(path, tmp_path))
    actual = product.note('answer-p14', 'ANSWER_ORIGINAL_QUESTION', 'Question', records, None, [])
    assert actual == result and not provider.requests
    state = json.loads((product.directory/'calls/dispatch.json').read_text())
    assert 'NOT_A_NEW_MODEL_SAMPLE' in state['calls']['answer-p14']['retained_initial']['evidence_class']
    product.note('corrected-audit-source-p14-0', 'AUDIT_ANSWER_AGAINST_SOURCE', 'Question',
        records, result['value'], [r['id'] for r in records], audit=True)
    assert len(provider.requests) == 1


@pytest.mark.parametrize('mutation', ['request', 'model', 'source', 'result', 'uncertain', 'correction', 'missing'])
def test_retained_mutation_or_unsupported_replay_refuses_without_live_call(tmp_path, mutation):
    original, result, records, path, manifest = initial(tmp_path)
    provider = Scripted()
    source = envelope()
    question = 'Question changed' if mutation == 'request' else 'Question'
    if mutation == 'model':
        provider.routing = {'model': 'new-model'}
    if mutation == 'source':
        source['source_packet']['units'][0]['text'] += ' Changed rule.'
    if mutation == 'result':
        changed = deepcopy(result); changed['value']['conclusion'] = 'Changed answer.'
        save(tmp_path/manifest['calls']['answer-p14']['result']['path'], changed)
    if mutation == 'uncertain':
        p = tmp_path/manifest['dispatch']['path']; state = json.loads(p.read_text())
        state['calls']['answer-p14']['status'] = 'RESERVED'; save(p,state)
        manifest['dispatch'] = evidence_file(p,tmp_path); save(path,manifest)
    if mutation == 'correction':
        manifest['calls']['corrected-audit-source-p14-0'] = manifest['calls']['answer-p14']
        save(path,manifest)
    if mutation == 'missing':
        manifest['calls'].clear()
        save(path,manifest)
    product = BoundedProduct(tmp_path, tmp_path/'fresh', provider, source, list, limits=limits(),
        retained_initial=evidence_file(path, tmp_path))
    with pytest.raises(LegalMathError):
        product.note('answer-p14', 'ANSWER_ORIGINAL_QUESTION', question, records, None, [])
    assert not provider.requests
