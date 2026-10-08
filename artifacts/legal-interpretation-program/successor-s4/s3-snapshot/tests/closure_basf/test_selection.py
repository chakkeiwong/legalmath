import json, hashlib, subprocess, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.prospectus_basf_admission import build_packet, load_packet, consume
from scripts.prospectus_refresh_work import sources
def test_exhaustive_selection_coverage():
    packet=build_packet()
    assert len(packet["decisions"])==63
    assert len([d for d in packet["decisions"] if d["kind"]=="checkbox"])==55
    assert len([d for d in packet["decisions"] if d["kind"]=="yes_no"])==8
    assert packet["full_dossier_status"]=="UNRESOLVED"
def test_expected_core_options_and_branches():
    p=build_packet()
    by={d["id"]:d for d in p["decisions"]}
    assert by["fixed_rate"]["selected"] is True
    assert by["floating_rate"]["selected"] is False
    assert by["cleanup_call"]["selected"] is True
    assert by["transaction_call"]["selected"] is False
    assert p["controlling_language"]=="de"
    assert any(b["id"]=="successor_guarantee" and b["disposition"]=="CONDITIONAL_REQUIREMENT_RETAINED" for b in p["conditional_branches"])
def test_report_scope_retains_range_discrepancy():
    annual=build_packet()["annual_2022"]
    assert annual["complete_incorporation_scope"] is False
    assert annual["range_discrepancy"].startswith("Overall heading ends at 209")
    assert annual["pages"][0]["physical_page"]==197
    assert annual["pages"][-1]["physical_page"]==290
def test_consumer_is_bounded():
    value=consume(build_packet())
    assert value["full_german_contract_constructed"] is False
    assert value["production_promotion"] is False
    assert len(value["selected"])>0
def test_packet_rejects_mutation():
    packet=build_packet()
    packet["decisions"][0]["selected"]=True
    with pytest.raises(ValueError,match="differs"):
        load_packet(packet)
