from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics.clauses import propose
from legalmath.interpretation.semantics.lower import envelope,pilot_reading,expression,boolean
from legalmath.interpretation.semantics.render import decision_set
from legalmath.interpretation.semantics.records import Outcome

def test_footnote_removal_and_source_amendment_detected(pilot_inputs,branches):
    packet,question,rows,settings=pilot_inputs
    altered=deepcopy(packet)
    altered["units"]=[u for u in altered["units"] if "at a minimum, they comply" not in u["text"]]
    with pytest.raises(ValueError): propose(altered,question,rows,settings)
    altered=deepcopy(packet);altered["units"][0]["text"]+=" amended"
    with pytest.raises(LegalMathError): envelope(branches[0],altered,pilot_reading(branches[0]),question)

def test_dropped_branch_cannot_create_unanimity(branches):
    selected=branches[:3]
    outputs=[Outcome(query_id="q",branch_id=b.identity(),extension_ids=("grounded-empty",),value="false",
         completion="complete",lowering="supported",reasons=("unknown-interpretation",),witnesses=()) for b in selected]
    with pytest.raises(ValueError): decision_set(selected,outputs[:2],[b.identity() for b in selected])

def test_inverted_condition_and_unknown_coercion_have_distinguishing_assignments():
    expr=expression("(if request true false)",{"request"})
    inverted=expression("(if request false true)",{"request"})
    assert boolean(expr,{"request":"true"})!=boolean(inverted,{"request":"true"})
    assert boolean(expr,{"request":"unknown"})=="unknown"
    assert boolean(expr,{"request":"false"})=="false"

def test_actor_and_unresolved_premise_changes_invalidate_branch_identity(branches):
    b=branches[0];c=b.clauses[0]
    changed=b.model_copy(update={"clauses":(c.model_copy(update={"actor":"different provider"}),*b.clauses[1:])})
    assert changed.identity()!=b.identity()
    assert b.model_copy(update={"unresolved":()}).identity()!=b.identity()

def test_consistently_edited_formula_cannot_borrow_pilot_branch(branches,pilot_inputs):
    b=branches[0];packet,question,_,_=pilot_inputs
    r=pilot_reading(b);r["formalization"]["result"]="false"
    with pytest.raises(LegalMathError):
        envelope(b,packet,r,question)
