from pathlib import Path
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import public_issue as implementation
from tests.assurance.test_public_issue import fixture,JDK

@pytest.mark.parametrize('asset',['java/runtime/Policy.java','schemas/rule-bundle.schema.json'])
def test_changed_runtime_or_schema_rejects_completed_resume_without_a_call(asset,tmp_path,monkeypatch):
    package=tmp_path/'package/legalmath'
    module=package/'interpretation/assurance/public_issue.py';module.parent.mkdir(parents=True)
    module.write_text('# controlled package identity fixture\n')
    path=package/asset;path.parent.mkdir(parents=True);path.write_text('original fixture bytes')
    monkeypatch.setattr(implementation,'__file__',str(module))
    public,ledger,provider=fixture(tmp_path);out=tmp_path/'run'
    implementation.run_public_issue(public,out,ledger,JDK,arm='single-reader',provider=provider)
    path.write_text('changed fixture bytes')
    with pytest.raises(LegalMathError) as error:
        implementation.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)
    assert error.value.code=='E_STALE_REVIEW'
    assert provider.calls==1
