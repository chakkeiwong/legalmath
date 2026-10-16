"""Local mission revision preserves historical limits and reviewed evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts import legal_mission_control as control

def current():
    return control.read(ROOT/control.BASE/"mission.json"),control.read(ROOT/control.BASE/"tools.json")

def test_context_revision_counts_one_new_detour_and_no_live_calls():
    m,t=current()
    s=control.validate(m,t)
    assert s["detours_since_advance"]==18
    r=control.read(ROOT/m["context_integration_revision"]["authorization"]["path"])
    assert r["live_calls"]==0 and r["historical_charged_calls"]==41
    old=control.read(ROOT/m["recorded_live_pilot"]["authorization"]["path"])
    assert old["deadline_utc"]=="2026-10-12T04:28:01+00:00"

def test_removed_registration_and_altered_plan_are_rejected():
    m,t=current()
    bad=deepcopy(m)
    bad["history"]=[r for r in bad["history"] if r["id"]!="context-integration-register-2026-10-12"]
    with pytest.raises(control.Refused,match="registration"):
        control.validate(bad,t)
    bad=deepcopy(m)
    bad["context_integration_revision"]["plan"]["sha256"]="0"*64
    with pytest.raises(control.Refused,match="Changed evidence"):
        control.validate(bad,t)

def test_historical_plan_is_preserved_byte_for_byte():
    m,_=current()
    matches=[r for r in m["historical_evidence_relocations"] if
        r["original_path"]=="docs/plans/legal-mission-capacity-resolution-2026-10-12.md"]
    assert len(matches)==1
    control.verify_ref(ROOT,matches[0]["retained"])
    assert matches[0]["retained"]["sha256"]=="01027db467f362857c0e8190b688c747435f2a047dd95c1f107bb09413451972"

