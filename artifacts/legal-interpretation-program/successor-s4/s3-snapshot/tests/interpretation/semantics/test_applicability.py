from legalmath.interpretation.semantics.evidence import *

def test_wrong_provider_later_knowledge_and_partial_dates():
    events,scope=declared_fixture()
    e=events[1]
    assert applicability(e,scope,"replacement-provider","2026-10-06")[0]=="out-of-scope"
    assert applicability(e,scope,"operator-1","2026-02-01")[1]==("learned-after-cutoff",)
    partial=e.model_copy(update={"event":Interval(start=None,end="2026-02-01")})
    assert applicability(partial,scope,"operator-1","2026-10-06")[0]=="unknown"

def test_backdated_correction_does_not_change_original_evidence():
    events,scope=declared_fixture()
    old=events[1]
    correction=old.model_copy(update={"id":"correction","kind":"correction","known_on":"2026-11-01","relates_to":(old.id,)})
    result=derive([old,correction],"supervision_event_recorded",scope,"operator-1","2026-10-06")
    assert result["state"]=="true"
    assert result["observations"][1]["reasons"]==["learned-after-cutoff"]

def test_event_must_fall_within_its_validity_even_if_both_overlap_broad_assessment():
    events,scope=declared_fixture()
    event=events[1].model_copy(update={"validity":Interval(start="2026-06-01",end="2026-12-31")})
    assert applicability(event,scope,"operator-1","2026-10-06")==("out-of-scope",("event-outside-validity",))
