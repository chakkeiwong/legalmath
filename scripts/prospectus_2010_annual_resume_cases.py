"""Split annual comparisons; usable with only an isolated installed package."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("annual187_cases", Path(__file__).with_name("prospectus_2010_annual_cases.py"))
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
require, read, sha = legacy.require, legacy.read, legacy.sha
INPUT_GROUPS = {"input-a": legacy.INPUT_CASES[:4], "input-b": legacy.INPUT_CASES[4:]}
PHASE_GROUPS = {"phase-a": legacy.PHASE_CASES[:2], "phase-b": legacy.PHASE_CASES[2:4], "phase-c": legacy.PHASE_CASES[4:]}
PROTECTED = {"source_statement_cells", "request_sha256", "consumed_products", "report_sha256"}


def configure(root, folder):
    global ROOT, HERE, SOURCE, service, digest, evidence_digest
    ROOT, HERE = Path(root), Path(folder)
    legacy.configure(ROOT, HERE)
    SOURCE, service, digest, evidence_digest = legacy.SOURCE, legacy.service, legacy.digest, legacy.evidence_digest


def hashes(products):
    return {p: v["sha256"] for p, v in products.items()}


def baseline_products():
    original = legacy.original()
    actual = legacy.rebuild(original)
    require(actual == original, "Complete original annual products differ")
    return {"complete_products_equal": True, "product_hashes": hashes(actual)}


def baseline_answer():
    products = legacy.original()
    require(hashes(products) == read(HERE / "checks/baseline-products.json")["product_hashes"], "Baseline product link differs")
    answer = legacy.consume(products)
    require(answer == read(SOURCE / "attempt-003/candidate-answer.json.gz"), "Complete original public answer differs")
    return {"complete_answer_equal": True, "answer_sha256": digest(answer), "report_sha256": answer["report_sha256"]}


def candidate_products(installed=False):
    before = legacy.original()
    request = deepcopy(before["P1"]["payload"]["request"])
    graph = before["P1"]["payload"]["graph"]
    request["source_statement_cells"] = legacy.supplied(graph)
    after = legacy.rebuild(before, legacy.p1_from(request, graph))
    for phase in ("P2", "P3", "P4", "P5"):
        expected = deepcopy(before[phase]["payload"])
        if phase == "P2": expected["source_statement_cells"] = after[phase]["payload"]["source_statement_cells"]
        if phase == "P3": expected["source_statement_cells_sha256"] = after[phase]["payload"]["source_statement_cells_sha256"]
        require(expected == after[phase]["payload"], "Unexpected product payload change: " + phase)
    if installed:
        require(after == legacy.after_products(), "Complete installed construction differs")
    else:
        legacy.save("after-delta.json.gz", {"baseline": "source-bes-dep-09/attempt-003/candidate",
            "payload_additions": {"P1": {"source_statement_cells": request["source_statement_cells"]},
                "P2": {"source_statement_cells": after["P2"]["payload"]["source_statement_cells"]},
                "P3": {"source_statement_cells_sha256": after["P3"]["payload"]["source_statement_cells_sha256"]}},
            "expected_hashes": hashes(after)})
    return {"only_declared_payload_changes": True, "product_hashes": hashes(after)}


def candidate_answer(installed=False):
    products = legacy.after_products()
    require(hashes(products) == read(HERE / "checks/candidate-products.json")["product_hashes"], "Candidate product link differs")
    answer = legacy.consume(products)
    baseline = read(SOURCE / "attempt-003/candidate-answer.json.gz")
    require(digest(baseline) == read(HERE / "checks/baseline-answer.json")["answer_sha256"], "Baseline answer link differs")
    require(set(answer) == set(baseline) | {"source_statement_cells"}, "Unexpected answer field")
    require({k: v for k, v in answer.items() if k not in PROTECTED} ==
            {k: v for k, v in baseline.items() if k not in PROTECTED}, "Protected public answer changed")
    reading = products["P1"]["payload"]["request"]["source_statement_cells"]["reading"]
    output = answer["source_statement_cells"]
    require(all(output[k] == value for k, value in reading.items()), "Annual reading incomplete")
    require(output["consumed"] and not output["independent_financial_acceptance"], "Unsupported financial promotion")
    ids = {d["id"] for d in products["P1"]["payload"]["request"]["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in answer["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Dependencies changed")
    require(answer["questions"]["Q3"]["status"] == "PARTIAL" and not answer["may_execute_transaction"]
            and not answer["independent_legal_acceptance"], "Unsupported legal promotion")
    if installed:
        require(answer == read(HERE / "after-answer.json.gz"), "Complete installed answer differs")
    else:
        legacy.save("after-answer.json.gz", answer)
        legacy.save("answer-addition.json.gz", output)
    return {"complete_public003_protected_equal": True, "complete_reading_equal": True,
            "answer_sha256": digest(answer), "report_sha256": answer["report_sha256"],
            "product_hashes": hashes(products), "source_occurrences": 1171, "primary_cells": 613,
            "note_cells": 36, "unresolved_dependencies": 14, "Q3": "PARTIAL", "fresh_extraction": False}


def composition():
    complete, overlay, refs = legacy.composed_prior()
    answer = read(HERE / "after-answer.json.gz")
    require(digest(answer) == read(HERE / "checks/candidate-answer.json")["answer_sha256"], "Candidate answer changed")
    require(not set(answer) & set(overlay), "Duplicate source overlay keys")
    composed = {**answer, **overlay}
    require({k: v for k, v in composed.items() if k not in PROTECTED} ==
            {k: v for k, v in complete.items() if k not in PROTECTED}, "Complete007 protected answer differs")
    return {"complete007_protected_equal": True, "prior007_sha256": refs["complete_composed_answer_sha256"],
            "after_composed_sha256": evidence_digest(composed), "original_overlay_references": refs,
            "candidate_answer_path": str((HERE / "after-answer.json.gz").relative_to(ROOT)),
            "candidate_answer_file_sha256": sha(HERE / "after-answer.json.gz")}


def inputs(action):
    values = legacy.after_products()
    original_request = values["P1"]["payload"]["request"]
    original_graph = values["P1"]["payload"]["graph"]
    result = {}
    for case in INPUT_GROUPS[action]:
        request, graph = deepcopy(original_request), original_graph
        reading = request["source_statement_cells"]["reading"]
        expected = "reading differs"
        if case == "EPS-conflict-erased": reading["eps_cash_notes"]["analysis"]["conflict_finding"] = "No discrepancy"
        elif case == "unknown-imputed":
            next(c for t in reading["primary_statements"]["profile"]["reading"]["tables"].values()
                 for r in t["rows"] for c in r["cells"] if c["value"] is None)["value"] = 0
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
        p1 = legacy.p1_from(request, graph)
        result[case] = {**legacy.refuse(lambda: service.construction_product(p1, ROOT), expected),
                        "P1_sha256": p1["sha256"], "graph_sha256": digest(graph),
                        "supplied_sha256": digest(request["source_statement_cells"]), "request_resealed": True}
    return result


def phases(action):
    values = legacy.after_products()
    result = {}
    for case in PHASE_GROUPS[action]:
        bad = {p: {**v, "payload": deepcopy(v["payload"])} if p != "P1" else
               {**v, "payload": {**v["payload"], "request": deepcopy(v["payload"]["request"])}}
               for p, v in values.items()}
        if case == "missing-p2": del bad["P2"]["payload"]["source_statement_cells"]
        elif case == "changed-p2": bad["P2"]["payload"]["source_statement_cells"]["reading"]["eps_cash_notes"]["analysis"]["conflict_finding"] = "No discrepancy"
        elif case == "missing-p3": del bad["P3"]["payload"]["source_statement_cells_sha256"]
        elif case == "changed-p3": bad["P3"]["payload"]["source_statement_cells_sha256"] = "0" * 64
        else: del bad["P1"]["payload"]["request"]["source_statement_cells"]
        legacy.reseal(bad)
        result[case] = {**legacy.refuse(lambda: legacy.consume(bad), "Consumed statement cells"),
                        "product_hashes": hashes(bad), "all_parents_resealed": True}
    return result


def prior(action):
    root = legacy.BASE / "attempts"
    if action == "prior-9m":
        folder = root / "source-bes-dep-01/attempt-005"
        answer = legacy.consume(read(folder / "after-products.json.gz"))
        require(digest(answer) == read(folder / "answer-reconstruction.json")["expected_complete_answer_sha256"], "Complete9M answer differs")
    else:
        folder = root / ("source-bes-dep-11/attempt-004" if action == "prior-q1" else "source-bes-dep-08/attempt-006")
        ref = read(folder / "after-P1-reference.json.gz")
        path = ROOT / ref["original_p1" if action == "prior-q1" else "original_P1"]
        require(sha(path) == ref["original_p1_file_sha256" if action == "prior-q1" else "file_sha256"], "Prior original P1 changed")
        p1 = legacy.p1_from(ref["request"], read(path)["payload"]["graph"])
        require(p1["sha256"] == ref["expected_P1_sha256" if action == "prior-q1" else "expected_sha256"], "Prior P1 differs")
        products = {"P1": p1, **read(folder / "after-P2-P5.json.gz")}
        answer = service.consume(products, ROOT, mode="frozen") if action == "prior-q1" else legacy.consume(products)
        require(answer == read(folder / "after-answer.json.gz"), "Complete prior answer differs")
    return {"complete_answer_equal": True, "answer_sha256": digest(answer), "report_sha256": answer["report_sha256"]}


def dispatch(action, installed=False):
    if action == "candidate-products": return candidate_products(installed)
    if action == "candidate-answer": return candidate_answer(installed)
    if action in INPUT_GROUPS: return inputs(action)
    if action in PHASE_GROUPS: return phases(action)
    if action.startswith("prior-"): return prior(action)
    return {"baseline-products": baseline_products, "baseline-answer": baseline_answer, "composition": composition}[action]()


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
    package = (folder / "installed/legalmath").resolve()
    require(legacy.package_files(package) == expected, "Installed package differs")
    result = dispatch(action, installed=True)
    require(result == read(folder / "checks" / (action + ".json")), "Installed stage differs: " + action)
    modules = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(package), "Checkout import: " + name)
            require(sha(path) == expected[str(path.relative_to(package))], "Loaded module differs")
            modules[name] = str(path)
    require(legacy.package_files(package) == expected, "Installed package drift")
    legacy.save("installed-checks/" + action + ".json", {"status": "PASS", "details": result,
        "python": sys.executable, "isolated": sys.flags.isolated, "modules": modules,
        "sys_path": sys.path, "package_files": len(expected), "native_calls": 0})
    print(json.dumps({"status": "PASS", "action": action, "package_files": len(expected)}))


if __name__ == "__main__":
    installed_main()
