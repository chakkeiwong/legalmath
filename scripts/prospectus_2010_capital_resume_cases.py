"""Split capital-profile comparisons, with no package import before configuration."""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load("annual188_cases", Path(__file__).with_name("prospectus_2010_annual_resume_cases.py"))
legacy = prior.legacy
require, read, sha = legacy.require, legacy.read, legacy.sha
PROFILE = "bes-annual2010-statements-capital-notes.v2"
PAGES = (92, 93, 94, 95, 96, 108, 109, 114, 129, 130, 158, 159, 160, 161)
FIXTURE = "tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v2.json.gz"
PROTECTED = {"source_statement_cells", "request_sha256", "consumed_products", "report_sha256"}
CELL_IDENTITIES = {"profile", "evidence_sha256", "reading_sha256"}
INPUT_GROUPS = {
    "input-a": ("capital-call-erased", "capital-guarantee-omitted"),
    "input-b": ("capital-condition-erased", "capital-policy-erased"),
    "input-c": ("capital-omitted", "old-reading-erased"),
    "input-d": ("authority-promoted", "geometry"),
}
PHASE_GROUPS = {
    "phase-a": ("missing-p2", "changed-p2"),
    "phase-b": ("missing-p3", "changed-p3"),
    "phase-c": ("unsupplied", "capital-stale"),
}


def configure(root, folder):
    global ROOT, HERE, SOURCE, service, digest, evidence_digest
    ROOT, HERE = Path(root), Path(folder)
    prior.configure(ROOT, HERE)
    SOURCE, service, digest, evidence_digest = prior.SOURCE, prior.service, prior.digest, prior.evidence_digest


def save(name, value):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    # The supervisor also accounts for all historical and support files.
    cap = read(HERE / "resource-contract.json")
    used = sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    require(used + len(data) < cap["attempt_available_bytes"] - cap["reserve_bytes"],
            "Capital comparison storage reserve exhausted")
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def hashes(products):
    return prior.hashes(products)


def delta_products(delta):
    products = legacy.original()
    require(delta["baseline"] == "source-bes-dep-09/attempt-003/candidate", "Wrong product delta baseline")
    for phase, addition in delta["payload_additions"].items():
        require(phase in {"P1", "P2", "P3"}, "Unexpected product delta phase")
        target = products[phase]["payload"]
        if phase == "P1":
            target = deepcopy(target["request"])
            products[phase]["payload"]["request"] = target
        require(not set(target) & set(addition), "Product delta replaces protected value")
        target.update(deepcopy(addition))
    legacy.reseal(products)
    require(hashes(products) == delta["expected_hashes"], "Reconstructed complete products differ")
    return products


def v1_products():
    return delta_products(read(SOURCE / "attempt-009/after-delta.json.gz"))


def after_products():
    return delta_products(read(HERE / "after-delta.json.gz"))


def supplied(graph):
    # The original review metadata is protected too; retain it exactly.
    old = read(SOURCE / "attempt-009/after-delta.json.gz")["payload_additions"]["P1"]["source_statement_cells"]
    return {**old, "profile": PROFILE, "graph_sha256": digest(graph),
            "reading": read(ROOT / FIXTURE)["reading"]}


def baseline_products():
    expected = v1_products()
    actual = legacy.rebuild(expected)
    require(actual == expected, "Complete v1 annual products differ")
    return {"complete_products_equal": True, "product_hashes": hashes(actual)}


def baseline_answer():
    products = v1_products()
    require(hashes(products) == read(HERE / "checks/baseline-products.json")["product_hashes"],
            "Baseline product link differs")
    answer = legacy.consume(products)
    expected = read(SOURCE / "attempt-009/after-answer.json.gz")
    require(answer == expected, "Complete v1 annual answer differs")
    return {"complete_answer_equal": True, "answer_sha256": digest(answer),
            "report_sha256": answer["report_sha256"]}


def candidate_products(installed=False):
    before = legacy.original()
    request = deepcopy(before["P1"]["payload"]["request"])
    graph = before["P1"]["payload"]["graph"]
    request["source_statement_cells"] = supplied(graph)
    after = legacy.rebuild(before, legacy.p1_from(request, graph))
    for phase in ("P2", "P3", "P4", "P5"):
        expected = deepcopy(before[phase]["payload"])
        if phase == "P2":
            expected["source_statement_cells"] = after[phase]["payload"]["source_statement_cells"]
        if phase == "P3":
            expected["source_statement_cells_sha256"] = after[phase]["payload"]["source_statement_cells_sha256"]
        require(expected == after[phase]["payload"], "Unexpected product payload change: " + phase)
    delta = {"baseline": "source-bes-dep-09/attempt-003/candidate",
        "payload_additions": {
            "P1": {"source_statement_cells": request["source_statement_cells"]},
            "P2": {"source_statement_cells": after["P2"]["payload"]["source_statement_cells"]},
            "P3": {"source_statement_cells_sha256": after["P3"]["payload"]["source_statement_cells_sha256"]}},
        "expected_hashes": hashes(after)}
    require(delta_products(delta) == after, "Full constructed-product delta reconstruction differs")
    if installed:
        require(delta == read(HERE / "after-delta.json.gz"), "Complete installed product delta differs")
    else:
        save("after-delta.json.gz", delta)
    return {"only_declared_payload_changes": True, "product_hashes": hashes(after),
            "source_occurrences": 1817, "profile": PROFILE}


def checked_reference(ref):
    path = ROOT / ref["path"]
    require(sha(path) == ref["file_sha256"], "Composed answer reference bytes changed")
    value = read(path)
    require(evidence_digest(value) == ref["content_sha256"], "Composed answer reference content changed")
    return value


def complete010():
    refs = read(SOURCE / "attempt-010/answer-composition.json")
    composition009 = checked_reference(refs["composition009"])
    answer = checked_reference(refs["baseline"])
    require(sha(ROOT / refs["baseline"]["path"]) == composition009["candidate_answer_file_sha256"],
            "009 public answer identity differs")
    overlay = {}
    for key in ("previous_overlay", "overlay"):
        part = checked_reference(composition009["original_overlay_references"][key])
        require(not set(answer) & set(part) and not set(overlay) & set(part), "Duplicate006/007 overlay key")
        overlay.update(part)
    require(evidence_digest({**answer, **overlay}) == refs["prior_complete_answer_sha256"] ==
            composition009["after_composed_sha256"] ==
            "e85a5e137458f47d5b2d47d8b701a40fbaa2ccd768a766c878ac1e3d1db79e15",
            "Complete009 comparator differs")
    capital = checked_reference(refs["overlay"])
    require(not (set(answer) | set(overlay)) & set(capital), "Duplicate010 overlay key")
    overlay.update(capital)
    complete = {**answer, **overlay}
    require(evidence_digest(complete) == refs["complete_composed_answer_sha256"] ==
            "beccc421770c8e57ae21b5d1656983b780ce6fd13e2af78ff52f3fb54d93be4d",
            "Complete010 comparator differs")
    return complete, overlay, refs


def protected_cells(old, new):
    require(set(new) == set(old) | {"capital_notes"}, "Unexpected source-statement fields")
    for key, value in old.items():
        if key in CELL_IDENTITIES:
            continue
        if key == "source_context":
            require(set(new[key]) == set(value), "Source-context fields changed")
            require({k: v for k, v in new[key].items() if k not in {"source_pages", "scope"}} ==
                    {k: v for k, v in value.items() if k not in {"source_pages", "scope"}},
                    "Protected source-context qualification changed")
            require(new[key]["source_pages"] == list(PAGES), "Combined source page inventory differs")
            require(new[key]["scope"] == read(ROOT / FIXTURE)["reading"][key]["scope"],
                    "Combined source scope differs")
        else:
            require(new[key] == value, "Protected source-statement value changed: " + key)
    capital = {"profile": read(SOURCE / "attempt-010/profile.json"),
               "analysis": read(SOURCE / "attempt-010/analysis.json")}
    require(new["capital_notes"] == capital, "Capital profile/analysis differs from010")
    require(new["profile"] == PROFILE and new["consumed"] and not new["independent_financial_acceptance"],
            "Unsupported financial promotion or wrong profile")


def candidate_answer(installed=False):
    products = after_products()
    require(hashes(products) == read(HERE / "checks/candidate-products.json")["product_hashes"],
            "Candidate product link differs")
    answer = legacy.consume(products)
    old = read(SOURCE / "attempt-009/after-answer.json.gz")
    require(set(answer) == set(old), "Unexpected candidate public answer fields")
    require({k: v for k, v in answer.items() if k not in PROTECTED} ==
            {k: v for k, v in old.items() if k not in PROTECTED}, "Protected public answer changed")
    protected_cells(old["source_statement_cells"], answer["source_statement_cells"])
    reading = products["P1"]["payload"]["request"]["source_statement_cells"]["reading"]
    require(all(answer["source_statement_cells"][k] == v for k, v in reading.items()),
            "Combined reading did not reach public consumer")
    ids = {d["id"] for d in products["P1"]["payload"]["request"]["bundle"]["dependencies"]}
    expected_ids = {"BES-DEP-" + str(i).zfill(2) for i in range(1, 12)} | {
        "BES-DEP-AGENCY-" + str(i).zfill(2) for i in range(1, 4)}
    deps = {d["id"]: d for d in answer["dependencies"]}
    require(ids == expected_ids and all(deps[k]["status"] == "UNRESOLVED" for k in ids),
            "Original dependency limits changed")
    require(answer["questions"]["Q3"]["status"] == "PARTIAL" and not answer["may_execute_transaction"]
            and not answer["independent_legal_acceptance"], "Unsupported legal promotion")
    delta = {"baseline": {"path": str((SOURCE / "attempt-009/after-answer.json.gz").relative_to(ROOT)),
                          "file_sha256": sha(SOURCE / "attempt-009/after-answer.json.gz")},
             "replacements": {k: answer[k] for k in PROTECTED},
             "answer_sha256": digest(answer), "compact_answer_sha256": evidence_digest(answer)}
    reconstructed = {**old, **delta["replacements"]}
    require(reconstructed == answer, "Complete answer delta reconstruction differs")
    if installed:
        require(delta == read(HERE / "answer-delta.json.gz"), "Complete installed answer delta differs")
    else:
        save("answer-delta.json.gz", delta)
    return {"complete009_public_protected_equal": True, "capital_profile_analysis_exact": True,
            "all_old_cell_fields_protected": True, "answer_sha256": digest(answer),
            "compact_answer_sha256": evidence_digest(answer), "report_sha256": answer["report_sha256"],
            "source_occurrences": 1817, "old_occurrences": 1171, "capital_occurrences": 646,
            "unresolved_dependencies": len(ids), "Q3": answer["questions"]["Q3"]["status"],
            "product_hashes": hashes(products)}


def reconstructed_answer():
    delta = read(HERE / "answer-delta.json.gz")
    ref = delta["baseline"]
    require(sha(ROOT / ref["path"]) == ref["file_sha256"], "Answer-delta baseline changed")
    require(set(delta["replacements"]) == PROTECTED, "Unexpected answer delta replacements")
    answer = {**read(ROOT / ref["path"]), **delta["replacements"]}
    require(digest(answer) == delta["answer_sha256"] and
            evidence_digest(answer) == delta["compact_answer_sha256"], "Reconstructed answer identity differs")
    return answer


def composition():
    old, overlay, refs = complete010()
    answer = reconstructed_answer()
    require(not set(answer) & set(overlay), "Duplicate candidate overlay key")
    complete = {**answer, **overlay}
    require(set(complete) == set(old) and
            {k: v for k, v in complete.items() if k not in PROTECTED} ==
            {k: v for k, v in old.items() if k not in PROTECTED}, "Complete010 protected answer changed")
    protected_cells(old["source_statement_cells"], complete["source_statement_cells"])
    return {"complete010_protected_equal": True, "all_three_overlays_equal": True,
            "baseline_complete_sha256": refs["complete_composed_answer_sha256"],
            "candidate_complete_sha256": evidence_digest(complete),
            "distinct_identity_expected": evidence_digest(complete) != evidence_digest(old),
            "answer_delta_file_sha256": sha(HERE / "answer-delta.json.gz"),
            "large_answer_copies": 0}


def refusal(call, expected):
    try:
        call()
    except ValueError as exc:
        require(expected == str(exc), "Wrong adverse refusal: " + str(exc))
        return {"refused": True, "reason": str(exc)}
    raise ValueError("Changed combined annual evidence accepted")


def retained_adverse(name, value, installed):
    path = "adverse-inputs/" + name + ".json.gz"
    if installed:
        require(read(HERE / path) == value, "Installed adverse input differs: " + name)
    else:
        save(path, value)
    return {"path": path, "file_sha256": sha(HERE / path), "content_sha256": evidence_digest(value)}


def inputs(action, installed=False):
    products = after_products()
    original_request = products["P1"]["payload"]["request"]
    original_graph = products["P1"]["payload"]["graph"]
    results = {}
    for case in INPUT_GROUPS[action]:
        request, graph = deepcopy(original_request), original_graph
        reading = request["source_statement_cells"]["reading"]
        if case == "capital-call-erased":
            reading["capital_notes"]["analysis"]["call_dates_not_maturities"] = False
        elif case == "capital-guarantee-omitted":
            del reading["capital_notes"]["profile"]["reading"]["facts"]["note37"]["guarantee"]
        elif case == "capital-condition-erased":
            reading["capital_notes"]["analysis"]["conditional_distributions"] = False
        elif case == "capital-policy-erased":
            del reading["capital_notes"]["profile"]["reading"]["facts"]["policy_2_9"]["contradictory_opening"]
        elif case == "capital-omitted":
            del reading["capital_notes"]
        elif case == "old-reading-erased":
            del reading["eps_cash_notes"]
        elif case == "authority-promoted":
            reading["source_context"]["independent_financial_review"] = True
        else:
            graph = deepcopy(original_graph)
            unit = next(u for u in graph["units"] if u["document"] == "bes-2010-en" and u["page"] == 158)
            unit["bbox"][0] += 1
        request["source_statement_cells"]["graph_sha256"] = digest(graph)
        bad = legacy.p1_from(request, graph)
        graph_delta = [] if graph is original_graph else [unit]
        adverse = {"baseline_product_hashes": hashes(products),
            "source_statement_cells": request["source_statement_cells"],
            "graph_unit_replacements": graph_delta, "P1_sha256": bad["sha256"],
            "graph_sha256": digest(graph), "request_sha256": digest(request)}
        # Prove the retained delta recreates the actual resealed adverse request.
        rebuilt_request = deepcopy(original_request)
        rebuilt_request["source_statement_cells"] = deepcopy(adverse["source_statement_cells"])
        rebuilt_graph = original_graph
        if graph_delta:
            rebuilt_graph = deepcopy(original_graph)
            replacements = {u["id"]: u for u in graph_delta}
            rebuilt_graph["units"] = [deepcopy(replacements.get(u["id"], u)) for u in original_graph["units"]]
        require(legacy.p1_from(rebuilt_request, rebuilt_graph) == bad, "Adverse P1 delta differs")
        ref = retained_adverse(case, adverse, installed)
        expected = ("Statement cell original pages or geometry changed" if graph_delta else
                    "Statement cell reading differs from the reviewed source profile")
        results[case] = {**refusal(lambda: service.construction_product(bad, ROOT), expected),
                         "adverse": ref, "P1_sha256": bad["sha256"], "request_resealed": True}
    return results


def phase_delta(products, case):
    if case == "missing-p2":
        return {"P2": {"remove": ["source_statement_cells"]}}
    if case in {"changed-p2", "capital-stale"}:
        cells = deepcopy(products["P2"]["payload"]["source_statement_cells"])
        if case == "changed-p2":
            cells["reading"]["capital_notes"]["analysis"]["call_dates_not_maturities"] = False
        else:
            del cells["reading"]["capital_notes"]["profile"]["reading"]["facts"]["note37"]["guarantee"]
        return {"P2": {"replace": {"source_statement_cells": cells}}}
    if case == "missing-p3":
        return {"P3": {"remove": ["source_statement_cells_sha256"]}}
    if case == "changed-p3":
        return {"P3": {"replace": {"source_statement_cells_sha256": "0" * 64}}}
    return {"P1": {"remove": ["source_statement_cells"]}}


def apply_phase_delta(values, delta):
    products = {p: {**v, "payload": deepcopy(v["payload"])} if p != "P1" else
                {**v, "payload": {**v["payload"], "request": deepcopy(v["payload"]["request"])}}
                for p, v in values.items()}
    for phase, changes in delta.items():
        target = products[phase]["payload"]
        if phase == "P1":
            target = target["request"]
        for key in changes.get("remove", []):
            del target[key]
        target.update(deepcopy(changes.get("replace", {})))
    return legacy.reseal(products)


def phases(action, installed=False):
    products = after_products()
    results = {}
    for case in PHASE_GROUPS[action]:
        delta = phase_delta(products, case)
        bad = apply_phase_delta(products, delta)
        adverse = {"baseline_product_hashes": hashes(products), "payload_delta": delta,
                   "product_hashes": hashes(bad), "all_parents_resealed": True}
        ref = retained_adverse(case, adverse, installed)
        retained = read(HERE / ref["path"])
        require(hashes(apply_phase_delta(products, retained["payload_delta"])) == retained["product_hashes"],
                "Adverse complete phase-chain reconstruction differs")
        expected = ("Consumed statement cells lack supplied source evidence" if case == "unsupplied" else
                    "Consumed statement cells differ from supplied source evidence")
        results[case] = {**refusal(lambda: legacy.consume(bad), expected),
                         "adverse": ref, "product_hashes": hashes(bad), "all_parents_resealed": True}
    return results


def dispatch(action, installed=False):
    if action == "baseline-products": return baseline_products()
    if action == "baseline-answer": return baseline_answer()
    if action == "candidate-products": return candidate_products(installed)
    if action == "candidate-answer": return candidate_answer(installed)
    if action == "composition": return composition()
    if action in INPUT_GROUPS: return inputs(action, installed)
    if action in PHASE_GROUPS: return phases(action, installed)
    if action in {"prior-9m", "prior-q1", "prior-fy"}: return prior.prior(action)
    raise ValueError("Unknown capital comparison: " + action)


def installed_main():
    root, folder, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    sys.dont_write_bytecode = True
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    require(sys.flags.isolated == 1, "Isolated interpreter required")
    require(not any(n == "legalmath" or n.startswith("legalmath.") for n in sys.modules),
            "Package loaded before isolated path setup")
    sys.path.insert(0, str(folder / "installed"))
    def block(event, args):
        if event.startswith("socket.") or event in {
            "subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.spawn"}:
            raise RuntimeError("Installed capital comparison forbids network/native processes: " + event)
    sys.addaudithook(block)
    configure(root, folder)
    expected = read(folder / "final-package.json")
    package = (folder / "installed/legalmath").resolve()
    require(legacy.package_files(package) == expected, "Installed package bytes differ")
    result = dispatch(action, installed=True)
    require(result == read(folder / "checks" / (action + ".json")), "Installed stage differs: " + action)
    modules = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(package), "Checkout import: " + name)
            require(sha(path) == expected[str(path.relative_to(package))], "Loaded module bytes differ")
            modules[name] = str(path)
    require(legacy.package_files(package) == expected, "Installed package drift")
    save("installed-checks/" + action + ".json", {"status": "PASS", "details": result,
        "python": sys.executable, "isolated": sys.flags.isolated, "modules": modules,
        "sys_path": sys.path, "package_files": len(expected), "native_calls": 0})
    print(json.dumps({"status": "PASS", "action": action, "package_files": len(expected)}))


if __name__ == "__main__":
    installed_main()
