from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import threading

import pytest

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import supplemental_repair as repair
from legalmath.interpretation.search.models import commitment


@contextmanager
def raises_code(code):
    with pytest.raises(LegalMathError) as exc:
        yield
    assert exc.value.code == code


@pytest.fixture
def authorization(tmp_path):
    checkpoint = tmp_path/"checkpoint.json"
    checkpoint.write_bytes(canonical({"maximum": 500, "calls": []}))
    value = {"profile": repair.PROFILE, "authorization": "100 additional calls authorized by user",
        "maximum": 100, "ledger": "allowance.json",
        "ends_at": (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
        "maximum_new_attempts_per_issue": 2, "phase_limits": repair.PHASE_LIMITS,
        "repair_reserve": 16, "allowed_issues": ["issue."+str(i) for i in range(120)],
        "predecessors": [{"path": checkpoint.name, "sha256": raw_digest(checkpoint.read_bytes())}]}
    path = tmp_path/"authorization.json"
    path.write_bytes(canonical(value))
    return path


def allowance(auth, task="task", phase="coverage", issues=("issue.0",), correction=False):
    return repair.SupplementalAllowance(auth, task=task, phase=phase, issues=issues, repair=correction)


def test_unexhausted_previous_grant_is_preserved_not_falsified(authorization):
    a = allowance(authorization)
    before = (authorization.parent/"checkpoint.json").read_bytes()
    assert a.reserve("1"*64) == 1
    assert a.verify()["used"] == 1
    assert (authorization.parent/"checkpoint.json").read_bytes() == before


def test_restarts_and_task_renaming_cannot_reset_issue_spending(authorization):
    allowance(authorization, task="first").reserve("1"*64)
    allowance(authorization, task="renamed", correction=True).reserve("2"*64)
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(authorization, task="third", correction=True).reserve("3"*64)
    assert allowance(authorization).verify()["used"] == 2


def test_unknown_issue_cannot_obtain_fresh_quota(authorization):
    with raises_code("E_AUTHORITY"):
        allowance(authorization, issues=("relabeled.issue",)).reserve("a"*64)


def test_failure_reservation_is_spent_and_not_refunded(authorization):
    a = allowance(authorization)
    a.reserve("a"*64)
    # A provider failure occurs after this durable reservation.
    assert allowance(authorization).verify()["used"] == 1
    assert allowance(authorization).verify()["issue_spending"] == {"issue.0": 1}


def test_global_phase_and_repair_limits_are_all_enforced(authorization):
    n = 0
    for phase, maximum in repair.PHASE_LIMITS.items():
        for _ in range(maximum):
            allowance(authorization, task=str(n), phase=phase, issues=("issue."+str(n),)).reserve(digest(n))
            n += 1
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(authorization, issues=("issue.110",)).reserve("e"*64)
    for _ in range(16):
        allowance(authorization, task=str(n), issues=("issue."+str(n),), correction=True).reserve(digest(n))
        n += 1
    assert n == 100 and allowance(authorization).verify()["used"] == 100
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(authorization, issues=("issue.111",), correction=True).reserve("f"*64)


def test_parallel_reservations_cannot_exceed_per_issue_cap(authorization):
    results = []
    def call(i):
        try:
            results.append(allowance(authorization, task=str(i)).reserve(digest(i)))
        except LegalMathError as exc:
            results.append(exc.code)
    threads = [threading.Thread(target=call,args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert sum(isinstance(r,int) for r in results) == 2
    assert results.count("E_RESOURCE_LIMIT") == 3


def test_changed_predecessor_or_authorization_is_rejected(authorization):
    a = allowance(authorization)
    (authorization.parent/"checkpoint.json").write_text("{}")
    with raises_code("E_INTEGRITY"):
        a.reserve("a"*64)


def test_expired_supplemental_window_does_not_spend(authorization):
    value = json.loads(authorization.read_text())
    value["ends_at"] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    authorization.write_bytes(canonical(value))
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(authorization).reserve("a"*64)
    assert not (authorization.parent/"allowance.json").exists()


def example_request():
    text = "A complete source quotation with Unicode responsibility — no omission."
    return {"task":"EXAMPLE", "source_packet":{"units":[{"text":text,"unit_id":"u1"}]},
        "candidates":{"a":{"statement":text,"questions":[text]},"b":{"statement":text}},
        "identity":"b"*64, "selected":["b"*64]}


def test_pool_preserves_literal_source_and_exact_full_request():
    original = example_request()
    wire = repair.encode(original)
    assert wire["source_packet"] == original["source_packet"]
    assert repair.decode(wire,digest(original)) == original
    assert wire["context_texts"] and original == example_request()


@pytest.mark.parametrize("mutation", ["pool","source","index","extra","identity"])
def test_pool_tampering_is_rejected_against_independent_original(mutation):
    original = example_request()
    wire = repair.encode(original)
    if mutation == "pool": wire["context_texts"][0] += " altered"
    elif mutation == "source": wire["source_packet"]["units"][0]["text"] += " altered"
    elif mutation == "index": wire["candidates"]["a"]["statement"] = {"text_ref":True}
    elif mutation == "extra": wire["context_texts"].append("Unused material")
    else: wire["selected"] = ["f"*64]
    with raises_code("E_INTEGRITY"):
        repair.decode(wire,digest(original))


def assessment_example():
    packet = {"units":[{"unit_id":"u1","text":"The provider should maintain proper records."}]}
    quote = {"unit_id":"u1","quote":packet["units"][0]["text"]}
    reading = {"local_id":"records","family":"scope","subject":"Provider records",
        "statement":packet["units"][0]["text"],"distinction":"Declared records interpretation",
        "citations":[quote],"assumptions":["Provider in scope is independently identified."],
        "questions":["What makes a record proper?"],"formalization":None}
    formal = {"facts":[{"name":name,"type":"bool","meaning":meaning,"unit":"provider-period",
        "source_unit_ids":["u1"],"requires_judgment":True} for name,meaning in [
        ("active","Provider and assessed period are in scope."),
        ("records","Proper records are maintained under an externally supplied records standard.")]],
        "scope":"active","result":"records","result_type":"bool"}
    row = {"reading_id":"r1","reading_hash":commitment(reading),
        "disposition":"CONDITIONAL_FORMALIZATION",
        "dimensions":[{"dimension":d,"status":"OPEN","evidence":[quote],"explanation":"Conditional check."} for d in repair.DIMENSIONS],
        "formalization":formal,
        "premises":[{"when":"(and active records)","expected":True,"evidence":[quote],"rationale":"Records present under the assumed standard."},
                    {"when":"(and active (not records))","expected":False,"evidence":[quote],"rationale":"Required records absent."}],
        "added_assumptions":[],"unresolved_questions":["Legal records standard remains open."],
        "related_readings":[],"relationship_explanation":"No other reading is merged."}
    response={"binding_hash":"b"*64,"assessments":[row],"newly_proposed_readings":[]}
    return packet,reading,response


def test_nonvacuous_formalization_produces_conditional_evidence_only():
    packet,reading,response=assessment_example()
    value=repair.validate_assessment(response,"b"*64,packet,{"r1":reading},["r1"])
    evidence=repair.formal_evidence(packet,reading,{"question":"Records?"},value["assessments"][0])
    assert evidence["certificate"]["status"]=="NO_DECLARED_OBLIGATION_VIOLATION"
    assert evidence["certificate"]["valuations_checked"]==4
    assert evidence["source_entailment"]=="NOT_ESTABLISHED"
    assert not evidence["original_reading_replaced"] and reading["formalization"] is None


@pytest.mark.parametrize("mutation", ["identity","quote","dimension","no_premises","vacuous","scope","facts"])
def test_invalid_assessments_do_not_enter_formal_evidence(mutation):
    packet,reading,response=assessment_example()
    row=response["assessments"][0]
    if mutation=="identity":row["reading_hash"]="f"*64
    elif mutation=="quote":row["premises"][0]["evidence"][0]["quote"]="invented quotation"
    elif mutation=="dimension":row["dimensions"][0]["dimension"]=row["dimensions"][1]["dimension"]
    elif mutation=="no_premises":row["premises"]=[]
    elif mutation=="vacuous":row["premises"][0]["when"]="false"
    elif mutation=="scope":row["premises"][0]["when"]="records"
    else:row["formalization"]["facts"][0]["source_unit_ids"]=["missing"]
    with pytest.raises(LegalMathError):
        repair.validate_assessment(response,"b"*64,packet,{"r1":reading},["r1"])


def test_disagreed_formal_target_is_rejected_without_removing_reading():
    packet,reading,response=assessment_example()
    row=response["assessments"][0]
    row["formalization"]["result"]="true"
    checked=repair.validate_assessment(response,"b"*64,packet,{"r1":reading},["r1"])
    evidence=repair.formal_evidence(packet,reading,{"question":"Records?"},checked["assessments"][0])
    assert evidence["certificate"]["status"]=="CONDITIONALLY_REJECTED"
    assert evidence["certificate"]["witnesses"]
    assert not evidence["certificate"]["legal_elimination"]


def test_coverage_and_integration_share_the_same_original_issue_limit(authorization):
    value=json.loads(authorization.read_text())
    value["allowed_issues"] += ["coverage.structure-reader.challenge.original", "integration.structure-reader.challenge.original"]
    authorization.write_bytes(canonical(value))
    allowance(authorization, phase="coverage", issues=("coverage.structure-reader.challenge.original",)).reserve("1"*64)
    allowance(authorization, phase="integration", issues=("integration.structure-reader.challenge.original",)).reserve("2"*64)
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(authorization, phase="integration", issues=("integration.structure-reader.challenge.original",), correction=True).reserve("3"*64)
    assert allowance(authorization).verify()["issue_spending"] == {"challenge.structure-reader.challenge.original":2}


def test_operational_status_recovers_fractional_timing_without_new_calls(authorization, monkeypatch):
    import importlib.util
    path=Path(__file__).resolve().parents[2]/"scripts/run_assurance_gap_continuation.py"
    spec=importlib.util.spec_from_file_location("supplemental_runner_test",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,"BASE",Path("."))
    task=authorization.parent/"tasks"/"coverage.retained"/"attempt-01"
    task.mkdir(parents=True)
    (task/"result.json").write_text(json.dumps({"status":"VALIDATED","phase":"coverage","elapsed_seconds":142.395}))
    before=authorization.read_bytes()
    report=module.status(authorization.parent)
    assert report["tasks"]=={"VALIDATED":1} and report["used"]==0
    assert authorization.read_bytes()==before
    (task/"duplicate.json").write_text('{"value":1,"value":2}')
    with raises_code("E_INTEGRITY"):
        module.read(task/"duplicate.json")


def test_two_provider_failures_stop_before_next_pair(authorization, monkeypatch):
    import importlib.util
    path=Path(__file__).resolve().parents[2]/"scripts/run_assurance_gap_continuation.py"
    spec=importlib.util.spec_from_file_location("supplemental_scheduler_test",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,"BASE",Path("."))
    def tasks(repo,phase):
        for i in range(4):
            yield "structure-reader" if i%2==0 else "exception-challenger",[str(i)],["issue."+str(i)],{"n":i},{}
    def dispatch(repo,phase,role,selected,issues,request,schema,retry=False):
        allowance(authorization,task=selected[0],issues=issues).reserve(digest(request))
        return {"task":selected[0],"status":"FAILED","error":"E_DEPENDENCY"}
    monkeypatch.setattr(module,"tasks_for",tasks)
    monkeypatch.setattr(module,"dispatch",dispatch)
    result=module.run(authorization.parent,"coverage",workers=2)
    assert result["used"]==2
    progress=json.loads((authorization.parent/"coverage-progress.json").read_text())
    assert progress["provider_failure_streak"]==2 and len(progress["rows"])==2


def test_authority_xml_selection_ignores_schedule_parts_and_rejects_ambiguity():
    import xml.etree.ElementTree as ET
    from assurance_gap_authorities import operative_part_four
    ns="http://www.xml.gov.hk/schemas/hklm/1.0"
    sections="".join('<section temporalId="'+s+'"/>' for s in ("s103","s104","s105"))
    body='<part name="P4" temporalId="P4">'+sections+'</part>'
    other='<schedule><part name="P4" temporalId="sch10_P4">Unrelated transitional provisions</part></schedule>'
    tree=ET.fromstring('<root xmlns="'+ns+'"><main>'+body+other+'</main></root>')
    assert operative_part_four(tree).get("temporalId")=="P4"
    for changed in (other,body+body):
        tree=ET.fromstring('<root xmlns="'+ns+'"><main>'+changed+'</main></root>')
        with raises_code("E_REFERENCE"):
            operative_part_four(tree)


def test_authority_chapter_selection_rejects_contents_and_ambiguous_body():
    from assurance_gap_authorities import operational_chapter
    contents="Chapter 6: Operational requirements 18\nMember register 19\nChapter 7: Investment: core requirements 24\n"
    body="Chapter 6: Operational requirements\n6.1 Schemes issue documents\n6.8 Maintain register\n6.9 Investment plans\nChapter 7: Investment: core requirements\n"
    assert "6.8 Maintain register" in operational_chapter(contents+body)
    for text in (contents,contents+body+body):
        with raises_code("E_REFERENCE"):
            operational_chapter(text)


def test_corrected_authority_source_uses_same_task_and_second_spent_attempt(authorization,monkeypatch):
    import importlib.util
    from types import SimpleNamespace
    path=Path(__file__).resolve().parents[2]/"scripts/run_assurance_gap_continuation.py"
    spec=importlib.util.spec_from_file_location("supplemental_authority_retry_test",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,"BASE",Path("."))
    monkeypatch.setattr(module,"validator",lambda *a: lambda value:value)
    class Provider:
        def __init__(self,allowance):self.allowance=allowance
        def complete(self,wire,schema,settings):
            slot=self.allowance.reserve(digest(wire))
            return SimpleNamespace(value={"slot":slot},provenance={"allowance_slot":slot})
    monkeypatch.setattr(module,"CodexProvider",Provider)
    request={"source_packet":{"units":[{"unit_id":"part4","text":"wrong schedule part"}]},
             "instructions":"Review supplied source"}
    args=(authorization.parent,"authority","structure-reader",["question"],["issue.0"])
    first=module.dispatch(*args,request,{})
    changed=deepcopy(request);changed["source_packet"]["units"][0]["text"]="Operative investment provisions"
    assert module.dispatch(*args,changed,{})==first
    second=module.dispatch(*args,changed,{},retry=True)
    assert first["task"]==second["task"] and second["value"]["slot"]==2
    assert module.dispatch(*args,changed,{},retry=True)==second
    third=deepcopy(changed);third["source_packet"]["units"][0]["text"]="Another change"
    assert module.dispatch(*args,third,{},retry=True)==second
    assert allowance(authorization).verify()["used"]==2
    results=list(authorization.parent.glob("tasks/*/attempt-*/result.json"))
    assert len(results)==2 and all(json.loads(p.read_text())["status"]=="VALIDATED" for p in results)


def test_nested_record_tables_preserve_full_request_and_reject_shape_mutation():
    records=[{"obligation_identity":"identity."+str(i),"candidate_identity":"candidate."+str(i),
              "rationale":"Unique substantial explanation number "+str(i),
              "evidence":[{"unit_id":"source","quote":"Exact source quote "+str(j)} for j in range(4)]}
             for i in range(12)]
    original={"source_packet":{"units":[{"unit_id":"source","text":"Literal complete source"}]},
              "obligations":records,"candidates":{str(i):r for i,r in enumerate(records)}}
    wire=repair.encode(original)
    assert "record_columns" in wire["obligations"]
    assert "record_entries" in wire["candidates"]
    assert wire["source_packet"]==original["source_packet"]
    assert repair.decode(wire,digest(original))==original
    assert len(canonical(wire))<len(canonical(original))
    for mode in ("duplicate_column","dropped_value","changed_value"):
        changed=deepcopy(wire)
        if mode=="duplicate_column":
            changed["obligations"]["record_columns"][0]=changed["obligations"]["record_columns"][1]
        elif mode=="dropped_value":
            changed["obligations"]["record_rows"][0].pop()
        else:changed["obligations"]["record_rows"][0][0]="different"
        with raises_code("E_INTEGRITY"):repair.decode(changed,digest(original))


def test_legacy_pool_receipts_remain_decodable():
    original=example_request();wire=repair.encode(original)
    wire["context_encoding"]["profile"]=repair.POOL_V1
    assert repair.decode(wire,digest(original))==original


def test_record_table_of_nested_pooled_references_reconstructs_strings():
    text="A long shared source statement whose exact content must survive repeated references."
    original={"source_packet":{"units":[]},"values":[text]*12,
              "nested":[{"long_identity_key":"id."+str(i),"long_question_key":text} for i in range(12)]}
    assert repair.decode(repair.encode(original),digest(original))==original


def test_integration_authority_citations_require_unchanged_declared_sources(tmp_path):
    from run_assurance_gap_continuation import integration_citation_packet
    from legalmath.interpretation.assurance.semantics import check_quotes
    source=tmp_path/"authority.txt";source.write_text("Section 6.8 requires a register.")
    packet={"units":[{"unit_id":"original","text":"Original circular."}]}
    context={"units":[{"unit_id":"authority","text":source.read_text(),"locator":"authority.txt"}]}
    path=tmp_path/"context.json";path.write_text(json.dumps(context))
    evidence={"complete_reviewed_context":{"path":"context.json","sha256":raw_digest(path.read_bytes())},
              "quoted_source_unit_metadata":{"authority":{"source_locator":"authority.txt","source_sha256":raw_digest(source.read_bytes())}}}
    request={"new_evidence":{"authority_evidence":evidence}}
    combined=integration_citation_packet(tmp_path,request,packet)
    check_quotes([{"unit_id":"authority","quote":source.read_text()}],combined)
    assert len(packet["units"])==1
    with raises_code("E_REFERENCE"):
        check_quotes([{"unit_id":"authority","quote":"Invented authority."}],combined)
    changed=deepcopy(request)
    changed["new_evidence"]["authority_evidence"]["quoted_source_unit_metadata"]["foreign"]={}
    with raises_code("E_REFERENCE"):integration_citation_packet(tmp_path,changed,packet)
    source.write_text("Changed source")
    with raises_code("E_INTEGRITY"):integration_citation_packet(tmp_path,request,packet)
    path.write_text("{}")
    with raises_code("E_INTEGRITY"):integration_citation_packet(tmp_path,request,packet)
