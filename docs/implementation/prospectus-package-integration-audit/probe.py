"""Bounded synthetic boundary probes; no historical artifacts are modified."""
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.successor import (clause_graph, construction_ast,
    contract_assembly, evaluation, law_facts, predicates, service, source_graph)
from legalmath.prospectus.successor.contracts import VERSION, digest, write
from legalmath.prospectus.successor.read_context import ReadContext, current

TIME = "2026-01-01T00:00:00Z"
PREFIX = ("The Notes are unsecured obligations of the Issuer. "
          "The Notes will be redeemed at 100 per cent of their principal amount at maturity. ")
LOSS = "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."


def request(folder, texts):
    path = folder / "source.txt"
    path.write_text("\f".join(texts))
    bundle = {"instrument_id": "audit-synthetic", "purpose": "review",
              "issue_date": TIME, "effective_at": TIME, "known_at": TIME,
              "documents": [{"id": "d", "path": "source.txt", "sha256": digest(path.read_bytes()),
                             "format": "text", "language": "en", "authority": "Synthetic audit input",
                             "document_date": TIME, "known_from": TIME}]}
    graph = source_graph.build(bundle, folder)
    return {"version": VERSION, "bundle": bundle,
            "assembly": {"operations": [{"unit": u["id"], "role": "OPERATIVE",
                "reason": "Explicit synthetic scope", "source_text_sha256": u["text_sha256"],
                "context": "whole"} for u in graph["units"]]},
            "scope": {q: {"complete": True} for q in ("Q1", "Q2")}}


def anchor(unit):
    return {k: unit[k] for k in ("document", "source_sha256")} | {
        "unit": unit["id"], "start": 0, "end": len(unit["raw"]), "quote": unit["raw"]}


def outcome(call):
    try:
        return {"accepted": True, "result": call()}
    except Exception as exc:
        return {"accepted": False, "exception": type(exc).__name__, "message": str(exc)}


def ocr_probe(folder):
    req = request(folder, ["Synthetic identity; this probe tests the retained JSON loader."])
    document = req["bundle"]["documents"][0]
    data = {"source_sha256": document["sha256"], "page_count": 2,
            "runtime": {"dpi": 300, "language": "eng"}, "pages": [
                {"page": n, "text": "line", "words": [[0, 0, 10, 10, "line", 0, 0, 0]]}
                for n in (1, 2)]}
    results = {}
    for name, pages in (("valid", [1, 2]), ("duplicate", [1, 1]),
                        ("reversed", [2, 1]), ("out_of_range", [0, 3])):
        candidate = copy.deepcopy(data)
        for row, number in zip(candidate["pages"], pages):
            row["page"] = number
        path = folder / "ocr.json"
        write(path, candidate)
        doc = {**document, "ocr": {"path": "ocr.json", "sha256": digest(path.read_bytes())}}
        def load():
            units, count, _ = source_graph.retained_ocr_units(doc, folder)
            return {"pages": [u["page"] for u in units], "unit_ids": [u["id"] for u in units], "page_count": count}
        results[name] = outcome(load)
    return results


def constraint_probe(folder):
    req = request(folder, [PREFIX + LOSS, "This unselected alternative asserts trigger."])
    req["assembly"]["operations"][1]["role"] = "EXCLUDED"
    graph = source_graph.build(req["bundle"], folder)
    assembled = contract_assembly.assemble(graph, req["assembly"])
    clauses = clause_graph.build(assembled)["nodes"]
    next(n for n in clauses if n["effect"] == "principal_loss")["conditions"] = "trigger"
    req.update(clauses=clauses, predicate_engine="z3")
    control = service.assess(req, folder)["questions"]["Q1"]
    req["predicate_constraints"] = [{"id": "unselected", "expression": "trigger",
        "source": anchor(graph["units"][1]), "reason": "Deliberately quote an excluded alternative"}]
    constrained = service.assess(req, folder)["questions"]["Q1"]
    direct = predicates.solve("trigger", {}, req["predicate_constraints"], graph=graph)
    return {"without_constraint": control, "with_excluded_source_constraint": constrained,
            "direct_solver": direct, "service_question_keys": sorted(constrained)}


def diagnostic_probe(folder):
    req = request(folder, [PREFIX + LOSS])
    graph = source_graph.build(req["bundle"], folder)
    source = anchor(graph["units"][0])
    constraints = [{"id": name, "expression": expr, "source": source, "reason": "Synthetic contradiction"}
                   for name, expr in (("yes", "trigger"), ("no", {"not": "trigger"}))]
    req.update(predicate_engine="z3", predicate_constraints=constraints)
    return {"direct": predicates.solve(True, {}, constraints, graph=graph),
            "service": service.assess(req, folder)["questions"]["Q1"]}


def engine_scope_probe(folder):
    req = request(folder, [PREFIX])
    graph = source_graph.build(req["bundle"], folder)
    source = anchor(graph["units"][0])
    expr = {"all": ["f" + str(i) for i in range(13)]}
    basis = {"id": "law", "authority": "Synthetic", "jurisdiction": "X", "edition": "1",
             "instrument_id": req["bundle"]["instrument_id"], "source": source,
             "valid_from": TIME, "known_from": TIME, "premises": expr}
    req.update(predicate_engine="z3", law_bases=[basis])
    spec = {"version": "contract-ast.v2", "root": "t", "nodes": [
        {"id": "t", "kind": "Text", "source": source}], "constraints": [expr]}
    return {"z3_direct": outcome(lambda: predicates.solve(expr, {})),
            "service_law_with_z3_selected": outcome(lambda: service.assess(req, folder)),
            "constructor": outcome(lambda: construction_ast.render(graph, spec))}


def reference_probe(folder):
    req = request(folder, ["Condition 2 applies.", PREFIX])
    graph = source_graph.build(req["bundle"], folder)
    anchors = [anchor(u) for u in graph["units"]]
    req["assembly"]["ast"] = {"version": "contract-ast.v2", "root": "s", "nodes": [
        {"id": "s", "kind": "Sequence", "children": ["a", "b"]},
        {"id": "a", "kind": "Text", "source": anchors[0]},
        {"id": "b", "kind": "Text", "source": anchors[1]}]}
    assembled = contract_assembly.assemble(graph, req["assembly"])
    ref = graph["references"][0]
    decision = {"source_sha256": ref["source_sha256"], "reason": "Synthetic explicit target"}
    results = {}
    for name, target in (("raw_target", graph["units"][1]["id"]), ("assembled_target", "ast:2")):
        req["reference_dispositions"] = {ref["id"]: {**decision, "targets": [target]}}
        results[name] = outcome(lambda: service.dependencies(req, graph, assembled))
    return {"operative_units": [u["unit"] for u in assembled["units"]], "results": results}


def evaluation_probe(folder):
    cohort = [{"id": "sample", "questions": ["Q1"]}]
    identities = {"implementer": "developer", "readers": ["a", "b"], "adjudicator": "c"}
    label = {"id": "sample", "question": "Q1", "value": "YES", "blinded": True,
             "readers": ["a", "b"], "adjudicator": "c", "cohort_sha256": digest(cohort),
             "evidence": [{"source_sha256": "0" * 64, "quote": "No such source supplied",
                           "start": -10, "end": -9}]}
    return outcome(lambda: evaluation.score([{"id": "sample", "question": "Q1", "value": "YES"}],
                     [label], cohort, identities, "1" * 64))


def unrecorded_read_probe(folder):
    path = folder / "undeclared"
    path.write_text("before")
    context = ReadContext(folder, folder / "snapshots")
    code = "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())"
    run = context.tool([sys.executable, "-c", code, str(path)], timeout=5)
    manifest = context.manifest()
    path.write_text("after")
    return {"child_output": run.stdout.decode().strip(), "read_changed": True,
            "manifest_still_current": current(folder, manifest),
            "declared_boundary": manifest["boundary"]}


def main():
    started = time.monotonic()
    results = {}
    with tempfile.TemporaryDirectory(prefix="prospectus-audit-") as temp:
        for function in (ocr_probe, constraint_probe, diagnostic_probe, engine_scope_probe,
                         reference_probe, evaluation_probe, unrecorded_read_probe):
            folder = Path(temp) / function.__name__
            folder.mkdir()
            results[function.__name__] = outcome(lambda: function(folder))
    record = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "command": [sys.executable, *sys.argv], "python": sys.version,
              "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1; no GPU probe", "random_seeds": "Z3 random_seed=0",
              "data_version": "Synthetic boundary fixtures in this probe; not legal truth labels",
              "plan": "docs/plans/prospectus-package-integration-audit-2026-10-08.md",
              "result_file": "docs/implementation/prospectus-package-integration-audit/probe-results.json",
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "wall_seconds": time.monotonic() - started,
              "packages": {n: importlib.metadata.version(n) for n in ("legalmath", "z3-solver")},
              "results": results}
    output = Path(__file__).with_name("probe-results.json")
    if output.exists():
        raise ValueError("Audit result already exists; preserve it")
    write(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
