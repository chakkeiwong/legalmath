from copy import deepcopy
import pytest
from legalmath.interpretation.semantics.clauses import propose

def test_source_relations_and_unknown_applicability(branches, pilot_inputs, inventory):
    packet, question, retained, settings = pilot_inputs
    assert len(inventory["retained"]) == len(retained) == 70
    assert not inventory["complete_english_inventory"]
    for b in branches:
        assert b.origin == "sourced-development-nomination"
        for c in b.clauses:
            assert c.modality == "SHOULD"
            for s in c.sources:
                text = next(u["text"] for u in packet["units"] if u["unit_id"] == s.unit_id)
                s.verify(text, b.source_hash, b.question_hash)
        if b.proposal_id.startswith("responsibility"):
            assert {r.id for r in b.unresolved} == {"applicability.ut6.8", "applicability.appendix-A"}
            assert {s.locator for s in b.clauses[0].sources} == {"p10", "fn1", "ut6.8", "appendix-A"}

def test_missing_source_not_silently_omitted(pilot_inputs):
    packet, question, retained, policy = pilot_inputs
    packet = deepcopy(packet)
    packet["units"] = [u for u in packet["units"] if "at a minimum, they comply" not in u["text"]]
    with pytest.raises(ValueError, match="fn5"):
        propose(packet, question, retained, policy)
