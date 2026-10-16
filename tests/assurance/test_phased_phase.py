from pathlib import Path
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased.phase import execute
from legalmath.interpretation.assurance.bounded_product import BoundedProduct,AUDIT
from tests.assurance.test_bounded_product import envelope,limits,Scripted


def setup(tmp_path):
    product=BoundedProduct(tmp_path,tmp_path/'product',Scripted(),envelope(),list,limits=limits())
    q=envelope()['original_questions'][0]
    records=[r for r in product.route.records.values() if r['kind']=='source']
    request=product.request('AUDIT_ANSWER_AGAINST_SOURCE',q,records,
        payload={'conclusion':'Conditional.'},expected=[r['id'] for r in records])
    calls=[{'key':'review-'+str(i),'request':request,'schema':AUDIT,
        'validate':lambda value:product.citations(value,records)} for i in range(2)]
    return product,calls


def test_interrupted_phase_reactivates_then_reuses_exact_outcomes(tmp_path):
    product,calls=setup(tmp_path);admissions=[]
    def admit(name,count):
        admissions.append(name)
        return {'phase':name,'count':count}
    def interrupt(value):
        if value.get('last_call'):
            raise RuntimeError('IDE reload')
    with pytest.raises(RuntimeError):
        execute(product,'initial',calls,implementation_identity='test',admit=admit,refresh=interrupt)
    assert len(product.provider.requests)==1
    result=execute(product,'initial',calls,implementation_identity='test',admit=admit)
    assert len(product.provider.requests)==2 and admissions==['initial','initial']
    assert result['execution_complete'] and all(r['result']['value']['verdict']=='UNRESOLVED' for r in result['results'])
    assert execute(product,'initial',calls,implementation_identity='test',admit=admit)==result
    assert len(product.provider.requests)==2 and len(admissions)==2


def test_changed_settled_result_and_uncertain_dispatch_are_vetoes(tmp_path):
    product,calls=setup(tmp_path)
    execute(product,'initial',calls,implementation_identity='test',admit=lambda *a:{})
    path=product.dispatch.directory/'review-1/result.json'
    path.write_text('{}')
    with pytest.raises(LegalMathError):
        execute(product,'initial',calls,implementation_identity='test',admit=lambda *a:{})


def test_resource_refusal_does_not_block_independent_phase(tmp_path):
    product,calls=setup(tmp_path)
    def refuse(*args):
        raise LegalMathError('E_RESOURCE_LIMIT',details='Insufficient phase resources')
    first=execute(product,'refused',calls,implementation_identity='test',admit=refuse)
    assert first['resource_refusal'] and not product.provider.requests
    other=execute(product,'independent',calls[:1],implementation_identity='test',admit=lambda *a:{})
    assert other['execution_complete']
