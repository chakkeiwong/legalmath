"""Audit counterexamples and service-level controls; no legal gold labels."""
from copy import deepcopy
from itertools import product
import pytest
from test_successor import request, TIME, PREFIX
from legalmath.prospectus.successor import (source_graph, contract_assembly, clause_graph,
    construction_ast, service, evaluation, predicates, occurrences, release)
from legalmath.prospectus.successor.contracts import digest, write

LOSS = "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."


def fixture(tmp_path, texts):
    req = request(tmp_path, texts)
    graph = source_graph.build(req["bundle"], tmp_path)
    return req, graph, [occurrences.anchor(u) for u in graph["units"]]


@pytest.mark.parametrize("pages", [[1, 1], [2, 1], [0, 3], [True, 2], [1, 3]])
def test_ocr_rejects_invalid_page_identity(tmp_path, pages):
    req, _, _ = fixture(tmp_path, [PREFIX])
    doc = req["bundle"]["documents"][0]
    data = {"source_sha256": doc["sha256"], "page_count": 2,
            "runtime": {"dpi": 300, "language": "eng"},
            "pages": [{"page": n, "text": "word", "words": [[0, 0, 10, 10, "word", 0, 0, 0]]} for n in pages]}
    path = tmp_path / "ocr.json"
    write(path, data)
    doc["ocr"] = {"path": "ocr.json", "sha256": digest(path.read_bytes())}
    with pytest.raises(ValueError, match="exact ordered"):
        source_graph.retained_ocr_units(doc, tmp_path)
    for n, page in enumerate(data["pages"], 1):
        page["page"] = n
    write(path, data)
    doc["ocr"]["sha256"] = digest(path.read_bytes())
    units, count, _ = source_graph.retained_ocr_units(doc, tmp_path)
    assert count == 2 and len({u["id"] for u in units}) == 2


def test_excluded_constraint_cannot_activate_service_answer(tmp_path):
    req, graph, anchors = fixture(tmp_path, [PREFIX + LOSS, "Unselected alternative"])
    req["assembly"]["operations"][1]["role"] = "EXCLUDED"
    assembly = contract_assembly.assemble(graph, req["assembly"])
    req["clauses"] = clause_graph.build(assembly)["nodes"]
    next(n for n in req["clauses"] if n["effect"] == "principal_loss")["conditions"] = "trigger"
    req["predicate_engine"] = "z3"
    assert service.assess(req, tmp_path)["questions"]["Q1"]["status"] == "UNKNOWN"
    req["predicate_constraints"] = [{"id": "trigger", "expression": "trigger", "source": anchors[1], "reason": "Excluded premise"}]
    with pytest.raises(ValueError, match="operative occurrence"):
        service.assess(req, tmp_path)
    req["predicate_constraints"][0]["source"] = anchors[0]
    answer = service.assess(req, tmp_path)["questions"]["Q1"]
    assert answer["status"] == "YES" and answer["premise_applicability"]


def test_constraint_cannot_reuse_deleted_raw_interval(tmp_path):
    req, graph, anchors = fixture(tmp_path, [PREFIX + "obsolete", "Deletion authority"])
    req["assembly"]["operations"][1]["role"] = "INSTRUCTION"
    req["assembly"]["operations"][0]["edits"] = [{"start": len(PREFIX), "end": len(PREFIX) + 8,
        "old": "obsolete", "new": "", "reason": "Synthetic deletion", "basis": [{"unit": anchors[1]["unit"], "quote": anchors[1]["quote"]}]}]
    req.update(predicate_engine="z3", predicate_constraints=[{"id": "x", "expression": "x", "reason": "Old text",
        "source": occurrences.anchor(graph["units"][0], len(PREFIX), len(PREFIX) + 8)}])
    with pytest.raises(ValueError, match="operative occurrence"):
        service.assess(req, tmp_path)


def test_external_construction_authority_is_supported_but_not_a_role_bypass(tmp_path):
    req, graph, a = fixture(tmp_path, [PREFIX + LOSS, "The chosen terms apply."])
    spec = {"version": "contract-ast.v2", "root": "choose", "nodes": [
        {"id": "choose", "kind": "Choice", "options": {"a": "body", "b": "empty"}},
        {"id": "body", "kind": "Text", "source": a[0]}, {"id": "empty", "kind": "Sequence", "children": []}],
        "selections": {"choose": {"option": "a", "reason": "Synthetic authority", "source": a[1]}}}
    req["assembly"]["ast"] = spec
    assembly = contract_assembly.assemble(graph, req["assembly"])
    row = {"id": "selected", "expression": True, "source": a[1], "reason": "Selection authority",
           "applicability": {"role": "CONSTRUCTION_AUTHORITY", "assembly_sha256": digest(assembly),
                             "context": graph["context"], "questions": ["Q1", "Q2"]}}
    req.update(predicate_engine="z3", predicate_constraints=[row])
    assert service.assess(req, tmp_path)["questions"]["Q1"]["status"] == "YES"
    row["source"] = a[0]
    with pytest.raises(ValueError, match="consumed construction authority"):
        service.assess(req, tmp_path)


@pytest.mark.parametrize("target", ["d:p2:l0", "ast:2"])
def test_ast_reference_targets_resolve_across_identity_change(tmp_path, target):
    req, graph, a = fixture(tmp_path, ["Condition 2 applies.", PREFIX])
    req["assembly"]["ast"] = {"version": "contract-ast.v2", "root": "s", "nodes": [
        {"id": "s", "kind": "Sequence", "children": ["a", "b"]},
        {"id": "a", "kind": "Text", "source": a[0]}, {"id": "b", "kind": "Text", "source": a[1]}]}
    ref = graph["references"][0]
    req["reference_dispositions"] = {ref["id"]: {"source_sha256": ref["source_sha256"], "reason": "Exact definition", "targets": [target]}}
    report = service.assess(req, tmp_path)
    assert report["dependencies"] and all(d["status"] == "RESOLVED" for d in report["dependencies"])


def test_duplicate_ast_target_needs_selected_use(tmp_path):
    req, graph, a = fixture(tmp_path, ["Definition"])
    req["assembly"]["ast"] = {"version": "contract-ast.v2", "root": "s", "nodes": [
        {"id": "s", "kind": "Sequence", "children": ["a", "a"]}, {"id": "a", "kind": "Text", "source": a[0]}]}
    assembly = contract_assembly.assemble(graph, req["assembly"])
    with pytest.raises(ValueError, match="ambiguous"):
        occurrences.target(graph, assembly, a[0]["unit"])
    assert occurrences.target(graph, assembly, {"source": a[0], "use": "ast:2"})["unit"] == "ast:2"


def test_partially_replaced_reference_target_is_not_whole_raw_unit(tmp_path):
    req, graph, a = fixture(tmp_path, ["original definition", "authority"])
    req["assembly"]["operations"][0]["edits"] = [{"start": 0, "end": 8, "old": "original", "new": "changed",
        "reason": "Source-reviewed replacement", "basis": [{"unit": a[1]["unit"], "quote": a[1]["quote"]}]}]
    assembly = contract_assembly.assemble(graph, req["assembly"])
    with pytest.raises(ValueError, match="unavailable"):
        occurrences.target(graph, assembly, a[0]["unit"])
    retained = occurrences.anchor(graph["units"][0], 9, len(graph["units"][0]["raw"]))
    assert occurrences.target(graph, assembly, {"source": retained, "use": a[0]["unit"]})["start"] == 8


def label_fixture(tmp_path):
    req, graph, a = fixture(tmp_path, [PREFIX])
    cohort = [{"id": "case", "questions": ["Q1"], "request_sha256": digest(req)}]
    identities = {"implementer": "dev", "readers": ["a", "b"], "adjudicator": "c"}
    labels = [{"id": "case", "question": "Q1", "value": "NO", "blinded": True, "readers": ["a", "b"],
               "adjudicator": "c", "cohort_sha256": digest(cohort), "evidence": [a[0]]}]
    predictions = [{"id": "case", "question": "Q1", "value": "NO"}]
    records = {"case": {"method_sha256": "b" * 64, "report": service.assess(req, tmp_path)}}
    return predictions, labels, cohort, identities, graph, records


@pytest.mark.parametrize("mutation", ["negative", "quote", "edition", "prediction"])
def test_invalid_evaluation_evidence_rejected(tmp_path, mutation):
    predictions, labels, cohort, ids, graph, records = label_fixture(tmp_path)
    if mutation == "negative":
        labels[0]["evidence"][0].update(start=-10, end=-9)
    elif mutation == "quote":
        labels[0]["evidence"][0]["quote"] = "invented"
    elif mutation == "edition":
        labels[0]["evidence"][0]["source_sha256"] = "0" * 64
    else:
        predictions[0]["value"] = "YES"
    with pytest.raises(ValueError):
        evaluation.score(predictions, labels, cohort, ids, "b" * 64, graphs={"case": graph}, prediction_records=records)


def test_verified_score_and_legacy_nonacceptance(tmp_path):
    predictions, labels, cohort, ids, graph, records = label_fixture(tmp_path)
    verified = evaluation.score(predictions, labels, cohort, ids, "b" * 64, graphs={"case": graph}, prediction_records=records)
    assert verified["counts"]["Q1"]["C"] == 1 and verified["source_binding"] == "VERIFIED"
    legacy = evaluation.score(predictions, labels, cohort, ids, "b" * 64)
    assert legacy["status"] == "UNVERIFIED_LABEL_ACCOUNTING"
    assert release.assess(verified, [{"question": "Q1"}], [])["status"] == "BLOCKED"


def test_solver_evidence_survives_service_conflict_and_witness(tmp_path):
    req, graph, a = fixture(tmp_path, [PREFIX + LOSS])
    req.update(predicate_engine="z3", predicate_constraints=[
        {"id": name, "expression": expr, "source": a[0], "reason": "Declared premise"}
        for name, expr in [("positive", "trigger"), ("negative", {"not": "trigger"})]])
    answer = service.assess(req, tmp_path)["questions"]["Q1"]
    assert answer["status"] == "CONFLICT"
    assert set(answer["reasoning"][0]["result"]["unsat_core"]) == {"constraint:positive", "constraint:negative"}
    req["predicate_constraints"] = req["predicate_constraints"][:1]
    result = service.assess(req, tmp_path)["questions"]["Q1"]["reasoning"][0]["result"]
    assert result["witnesses"]["true"]["trigger"] is True


def test_z3_reaches_large_law_and_construction(tmp_path):
    req, graph, a = fixture(tmp_path, [PREFIX])
    expr = {"all": ["f" + str(i) for i in range(13)]}
    basis = {"id": "law", "authority": "Synthetic", "jurisdiction": "X", "edition": "1", "source": a[0],
             "instrument_id": req["bundle"]["instrument_id"], "valid_from": TIME, "known_from": TIME, "premises": expr}
    req.update(predicate_engine="z3", law_bases=[basis])
    req["facts"] = [{"name": name, "basis_id": "law", "instrument_id": req["bundle"]["instrument_id"],
        "jurisdiction": "X", "source": a[0], "value": True, "valid_from": TIME, "known_from": TIME, "observed_at": TIME} for name in expr["all"]]
    req["assembly"]["ast"] = {"version": "contract-ast.v2", "root": "a", "nodes": [{"id": "a", "kind": "Text", "source": a[0]}],
                              "constraints": [{"any": [expr, {"not": expr}]}]}
    answer = service.assess(req, tmp_path)
    assert answer["questions"]["Q4"]["status"] == "YES"
    assert answer["assembly"]["rendered_ast"]["reasoning"][0]["result"]["status"] == "YES"
    req["predicate_engine"] = "finite"
    finite = service.assess(req, tmp_path)
    assert finite["questions"]["Q4"]["value"][0]["reasoning"]["reason"] == "DOMAIN_LIMIT"


def test_constrained_solver_independent_truth_table(tmp_path):
    _, graph, a = fixture(tmp_path, ["Declared correlation"])
    queries = ["a", {"not": "b"}, {"all": ["a", "b"]}, {"any": ["a", {"not": "a"}]}]
    for equal in (True, False):
        expression = {"any": [{"all": ["a", "b" if equal else {"not": "b"}]},
                              {"all": [{"not": "a"}, {"not": "b"} if equal else "b"]}]}
        for query in queries:
            for observed in (None, True, False):
                worlds = [dict(zip(("a", "b"), v)) for v in product((False, True), repeat=2)
                          if (v[0] == v[1]) == equal and (observed is None or v[0] == observed)]
                values = {predicates.evaluate(query, w) for w in worlds}
                expected = "YES" if values == {True} else "NO" if values == {False} else "UNKNOWN"
                result = predicates.solve(query, {"a": observed}, [{"id": "correlated", "expression": expression,
                    "source": a[0], "reason": "Boolean equality or inequality"}], graph=graph)
                assert result["status"] == expected
