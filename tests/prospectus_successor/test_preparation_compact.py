import json
from scripts.prospectus_preparation_fixture import create
from legalmath.prospectus.successor import preparation as module
from legalmath.prospectus.successor.contracts import read


def test_product_size_bound_uses_lossless_compact_encoding(tmp_path,monkeypatch):
    _,pin,expected=create(tmp_path)
    value=expected['P1']
    compact=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
    pretty=json.dumps(value,ensure_ascii=False,indent=2).encode()
    assert len(compact)<len(pretty)
    monkeypatch.setattr(module,'PRODUCT_LIMIT',len(compact)+1)
    result=module.prepare(tmp_path,stage='P1',recipe_path='recipe.json',recipe_sha256=pin,output='compact')
    path=tmp_path/'compact/P1.json'
    assert path.read_bytes()==compact and read(path)==value
    assert result['status']=='PREPARED'
    assert not list(path.parent.glob('*.tmp'))
