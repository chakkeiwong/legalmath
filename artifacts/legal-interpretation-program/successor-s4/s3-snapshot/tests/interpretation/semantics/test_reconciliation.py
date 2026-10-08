from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from legalmath.canonical import digest, canonical, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics import integration
from legalmath.interpretation.semantics.reconciliation import reconcile, validate_entry
from legalmath.interpretation.semantics.sourced import context
from scripts.legal_interpretation_successor_data import retained_inputs, make_reconciliation, policy, execute_product

ROOT=Path(__file__).resolve().parents[3]
AT="2026-10-06T00:00:00.000000Z"
def options(semantics="grounded"):
    return {"profile":integration.PROFILE,"settings":[policy(semantics).model_dump(mode="json")],"case_limit":2}
@pytest.fixture(scope="module")
def retained():
    return retained_inputs(ROOT)

def test_every_original_role_formula_and_source_is_retained(retained):
    packet,overlay,candidates,questions,table=retained
    value=reconcile(packet,overlay,table,questions)
    assert (value["reading_count"],value["role_count"])==(35,70)
    assert sum(e["repair_records_present"] for e in value["entries"].values())==12
    original={(r["reading_id"],r["role"]):r for r in overlay["records"]}
    for cid,entry in value["entries"].items():
        assert entry["original_reading"]==candidates[cid]
        assert entry["legal_equivalence"]=="NOT_ESTABLISHED"
        for record in entry["records"]:
            assert record==original[cid,record["role"]]
        assert entry["claims"] and entry["source_warrant"]["sources"]
        validate_entry(entry,packet,cid,candidates[cid],questions[cid])

@pytest.mark.parametrize("mutation",["quote","record","reading","question","omission","formula"])
def test_reconciliation_rejects_changed_premises(retained,mutation):
    packet,overlay,candidates,questions,table=deepcopy(retained)
    value=reconcile(packet,overlay,table,questions)
    cid=next(iter(candidates));entry=value["entries"][cid]
    if mutation=="quote":entry["claims"][0]["sources"][0]["quote"]="invented"
    if mutation=="record":entry["records"][0]["operative"]["reading"]["explanation"]="changed"
    if mutation=="reading":candidates[cid]["distinction"]="changed"
    if mutation=="question":questions[cid]["actor"]="unrelated"
    if mutation=="formula":entry["original_reading"]["formalization"]={"facts":[],"scope":"true","result":"false","result_type":"bool"}
    with pytest.raises(LegalMathError):
        if mutation=="omission":
            table.pop(cid);reconcile(packet,overlay,table,questions)
        else:validate_entry(entry,packet,cid,candidates[cid],questions[cid])

@pytest.mark.parametrize("mutation",["pilot_quote","pilot_source","pilot_question","relation"])
def test_comparison_warrants_are_checked_independently(retained,mutation):
    packet,overlay,candidates,questions,table=deepcopy(retained)
    cid=next(iter(table))
    span=table[cid]["pilot_clauses"][0]["clauses"][0]["sources"][0]
    if mutation=="pilot_quote":span["quote"]="X"+span["quote"][1:]
    if mutation=="pilot_source":span["source_hash"]="0"*64
    if mutation=="pilot_question":span["request_hash"]="0"*64
    if mutation=="relation":table[cid]["relation"]="established legal equivalence"
    with pytest.raises(LegalMathError):
        reconcile(packet,overlay,table,questions)

def test_all_historical_branches_keep_distinct_ids_and_questions(retained):
    packet,overlay,candidates,questions,table=retained
    rec=reconcile(packet,overlay,table,questions)
    rows=integration.inventory(packet,candidates,questions,options(),AT,context(reconciliation=rec))
    assert len(rows)==35 and len({r["branch"]["proposal_id"] for r in rows})==35
    assert len({r["branch"]["legacy_reading_hash"] for r in rows})==35
    assert all(len(r["branch"]["clauses"])>1 and r["branch"]["unresolved"] for r in rows)
    graph=integration.reasoning(rows,packet,candidates,questions,context(reconciliation=rec))
    assert len(next(iter(graph.values()))["unencoded_candidates"])==35

def fixture():
    from tests.assurance.support import packet,reading
    p=packet();a=reading();b=deepcopy(a);b["local_id"]="alternative"
    candidates={"a":a,"b":b}
    questions={cid:{"actor":"distributor","question":"test","control_id":"test"} for cid in candidates}
    evidence=a["citations"]
    def arg(name,negative=False,parents=None):
        return {"argument_id":name,"candidate_id":"a" if name=="a" else "b","premises":[],
                "parents":parents or [],"inference_id":"rule."+name,"inference_kind":"DEFEASIBLE",
                "inference":"Declared conditional source warrant","conclusion":{"atom":"p","negative":negative},"evidence":evidence}
    criticism={"arguments":[arg("a"),arg("b",True)],"attacks":[
        {"attacker":"a","target":"b","kind":"REBUT","target_component":"b","rationale":"Declared contrary"},
        {"attacker":"b","target":"a","kind":"REBUT","target_component":"a","rationale":"Declared contrary"}],
        "preferences":[],"cases":[],"case_queries":[],"questions":[]}
    return p,candidates,questions,criticism

def evaluate_fixture(p,c,q,crit,semantics="grounded"):
    opts=options(semantics);ctx=context(crit)
    rows=integration.inventory(p,c,q,opts,AT,ctx)
    return next(iter(integration.reasoning(rows,p,c,q,ctx).values()))

@pytest.mark.parametrize("semantics",["grounded","preferred"])
def test_typed_rebuttals_actually_change_extensions_and_branch_membership(semantics):
    p,c,q,crit=fixture()
    result=evaluate_fixture(p,c,q,crit,semantics)
    expected=[[]] if semantics=="grounded" else [["a"],["b"]]
    assert result["evaluation"]["extensions"]==expected
    assert len(result["theory"]["attacks"])==2
    assert {m["acceptance"] for m in result["candidate_membership"].values()}==({"none"} if semantics=="grounded" else {"some"})
    if semantics=="grounded":
        assert result["evaluation"]["extensions"][0]==result["criticism_evaluation"]["semantics"]["grounded"]
    else:
        assert result["evaluation"]["extensions"]==result["criticism_evaluation"]["semantics"]["stable_extensions"]

@pytest.mark.parametrize("kind",["UNDERMINE","UNDERCUT"])
def test_premise_and_inference_attacks_are_checked_and_propagated(kind):
    p,c,q,crit=fixture()
    a,b=crit["arguments"]
    if kind=="UNDERMINE":
        b["premises"]=[{"premise_id":"premise.b","proposition":a["conclusion"]|{"negative":True},
                        "kind":"ORDINARY","status":"SUPPORTED","evidence":a["evidence"],"explanation":"Proposed premise"}]
        target="premise.b"
    else:
        a["conclusion"]={"atom":"applicable.rule.b","negative":True};target="rule.b"
    crit["attacks"]=[{"attacker":"a","target":"b","kind":kind,"target_component":target,"rationale":"Test named target"}]
    descendant={**deepcopy(b),"argument_id":"child","inference_id":"rule.child","parents":["b"],"premises":[]}
    crit["arguments"].append(descendant)
    r=evaluate_fixture(p,c,q,crit)
    assert r["evaluation"]["extensions"]==[["a"]]
    assert {tuple(x) for x in r["criticism_evaluation"]["defeats"]}=={("a","b"),("a","child")}

def test_unknown_premise_priority_and_cases_never_supply_authority():
    p,c,q,crit=fixture()
    crit["arguments"][0]["premises"]=[{"premise_id":"needed","proposition":{"atom":"fact","negative":False},
        "kind":"ORDINARY","status":"QUESTIONED","evidence":[],"explanation":"Absent evidence"}]
    crit["preferences"]=[{"preferred":"a","over":"b","evidence":crit["arguments"][0]["evidence"],"rationale":"Unestablished priority"}]
    r=evaluate_fixture(p,c,q,crit)
    assert r["evaluation"]["extensions"]==[["b"]]
    assert r["criticism_evaluation"]["blocked_arguments"]==["a"]
    assert r["criticism_evaluation"]["preference_proposals"]
    assert r["legal_acceptance"]=="NOT_ESTABLISHED"

@pytest.mark.parametrize("mutation",["quote","target","candidate"])
def test_invalid_criticism_rejected_before_graph_construction(mutation):
    p,c,q,crit=fixture()
    if mutation=="quote":crit["arguments"][0]["evidence"][0]["quote"]="not in source"
    elif mutation=="target":crit["attacks"][0]["target_component"]="wrong"
    else:crit["arguments"][0]["candidate_id"]="missing"
    with pytest.raises(LegalMathError):evaluate_fixture(p,c,q,crit)

def test_cycles_and_larger_preferred_theories_remain_incomplete():
    p,c,q,crit=fixture()
    crit["arguments"][0]["parents"]=["b"];crit["arguments"][1]["parents"]=["a"]
    assert evaluate_fixture(p,c,q,crit)["evaluation"]["completion"]=="incomplete"
    p,c,q,crit=fixture();crit["attacks"]=[]
    for i in range(7):
        crit["arguments"].append({**deepcopy(crit["arguments"][0]),"argument_id":"extra."+str(i),"inference_id":"extra.rule."+str(i)})
    r=evaluate_fixture(p,c,q,crit,"preferred")
    assert r["evaluation"]["completion"]=="incomplete"
    assert r["evaluation"]["reason"]=="reference-subset-limit"

@pytest.fixture(scope="module")
def actual_product():
    with TemporaryDirectory(prefix="sourced-complete-",dir=ROOT/"artifacts") as directory:
        yield execute_product(directory)

def test_actual_complete_route_binds_criticism_and_reexecutes_java(actual_product):
    from legalmath.interpretation.assurance.complete_investigation import verify
    from legalmath.interpretation.assurance import investigation_observations as obs
    root,runner,dossier=actual_product
    assert verify(root,dossier)["execution_complete"]
    result=dossier["semantic_stage"]["report"]
    assert all(len(g["theory"]["attacks"])==2 for g in result["reasoning"].values())
    grounded=next(g for g in result["reasoning"].values() if g["evaluation"]["semantics"]=="grounded")
    assert grounded["evaluation"]["extensions"]==[[]]
    assert all(r["target"]["java"]=="EXECUTED" for r in result["branch_reports"])
    assert obs.check_stages(root,dossier,obs.method(runner),runner)["semantic_summary_hash"]

def test_criticism_change_invalidates_receipt_and_branch_identity(actual_product):
    root,runner,dossier=actual_product
    path=root/dossier["semantic_stage"]["directory"]
    inputs=loads((path/"inputs.json").read_bytes())
    bad=deepcopy(inputs["context"]);bad["criticism"]["attacks"]=[]
    args=[inputs[k] for k in ("packet","candidates","questions","options","at")]
    with pytest.raises(LegalMathError):
        integration.verify(path,*args,jdk=runner.jdk,context=bad)
    original=integration.inventory(*args,context=inputs["context"])
    changed=integration.inventory(*args,context=bad)
    assert {digest(r["branch"]) for r in original}.isdisjoint({digest(r["branch"]) for r in changed})
