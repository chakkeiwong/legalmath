"""Installed dataflow probes with predeclared deterministic expected answers.

The synthetic interpretation and hypothetical financial scenarios are development
evidence. They never supply independent legal labels or actual event facts.
"""
from copy import deepcopy
import subprocess
from . import service, source_graph
from .contracts import VERSION, digest, read, write


def installed_semantic_checks(root, folder, install, env, python):
    out = folder / "semantic-checks"
    out.mkdir()
    checks = []

    def consume(name, products, question, expected, select=None):
        manifest = {"products": {}}
        for phase, product in products.items():
            path = out / "products" / (product["sha256"] + ".json")
            if not path.exists():
                write(path, product)
            manifest["products"][phase] = {"path": str(path.relative_to(root)),
                                           "sha256": digest(path.read_bytes())}
        path = out / (name + "-inputs.json")
        report = out / (name + "-report.json")
        write(path, manifest)
        command = [str(python), str(install / "bin/legalmath"), "prospectus", "consume",
                   "--products", str(path), "--repository", str(root), "--output", str(report)]
        run = subprocess.run(command, cwd=install, env=env, capture_output=True, text=True, timeout=180)
        (out / (name + ".log")).write_text(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError("Installed semantic probe failed: " + name)
        result = read(report)
        answer = result["questions"][question]
        actual = select(answer) if select else answer["status"]
        if actual != expected or result["may_execute_transaction"]:
            raise ValueError("Installed semantic probe mismatch: " + name)
        if result != service.consume(products, root):
            raise ValueError("Installed and worktree semantic probe differ: " + name)
        checks.append({"name": name, "question": question, "expected": expected, "actual": actual,
                       "outcome": "PASS", "command": command, "report_sha256": digest(report.read_bytes()),
                       "products": result["consumed_products"]})

    def stages(request):
        p1 = service.source_product(request, root)
        p2 = service.construction_product(p1, root)
        p3 = service.interpretation_product(p1, p2)
        return {"P1": p1, "P2": p2, "P3": p3,
                "P4": service.law_product(p1, p3), "P5": service.financial_product(p1, p2, p3)}

    time = "2026-01-01T00:00:00Z"
    source = out / "synthetic-contract.txt"
    source.write_text("The Notes are unsecured obligations of the Issuer. "
                      "The Notes will be redeemed at 100 per cent of their principal amount at maturity.")
    bundle = {"instrument_id": "synthetic-dataflow", "purpose": "review", "issue_date": time,
              "effective_at": time, "known_at": time, "dependencies": [], "documents": [
                  {"id": "fixture", "path": str(source.relative_to(root)), "sha256": digest(source.read_bytes()),
                   "format": "text", "language": "en", "authority": "Synthetic engineering fixture",
                   "document_date": time, "known_from": time}]}
    graph = source_graph.build(bundle, root)
    unit = graph["units"][0]
    request = {"version": VERSION, "bundle": bundle,
               "assembly": {"operations": [{"unit": unit["id"], "role": "OPERATIVE", "context": "whole",
                   "reason": "Complete synthetic fixture", "source_text_sha256": unit["text_sha256"]}]},
               "scope": {q: {"complete": True, "reason": "Complete synthetic fixture"} for q in ("Q1", "Q2")}}
    products = stages(request)
    consume("selected-baseline", products, "Q1", "NO")
    changed = deepcopy(products["P2"]["payload"])
    changed["assembly"]["units"][0]["role"] = "UNKNOWN"
    changed_products = {**products, "P2": service.seal("P2", bundle, {"P1": products["P1"]["sha256"]}, changed)}
    changed_products["P3"] = service.interpretation_product(changed_products["P1"], changed_products["P2"])
    changed_products["P4"] = service.law_product(changed_products["P1"], changed_products["P3"])
    changed_products["P5"] = service.financial_product(changed_products["P1"], changed_products["P2"], changed_products["P3"])
    consume("selected-changed", changed_products, "Q1", "UNKNOWN")

    anchor = {"unit": unit["id"], "document": unit["document"], "source_sha256": unit["source_sha256"],
              "start": 0, "end": len(unit["raw"]), "quote": unit["raw"]}
    basis = {"id": "synthetic-rule", "authority": "Synthetic proposition; no legal interpretation",
             "jurisdiction": "fixture", "edition": "1", "instrument_id": bundle["instrument_id"],
             "source": anchor, "valid_from": time, "known_from": time, "premises": ["necessary"]}
    fact = {"name": "necessary", "basis_id": basis["id"], "jurisdiction": "fixture",
            "instrument_id": bundle["instrument_id"], "value": True, "source": anchor,
            "valid_from": time, "known_from": time, "observed_at": time}
    for value, expected in ((True, "YES"), (False, "NO")):
        p4 = service.law_product(products["P1"], products["P3"],
                                law_input={"law_bases": [basis], "facts": [{**fact, "value": value}]})
        consume("law-" + str(value).lower(), {**products, "P4": p4}, "Q4", expected)

    from ..closure_mechanisms import PROFILES
    from .jobs import INVENTORY
    key = "deutsche-at1-2025"
    meta = read(root / INVENTORY)["documents"][PROFILES[key]["document"]]
    scenario = deepcopy(read(root / "docs/prospectus/evidence-closure/scenarios.json")[key])
    for index, holding in enumerate(scenario.get("holdings", [])):
        holding.update(legal_holder_id="synthetic-holder-a", account_id="synthetic-account-" + str(index))
    financial_request = {"version": VERSION, "bundle": {**bundle, "instrument_id": key, "documents": [
        {"id": meta["id"], "path": meta["original"], "sha256": PROFILES[key]["sha256"], "format": "pdf",
         "language": "de/en", "authority": "Retained issuer prospectus; hypothetical calculation only",
         "document_date": "2025-01-01T00:00:00Z", "known_from": time}]}}
    # The artificial document date controls visibility in this engineering probe;
    # it is not admitted as a source publication date in the real campaign.
    financial_products = stages(financial_request)
    for loss, expected in (("50", "25"), ("60", "30")):
        p5 = service.financial_product(financial_products["P1"], financial_products["P2"], financial_products["P3"],
                                       scenario={**scenario, "required_loss": loss})
        consume("financial-loss-" + loss, {**financial_products, "P5": p5}, "Q5", expected,
                lambda answer: answer["value"]["calculation"]["write_down"])
    result = {"scope": "DETERMINISTIC_DEVELOPMENT_DATAFLOW; no independent legal acceptance",
              "checks": checks, "phase_inputs_changed_independently": ["P2", "P4", "P5"],
              "financial_date": "Synthetic visibility date only; not a real publication assertion"}
    write(out / "result.json", result)
    return result
