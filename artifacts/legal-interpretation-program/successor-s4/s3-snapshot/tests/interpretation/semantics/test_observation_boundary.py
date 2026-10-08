from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from legalmath.canonical import canonical,loads,digest
from legalmath.errors import LegalMathError
from legalmath.qualification import prospective as ledger
from legalmath.interpretation.assurance import investigation_observations as obs
from legalmath.interpretation.assurance.integration_contract import evidence_file
from tests.assurance.test_investigation_observations import window
from scripts.legal_interpretation_demo import execute

@pytest.fixture(scope="module")
def execution():
    root=Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix="semantic-window-",dir=root/"artifacts") as directory:
        root,runner,dossier=execute(directory,2)
        yield root,runner,dossier,loads((Path(directory)/"current.json").read_bytes())

def fault_ref(execution,mutate):
    root,runner,original,_=execution
    dossier=deepcopy(original);mutate(dossier)
    path=runner.directory/"boundary-fault.json";path.write_bytes(canonical(dossier))
    return evidence_file(path,root)

def test_enabled_stage_is_required_through_actual_observe(tmp_path,monkeypatch,execution):
    root,runner,dossier,ref=execution
    directory,spec,_=window(tmp_path,monkeypatch,execution)
    changed=fault_ref(execution,lambda d:d.pop("semantic_stage"))
    with pytest.raises(LegalMathError) as error:
        obs.observe(directory,spec["window_hash"],"future.fixture",changed,runner)
    assert error.value.code=="E_REFERENCE"
    assert obs.report(directory,spec["window_hash"])["observed"]==0

@pytest.mark.parametrize("mutation",["settings","profile","old-disabled-window"])
def test_frozen_semantics_rejects_new_or_unknown_configuration(tmp_path,monkeypatch,execution,mutation):
    _,runner,dossier,ref=execution
    original=deepcopy(runner.semantic_options)
    if mutation=="old-disabled-window": monkeypatch.setattr(runner,"semantic_options",None)
    directory,spec,_=window(tmp_path,monkeypatch,execution)
    changed=deepcopy(original)
    if mutation=="settings": changed["settings"][0]["max_arguments"]+=1
    if mutation=="profile": changed["profile"]="unknown.semantic.profile"
    monkeypatch.setattr(runner,"semantic_options",changed)
    with pytest.raises(LegalMathError) as error:
        obs.observe(directory,spec["window_hash"],"future.fixture",ref,runner)
    assert error.value.code=="E_STALE_REVIEW"

@pytest.mark.parametrize("mutation",["missing","swapped"])
def test_branch_receipts_cannot_be_omitted_or_swapped_in_observation(tmp_path,monkeypatch,execution,mutation):
    _,runner,_,_=execution
    directory,spec,_=window(tmp_path,monkeypatch,execution)
    def change(d):
        reports=d["semantic_stage"]["report"]["branch_reports"]
        if mutation=="missing": reports.pop()
        else: reports[0],reports[1]=reports[1],reports[0]
    ref=fault_ref(execution,change)
    with pytest.raises(LegalMathError):obs.observe(directory,spec["window_hash"],"future.fixture",ref,runner)
    assert obs.report(directory,spec["window_hash"])["pending"]==1

def test_semantic_stage_time_is_checked_at_observe_boundary(tmp_path,monkeypatch,execution):
    _,runner,_,ref=execution
    directory,spec,selected=window(tmp_path,monkeypatch,execution)
    real_check=obs.check_stages
    def inject_timestamp_fault(*args,**kw):
        checked=real_check(*args,**kw)  # actual file, input, branch and Java rechecks
        checked["stage_started_ms"]["semantics"]=int(ledger.instant(selected["at"]).timestamp()*1000)-1
        return checked
    monkeypatch.setattr(obs,"check_stages",inject_timestamp_fault)
    with pytest.raises(LegalMathError) as error:
        obs.observe(directory,spec["window_hash"],"future.fixture",ref,runner)
    assert error.value.code=="E_STALE_REVIEW"

def test_repair_keeps_old_window_ineligible_and_new_window_can_admit(tmp_path,monkeypatch,execution):
    _,runner,_,ref=execution
    directory,spec,_=window(tmp_path,monkeypatch,execution)
    obs.repair(directory,spec["window_hash"],runner,reason="Declared engineering repair fixture")
    with pytest.raises(LegalMathError) as error:
        obs.observe(directory,spec["window_hash"],"future.fixture",ref,runner)
    assert error.value.code=="E_STALE_REVIEW"
    assert obs.report(directory,spec["window_hash"])["pending"]==1
    monkeypatch.setattr(ledger,"now",lambda:"2027-01-01T00:00:00Z")
    fresh=obs.freeze(tmp_path/"fresh",runner,["synthetic-test-only"],ends_at="2027-01-03T00:00:00Z")
    monkeypatch.setattr(ledger,"now",lambda:"2027-01-02T02:00:00Z")
    item={"task_id":"later.fixture","family":"synthetic-test-only","source_hash":"c"*64,"question_hash":"d"*64,
          "published_at":"2027-01-02T00:00:00Z","first_seen_at":"2027-01-02T01:00:00Z"}
    assert obs.admit(tmp_path/"fresh",fresh["window_hash"],item,runner)["status"]=="PENDING"

def test_complete_semantic_fixture_can_be_observed_without_legal_promotion(tmp_path,monkeypatch,execution):
    _,runner,_,ref=execution
    directory,spec,_=window(tmp_path,monkeypatch,execution)
    event=obs.observe(directory,spec["window_hash"],"future.fixture",ref,runner)
    assert event["summary"]["semantic_summary_hash"]
    assert event["summary"]["legal_correctness"]=="NOT_ESTABLISHED"
    assert obs.report(directory,spec["window_hash"])["observed"]==1
