import pytest
from pydantic import ValidationError
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics.records import Interval, SourceSpan, Support, Settings

@pytest.mark.parametrize("positive,negative,state",[((),(),"unknown"),(("a",),(),"true"),((),("b",),"false"),(("a",),("b",),"conflict")])
def test_support_preserves_all_states_without_implicit_truth(positive,negative,state):
    value=Support(positive=positive,negative=negative)
    assert Support.model_validate_json(value.model_dump_json()).state==state
    with pytest.raises(TypeError): bool(value)
    with pytest.raises(ValidationError): value.positive=("changed",)

def test_unknown_dates_stay_unknown_and_invalid_dates_rejected():
    assert Interval(start=None,end="2026-04-20").start is None
    for a,b in [("0000-01-01",None),("2026",None),("2026-05-01","2026-04-20")]:
        with pytest.raises(ValidationError): Interval(start=a,end=b)

def test_unicode_location_requires_source_and_request_identity():
    text="甲 duty β"
    span=SourceSpan(source_hash="a"*64,edition="26EC22",unit_id="p14",unit_hash=digest(text),
                    locator="paragraph 14",start=2,end=6,quote="duty",request_hash="b"*64,role="unknown")
    assert span.verify(text,"a"*64,"b"*64).role=="unknown"
    for args in [(text+"!","a"*64,"b"*64),(text,"c"*64,"b"*64),(text,"a"*64,"c"*64)]:
        with pytest.raises(LegalMathError): span.verify(*args)
    with pytest.raises(ValidationError): Settings(semantics="implicit",ordering="none",priorities=(),max_arguments=8,max_extensions=8,timeout_seconds=1)
