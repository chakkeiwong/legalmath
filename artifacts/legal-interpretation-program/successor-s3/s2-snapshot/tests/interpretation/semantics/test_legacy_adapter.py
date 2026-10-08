import pytest
from pydantic import ValidationError
from legalmath.interpretation.semantics.records import legacy_envelope, LegacyEnvelope
from legalmath.canonical import digest

def test_historical_packet_lossless_and_metadata_not_invented():
    old={"units":[{"unit_id":"source.1","text":"SHOULD remain responsible.","qualification":"extraction incomplete"}]}
    wrapped=legacy_envelope(old,"historical-units")
    assert wrapped.restore()==old and wrapped.original_hash==digest(old)
    assert "meaning" in wrapped.unresolved_fields and "actor" in wrapped.unresolved_fields
    changed=wrapped.restore();changed["units"][0]["text"]="changed"
    assert wrapped.restore()==old
    assert LegacyEnvelope.model_validate_json(wrapped.model_dump_json())==wrapped
    with pytest.raises(ValidationError):
        LegacyEnvelope.model_validate({**wrapped.model_dump(),"original_hash":"0"*64})

@pytest.mark.parametrize("modality",["MUST","MUST_NOT","SHOULD","SHOULD_NOT","MAY","DESCRIPTIVE","UNCERTAIN"])
def test_atomic_modality_roundtrip(modality):
    claim={"claim_id":"claim.1","kind":"OBLIGATION","actor":"Provider","action":"confirm",
      "modality":modality,"conditions":[],"exceptions":[],"temporal":[],"statement":"Proposed duty",
      "relevance":"UNCERTAIN","evidence":[{"unit_id":"p14","quote":"confirm"}],"uncertainty":["Meaning unresolved"]}
    assert legacy_envelope(claim,"AtomicClaim").restore()==claim
