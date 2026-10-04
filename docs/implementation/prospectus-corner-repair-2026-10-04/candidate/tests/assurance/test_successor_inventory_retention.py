from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'src'),'/home/chakwong/python/legalmath']
import pytest
from legalmath.canonical import loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.engine import Assurance
from legalmath.interpretation.assurance.semantics import merge_inventories
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from tests.assurance.test_integration import responder,settings,source


@pytest.mark.parametrize('failed_roles',[{'atomic-reader','qualification-reader'},{'qualification-reader'}])
def test_failed_replacement_keeps_prior_claims_and_marks_repair_incomplete(tmp_path,failed_roles):
    normal=responder()
    def respond(request):
        if request['task']=='REPAIR_SOURCE_INVENTORY':
            if request['role'] in failed_roles:raise LegalMathError('E_RESOURCE_LIMIT',details='Controlled repair deadline')
            return normal({**request,'task':'SOURCE_INVENTORY'})
        response=normal(request)
        if request['task']=='SOURCE_INVENTORY':response['claims'][0]['exceptions']=[]
        return response
    out=tmp_path/'repair';provider=FunctionProvider(respond)
    result=Assurance(out,provider,Path('/home/chakwong/python/legalmath/.localresources/java-toolchain/jdk-17.0.20.1+1'),AT,settings(1)).drive([source()],'Selected gift control')
    initial=loads((out/'inventories-initial.json').read_bytes())
    assert loads((out/'inventories.json').read_bytes())==initial
    assert loads((out/'claims.json').read_bytes())==merge_inventories(initial)
    assert result['source_claims']>0 and not result['execution_complete']
    assert any(r['kind']=='SOURCE_INVENTORY_REPAIR_INCOMPLETE' for r in result['findings'])
    receipt=loads((out/'inventory-repair-000.json').read_bytes())
    assert receipt['status']=='INCOMPLETE_PRIOR_INVENTORY_RETAINED'
    assert set(receipt['completed_roles'])=={'atomic-reader','qualification-reader'}-failed_roles
    assert receipt['concern']
