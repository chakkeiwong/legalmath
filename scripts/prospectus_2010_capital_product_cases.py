"""Actual product comparisons for the optional annual capital-note profile."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import scripts.prospectus_2010_annual_cases as legacy

PROFILE = "bes-annual2010-statements-capital-notes.v2"
PAGES = (92, 93, 94, 95, 96, 108, 109, 114, 129, 130, 158, 159, 160, 161)
OCCURRENCES = 1817
INPUT_GROUPS = {
    "input-a": ("capital-call-erased", "capital-issuer-erased"),
    "input-b": ("capital-condition-erased", "capital-policy-erased"),
    "input-c": ("capital-omitted", "old-reading-erased"),
    "input-d": ("authority-promoted", "geometry"),
}
PHASE_GROUPS = {
    "phase-a": ("missing-p2", "changed-p2"),
    "phase-b": ("missing-p3", "changed-p3"),
    "phase-c": ("unsupplied", "capital-stale"),
}
PROTECTED = {"source_statement_cells", "request_sha256", "consumed_products", "report_sha256"}


def evidence_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()).hexdigest()


def configure(root, folder):
    global ROOT, FOLDER, BASE, SOURCE, service, digest, evidence_digest
    ROOT, FOLDER = Path(root), Path(folder)
    BASE = ROOT / "docs/implementation/prospectus-execution-authority"
    SOURCE = BASE / "attempts/source-bes-dep-09"
    from legalmath.prospectus.successor import service
    from legalmath.prospectus.successor.contracts import digest
    legacy.configure(ROOT, FOLDER)


def read(path):
    path = Path(path)
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    path = FOLDER / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def p1_from(request, graph):
    return service.seal("P1", request["bundle"], {"request": digest(request)},
                        {"request": request, "graph": graph})


def original():
    ref = read(SOURCE / "attempt-003/candidate-P1-reference.json.gz")
    path = ROOT / ref["original_P1"]
    legacy.require(sha(path) == ref["file_sha256"], "Original annual source changed")
    p1 = p1_from(ref["request"], read(path)["payload"]["graph"])
    legacy.require(p1["sha256"] == ref["expected_sha256"], "Original annual P1 differs")
    return {"P1": p1, **read(SOURCE / "attempt-003/candidate-P2-P5.json.gz")}


def supplied(graph):
    retained = read(FOLDER / "combined-fixture.json.gz")
    return {"version": "source-statement-cells.v1", "profile": PROFILE,
            "document": "bes-2010-en", "graph_sha256": digest(graph),
            "review": {"kind": "DEVELOPMENT", "reviewer": "retained source reviews",
                       "reason": "Combined annual primary/EPS/cash and capital-note readings"},
            "reading": retained["reading"]}


def rebuild(reference, p1=None):
    p1 = reference["P1"] if p1 is None else p1
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2, reference["P3"]["payload"]["interpretation_input"])
    law, finance = reference["P4"]["payload"], reference["P5"]["payload"]
    return {"P1": p1, "P2": p2, "P3": p3,
            "P4": service.law_product(p1, p3, law.get("cases"), law.get("law_input")),
            "P5": service.financial_product(p1, p2, p3, finance.get("cases"), finance.get("scenario_input"))}


def consume(products):
    return service.consume(products, ROOT, include_artifacts=True, mode="frozen")


def reseal(products):
    p1 = products["P1"]
    products["P1"] = p1_from(p1["payload"]["request"], p1["payload"]["graph"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")),
                           ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        products[phase] = service.seal(phase, p1["payload"]["request"]["bundle"],
                                       {p: products[p]["sha256"] for p in parents},
                                       products[phase]["payload"])
    return products


def after_products():
    products = original()
    request = deepcopy(products["P1"]["payload"]["request"])
    graph = products["P1"]["payload"]["graph"]
    request["source_statement_cells"] = supplied(graph)
    products = rebuild(products, p1_from(request, graph))
    return products


def hashes(products):
    return {p: v["sha256"] for p, v in products.items()}


def baseline_products():
    before = original()
    legacy.require(rebuild(before) == before, "Complete original annual products differ")
    return {"complete_products_equal": True, "product_hashes": hashes(before)}


def baseline_answer():
    answer = consume(original())
    expected = read(SOURCE / "attempt-003/candidate-answer.json.gz")
    legacy.require(answer == expected, "Complete original public answer differs")
    return {"complete_answer_equal": True, "answer_sha256": digest(answer), "report_sha256": answer["report_sha256"]}


def candidate_products():
    before = original()
    after = after_products()
    for phase in ("P2", "P3", "P4", "P5"):
        expected = deepcopy(before[phase]["payload"])
        if phase == "P2": expected["source_statement_cells"] = after[phase]["payload"]["source_statement_cells"]
        if phase == "P3": expected["source_statement_cells_sha256"] = after[phase]["payload"]["source_statement_cells_sha256"]
        legacy.require(expected == after[phase]["payload"], "Unexpected product payload change: " + phase)
    result = {"only_declared_payload_changes": True, "product_hashes": hashes(after),
              "source_occurrences": OCCURRENCES, "profile": PROFILE}
    save("candidate-products.json", result)
    return result


def complete010():
    composition = read(SOURCE / "attempt-010/answer-composition.json")
    baseline = read(ROOT / composition["baseline"]["path"])
    overlay = read(ROOT / composition["overlay"]["path"])
    legacy.require(sha(ROOT / composition["baseline"]["path"]) == composition["baseline"]["file_sha256"], "010 baseline changed")
    legacy.require(sha(ROOT / composition["overlay"]["path"]) == composition["overlay"]["file_sha256"], "010 overlay changed")
    result = {**baseline, **overlay}
    legacy.require(evidence_digest(result) == composition["complete_composed_answer_sha256"], "Complete010 comparator differs")
    return result, composition


def candidate_answer():
    products = after_products()
    expected_products = read(FOLDER / "candidate-products.json")["product_hashes"]
    legacy.require(hashes(products) == expected_products, "Candidate product link differs")
    answer = consume(products)
    baseline, composition = complete010()
    legacy.require(set(answer) == set(read(SOURCE / "attempt-009/after-answer.json.gz")) | {"source_statement_cells"},
                   "Unexpected candidate answer fields")
    legacy.require({k: v for k, v in answer.items() if k not in PROTECTED} ==
                   {k: v for k, v in baseline.items() if k not in PROTECTED},
                   "Protected answer changed outside declared fields")
    old_cells = read(SOURCE / "attempt-009/after-answer.json.gz")["source_statement_cells"]
    new_cells = answer["source_statement_cells"]
    legacy.require(new_cells["primary_statements"] == old_cells["primary_statements"] and
                   new_cells["eps_cash_notes"] == old_cells["eps_cash_notes"],
                   "Earlier supplied readings changed")
    legacy.require(new_cells["capital_notes"]["profile"]["reading"]["context"]["count"] == 646 and
                   new_cells["consumed"] and not new_cells["independent_financial_acceptance"],
                   "Capital notes did not reach the public consumer")
    composed = {**answer, **read(ROOT / composition["overlay"]["path"])}
    legacy.require({k: v for k, v in composed.items() if k not in PROTECTED} ==
                   {k: v for k, v in baseline.items() if k not in PROTECTED},
                   "Complete010 supplemental composition changed")
    result = {"complete010_protected_equal": True, "complete_answer_sha256": digest(answer),
              "complete_composed_sha256": evidence_digest(composed), "baseline_complete_sha256": evidence_digest(baseline),
              "source_occurrences": OCCURRENCES, "old_occurrences": 1171, "capital_occurrences": 646,
              "Q3": answer["questions"]["Q3"]["status"], "original_dependencies_unresolved": 14}
    save("candidate-answer.json", result)
    save("candidate-answer-delta.json.gz", {"baseline": "source-bes-dep-09/attempt-009/after-answer.json.gz",
         "capital_overlay": "source-bes-dep-09/attempt-010/answer-overlay.json.gz",
         "source_statement_cells": new_cells, "expected": result})
    return result


def refuse(call, expected):
    try:
        call()
    except ValueError as exc:
        legacy.require(expected in str(exc), "Unexpected refusal: " + str(exc))
        return {"refused": True, "reason": str(exc)}
    raise ValueError("Changed combined annual evidence accepted")


def input_controls(action):
    values = after_products()
    original_request = values["P1"]["payload"]["request"]
    original_graph = values["P1"]["payload"]["graph"]
    results = {}
    for case in INPUT_GROUPS[action]:
        request, graph = deepcopy(original_request), original_graph
        supplied_value = request["source_statement_cells"]
        reading = supplied_value["reading"]
        expected = "reading differs"
        if case == "capital-call-erased": reading["capital_notes"]["analysis"]["call_dates_not_maturities"] = False
        elif case == "capital-issuer-erased": reading["capital_notes"]["analysis"]["conditional_distributions"] = []
        elif case == "capital-condition-erased": reading["capital_notes"]["profile"]["reading"]["facts"].pop()
        elif case == "capital-policy-erased": reading["capital_notes"]["profile"]["reading"]["sections"].popitem()
        elif case == "capital-omitted": del reading["capital_notes"]
        elif case == "old-reading-erased": del reading["eps_cash_notes"]
        elif case == "authority-promoted": reading["source_context"]["independent_financial_review"] = True
        else:
            graph = deepcopy(original_graph)
            unit = next(u for u in graph["units"] if u["page"] == 158)
            unit["bbox"][0] += 1
            expected = "original pages"
        supplied_value["graph_sha256"] = digest(graph)
        bad = p1_from(request, graph)
        results[case] = {**refuse(lambda: service.construction_product(bad, ROOT), expected),
                         "P1_sha256": bad["sha256"], "graph_sha256": digest(graph),
                         "supplied_sha256": digest(supplied_value), "request_resealed": True}
    save(action + ".json", results)
    return {"actual_public_refusals": len(results), "cases": results}


def phase_controls(action):
    values = after_products()
    results = {}
    for case in PHASE_GROUPS[action]:
        bad = {p: {**v, "payload": deepcopy(v["payload"])} if p != "P1" else
               {**v, "payload": {**v["payload"], "request": deepcopy(v["payload"]["request"])}}
               for p, v in values.items()}
        if case == "missing-p2": del bad["P2"]["payload"]["source_statement_cells"]
        elif case == "changed-p2": bad["P2"]["payload"]["source_statement_cells"]["reading"]["capital_notes"]["analysis"]["call_dates_not_maturities"] = False
        elif case == "missing-p3": del bad["P3"]["payload"]["source_statement_cells_sha256"]
        elif case == "changed-p3": bad["P3"]["payload"]["source_statement_cells_sha256"] = "0" * 64
        elif case == "unsupplied": del bad["P1"]["payload"]["request"]["source_statement_cells"]
        else: bad["P2"]["payload"]["source_statement_cells"]["reading"]["capital_notes"]["profile"]["reading"]["facts"].pop()
        reseal(bad)
        results[case] = {**refuse(lambda: consume(bad), "Consumed statement cells"),
                         "product_hashes": hashes(bad), "all_parents_resealed": True}
    save(action + ".json", results)
    return {"actual_public_refusals": len(results), "cases": results}


def prior_profiles():
    # The unchanged three-profile regression helper preserves its complete answer comparisons.
    return legacy.prior_profiles()


def dispatch(action):
    if action == "baseline-products": return baseline_products()
    if action == "baseline-answer": return baseline_answer()
    if action == "candidate-products": return candidate_products()
    if action == "candidate-answer": return candidate_answer()
    if action in INPUT_GROUPS: return input_controls(action)
    if action in PHASE_GROUPS: return phase_controls(action)
    if action == "prior-profiles": return prior_profiles()
    raise ValueError("Unknown product stage: " + action)
