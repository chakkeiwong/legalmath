"""Discriminating event, scope and actual-route tests without legal answer labels."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import pytest
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics import integration
from legalmath.interpretation.semantics.scoped_standards import parse, compute, recorded_requirement
from scripts.legal_interpretation_s3_data import retained_inputs, product_inputs, execute_product, ROOT


@pytest.fixture
def data():
    return retained_inputs()


def run(data):
    packet, value = data
    return compute(value, packet, {}, {}, [])


def results(data):
    return {r["rule_id"]: r for r in run(data)["evaluation"]["results"]}


def premise(row, name):
    return next(p for p in row["premises"] if p["requirement"]["id"] == name)


def test_events_do_not_supply_sufficiency(data):
    rows = results(data)
    assert premise(rows["diagnostic.supervision"], "recorded.supervision")["state"] == "true"
    for r in rows.values():
        if r["rule_id"].startswith("diagnostic."):
            assert r["status"] == "NOT_DERIVED"
            assert any(p["state"] == "unknown" and p["requirement"]["kind"] == "inference-premise" for p in r["premises"])
    assert all(r["opposite_consequence"] == "NOT_ESTABLISHED" for r in rows.values())


def test_ledger_does_not_imply_access_or_changed_terms_acceptance(data):
    rows = results(data)
    assert premise(rows["diagnostic.ledger-access"], "recorded.ledger-entry")["state"] == "true"
    assert premise(rows["diagnostic.ledger-access"], "recorded.customer-access")["state"] == "unknown"
    assert premise(rows["diagnostic.terms-acceptance"], "recorded.terms-change")["state"] == "true"
    assert premise(rows["diagnostic.terms-acceptance"], "recorded.terms-acceptance")["state"] == "unknown"


def test_ABC_objects_and_distinct_requests_survive(data):
    rows = results(data)
    a,b,c = (rows[k] for k in ("p14-A-demonstration","fn5-B-demonstration","fn5-C-demonstration"))
    assert (a["status"],b["status"],c["status"]) == ("NOT_DERIVED","CONDITIONALLY_DERIVED","NOT_DERIVED")
    assert a["consequence"] != c["consequence"]
    assert rows["p15-audit"]["status"] == "CONDITIONALLY_DERIVED"
    assert rows["p16-opinion"]["status"] == "NOT_DERIVED"
    assert premise(rows["p16-opinion"], "p16-request")["excluded"][0]["id"] == "wrong-party.p16"


def test_exclusions_and_conflict_are_retained(data):
    report = run(data)
    events = {r["observation"]["id"]: r for r in report["observation_admission"]}
    for name, reason in (("remediation","learned-after-cutoff"),("reconciliation","incomplete-period-coverage"),
                         ("other-relationship","different-identity"),("negative-without-completeness","missing-completeness-premise")):
        assert not events[name]["admitted"]
        assert reason in events[name]["reasons"]
    assert premise(results(data)["p10-responsibility"],"p10-responsibility.interpretation")["state"] == "conflict"


@pytest.mark.parametrize("field,value,reason", [
    ("provider","other","different-identity"), ("jurisdiction","other","different-identity"),
    ("known_on",None,"unknown-knowledge-date"), ("known_on","2026-05-02","learned-after-cutoff"),
    ("event",{"start":"2026-05-02","end":"2026-05-02"},"event-after-cutoff"),
    ("event",{"start":None,"end":None},"unknown-event-interval"),
])
def test_observation_admission_rejects_bad_scope(data,field,value,reason):
    data[1]["observations"][0][field] = value
    row = run(data)["observation_admission"][0]
    assert not row["admitted"] and reason in row["reasons"]


@pytest.mark.parametrize("field",["actor","product","component","activity"])
def test_relationship_and_other_identities_never_transfer(data,field):
    data[1]["observations"][0]["scope"][field] = "another"
    assert "different-identity" in run(data)["observation_admission"][0]["reasons"]


def test_partial_intervals_cannot_be_pooled_to_cover_period(data):
    event = data[1]["observations"][0]
    event["scope"]["interval"]["end"] = "2026-04-25"
    second = deepcopy(event)
    second["id"] = "second-half"
    second["scope"]["interval"] = {"start":"2026-04-25","end":"2026-04-30"}
    data[1]["observations"].append(second)
    assert premise(results(data)["diagnostic.supervision"],"recorded.supervision")["state"] == "unknown"


def test_declared_complete_negative_retains_conflict(data):
    negative = data[1]["observations"][-1]
    negative["completeness"] = {"id":"declared-complete","statement":"Synthetic completeness assumption",
        "status":"declared","dependencies":[]}
    row = results(data)["diagnostic.supervision"]
    assert premise(row,"recorded.supervision")["state"] == "conflict"
    assert row["status"] == "NOT_DERIVED"


def test_separate_sufficiency_premise_allows_only_conditional_result(data):
    value = data[1]
    req = next(r for r in value["standards"] if r["id"]=="diagnostic.supervision")["requirements"][1]
    p = deepcopy(value["premises"][0])
    p.update(id="explicit-sufficiency",requirement_id=req["id"],kind="inference-premise",positive=True)
    value["premises"].append(p)
    row = results(data)["diagnostic.supervision"]
    assert row["status"] == "CONDITIONALLY_DERIVED"
    assert row["legal_correctness"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("mutation",["bytes","missing-document","predicate","bypass","duplicate","capacity","profile"])
def test_input_integrity_and_closed_event_vocabulary(data,mutation):
    v=data[1]
    if mutation=="bytes":v["documents"][0]["text"] += "altered"
    elif mutation=="missing-document":v["documents"].pop()
    elif mutation=="predicate":
        r=next(r for r in v["standards"] if r["id"]=="diagnostic.supervision")
        r["requirements"][-1]["statement"]="Supervision is legally adequate."
    elif mutation=="bypass":v["premises"][0]["requirement_id"]="recorded.supervision"
    elif mutation=="duplicate":v["observations"].append(v["observations"][0])
    elif mutation=="capacity":v["observations"]=[{**v["observations"][0],"id":str(i)} for i in range(1024)]
    else:v["profile"]="unversioned"
    with pytest.raises(LegalMathError):run(data)


def test_source_and_kind_faults(data):
    data[1]["premises"][0]["kind"]="source-assertion"
    rows=results(data)
    assert premise(rows["p14-confirmation"],"26EC22-applicable")["state"]=="unknown"
    data[0]["units"][-1]["text"]+=" Amendment."
    with pytest.raises(LegalMathError):run(data)


def test_v2_rejects_v3_context_and_v3_requires_inputs(data):
    from scripts.legal_interpretation_demo import options
    v2=options(1);v3={**v2,"profile":integration.SCOPED_PROFILE}
    ctx=integration.investigation_context(v3,None,data[1])
    with pytest.raises(LegalMathError):integration.context_for(v2,ctx)
    with pytest.raises(LegalMathError):integration.investigation_context(v3,None)
    with pytest.raises(LegalMathError):integration.investigation_context(v2,None,data[1])
    with pytest.raises(LegalMathError):integration.context_for(v3,{**ctx,"extra":"field"})


@pytest.fixture(scope="module")
def product():
    with tempfile.TemporaryDirectory(prefix="s3-product-",dir=ROOT/"artifacts") as td:
        runner,dossier,provenance=execute_product(td)
        yield runner,dossier,provenance


def test_actual_dossier_preserves_branch_bound_standards_and_replays(product):
    from legalmath.interpretation.assurance.investigation_observations import method,check_stages
    runner,dossier,provenance=product
    report=dossier["semantic_stage"]["report"]
    assert report["profile"]==integration.SCOPED_PROFILE
    assert dossier["execution_complete"]
    assert len(report["standards"]["branches"])==6
    assert not report["standards"]["unattached_rules"]
    for b in report["standards"]["branches"]:
        assert len(b["attachments"])==1 and len(b["results"])==18
        assert b["standards_lowering"]=="NOT_IMPLEMENTED"
    assert any(e["reasons"] for e in report["standards"]["observation_admission"])
    checked=check_stages(ROOT,dossier,method(runner),runner)
    assert checked["execution_complete"] and checked["semantic_summary_hash"]==digest(report)
    assert all(p["original"]["quote"]==p["projected"]["quote"] for p in provenance)


@pytest.mark.parametrize("fault",["source","scope","kind","evidence","attachment","cutoff"])
def test_actual_semantic_receipt_rejects_changed_inputs(product,fault):
    runner,dossier,_=product
    path=ROOT/dossier["semantic_stage"]["directory"]
    inputs=loads((path/"inputs.json").read_bytes())
    c=inputs["context"];v=c["standards"]
    if fault=="source":v["packet_hash"]="0"*64
    elif fault=="scope":v["assessment"]["scope"]["actor"]="changed"
    elif fault=="kind":v["premises"][0]["kind"]="source-assertion"
    elif fault=="evidence":v["observations"][0]["evidence_hash"]=v["documents"][0]["sha256"]
    elif fault=="attachment":v["attachments"][0]["rule_ids"]=["fn5-B-demonstration"]
    else:v["observations"][0]["known_on"]="2026-05-02"
    with pytest.raises(LegalMathError):
        integration.verify(path,inputs["packet"],inputs["candidates"],inputs["questions"],
            inputs["options"],inputs["at"],context=c,target=dossier["binding"]["investigation_method"]["toolchains"]["java"])


def test_dossier_cannot_drop_or_promote_standards(product):
    from legalmath.interpretation.assurance.complete_investigation import verify
    _,dossier,_=product
    value=deepcopy(dossier)
    value["semantic_stage"]["report"]["standards"]["branches"]=[]
    with pytest.raises(LegalMathError):verify(ROOT,value)
