"""Source-derived adversarial controls for the bounded BASF consumer."""
import copy
import json
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_basf as runner
from scripts import prospectus_basf_admission as a
from scripts.prospectus_refresh_work import sources, BASF, SUPPLEMENT, ANNUAL
from scripts.prospectus_refresh_admission import source_document
from scripts.prospectus_refresh_sources import norm

@pytest.fixture(scope="module")
def spec():
    return json.loads(a.SPEC.read_text())

@pytest.fixture(scope="module")
def docs():
    return {key: source_document(row) for key, row in sources().items()}

@pytest.fixture(scope="module")
def packet():
    return a.build_packet()

def test_full_source_replay_and_consumer(packet):
    a.verify_anchors(packet)
    view = a.consume(packet)
    assert len(packet["decisions"]) == 63
    assert len([v for v in packet["decisions"] if v["kind"] == "checkbox"]) == 55
    assert view["full_dossier_status"] == "UNRESOLVED"
    assert view["legal_answer"] is None and view["production_promotion"] is False
    assert all(not v["locator_is_complete_clause"] for v in view["german_locators"].values())

def test_distinct_calls_and_target_occurrences(packet):
    by = {d["id"]: d for d in packet["decisions"]}
    assert by["dated_call"]["selected"] is True
    assert by["interest_date_call"]["selected"] is False
    assert by["floating_target"]["selected"] is False
    assert by["payment_target"]["selected"] is True
    assert by["cleanup_call"]["selected"] is True
    assert by["transaction_call"]["selected"] is False
    assert by["holder_put"]["selected"] is False
    assert by["change_of_control"]["selected"] is True
    assert by["reference_period"]["selected"] is False

def test_successor_guarantee_survives_initial_guarantee_exclusion(packet):
    branches = {r["id"]:r for r in packet["conditional_branches"]}
    assert branches["initial_finance_guarantee"]["disposition"] == "EXCLUDED_FOR_INITIAL_BASF_SE_ISSUER"
    assert branches["successor_guarantee"]["disposition"] == "CONDITIONAL_REQUIREMENT_RETAINED"
    assert "75%" in branches["cleanup_threshold"]["source"]["quote"]
    assert "AND reduction" in branches["cleanup_threshold"]["condition"]

@pytest.mark.parametrize("key", ["permanent","temporary_global","cbl","single_rate","floating_target",
    "annual_no_stub","long_stub","payment_target","call_dates","higher_pv","notice_clearing","german_controls"])
def test_changed_source_checkbox_abstains(key, spec, docs):
    document = copy.deepcopy(docs["basf-2032-final"])
    decisions = a.selectors(document, spec)
    row = next(r for r in decisions if r["id"] == key)
    text = norm(document["pages"][row["page"]-1]["text"])
    glyph = "\uf06f" if row["selected"] else "\uf078"
    document["pages"][row["page"]-1]["text"] = text[:row["start"]] + glyph + text[row["start"]+1:]
    with pytest.raises(ValueError, match="changed"):
        a.selectors(document, spec)

@pytest.mark.parametrize("mode", ["unknown","missing","duplicate","new_response_other_page","reorder"])
def test_source_coverage_corruption_fails(mode, spec, docs):
    document = copy.deepcopy(docs["basf-2032-final"])
    text = norm(document["pages"][2]["text"])
    if mode == "unknown":
        document["pages"][2]["text"] += " ☒ Unexpected selected option"
    elif mode == "missing":
        document["pages"][2]["text"] = text.replace("\uf078 Clearstream Banking S.A.", "Clearstream Banking S.A.")
    elif mode == "duplicate":
        document["pages"][2]["text"] += " ☒ Clearstream Banking S.A."
    elif mode == "new_response_other_page":
        document["pages"][6]["text"] += " Additional right Yes Zusätzliches Recht Ja"
    else:
        document["pages"][2],document["pages"][3] = document["pages"][3],document["pages"][2]
    with pytest.raises(ValueError):
        a.selectors(document, spec)

@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize("both", [False, True])
def test_bilingual_flip_or_conflict_fails(index, both, spec, docs):
    document = copy.deepcopy(docs["basf-2032-final"])
    row = spec["yesno"][index]
    text = norm(document["pages"][5]["text"])
    old_en = "Yes" if row["selected"] else "No"
    new_en = "No" if row["selected"] else "Yes"
    text = text.replace(row["en"]+" "+old_en, row["en"]+" "+new_en, 1)
    if both:
        old_de = "Ja" if row["selected"] else "Nein"
        new_de = "Nein" if row["selected"] else "Ja"
        text = text.replace(row["de"]+" "+old_de, row["de"]+" "+new_de, 1)
    document["pages"][5]["text"] = text
    with pytest.raises(ValueError):
        a.selectors(document, spec)

@pytest.mark.parametrize("mode", ["lost_choice","duplicate_id","same_position"])
def test_incomplete_specification_fails(mode, spec, docs):
    changed = copy.deepcopy(spec)
    if mode == "lost_choice":
        changed["checkboxes"].pop(0)
    elif mode == "duplicate_id":
        changed["checkboxes"][1]["id"] = changed["checkboxes"][0]["id"]
    else:
        row = next(r for r in changed["checkboxes"] if r["id"] == "payment_target")
        row["occurrence"] = 0
    with pytest.raises(ValueError):
        a.selectors(docs["basf-2032-final"], changed)

@pytest.mark.parametrize("mode", ["choice","locator","language","dossier","report_scope","guarantee","type"])
def test_forged_packet_rejected_after_reserialization(mode, packet):
    changed = copy.deepcopy(packet)
    if mode == "choice":
        changed["decisions"][0]["selected"] = True
    elif mode == "locator":
        changed["decisions"][0]["german_clause_locator"] = changed["decisions"][1]["german_clause_locator"]
    elif mode == "language":
        changed["controlling_language"] = "en"
    elif mode == "dossier":
        changed["full_dossier_status"] = "COMPLETE"
    elif mode == "report_scope":
        changed["annual_2022"]["complete_incorporation_scope"] = True
    elif mode == "guarantee":
        changed["conditional_branches"] = [r for r in changed["conditional_branches"] if r["id"] != "successor_guarantee"]
    else:
        changed["production_promotion"] = 0
    changed = json.loads(json.dumps(changed))
    with pytest.raises(ValueError, match="differs"):
        a.consume(changed)

def test_source_inventory_cannot_be_rehashed_to_new_edition(monkeypatch):
    changed = copy.deepcopy(sources())
    changed[BASF]["sha256"] = "a"*64
    monkeypatch.setattr(a, "sources", lambda: changed)
    with pytest.raises(ValueError, match="protected predecessor"):
        a.build_packet()

def test_stale_selection_review_rejected(monkeypatch, tmp_path):
    spec = tmp_path/"changed.json"
    spec.write_text("{}")
    original = runner.sha
    monkeypatch.setattr(runner, "sha", lambda p: "changed" if Path(p).name=="prospectus_basf_spec.json" else original(p))
    with pytest.raises(ValueError, match="specification not reviewed"):
        a.build_packet()

def test_stale_mapping_method_review_rejected(monkeypatch):
    original = runner.sha
    monkeypatch.setattr(runner, "sha", lambda p: "changed" if Path(p).name=="prospectus_basf_admission.py" else original(p))
    with pytest.raises(ValueError, match="method not reviewed"):
        a.build_packet()

def test_report_ranges_preserve_discrepancy_and_authority(packet):
    annual = packet["annual_2022"]
    pages = [r["physical_page"] for r in annual["pages"]]
    assert pages == list(range(197,204)) + [205,206,207] + list(range(209,291))
    assert len(pages) == 92
    assert "195 – p. 209" in annual["broad_heading"]["quote"]
    assert "German language is authoritative" in annual["auditor_language"]["quote"]
    assert annual["complete_incorporation_scope"] is False
    assert annual["column_extraction_qualified"] is False

@pytest.mark.parametrize("mode", ["reordered","wrong_label","wrong_original","lost_translation_qualifier"])
def test_report_source_corruption_fails(mode, docs):
    rows = sources()
    annual = copy.deepcopy(docs[ANNUAL])
    if mode == "reordered":
        annual["pages"][196], annual["pages"][197] = annual["pages"][197], annual["pages"][196]
    elif mode == "wrong_label":
        annual["pages"][196]["text"] = annual["pages"][196]["text"].replace("197","198",1)
    elif mode == "wrong_original":
        annual["source_sha256"] = "a"*64
    else:
        annual["pages"][196]["text"] = annual["pages"][196]["text"].replace("Solely the original text in German language is authoritative.","")
    with pytest.raises(ValueError):
        a.annual_scope(annual, rows[ANNUAL], docs[SUPPLEMENT], rows[SUPPLEMENT])

@pytest.mark.parametrize("change", ["method","input","prerequisite","failed"])
def test_stale_or_failed_phase_cannot_support_next_phase(change):
    record = {"status":"PASS","method":{"m":"1"},"inputs":{"i":"1"},"prerequisite":{"p":"1"}}
    assert runner.phase_current(record,"checks",record["method"],record["inputs"],record["prerequisite"])
    candidate = copy.deepcopy(record)
    if change == "failed":
        candidate["status"] = "FAIL"
    else:
        key = {"method":"m","input":"i","prerequisite":"p"}[change]
        candidate[{"input":"inputs"}.get(change,change)][key] = "2"
    assert not runner.phase_current(candidate,"checks",record["method"],record["inputs"],record["prerequisite"])
