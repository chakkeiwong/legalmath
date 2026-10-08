from scripts.run_legal_interpretation_program import coverage,latest,read
from legalmath.interpretation.semantics.evidence import declared_fixture,derive
from legalmath.interpretation.semantics.records import Interval

def test_every_original_obligation_and_retained_reading_survives():
    report=coverage()
    source=read(latest("P0").parent/"obligation-map.json")
    assert [r["obligation"] for r in report["original_obligations"]]==[r["obligation"] for r in source]
    assert len(report["retained_readings"])==35
    assert len({r["obligation"]["obligation_id"] for r in report["original_obligations"]})==46
    assert report["substantive_closures"]==0
    assert all(r["status"]=="OPEN_QUALIFIED" and r["operative_records"] for r in report["original_obligations"])

def test_provider_replacement_does_not_inherit_supervision_or_erase_incident():
    events,scope=declared_fixture()
    replacement=events[0].model_copy(update={"id":"new.appointment","provider":"operator-2",
        "event":Interval(start="2026-06-01",end="2026-06-01")})
    events.append(replacement)
    assert derive(events,"appointment_recorded",scope,"operator-2","2026-10-06")["state"]=="true"
    assert derive(events,"supervision_event_recorded",scope,"operator-2","2026-10-06")["state"]=="unknown"
    assert derive(events,"incident_recorded",scope,"operator-1","2026-10-06")["state"]=="true"
    assert derive(events,"sanction",scope,"operator-1","2026-10-06")["state"]=="unknown"
