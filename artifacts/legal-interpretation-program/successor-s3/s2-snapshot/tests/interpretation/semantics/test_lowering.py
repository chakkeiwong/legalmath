import pytest
from legalmath.canonical import digest
from legalmath.interpretation.semantics.lower import *
from legalmath.interpretation.search.formal import bundle,snapshots
from tests.search.test_formal import AT

def test_pilot_lowering_preserves_basis_and_source_envelope(branches,pilot_inputs):
    packet,question,_,_=pilot_inputs
    b=branches[0];r=pilot_reading(b);env=envelope(b,packet,r,question)
    compiled=bundle(r,env["legacy_packet"],AT)
    assert compiled["interpretations"][0]["basis"]=="reviewer_interpretation"
    assert env["provenance"]=="declared_semantic_branch"
    assert env["packet"]==packet and b.source_hash==digest(packet)
    cases=list(snapshots([compiled],AT,maximum=2))
    outcomes=[reference(b,r,{"id":str(i),"snapshot":s,"valid_at":AT,"known_at":AT}) for i,s in enumerate(cases)]
    assert outcomes[0].value=="true"
    assert "unknown-interpretation" in outcomes[0].reasons
    assert outcomes[1].value=="out-of-scope"

def test_conflicting_fact_refuses_scalar_without_losing_reference_reason(branches,pilot_inputs):
    b=branches[0];r=pilot_reading(b)
    case={"id":"conflict","snapshot":{"facts":{"in_scope":{"status":"known","value":True,"valid_from":AT,"recorded_at":AT},
           "sfc_request":{"status":"conflict"}}},"valid_at":AT,"known_at":AT}
    o=reference(b,r,case,completion="incomplete")
    assert o.value=="conflict" and o.lowering=="unsupported"
    assert {"conflicting-evidence","unfinished","unsupported-lowering","unknown-interpretation"}<=set(o.reasons)
