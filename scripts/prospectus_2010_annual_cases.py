"""Shared actual product comparisons; also executable from an isolated wheel target."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

PROFILE = "bes-annual2010-statements-notes.v1"
PAGES = (92, 93, 94, 95, 96, 114, 129, 130)
INPUT_CASES = ("EPS-conflict-erased", "unknown-imputed", "cash-boundary-erased",
               "note-omitted", "authority-promoted", "geometry", "edition", "missing-page")
PHASE_CASES = ("missing-p2", "changed-p2", "missing-p3", "changed-p3", "unsupplied")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    path = Path(path)
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure(root, folder):
    global ROOT, FOLDER, BASE, SOURCE, REVIEW, service, cells, digest, evidence_digest
    ROOT, FOLDER = Path(root), Path(folder)
    BASE = ROOT / "docs/implementation/prospectus-execution-authority"
    SOURCE = BASE / "attempts/source-bes-dep-09"
    REVIEW = BASE / "reviews/2010-annual-product-187"
    from legalmath.prospectus.successor import service, statement_cells as cells
    from legalmath.prospectus.successor.contracts import digest
    from legalmath.prospectus.execution_authority import digest as evidence_digest


def save(name, value):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    require(sum(p.stat().st_size for p in FOLDER.rglob("*") if p.is_file()) + len(data) < 56 * 1024**2,
            "Attempt result storage reserve exhausted")
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
    require(sha(path) == ref["file_sha256"], "Original annual source changed")
    p1 = p1_from(ref["request"], read(path)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_sha256"], "Original annual P1 differs")
    return {"P1": p1, **read(SOURCE / "attempt-003/candidate-P2-P5.json.gz")}


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


def supplied(graph):
    return {"version": "source-statement-cells.v1", "profile": PROFILE,
            "document": "bes-2010-en", "graph_sha256": digest(graph),
            "reading": read(REVIEW / "reading.json.gz"),
            "review": {"kind": "DEVELOPMENT", "reviewer": "retained original annual source review",
                       "reason": "Complete source09/006 primary and007 EPS/cash readings; supplied interpretation"}}


def reseal(products):
    p1 = products["P1"]
    products["P1"] = p1_from(p1["payload"]["request"], p1["payload"]["graph"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")),
                           ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        products[phase] = service.seal(phase, p1["payload"]["request"]["bundle"],
                                      {p: products[p]["sha256"] for p in parents}, products[phase]["payload"])
    return products


def after_products():
    products = original()
    delta = read(FOLDER / "after-delta.json.gz")
    for phase, addition in delta["payload_additions"].items():
        target = products[phase]["payload"]
        if phase == "P1":
            target = target["request"]
        require(not set(target) & set(addition), "Unexpected existing annual addition")
        target.update(addition)
    reseal(products)
    require({p: v["sha256"] for p, v in products.items()} == delta["expected_hashes"], "Annual product reconstruction differs")
    return products


def composed_prior():
    composition = read(SOURCE / "attempt-007/answer-composition.json")
    result, overlay = {}, {}
    for name in ("baseline", "previous_overlay", "overlay"):
        ref = composition[name]
        part = read(ROOT / ref["path"])
        require(sha(ROOT / ref["path"]) == ref["file_sha256"] and evidence_digest(part) == ref["content_sha256"],
                "Complete007 answer component changed")
        require(not set(result) & set(part), "Duplicate annual answer component")
        result.update(part)
        if name != "baseline":
            overlay.update(part)
    require(evidence_digest(result) == composition["complete_composed_answer_sha256"], "Complete007 answer changed")
    return result, overlay, composition


def matched(installed=False):
    reference = original()
    before = rebuild(reference)
    require(before == reference, "Rebuilt original annual products differ")
    baseline = consume(before)
    require(baseline == read(SOURCE / "attempt-003/candidate-answer.json.gz"), "Whole public003 baseline differs")
    request = deepcopy(before["P1"]["payload"]["request"])
    graph = before["P1"]["payload"]["graph"]
    request["source_statement_cells"] = supplied(graph)
    after = rebuild(before, p1_from(request, graph))
    answer = consume(after)
    protected = {"source_statement_cells", "request_sha256", "consumed_products", "report_sha256"}
    require(set(answer) == set(baseline) | {"source_statement_cells"}, "Unexpected public answer fields")
    require({k: v for k, v in answer.items() if k not in protected} ==
            {k: v for k, v in baseline.items() if k not in protected}, "Protected public answer changed")
    for phase in ("P2", "P3", "P4", "P5"):
        expected = deepcopy(before[phase]["payload"])
        if phase == "P2": expected["source_statement_cells"] = after[phase]["payload"]["source_statement_cells"]
        if phase == "P3": expected["source_statement_cells_sha256"] = after[phase]["payload"]["source_statement_cells_sha256"]
        require(expected == after[phase]["payload"], "Unexpected annual payload change: " + phase)
    reading = request["source_statement_cells"]["reading"]
    output = answer["source_statement_cells"]
    require(all(output[k] == reading[k] for k in reading), "Incomplete annual reading exposed")
    require(output["consumed"] and not output["independent_financial_acceptance"], "Unsupported financial promotion")
    complete, overlay, composition = composed_prior()
    require(not set(answer) & set(overlay), "Duplicate supplemental answer key")
    composed = {**answer, **overlay}
    require({k: v for k, v in composed.items() if k not in protected} ==
            {k: v for k, v in complete.items() if k not in protected}, "Complete007 supplemental answer changed")
    ids = {d["id"] for d in request["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in answer["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Original dependencies changed")
    require(answer["questions"]["Q3"]["status"] == "PARTIAL" and not answer["may_execute_transaction"]
            and not answer["independent_legal_acceptance"], "Unsupported legal promotion")
    result = {"whole_public003_equal_except_declared_addition": True, "complete007_protected_equal": True,
              "prior_composed_sha256": composition["complete_composed_answer_sha256"],
              "after_composed_sha256": evidence_digest(composed), "after_answer_sha256": digest(answer),
              "baseline_answer_sha256": digest(baseline), "report_sha256": answer["report_sha256"],
              "product_hashes": {p: v["sha256"] for p, v in after.items()},
              "source_occurrences": 1171, "primary_cells": 613, "note_cells": 36,
              "original_dependencies_unresolved": 14, "Q3": "PARTIAL", "fresh_extraction": False}
    if installed:
        require(result == read(FOLDER / "matched.json"), "Installed full annual answer/products differ")
    else:
        save("after-delta.json.gz", {"baseline": "source-bes-dep-09/attempt-003/candidate",
             "payload_additions": {"P1": {"source_statement_cells": request["source_statement_cells"]},
                 "P2": {"source_statement_cells": after["P2"]["payload"]["source_statement_cells"]},
                 "P3": {"source_statement_cells_sha256": after["P3"]["payload"]["source_statement_cells_sha256"]}},
             "expected_hashes": result["product_hashes"]})
        save("answer-addition.json.gz", output)
        save("matched.json", result)
        save("answer-composition.json", {"prior007": composition, "actual_public_product": result,
             "addition": {"path": str((FOLDER / "answer-addition.json.gz").relative_to(ROOT)),
                          "sha256": sha(FOLDER / "answer-addition.json.gz")},
             "rule": "Reconstruct after products from verified003 plus after-delta, consume them, preserve both007 source overlays unchanged; full hashes checked in memory"})
    return result


def refuse(call, expected):
    try:
        call()
    except ValueError as exc:
        require(expected in str(exc), "Unexpected refusal: " + str(exc))
        return {"refused": True, "reason": str(exc)}
    raise ValueError("Changed annual evidence accepted")


def input_controls(installed=False):
    values = after_products()
    original_request = values["P1"]["payload"]["request"]
    original_graph = values["P1"]["payload"]["graph"]
    results = {}
    for case in INPUT_CASES:
        request = deepcopy(original_request)
        graph = original_graph
        reading = request["source_statement_cells"]["reading"]
        expected = "reading differs"
        if case == "EPS-conflict-erased": reading["eps_cash_notes"]["analysis"]["conflict_finding"] = "No discrepancy"
        elif case == "unknown-imputed":
            cell = next(c for t in reading["primary_statements"]["profile"]["reading"]["tables"].values()
                        for r in t["rows"] for c in r["cells"] if c["value"] is None)
            cell["value"] = 0
        elif case == "cash-boundary-erased": reading["eps_cash_notes"]["analysis"]["cash_definition"] = "All deposits eligible"
        elif case == "note-omitted": del reading["eps_cash_notes"]["profile"]["reading"]["sections"]
        elif case == "authority-promoted": reading["source_context"]["independent_financial_review"] = True
        else:
            graph = deepcopy(original_graph)
            unit = next(u for u in graph["units"] if u["document"] == "bes-2010-en" and u["page"] == 129)
            if case == "geometry": unit["bbox"][0] += 1
            elif case == "edition": unit["source_sha256"] = "0" * 64
            else: graph["units"] = [u for u in graph["units"] if not (u["document"] == "bes-2010-en" and u["page"] == 130)]
            expected = "original pages"
        request["source_statement_cells"]["graph_sha256"] = digest(graph)
        bad = p1_from(request, graph)
        result = {**refuse(lambda: service.construction_product(bad, ROOT), expected),
                  "P1_sha256": bad["sha256"], "graph_sha256": digest(graph),
                  "supplied_sha256": digest(request["source_statement_cells"]), "request_resealed": True}
        results[case] = result
        if not installed:
            save("input-controls/" + case + ".json", {"mutation": case, "result": result,
                 "reconstruction": "Bound input_controls applies this named mutation to after_products and recomputes graph/request/P1 identities"})
    if installed:
        require(results == read(FOLDER / "input-controls.json"), "Installed input refusals differ")
    else: save("input-controls.json", results)
    return {"actual_public_refusals": len(results), "cases": results}


def phase_controls(installed=False):
    values = after_products()
    results = {}
    for case in PHASE_CASES:
        # Copy only the changed product payloads; source graph is read-only here.
        bad = {p: {**v, "payload": deepcopy(v["payload"])} if p != "P1" else
               {**v, "payload": {**v["payload"], "request": deepcopy(v["payload"]["request"])}}
               for p, v in values.items()}
        if case == "missing-p2": del bad["P2"]["payload"]["source_statement_cells"]
        elif case == "changed-p2": bad["P2"]["payload"]["source_statement_cells"]["reading"]["eps_cash_notes"]["analysis"]["conflict_finding"] = "No discrepancy"
        elif case == "missing-p3": del bad["P3"]["payload"]["source_statement_cells_sha256"]
        elif case == "changed-p3": bad["P3"]["payload"]["source_statement_cells_sha256"] = "0" * 64
        else: del bad["P1"]["payload"]["request"]["source_statement_cells"]
        reseal(bad)
        results[case] = {**refuse(lambda: consume(bad), "Consumed statement cells"),
                         "product_hashes": {p: v["sha256"] for p, v in bad.items()}, "all_parents_resealed": True}
    if installed: require(results == read(FOLDER / "phase-controls.json"), "Installed phase refusals differ")
    else: save("phase-controls.json", results)
    return {"actual_public_refusals": len(results), "cases": results}


def prior_profiles():
    root = BASE / "attempts"
    nine = root / "source-bes-dep-01/attempt-005"
    answer = consume(read(nine / "after-products.json.gz"))
    require(digest(answer) == read(nine / "answer-reconstruction.json")["expected_complete_answer_sha256"], "Whole9M answer differs")
    result = {"9M2010": answer["report_sha256"]}
    q1 = root / "source-bes-dep-11/attempt-004"
    ref = read(q1 / "after-P1-reference.json.gz")
    require(sha(ROOT / ref["original_p1"]) == ref["original_p1_file_sha256"], "Q1 P1 bytes changed")
    p1 = p1_from(ref["request"], read(ROOT / ref["original_p1"])["payload"]["graph"])
    require(p1["sha256"] == ref["expected_P1_sha256"], "Q1 P1 identity changed")
    values = {"P1": p1, **read(q1 / "after-P2-P5.json.gz")}
    answer = service.consume(values, ROOT, mode="frozen")
    require(answer == read(q1 / "after-answer.json.gz"), "WholeQ1 answer differs")
    result["Q12011"] = answer["report_sha256"]
    fy = root / "source-bes-dep-08/attempt-006"
    ref = read(fy / "after-P1-reference.json.gz")
    require(sha(ROOT / ref["original_P1"]) == ref["file_sha256"], "FY P1 bytes changed")
    p1 = p1_from(ref["request"], read(ROOT / ref["original_P1"])["payload"]["graph"])
    require(p1["sha256"] == ref["expected_sha256"], "FY P1 identity changed")
    answer = consume({"P1": p1, **read(fy / "after-P2-P5.json.gz")})
    require(answer == read(fy / "after-answer.json.gz"), "WholeFY answer differs")
    result["FY2010"] = answer["report_sha256"]
    save("prior-profiles.json", {"complete_answers_equal": True, "reports": result})
    return {"complete_answers_equal": 3, "reports": result}


def package_files(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def environment_files(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink(): result[str(relative)] = {"symlink": os.readlink(path)}
        elif path.is_file(): result[str(relative)] = sha(path)
    return result


def installed_main():
    root, folder, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    sys.dont_write_bytecode = True
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    require(sys.flags.isolated == 1, "Isolated interpreter required")
    sys.path.insert(0, str(folder / "installed"))
    configure(root, folder)
    def block(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "os.exec"}:
            raise RuntimeError("Installed annual worker forbids network/native processes: " + event)
    sys.addaudithook(block)
    expected = read(folder / "final-package.json")
    package = folder / "installed/legalmath"
    require(package_files(package) == expected, "Installed package bytes differ")
    result = {"matched": matched, "input": input_controls, "phase": phase_controls}[action](installed=True)
    modules = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(package.resolve()), "Checkout import: " + name)
            require(sha(path) == expected[str(path.relative_to(package.resolve()))], "Loaded module changed")
            modules[name] = str(path)
    require(package_files(package) == expected, "Installed package drifted")
    save("installed-" + action + ".json", {"status": "PASS", "details": result,
         "python": sys.executable, "isolated": sys.flags.isolated, "sys_path": sys.path,
         "modules": modules, "package_files": len(expected), "native_calls": 0})
    print(json.dumps({"status": "PASS", "action": action, "package_files": len(expected)}))


if __name__ == "__main__":
    installed_main()
