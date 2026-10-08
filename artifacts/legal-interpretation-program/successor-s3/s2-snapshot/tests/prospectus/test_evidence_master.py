import pytest
from legalmath.prospectus import master_mechanisms as m


@pytest.mark.parametrize("clause", [
    "Materialised Bearer Notes should be surrendered for payment together with all unmatured Coupons, "
    "failing which an amount equal to the face value of each missing unmatured Coupon shall be "
    "deducted from the Final Redemption Amount, Amortised Nominal Amount, Early Redemption Amount "
    "or Optional Redemption Amount due for payment.",
    "References in these Conditions to principal shall be deemed to include any premium payable "
    "in respect of the Notes, Final Redemption Amounts, Early Redemption Amounts, Optional "
    "Redemption Amounts, Amortised Nominal Amounts and all other amounts in the nature of principal.",
])
def test_nominal_amount_in_coupon_or_definition_list_is_not_repayment(tmp_path, clause):
    from legalmath.prospectus.loss_absorption_reader import analyze_issue
    from tests.prospectus.test_loss_absorption import fixture
    issue, docs, _ = fixture(tmp_path, [
        "Example issuer. Example senior notes. The Notes are unsecured obligations. " + clause])
    row = analyze_issue(issue, docs, tmp_path)
    assert not any(e["kind"] == "cash_repayment" and e["disposition"] == "applicable"
                   for e in row["evidence"])
    assert row["answer"] is None


def test_final_redemption_nominal_equality_with_operative_action_is_retained(tmp_path):
    from legalmath.prospectus.loss_absorption_reader import analyze_issue
    from tests.prospectus.test_loss_absorption import fixture
    issue, docs, _ = fixture(tmp_path, ["Example issuer. Example senior notes. The Notes are unsecured obligations. "
        "Each Note shall be finally redeemed on its Maturity Date at its Final Redemption Amount "
        "(which, unless otherwise provided in the relevant Final Terms, is its nominal amount)."])
    assert analyze_issue(issue, docs, tmp_path)["answer"] is False


def test_contingent_debt_metadata_keeps_neutral_context_without_claiming_scope():
    issue={"id":"santander-at1-eur-2025","security_type":"coco_debt"}
    result=m.issue_context({"context":{"instrument_id":"old","instrument_kind":"at1_bond"}},issue)
    assert result["context"]=={"instrument_id":issue["id"],"instrument_kind":"debt_bond"}


@pytest.mark.parametrize("kind",["equity","preferred_stock","unknown"])
def test_context_does_not_guess_debt_from_unrecognized_type(kind):
    with pytest.raises(ValueError):m.issue_context({"context":{}},{"id":"x","security_type":kind})


from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from legalmath.prospectus import master_control as c
from legalmath.prospectus import master_mechanisms as m
from legalmath.prospectus import master_sources as s


@pytest.mark.parametrize("value",[True,False,1.25,"-1","NaN","1,000","EUR 2","1e3"])
def test_exact_money_rejects_invalid_or_inexact_values(value):
    with pytest.raises((ValueError,ZeroDivisionError)):m.amount(value)


@pytest.mark.parametrize("ratio,expected",[("0.051249",True),("0.05125",False),("0.051251",False)])
@pytest.mark.parametrize("loss",["0","25","50","200","500"])
def test_write_down_threshold_cap_and_conservation(ratio,expected,loss):
    out=m.write_down(ratio=ratio,required_loss=loss,principal="100",others=[{"currency":"EUR","principal":"100","effective":True},{"currency":"EUR","principal":"999","effective":False}],currency="EUR",premise_kind="HYPOTHETICAL")
    assert out["trigger_under_premises"]==expected
    independent=min(Fraction(loss),200)/2 if expected else 0
    assert Fraction(out["write_down"])==independent
    assert Fraction(out["write_down"])+Fraction(out["remaining_principal"])==100


def test_ineffective_other_instrument_cannot_dilute_loss():
    kwargs=dict(ratio="0.05",required_loss="50",principal="100",currency="EUR",premise_kind="HYPOTHETICAL")
    effective=m.write_down(**kwargs,others=[{"currency":"EUR","principal":"100","effective":True}])
    ineffective=m.write_down(**kwargs,others=[{"currency":"EUR","principal":"100","effective":False}])
    assert effective["write_down"]=="25" and ineffective["write_down"]=="50"


@pytest.mark.parametrize("other",[{"currency":"USD","principal":"100","effective":True},{"currency":"EUR","principal":"100","effective":None}])
def test_units_and_missing_effectiveness_rejected(other):
    with pytest.raises(ValueError):m.write_down(ratio="0.05",required_loss="50",principal="100",others=[other],currency="EUR",premise_kind="HYPOTHETICAL")


CONDITIONS=["subsequent_financial_year","no_annual_loss_created","no_continuing_or_recreated_trigger","regulatory_conditions_met","pari_passu_conditions_met","notice_and_payment_date_met","issuer_elected_write_up"]


def up(conditions):
    return m.write_up(annual_profit="100",written_down_initial="200",tier1="1000",distributions="5",mda_available="12",own_initial="100",pool_initial="200",own_prevailing="90",issuer_selected_total="100",conditions=conditions,premise_kind="HYPOTHETICAL")


def test_write_up_cap_is_not_an_entitlement():
    out=up(dict.fromkeys(CONDITIONS,True))
    assert out["H"]=="20" and out["available_pool_cap"]=="12" and out["write_up"]=="6"
    assert out["entitlement_from_cap"] is False and out["actual_write_up"]=="NOT_ESTABLISHED"


@pytest.mark.parametrize("condition",CONDITIONS)
def test_each_write_up_condition_can_veto(condition):
    conditions=dict.fromkeys(CONDITIONS,True);conditions[condition]=False
    assert up(conditions)["write_up"]=="0"
    del conditions[condition]
    with pytest.raises(ValueError):up(conditions)


def test_metadata_repair_preserves_source_selection_and_is_idempotent():
    old={"documents":{"d":{"sha256":"abc"}},"issues":[{"id":"senior","security_type":"debt"}],"scope":"30 old issues"}
    snapshot=deepcopy(old);new=m.repaired_inventory(old)
    assert old==snapshot and new["documents"]==old["documents"] and new["issues"]==old["issues"]
    assert "1 exposed" in new["scope"] and new==m.repaired_inventory(new)
    bank={"context":{"instrument_kind":"at1_bond","instrument_id":"wrong","facts_sha256":"unchanged"}}
    repaired=m.issue_context(bank,old["issues"][0])
    assert repaired["context"]["instrument_kind"]=="debt_bond" and repaired["context"]["facts_sha256"]=="unchanged"
    assert bank["context"]["instrument_id"]=="wrong"


@pytest.mark.parametrize("url",["http://www.enel.com/x","https://localhost/x","https://www.enel.com.evil/x","https://user@www.enel.com/x","https://www.enel.com:444/x","file:///tmp/file"])
def test_acquisition_host_and_scheme_are_bounded(url):
    with pytest.raises(ValueError):s.valid_url(url,{"public_hosts":["www.enel.com"]})


def setup_control(tmp_path,monkeypatch):
    root=tmp_path;out=root/"out";data=root/"data"
    monkeypatch.setattr(c,"ROOT",root);monkeypatch.setattr(c,"OUT",out);monkeypatch.setattr(c,"DATA",data)
    monkeypatch.setattr(c,"PLAN",root/"plan.md")
    (root/"plan.md").write_text("plan")
    c.write(root/"docs/prospectus/gap-closure/final-inventory.json",{"issues":[]})
    c.write(out/"allowlist.json",{"max_execution_seconds":100,"max_failures_per_input":3})
    monkeypatch.setattr(c,"method_files",lambda:{"fixed":"method"})
    monkeypatch.setattr(c.subprocess,"check_output",lambda *a,**k:"git-head\n")
    return root,out,data


def test_real_phase_failure_then_repair_retains_attempts_and_refreshes(tmp_path,monkeypatch):
    from legalmath.prospectus import master_phases
    root,out,data=setup_control(tmp_path,monkeypatch)
    def broken(*args):raise ValueError("constructed defect")
    monkeypatch.setattr(master_phases,"execute",broken)
    state=c.state();first=c.run_phase("E0",state)
    assert first["status"]=="FAILED" and c.read(out/"next-phase-plan.json")["next_phase"]=="E0"
    monkeypatch.setattr(master_phases,"execute",lambda *args:{"status":"PASS","repairs":["fixed constructed defect"],"open_issues":[]})
    second=c.run_phase("E0",state)
    assert second["status"]=="PASS" and second["directory"]!=first["directory"]
    assert c.read(out/"next-phase-plan.json")["next_phase"]=="E1"
    assert (root/first["directory"]/"result.json").exists()
    assert c.run_phase("E0",state)==second
    assert len(list((out/"phases/E0").glob('attempt-*')))==2
    (root/second["directory"]/"result.json").write_text("tamper")
    assert not c.current_phase("E0",state)


def test_interruption_is_preserved_and_resume_does_not_claim_success(tmp_path,monkeypatch):
    root,out,data=setup_control(tmp_path,monkeypatch)
    attempt=out/"phases/E0/attempt-001";attempt.mkdir(parents=True)
    state=c.state();state["phases"]["E0"]={"status":"RUNNING","directory":str(attempt.relative_to(root))}
    c.recover_interruption(state)
    assert state["phases"]["E0"]["status"]=="INTERRUPTED"
    assert (attempt/"interruption.json").exists() and not c.current_phase("E0",state)


def test_method_and_input_changes_invalidate_completion(tmp_path,monkeypatch):
    from legalmath.prospectus import master_phases
    root,out,data=setup_control(tmp_path,monkeypatch)
    monkeypatch.setattr(master_phases,"execute",lambda *args:{"status":"PASS","open_issues":[]})
    state=c.state();c.run_phase("E0",state)
    assert c.current_phase("E0",state)
    monkeypatch.setattr(c,"method_files",lambda:{"fixed":"changed"})
    assert not c.current_phase("E0",state)


def test_missing_private_inputs_never_become_permission():
    r=m.input_requirements({"id":"unknown"},[{}])
    assert r["calculation_profile"]=="NOT_IMPLEMENTED" and not r["may_execute_transaction"] and not r["actual_inputs_supplied"]


def test_campaign_paths_reject_escape(tmp_path,monkeypatch):
    root,out,data=setup_control(tmp_path,monkeypatch)
    with pytest.raises(ValueError):c.campaign_path("/etc/passwd")
    with pytest.raises(ValueError):c.campaign_path("data/../../outside")
    assert c.campaign_path("data/selection.json")==data/"selection.json"


def setup_sources(tmp_path, monkeypatch):
    root,out,data=setup_control(tmp_path,monkeypatch)
    for name,value in (("ROOT",root),("OUT",out),("DATA",data)):
        monkeypatch.setattr(s,name,value)
    monkeypatch.setattr(s,"method_files",c.method_files)
    c.write(out/"allowlist.json",{"public_hosts":["www.enel.com"],"max_http_requests":4,
        "max_requests_per_url":3,"max_http_seconds":1,"max_response_bytes":1024,
        "max_semantic_repairs":2})
    return root,out,data


def test_list_inspection_returns_success_even_during_active_execution(tmp_path,monkeypatch,capsys):
    root,out,data=setup_control(tmp_path,monkeypatch)
    monkeypatch.chdir(root)
    monkeypatch.setattr(c.sys,"argv",["master","inspect","requests"])
    with c.locked():
        assert c.main()==0
    assert json.loads(capsys.readouterr().out)==[]
    assert not (out/"state.json").exists()


def test_status_does_not_mark_live_phase_interrupted(tmp_path,monkeypatch,capsys):
    root,out,data=setup_control(tmp_path,monkeypatch)
    active=c.state();active["phases"]["E0"]={"status":"RUNNING","directory":"out/active"}
    c.write(out/"state.json",active);before=(out/"state.json").read_bytes()
    monkeypatch.chdir(root);monkeypatch.setattr(c.sys,"argv",["master","status"])
    with c.locked():
        assert c.main()==0
    assert json.loads(capsys.readouterr().out)["phases"]["E0"]=="RUNNING"
    assert (out/"state.json").read_bytes()==before


def test_inputs_bind_selection_but_later_reviews_do_not_reexecute_earlier_phases(tmp_path,monkeypatch):
    root,out,data=setup_control(tmp_path,monkeypatch)
    state=c.state();c.write(data/"sources.json",{"requests":[]})
    before={p:c.inputs(p,state) for p in ("E4","E5","E6","E7")}
    c.write(data/"witness-review.json",{"witnesses":[]})
    assert c.inputs("E4",state)==before["E4"] and c.inputs("E5",state)==before["E5"]
    assert c.inputs("E6",state)!=before["E6"]
    c.write(data/"source-review.json",{"findings":[]})
    assert c.inputs("E5",state)==before["E5"]
    c.write(data/"selection.json",{"issues":[]})
    assert c.inputs("E5",state)!=before["E5"]
    selection_hash=c.digest(c.inputs("E5",state))
    c.write(data/"sealed.json",{"documents":{},"freeze":"out/freeze.json"})
    c.write(data/"registered.json",{"inventory":"data/sealed.json","sha256":c.sha(data/"sealed.json")})
    assert c.digest(c.inputs("E5",state))!=selection_hash


def test_changed_selection_is_rejected_before_classification(tmp_path,monkeypatch):
    from legalmath.prospectus import master_phases
    root,out,data=setup_control(tmp_path,monkeypatch)
    c.write(data/"inventory.json",{"issues":[]})
    c.write(data/"selection.json",{"changed":True})
    c.write(data/"registered.json",{"inventory":"data/inventory.json","sha256":c.sha(data/"inventory.json"),
                                    "selection_sha256":"old"})
    with pytest.raises(ValueError,match="Selection changed"):
        master_phases.execute("E5",out/"attempt",c.state())


def test_http_reservation_survives_timeouts_and_enforces_retry_and_total_budgets(tmp_path,monkeypatch):
    root,out,data=setup_sources(tmp_path,monkeypatch)
    dispatched=[]
    def timed_out(argv,**kwargs):
        receipts=sorted((data/"requests").glob("*/receipt.json"))
        reservation=c.read(receipts[-1])
        assert reservation["status"]=="DISPATCH_RESERVED"
        dispatched.append(reservation["budget_sequence"])
        raise s.subprocess.TimeoutExpired(argv,1)
    monkeypatch.setattr(s.subprocess,"run",timed_out)
    state={"freeze":"out/freeze.json"}
    for i in range(3):
        assert s.acquire("same","https://www.enel.com/a","discovery",state)["status"]=="TIMEOUT"
    with pytest.raises(ValueError,match="retry budget"):
        s.acquire("same","https://www.enel.com/a","discovery",state)
    s.acquire("other","https://www.enel.com/b","discovery",state)
    with pytest.raises(ValueError,match="protocol budget"):
        s.acquire("third","https://www.enel.com/c","discovery",state)
    assert dispatched==[1,2,3,4]


def test_extraction_and_source_review_reject_altered_derivative(tmp_path,monkeypatch):
    root,out,data=setup_sources(tmp_path,monkeypatch)
    request=data/"requests/001-test";request.mkdir(parents=True)
    body=request/"response.body";body.write_text("<p>Issuer owes principal at maturity.</p>")
    receipt=request/"receipt.json"
    c.write(receipt,{"original":c.relative(body),"sha256":c.sha(body),"status":"RETAINED",
                    "kind":"html_or_other","key":"test"})
    extracted=s.extract(receipt)
    review={"findings":[{"subject":"test","finding":"Source states principal obligation",
             "remaining":"Other contracts not checked","evidence":[{"receipt":c.relative(receipt),"page":1,
             "quote":"Issuer owes principal at maturity."}]}]}
    assert s.validate_source_review(review)["human_legal_adjudication"] is False
    bad=deepcopy(review);bad["findings"][0]["evidence"][0]["quote"]="Unwritten contract"
    with pytest.raises(ValueError,match="quote missing"):s.validate_source_review(bad)
    document=c.read(extracted);document["pages"][0]["text"]="altered";c.write(extracted,document)
    with pytest.raises(ValueError,match="derivative changed"):s.extract(receipt)
    with pytest.raises(ValueError,match="Extraction changed"):s.verify_sources()


def test_discovery_freeze_preserves_chronology_and_post_pdf_repairs_require_matching_record(tmp_path,monkeypatch):
    root,out,data=setup_sources(tmp_path,monkeypatch)
    method=root/"fixed";method.write_text("first")
    monkeypatch.setattr(c,"method_files",lambda:{"fixed":c.sha(method)})
    state=c.state();c.freeze(state)
    c.write(data/"requests/001-discovery/receipt.json",{"kind":"html_or_other","status":"RETAINED"})
    method.write_text("second");c.freeze(state)
    frozen=c.read(root/state["freeze"])
    assert frozen["retained_pdfs_before_freeze"]==[] and len(frozen["discovery_requests_before_freeze"])==1
    assert state["semantic_repairs"]==[]
    before=state["freeze"]
    assert c.freeze(state)["freeze"]==before
    c.write(data/"requests/002-pdf/receipt.json",{"kind":"pdf","status":"RETAINED"})
    method.write_text("third")
    record={"counterexample":"bad witness","causal_change":"bounded repair","validation":"regression",
            "candidate_vs_direction":"repair candidate","old_method_hash":"unrelated","new_method_hash":"unrelated"}
    c.write(out/"repairs/001.json",record)
    with pytest.raises(ValueError,match="bind this old and new"):c.freeze(state)
    record.update(old_method_hash=c.digest(frozen["files"]),new_method_hash=c.digest(c.method_files()))
    c.write(out/"repairs/002.json",record);c.freeze(state)
    assert len(state["semantic_repairs"])==1


def test_phase_failure_budget_stops_identical_retries(tmp_path,monkeypatch):
    from legalmath.prospectus import master_phases
    root,out,data=setup_control(tmp_path,monkeypatch)
    monkeypatch.setattr(master_phases,"execute",lambda *a:{"status":"FAILED","open_issues":["failed"]})
    state=c.state()
    for _ in range(3):assert c.run_phase("E0",state)["status"]=="FAILED"
    with pytest.raises(RuntimeError,match="identical failure budget"):c.run_phase("E0",state)
    assert len(list((out/"phases/E0").glob("attempt-*")))==3


def test_resolved_workflow_requirements_do_not_hide_substantive_gaps(tmp_path,monkeypatch):
    root,out,data=setup_control(tmp_path,monkeypatch)
    state=c.state()
    for phase,result in {"E2":{"open_issues":["actual facts missing"]},
                         "E4":{"status":"QUALIFIED","open_issues":["seal selection"]},
                         "E5":{"classification":"data/rows.json","open_issues":["review witnesses"]}}.items():
        c.write(out/phase/"result.json",result)
        state["phases"][phase]={"directory":"out/"+phase}
    monkeypatch.setattr(c,"current_phase",lambda phase,state:phase in {"E5","E6"})
    assert c.open_requirements(state)==["actual facts missing"]


def test_public_cms_document_metadata_links_are_recovered_without_execution():
    parser=s.Links()
    parser.feed('<document-list first-results="{&quot;results&quot;:[{&quot;uri&quot;:&quot;https:\\/\\/www.nordea.com\\/doc.pdf&quot;,&quot;name_2&quot;:&quot;Dated issue terms&quot;}]}"></document-list>')
    assert parser.links==[{"href":"https://www.nordea.com/doc.pdf","text":"Dated issue terms",
                         "origin":"publisher_document_metadata"}]
    parser.feed('<document-list first-results="not JSON"></document-list>')
    assert len(parser.links)==1
