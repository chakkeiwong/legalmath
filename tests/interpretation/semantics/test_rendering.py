import pytest
from legalmath.interpretation.semantics.records import Outcome
from legalmath.interpretation.semantics.render import render,across_extensions,decision_set

@pytest.mark.parametrize("value",["true","false","unknown","conflict","out-of-scope"])
def test_every_value_and_reason_reaches_all_display_layers(branches,value):
    b=branches[0]
    reasons=("conflicting-evidence","unknown-applicability","unknown-interpretation","unsupported-lowering")
    o=Outcome(query_id="q",branch_id=b.identity(),extension_ids=("empty-grounded",),value=value,
              completion="complete",lowering="unsupported",reasons=reasons,witnesses=("p14","fn5"))
    r=render(b,o)
    assert r["operative"]==r["summary"]
    assert all(reason in r["summary"] for reason in reasons)
    assert r["detail"]["outcome"]==o.model_dump(mode="json")
    assert r["detail"]["clauses"]==[c.model_dump(mode="json") for c in b.clauses]

def test_extension_conflict_unknown_and_empty_inventory(branches):
    b=branches[0]
    true=Outcome(query_id="q",branch_id=b.identity(),extension_ids=("one",),value="true",
                 completion="complete",lowering="supported",reasons=("unknown-interpretation",),witnesses=())
    false=true.model_copy(update={"value":"false","extension_ids":("two",)})
    r=across_extensions([true,false])
    assert r.value=="conflict" and "conflicting-extensions" in r.reasons
    unknown=false.model_copy(update={"value":"unknown","reasons":("unknown-fact","unknown-interpretation")})
    assert across_extensions([true,unknown]).value=="unknown"
    assert not decision_set([],[],[])["uniform_for_query_projection"]
    with pytest.raises(ValueError): decision_set([b],[true],[])
