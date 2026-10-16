from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.acquisition import plan, recover
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def setup(tmp_path):
    from dataclasses import replace
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'old', provider, envelope(), list,
        limits=replace(limits(), records_per_request=2))
    prior = product.investigate()
    index = next(i for i,o in enumerate(prior['outputs']) if o['request']['task'] == 'READ_SOURCE')
    prior['outputs'][index]['result'] = {'status':'FAILED','error':'RuntimeError','reason':'invalid_request'}
    # Rebuild dependencies from the retained successful reading occurrences.
    product2 = BoundedProduct(tmp_path, tmp_path/'baseline', provider, envelope(), list,
        limits=replace(limits(), records_per_request=2))
    prior['discovered_dependencies'] = product2.resolve_dependencies(prior['outputs'])
    return provider, product, prior, index


def test_failed_source_redesign_retains_every_source_and_old_failure(tmp_path):
    provider, original, prior, index = setup(tmp_path)
    new = BoundedProduct(tmp_path,tmp_path/'recovery',provider,envelope(),list,limits=original.route.limits)
    packets, _ = plan(new, prior)
    assert len(packets) == 2
    assert {r['id'] for p in packets for r in p['packet']['request']['records']} == {
        r['id'] for r in prior['outputs'][index]['request']['records']}
    result = recover(new, prior, admit=lambda name,count:{'name':name,'count':count},
                     implementation_identity='fixture')
    assert result['outputs'][:len(prior['outputs'])] == prior['outputs']
    assert result['question_acquisition_complete']['p14']
    calls = len(provider.requests)
    assert recover(new, prior, admit=lambda *a:pytest.fail('Completed phase re-admitted'),
                   implementation_identity='fixture') == result
    assert len(provider.requests) == calls


def test_invalid_completed_bridge_requires_explicit_design(tmp_path):
    _, product, prior, index = setup(tmp_path)
    prior['outputs'][index]['request']['task'] = 'REVIEW_SOURCE_DEPENDENCY'
    with pytest.raises(LegalMathError):
        plan(product, prior)
