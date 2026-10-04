from pathlib import Path
import runpy

import pytest

from legalmath.canonical import digest
from legalmath.prospectus.common import write


@pytest.mark.parametrize("prior", [{"status":"FAILED_RETAINED"},
    {"status":"STRUCTURALLY_VALID_PROPOSAL","request_hash":"wrong","result_hash":"wrong"}])
def test_failed_or_unbound_response_cannot_be_skipped(monkeypatch,tmp_path,prior):
    module=runpy.run_path(str(Path(__file__).resolve().parents[2]/"scripts/run_instrument_transport_study.py"))
    run=module["execute"];env=run.__globals__
    class Allowance:
        maximum=1
        def __init__(self,path):pass
    monkeypatch.setitem(env,"GrantedAllowance",Allowance)
    # Any provider dispatch would fail this check; reuse must be rejected first.
    monkeypatch.setitem(env,"CodexProvider",lambda **kwargs:object())
    request={"source":"unchanged"};identity=digest(request)
    write(tmp_path/"prepared.json",{"calls_required":1,"requests":[{"id":"one","request_hash":identity}]})
    write(tmp_path/"requests/one.json",{"request":request})
    write(tmp_path/"responses/one.json",prior)
    with pytest.raises(ValueError,match="reviewed repair"):run(tmp_path/"grant.json",directory=tmp_path)
