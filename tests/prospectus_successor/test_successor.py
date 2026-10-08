"""Development counterexamples: engineering tests, never independent legal labels."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import pytest
from legalmath.prospectus.successor.contracts import VERSION, digest
from legalmath.prospectus.successor import source_graph, contract_assembly, clause_graph, law_facts
from legalmath.prospectus.successor.service import assess
from legalmath.prospectus.successor.financial_profiles import add_months
from legalmath.prospectus.successor.evaluation import score
from legalmath.prospectus.successor.release import assess as release
from legalmath.prospectus.legal_review import AUTHORITY_FACTS

PREFIX = "The Notes are unsecured obligations of the Issuer. The Notes will be redeemed at 100 per cent of their principal amount at maturity. "
TIME = "2026-01-01T00:00:00Z"


def legal_inputs(r, tmp_path):
    graph = source_graph.build(r["bundle"], tmp_path)
    u = graph["units"][0]
    source = {"unit":u["id"],"document":u["document"],"source_sha256":u["source_sha256"],
              "start":0,"end":len(u["raw"]),"quote":u["raw"]}
    basis = {"id":"law","authority":"synthetic","jurisdiction":"X","edition":"1","source":source,
             "valid_from":TIME,"known_from":TIME,"premises":list(AUTHORITY_FACTS),"instrument_id":"synthetic"}
    facts = [{"name":n,"basis_id":"law","instrument_id":"synthetic","jurisdiction":"X","value":True,
              "source":source,"valid_from":TIME,"known_from":TIME,"observed_at":TIME} for n in AUTHORITY_FACTS]
    return graph, basis, facts


def request(tmp_path, texts):
    path=tmp_path/"source.txt"
    path.write_text("\f".join(texts))
    bundle={"instrument_id":"synthetic", "purpose":"review","issue_date":TIME,
        "effective_at":TIME,"known_at":TIME,"documents":[{"id":"d","path":str(path),
        "sha256":digest(path.read_bytes()),"format":"text","language":"en","authority":"synthetic",
        "document_date":TIME,"known_from":TIME}],"dependencies":[]}
    graph=source_graph.build(bundle,tmp_path)
    operations=[{"unit":u["id"],"role":"OPERATIVE","reason":"Explicit complete synthetic source",
        "source_text_sha256":u["text_sha256"],"context":"whole"} for u in graph["units"]]
    return {"version":VERSION,"bundle":bundle,"assembly":{"operations":operations},
        "scope":{q:{"complete":True,"reason":"Constructed source"} for q in ("Q1","Q2")}}


@pytest.mark.parametrize("name,texts,q,allowed",[
    ("F01-repayment",[PREFIX],"Q1",{"NO"}),
    ("F02-write-down",[PREFIX+"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."],"Q1",{"YES"}),
    ("F03-blank",[PREFIX,""],"Q1",{"UNKNOWN"}),
    ("F04-unpaid",[PREFIX+"Upon a Solvency Event, the Issuer's obligation to repay the principal of the Notes ceases permanently without payment."],"Q1",{"YES","UNKNOWN"}),
    ("F05-condition",[PREFIX+"The payment obligations under the Notes are subject to Condition 14 of the Agency Agreement."],"Q1",{"UNKNOWN"}),
    ("F06-example",[PREFIX+"The following sentence is a non-operative example and has no legal effect: the Notes shall be converted into ordinary shares."],"Q2",{"NO","UNKNOWN"}),
    ("F07-holder",[PREFIX+"Conversion is solely at the holder's option. On exercise of that option, the Notes shall be converted into ordinary shares."],"Q2",{"NO","UNKNOWN"}),
    ("F08-page-scope",[PREFIX+"Conversion is solely at the holder's option.","On exercise of that option, the Notes shall be converted into ordinary shares."],"Q2",{"NO","UNKNOWN"}),
    ("F09-distant-exception",[PREFIX+"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero.","An exception elsewhere disapplies the reduction for this series."],"Q1",{"UNKNOWN"}),
    ("F10-actor-swap",[PREFIX+"Conversion is solely at the issuer's option. On exercise of that option, the Notes shall be converted into ordinary shares."],"Q2",{"UNKNOWN"}),
    ("F11-coupon",[PREFIX+"The issuer may cancel interest payments."],"Q1",{"NO","UNKNOWN"}),
    ("F12-paid-cancellation",[PREFIX+"The Notes will be cancelled after payment in full."],"Q1",{"NO","UNKNOWN"}),
    ("F13-discharge",[PREFIX+"All remaining principal claims shall be discharged without payment."],"Q1",{"YES","UNKNOWN"}),
    ("F14-creditor-vote",[PREFIX+"The holders may vote to amend the principal payable."],"Q1",{"UNKNOWN"}),
    ("F15-authority",[PREFIX+"The resolution authority may impose principal loss without holder consent."],"Q4",{"UNKNOWN"}),
    ("F16-preferred",[PREFIX+"The issuer may convert the Notes into common or preferred shares."],"Q2",{"NO","UNKNOWN"}),
    ("F17-cash",[PREFIX+"The issuer may elect cash or ordinary shares."],"Q2",{"NO","UNKNOWN"}),
    ("F18-veto",[PREFIX+"The holder may convert, subject to the issuer's veto."],"Q2",{"NO","UNKNOWN"}),
    ("F19-negation",[PREFIX+"The issuer cannot convert except after a Trigger Event."],"Q2",{"UNKNOWN"}),
    ("F20-cycle",[PREFIX+"Condition 2 refers to Condition 3. Condition 3 refers to Condition 2 and missing Condition 14."],"Q1",{"UNKNOWN"}),
    ("F21-supplement",[PREFIX+"A supplement replaces the repayment promise with unpaid discharge."],"Q1",{"UNKNOWN"}),
    ("F22-amendment",[PREFIX+"A post-issue amendment changes the conversion right."],"Q2",{"UNKNOWN"}),
    ("F23-language",[PREFIX+"The German controlling text differs from this English translation."],"Q1",{"UNKNOWN"}),
    ("F24-margin",[PREFIX+"Delete this guarantee if BASF SE is selected."],"Q1",{"UNKNOWN"}),
    ("F25-unselected",[PREFIX+"An unselected schedule provides for principal write-down."],"Q1",{"UNKNOWN"}),
    ("F26-duplicate",[PREFIX+"Condition 1 permits a write-down. Condition 1 prohibits write-down."],"Q1",{"UNKNOWN","CONFLICT"}),
    ("F27-successor",[PREFIX+"There is no initial guarantee, but a successor substitution requires a guarantee."],"Q1",{"UNKNOWN"}),
    ("F28-conjunct",[PREFIX+"The issuer has acquired 75 percent but has not reduced the global note."],"Q5",{"UNSUPPORTED"}),
    ("F29-acknowledgment",[PREFIX+"The holder acknowledges bail-in powers."],"Q4",{"UNKNOWN"}),
    ("F30-conventions",[PREFIX+"Settlement depends on an unspecified holiday calendar and rounding rule."],"Q5",{"UNSUPPORTED"}),
])
def test_development_screen(tmp_path,name,texts,q,allowed):
    assert assess(request(tmp_path,texts),tmp_path)["questions"][q]["status"] in allowed


def test_repeated_sentences_do_not_crash(tmp_path):
    r=request(tmp_path,[PREFIX + PREFIX])
    assert assess(r,tmp_path)["questions"]["Q1"]["status"] in {"NO","UNKNOWN"}


def test_source_mutation_rejected(tmp_path):
    r=request(tmp_path,[PREFIX])
    (tmp_path/"source.txt").write_text("changed")
    with pytest.raises(ValueError,match="bytes changed"):assess(r,tmp_path)


def test_removed_semantics_cannot_certify_coverage(tmp_path):
    r=request(tmp_path,[PREFIX+"A distant clause eliminates the repayment right."])
    g=source_graph.build(r["bundle"],tmp_path)
    a=contract_assembly.assemble(g,r["assembly"])
    r["clauses"]=clause_graph.nominate(a)[:2]
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"


def test_unrelated_missing_dependency_is_local(tmp_path):
    r=request(tmp_path,[PREFIX])
    r["bundle"]["dependencies"]=[{"id":"missing-income","questions":["Q5"],"status":"UNRESOLVED"}]
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="NO"


def test_typed_conflict(tmp_path):
    r=request(tmp_path,[PREFIX+"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."])
    g=source_graph.build(r["bundle"],tmp_path)
    a=contract_assembly.assemble(g,r["assembly"])
    r["clauses"]=clause_graph.nominate(a)
    rival=deepcopy(r["clauses"][-1]);rival.update(id="rival",polarity=False)
    r["clauses"].append(rival)
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="CONFLICT"


def test_excluded_text_cannot_become_positive(tmp_path):
    r=request(tmp_path,["Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."])
    r["assembly"]["operations"][0]["role"]="EXCLUDED"
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]!="YES"


def test_month_order_and_missing_convention():
    first=add_months("2023-03-31",1,"CLAMP")
    assert add_months(first,1,"CLAMP")=="2023-05-30"
    assert add_months("2023-03-31",2,"CLAMP")=="2023-05-31"
    with pytest.raises(ValueError):add_months("2023-03-31",1,"ERROR")
    with pytest.raises(ValueError):add_months("2023-03-31",1,None)


def test_dated_authority_counterfactual(tmp_path):
    r=request(tmp_path,[PREFIX])
    g, basis, facts = legal_inputs(r, tmp_path)
    assert law_facts.assess(r["bundle"],[basis],facts,g)["status"]=="YES"
    basis["known_from"]="2027-01-01T00:00:00Z"
    assert law_facts.assess(r["bundle"],[basis],facts,g)["status"]=="UNKNOWN"


def test_no_independent_review_no_release():
    ev=score([],[],[{"id":"case","questions":["Q1"]}],{})
    assert ev["status"]=="BLOCKED_INDEPENDENT_REVIEW"
    assert release(ev,[],[])["status"]=="BLOCKED"

def test_missing_dispositions_cannot_certify_negative(tmp_path):
    r=request(tmp_path,[PREFIX])
    r.pop("assembly")
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"


def test_one_recognized_sentence_does_not_erase_unknown(tmp_path):
    r=request(tmp_path,[PREFIX+"Loss is possible under an unfamiliar provision."])
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"


def test_lone_coupon_is_not_absence_evidence(tmp_path):
    r=request(tmp_path,["Coupon may be cancelled."])
    g=source_graph.build(r["bundle"],tmp_path);a=contract_assembly.assemble(g,r["assembly"])
    n=clause_graph.nominate(a)[0];n["effect"]="coupon";r["clauses"]=[n]
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"


def test_broad_nonoperative_phrase_does_not_hide_loss(tmp_path):
    r=request(tmp_path,[PREFIX+"Unlike a non-operative example, this clause has no legal effect only before the trigger: thereafter principal disappears without payment."])
    assert assess(r,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"




def test_bound_substitution_and_stale_edit(tmp_path):
    r=request(tmp_path,["The Notes pay [rate].","4 percent"])
    g=source_graph.build(r["bundle"],tmp_path)
    first,second=g["units"]
    op=r["assembly"]["operations"][0]
    op["edits"]=[{"start":14,"end":20,"old":"[rate]","new":"4 percent","reason":"Final terms field",
        "basis":[{"unit":second["id"],"quote":second["raw"]}]}]
    a=contract_assembly.assemble(g,r["assembly"])
    assert a["units"][0]["text"]=="The Notes pay 4 percent."
    assert a["operations"][0]["basis"][0]["source_sha256"]==second["source_sha256"]
    op["edits"][0]["old"]="wrong"
    with pytest.raises(ValueError):contract_assembly.assemble(g,r["assembly"])


def test_issue_time_excludes_later_amendment(tmp_path):
    r=request(tmp_path,[PREFIX])
    r["bundle"]["purpose"]="issue_formation"
    r["bundle"]["documents"][0]["document_date"]="2026-02-01T00:00:00Z"
    out=assess(r,tmp_path)
    assert not out["source_map"]["documents"][0]["visible"]
    assert out["questions"]["Q1"]["status"]=="UNKNOWN"


def test_financial_missing_premises_and_wrong_source(tmp_path):
    from legalmath.prospectus.successor.financial_profiles import assess as financial
    from legalmath.prospectus.closure_mechanisms import PROFILES
    key="bbva-at1-series15-2025"
    bundle={"instrument_id":key,"documents":[{"sha256":PROFILES[key]["sha256"]}]}
    scenario={"issue_id":key,"source_sha256":PROFILES[key]["sha256"],"premise_kind":"HYPOTHETICAL"}
    assert financial(bundle,scenario)["status"]=="UNSUPPORTED"
    bundle["documents"][0]["sha256"]="0"*64
    with pytest.raises(ValueError):financial(bundle,scenario)


def test_legal_fact_conflict_is_retained(tmp_path):
    r=request(tmp_path,[PREFIX])
    g, b, facts = legal_inputs(r, tmp_path)
    facts.append({**facts[0],"value":False})
    assert law_facts.assess(r["bundle"],[b],facts,g)["status"]=="CONFLICT"


def test_controller_receipt_mutation_invalidates_descendant(tmp_path,monkeypatch):
    from legalmath.prospectus.successor import controller as c
    from legalmath.prospectus.successor.contracts import write
    monkeypatch.setattr(c,"bindings",lambda root,phase=None:{"code":"fixed"})
    state={}
    for phase in ("P0","P1"):
        p=tmp_path/phase;p.mkdir()
        write(p/"result.json",{"value":1})
        write(p/"receipt.json",{"outputs":{"result.json":digest((p/"result.json").read_bytes())}})
        state[phase]={"method":digest({"code":"fixed"}),"artifact_ready":True,
            "dependencies":{d:state[d]["receipt_sha256"] for d in c.DAG[phase]},
            "directory":phase,"receipt_sha256":digest((p/"receipt.json").read_bytes())}
    assert c.current(tmp_path,state)["P1"]
    (tmp_path/"P0/result.json").write_text("mutated")
    current=c.current(tmp_path,state)
    assert not current["P0"] and not current["P1"]


def test_evaluator_accounts_for_finite_denominator():
    cohort=[{"id":"a","questions":["Q1"]},{"id":"b","questions":["Q1"]}]
    ids={"readers":["r1","r2"],"adjudicator":"r3","implementer":"author"}
    labels=[{"id":k,"question":"Q1","value":v,"blinded":True,"readers":["r1","r2"],
             "adjudicator":"r3","cohort_sha256":digest(cohort),
             "evidence":[{"source_sha256":"a"*64,"quote":"s","start":0,"end":1}]}
        for k,v in [("a","YES"),("b","NO")]]
    predictions=[{k:r[k] for k in ("id","question","value")} for r in labels]
    out=score(predictions,labels,cohort,ids,"b"*64)
    assert out["counts"]["Q1"]["correct_positive"]==1
    assert out["counts"]["Q1"]["correct_negative"]==1
    assert out["counts"]["Q1"]["N"]==2
    with pytest.raises(ValueError):score(predictions[:1],labels,cohort,ids,"b"*64)


def test_guarded_release_needs_both_positive_and_negative():
    ev={"status":"FINITE_DESCRIPTIVE_ONLY","counts":{"Q1":{"W":0,"C":1,"undecidable":0}}}
    assert release(ev,[{"question":"Q1"}],[{"reviewer":"a","accepted":True},{"reviewer":"b","accepted":True}])["status"]=="BLOCKED"
