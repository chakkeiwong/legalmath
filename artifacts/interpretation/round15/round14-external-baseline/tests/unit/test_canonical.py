import pytest
from legalmath.canonical import canonical, loads
from legalmath.errors import BoundaryError


def test_golden_utf8():
    assert canonical({"z": [True, None, -3], "a": "港\n"}) == '{"a":"港\\n","z":[true,null,-3]}'.encode()


@pytest.mark.parametrize("data", ['{"a":1,"a":2}', '1.0', '1e0', '-0', 'NaN', '9007199254740992', '"\\ud800"', '{"港":1}'])
def test_reject_unhashable(data):
    with pytest.raises(BoundaryError):
        loads(data)
