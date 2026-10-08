"""Forward regressions for the demonstrated production defects."""
from copy import deepcopy
import itertools
import pytest
from test_successor import request, legal_inputs, PREFIX, TIME
from legalmath.prospectus.successor import service, clause_graph, source_graph, contract_assembly
from legalmath.prospectus.successor.contracts import digest, write
from legalmath.prospectus.successor.law_facts import assess as law
from legalmath.prospectus.successor.financial_profiles import assess as financial
from legalmath.prospectus.successor.predicates import decide
from legalmath.prospectus.successor import controller, evaluation, release, integration
from legalmath.prospectus.closure_mechanisms import PROFILES, whole_shares

def test_all_declared_premises_participate_and_dates_are_bitemporal(tmp_path):
    r = request(tmp_path, [PREFIX])
    g, b, facts = legal_inputs(r, tmp_path)
    b["premises"].append("additional_condition")
    facts.append({**facts[0], "name":"additional_condition", "value":False})
    assert law(r["bundle"], [b], facts, g)["status"] == "NO"
    facts[-1]["value"] = True
    facts[-1]["valid_from"] = "2027-01-01T00:00:00Z"
    assert law(r["bundle"], [b], facts, g)["status"] == "UNKNOWN"
    facts[-1]["valid_from"] = TIME
    facts[-1]["source"] = "free-form"
    with pytest.raises(ValueError):
        law(r["bundle"], [b], facts, g)

def test_partial_truth_tables_and_correlated_conditions():
    formulas = [{"all":["a","b"]}, {"any":["a",{"not":"b"}]}, {"all":["a",{"not":"a"}]},
                {"any":["a",{"not":"a"}]}]
    for expr in formulas:
        for a,b in itertools.product((None,True,False), repeat=2):
            result = decide(expr, {"a":a,"b":b})
            from legalmath.prospectus.successor.predicates import evaluate
            outcomes = {evaluate(expr, {"a":x,"b":y}) for x in ((True,False) if a is None else (a,))
                        for y in ((True,False) if b is None else (b,))}
            assert result["status"] == ("YES" if outcomes == {True} else "NO" if outcomes == {False} else "UNKNOWN")
    with pytest.raises(ValueError, match="twelve"):
        decide({"all":[f"a{i}" for i in range(13)]}, {})

def test_negative_conditions_conversion_subquestions_and_scope(tmp_path):
    r=request(tmp_path,[PREFIX+"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."])
    g=source_graph.build(r["bundle"],tmp_path); a=contract_assembly.assemble(g,r["assembly"])
    nodes=clause_graph.nominate(a)
    nodes[-1].update(polarity=False, conditions={"any":["condition",{"not":"condition"}]})
    r["clauses"]=nodes
    assert service.assess(r,tmp_path)["questions"]["Q1"]["status"]=="NO"
    nodes[-1].update(polarity=True,effect="conversion",assets=["common","preferred"],election="issuer",modality="may")
    out=service.assess(r,tmp_path)["questions"]
    assert out["Q2"]["subquestions"]["possible_common"]["status"]=="YES"
    assert out["Q2"]["subquestions"]["common_only"]["status"]=="NO"
    assert out["Q2"]["subquestions"]["compulsory_common"]["status"]=="NO"
    r["scope"]["Q4"]={"complete":True,"reason":"Scope declaration cannot supply missing authority"}
    assert service.assess(r,tmp_path)["questions"]["Q3"]["status"]=="PARTIAL"

def test_duplicate_and_multiline_occurrences_are_covered(tmp_path):
    r=request(tmp_path,[PREFIX+PREFIX])
    out=service.assess(r,tmp_path)
    assert out["questions"]["Q1"]["status"]=="NO"
    assert not out["clause_graph"]["uncovered_units"]
    r=request(tmp_path,["The Notes are unsecured obligations","of the Issuer. The Notes will be redeemed at 100 per cent","of their principal amount at maturity."])
    out=service.assess(r,tmp_path)
    assert out["questions"]["Q1"]["status"]=="NO"
    assert any(len(n["spans"])>1 for n in out["clause_graph"]["nodes"])
    assert not out["clause_graph"]["uncovered_units"]

def test_excluded_reference_does_not_poison_other_questions(tmp_path):
    r=request(tmp_path,[PREFIX,"Header Condition 99"])
    r["assembly"]["operations"][-1]["role"]="HEADER"
    assert service.assess(r,tmp_path)["questions"]["Q1"]["status"]=="NO"

def test_distinct_legal_holders_with_identical_names_do_not_merge():
    holdings=[{"legal_holder_id":key,"registration_name":"Same name","principal":"5"} for key in ("a","b")]
    assert [h["shares"] for h in whole_shares(holdings,"3","principal")]==[1,1]
    holdings[1]["legal_holder_id"]="a"
    assert whole_shares(holdings,"3","principal")[0]["shares"]==3

def test_invalid_price_shape_is_structured_even_if_event_does_not_trigger():
    key="bbva-at1-series15-2025"
    s={"issue_id":key,"source_sha256":PROFILES[key]["sha256"],"premise_kind":"HYPOTHETICAL",
       "currency":"EUR","issuer_determined_cet1_ratio":"1","capital_reduction":False,
       "condition_7_7_redemption_override":False,"listed":True,"adjusted_floor_price":"4",
       "nominal_share_value":"1","five_eligible_closing_prices":None,"holdings":[]}
    assert financial({"instrument_id":key,"documents":[PROFILES[key]]},s)["status"]=="UNSUPPORTED"

def products(tmp_path):
    r=request(tmp_path,[PREFIX])
    p1=service.source_product(r,tmp_path);p2=service.construction_product(p1,tmp_path)
    p3=service.interpretation_product(p1,p2)
    return {"P1":p1,"P2":p2,"P3":p3,"P4":service.law_product(p1,p3),"P5":service.financial_product(p1,p2,p3)}

@pytest.mark.parametrize("phase",["P2","P3","P4","P5"])
def test_consumer_rejects_mutated_phase_products(tmp_path,phase):
    ps=products(tmp_path)
    ps[phase]["payload"]["changed"]=True
    with pytest.raises(ValueError,match="content changed"):service.consume(ps,tmp_path)

def test_selected_contract_is_actually_consumed(tmp_path):
    ps=products(tmp_path); bundle=ps["P1"]["payload"]["request"]["bundle"]
    assert service.consume(ps,tmp_path)["questions"]["Q1"]["status"]=="NO"
    selected=deepcopy(ps["P2"]["payload"])
    selected["assembly"]["units"][0]["role"]="UNKNOWN"
    ps["P2"]=service.seal("P2",bundle,{"P1":ps["P1"]["sha256"]},selected)
    with pytest.raises(ValueError,match="parent bindings"):service.consume(ps,tmp_path)
    ps["P3"]=service.interpretation_product(ps["P1"],ps["P2"])
    ps["P4"]=service.law_product(ps["P1"],ps["P3"])
    ps["P5"]=service.financial_product(ps["P1"],ps["P2"],ps["P3"])
    assert service.consume(ps,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"

def test_bank_rejects_stale_type_and_question_context(tmp_path):
    r=request(tmp_path,[PREFIX]);g,b,_=legal_inputs(r,tmp_path)
    context={"instrument_id":"synthetic","instrument_kind":"senior_bond","effective_at":TIME,"known_at":TIME}
    admission={"bundle_context_sha256":digest(integration.context_identity(r["bundle"])),
               "bank_context_sha256":digest(context),"instrument_kind":"senior_bond","reason":"Same hypothetical context",
               "sources":[b["source"]]}
    bank={"request":{"bank_request":{"context":context}},"context_admission":admission}
    bank["request"]["bank_request"]["context"]["instrument_kind"]="at1_bond"
    with pytest.raises(ValueError,match="stale"):integration.investigate(r["bundle"],bank,g)

def test_implementer_cannot_adjudicate():
    with pytest.raises(ValueError,match="independent"):
        evaluation.score([],[],[{"id":"c","questions":["Q1"]}],
                         {"readers":["r1","r2"],"adjudicator":"author","implementer":"author"},"a"*64)

def test_unscored_scope_and_unbound_signoffs_block_release():
    ev={"status":"FINITE_DESCRIPTIVE_ONLY","counts":{"Q1":{"W":0,"C":2,"undecidable":0,
        "correct_positive":1,"correct_negative":1}},"cohort_sha256":"a"*64,"method_sha256":"b"*64,
        "identities":{"readers":["r1","r2"]}}
    ev["evaluation_sha256"]=digest(ev)
    assert release.assess(ev,[{"question":"Q2"}],[{"reviewer":"r1","accepted":True},{"reviewer":"r2","accepted":True}])["status"]=="BLOCKED"

def test_recover_published_receipt_after_interrupted_pointer(tmp_path):
    folder=tmp_path/controller.REL/"phases/P0/attempt-001";folder.mkdir(parents=True)
    write(folder/"result.json",{"status":"ok"})
    record={"artifact_ready":True,"method":"m","dependencies":{}}
    write(folder/"receipt.json",{"outputs":{"result.json":digest((folder/"result.json").read_bytes())},"state":record})
    recovered=controller.recover(tmp_path)
    assert recovered["P0"]["method"]=="m"
    (folder/"result.json").write_text("corrupt")
    assert not controller.recover(tmp_path)

def test_changed_evidence_admission_is_real_repair(tmp_path,monkeypatch):
    monkeypatch.setattr(controller,"bindings",lambda root,phase=None:{"code":"fixed"})
    record={"obligation_id":"test","phase":"P4","name":"cases.json","before_sha256":None,
            "content":[],"reason":"Concrete admitted empty inventory for this negative test"}
    assert controller.admit_record(tmp_path,record)["outcome"].startswith("ADMITTED")
    record["before_sha256"]=digest((tmp_path/controller.REL/"inputs/P4/cases.json").read_bytes())
    with pytest.raises(ValueError,match="unchanged"):controller.admit_record(tmp_path,record)


def test_ast_choices_fields_references_and_dated_override(tmp_path):
    from legalmath.prospectus.successor.construction_ast import render
    r=request(tmp_path,["Old principal", "New principal", "[amount]", "100", "Amended terms apply"])
    g=source_graph.build(r["bundle"],tmp_path)
    def anchor(i):
        u=g["units"][i]
        return {"unit":u["id"],"document":u["document"],"source_sha256":u["source_sha256"],
                "start":0,"end":len(u["raw"]),"quote":u["raw"]}
    spec={"version":"contract-ast.v1","root":"sequence","nodes":[
        {"id":"old","kind":"Text","source":anchor(0)},
        {"id":"new","kind":"Text","source":anchor(1)},
        {"id":"field","kind":"Field","template":anchor(2),"source":anchor(3),"value":"100","reason":"Final terms"},
        {"id":"ref","kind":"Reference","target":"field","source":anchor(2),"reason":"Declared amount"},
        {"id":"override","kind":"Override","target":"old","replacement":"new","source":anchor(4),
         "reason":"Express replacement","valid_from":TIME,"known_from":TIME},
        {"id":"choice","kind":"Choice","options":{"selected":"override","other":"old"}},
        {"id":"sequence","kind":"Sequence","children":["choice","ref"]}],
        "selections":{"choice":{"option":"selected","reason":"Final terms selection","source":anchor(4)}},
        "constraints":[{"not":"choice:other"}]}
    out=render(g,spec)
    assert out["text"]=="New principal 100" and not out["unresolved"]
    assert sum(p["end"]-p["start"] for p in out["map"])==len(out["text"])
    spec["nodes"][4]["valid_from"]="2027-01-01T00:00:00Z"
    assert render(g,spec)["text"]=="Old principal 100"
    spec["selections"]["choice"]["option"]="other"
    with pytest.raises(ValueError,match="constraint"):render(g,spec)


def test_common_only_quantifies_over_all_conversion_routes(tmp_path):
    r=request(tmp_path,[PREFIX+"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."])
    g=source_graph.build(r["bundle"],tmp_path);a=contract_assembly.assemble(g,r["assembly"])
    nodes=clause_graph.nominate(a)
    nodes[-1].update(effect="conversion",assets=["common"],election="issuer",modality="may")
    other=deepcopy(nodes[-1]);other.update(id="other-route",assets=["preferred"])
    r["clauses"]=nodes+[other]
    assert service.assess(r,tmp_path)["questions"]["Q2"]["subquestions"]["common_only"]["status"]=="NO"


def test_published_product_blob_and_post_intake_source_mutation(tmp_path):
    ps=products(tmp_path)
    folder=tmp_path/"attempt";folder.mkdir()
    write(folder/"product.json",ps["P1"])
    blobs=controller.publish_products(tmp_path,folder)
    assert len(blobs)==1
    path=tmp_path/next(iter(blobs));path.write_text("corrupted")
    with pytest.raises(ValueError,match="Corrupted"):controller.publish_products(tmp_path,folder)
    (tmp_path/"source.txt").write_text("different source")
    with pytest.raises(ValueError,match="Source bytes changed"):service.consume(ps,tmp_path)


def test_conditional_repayment_cannot_prove_absence_when_inactive(tmp_path):
    r=request(tmp_path,[PREFIX])
    g=source_graph.build(r["bundle"],tmp_path);a=contract_assembly.assemble(g,r["assembly"])
    nodes=clause_graph.nominate(a)
    nodes[-1]["conditions"]="condition"
    r.update(clauses=nodes,observations={"condition":False})
    assert service.assess(r,tmp_path)["questions"]["Q1"]["status"]=="UNKNOWN"
    r["observations"]["condition"]=True
    assert service.assess(r,tmp_path)["questions"]["Q1"]["status"]=="NO"


def test_law_phase_accepts_changed_facts_without_rebuilding_source(tmp_path):
    ps=products(tmp_path);r=ps["P1"]["payload"]["request"]
    _,basis,facts=legal_inputs(r,tmp_path)
    for value,expected in ((True,"YES"),(False,"NO")):
        facts[-1]["value"]=value
        ps["P4"]=service.law_product(ps["P1"],ps["P3"],law_input={"law_bases":[basis],"facts":facts})
        assert service.consume(ps,tmp_path)["questions"]["Q4"]["status"]==expected
    with pytest.raises(ValueError,match="declared legal basis"):
        law(r["bundle"],[],facts,ps["P1"]["payload"]["graph"])


def test_supplied_clause_cannot_hide_a_question_or_promote_example(tmp_path):
    r=request(tmp_path,[PREFIX])
    g=source_graph.build(r["bundle"],tmp_path);a=contract_assembly.assemble(g,r["assembly"])
    nodes=clause_graph.nominate(a)
    nodes[0]["questions"]=["Q2"]
    with pytest.raises(ValueError,match="question scope"):
        clause_graph.build(a,nodes)
    nodes=clause_graph.nominate(a)
    a["units"][0]["role"]="EXAMPLE"
    with pytest.raises(ValueError,match="operative assertion"):
        clause_graph.build(a,nodes)


def test_retained_ocr_preserves_occurrences_and_rejects_bad_geometry(tmp_path):
    from legalmath.prospectus.successor.source_graph import retained_ocr_units
    raw={"source_sha256":"a"*64,"page_count":1,"runtime":{"dpi":300,"language":"eng"},
         "pages":[{"page":1,"text":"A B","words":[[-0.000015,0,1,2,"A",0,0,0],[2,0,3,2,"B",0,0,1]]}]}
    path=tmp_path/"ocr.json";write(path,raw)
    doc={"id":"d","sha256":"a"*64,"language":"en","ocr":{"path":"ocr.json","sha256":digest(path.read_bytes())}}
    units,_,meta=retained_ocr_units(doc,tmp_path)
    assert units[0]["raw"]=="A B" and units[0]["words"][1]["start"]==2
    assert units[0]["words"][0]["bbox"][0]==0 and "1e-3" in meta["geometry_normalization"]
    raw["pages"][0]["words"][0][0]=-1
    write(path,raw);doc["ocr"]["sha256"]=digest(path.read_bytes())
    with pytest.raises(ValueError,match="geometry"):
        retained_ocr_units(doc,tmp_path)
