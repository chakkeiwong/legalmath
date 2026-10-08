from legalmath.interpretation.semantics.evidence import *
from legalmath.interpretation.semantics.records import Premise

def test_supervision_is_not_adequate_supervision_or_title():
    events,scope=declared_fixture()
    assert derive(events,"supervision_event_recorded",scope,"operator-1","2026-10-06")["state"]=="true"
    for q in ("adequate_supervision","responsibility_retained","ownership_title","liability"):
        r=derive(events,q,scope,"operator-1","2026-10-06")
        assert r["state"]=="unknown" and "missing-evaluative-rule" in r["unresolved"]

def test_conflicting_records_and_history_survive_serialization():
    events,scope=declared_fixture()
    source=events[1]
    neg=source.model_copy(update={"id":"dispute","positive":False,
        "completeness":Premise(id="complete",statement="Complete declared event log for test",status="declared",dependencies=())})
    events.append(Observation.model_validate_json(neg.model_dump_json()))
    r=derive(events,"supervision_event_recorded",scope,"operator-1","2026-10-06")
    assert r["state"]=="conflict" and r["support"]["negative"]==["dispute"]
    assert derive(events,"incident_recorded",scope,"operator-1","2026-10-06")["state"]=="true"
    assert derive(events,"remediation_recorded",scope,"operator-1","2026-10-06")["state"]=="true"

def test_no_event_is_unknown_not_false():
    events,scope=declared_fixture()
    assert derive([],"supervision_event_recorded",scope,"operator-1","2026-10-06")["state"]=="unknown"
    negative=events[1].model_copy(update={"positive":False})
    assert derive([negative],"supervision_event_recorded",scope,"operator-1","2026-10-06")["state"]=="unknown"
