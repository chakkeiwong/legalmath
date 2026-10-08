"""Check final product computations, distinct from raw model graph proposals."""
from scripts.legal_gap_program import OLD, OUT, DOC, read, save, ref, check_ref, worker, command


def query_repair(folder, arm):
    from scripts.legal_gap_live import product_query
    requests = sorted((OUT / "live/products" / arm).glob("tool-stages/*/request.json"),
                      key=lambda p: int(p.parent.name))
    if not requests:
        return {"status": "UNTESTED_NO_PRODUCT_REQUEST"}
    request = read(requests[0])
    query = product_query(request)
    if not query:
        return {"status": "UNSUPPORTED_MISSING_LEGAL_QUESTION", "request": ref(requests[0])}
    units = [{"id": u["unit_id"], "text": u["text"]} for u in request["source_packet"]["units"]]
    benchmark = read(DOC / "benchmark.json")["retrieval_targets"]
    labels = {(u["id"], target["quote"]) for question in ("p10", "p14")
              for target in benchmark[question] for u in units if target["quote"] in u["text"]}
    targets = [{"unit_id": key, "quote": quote} for key, quote in sorted(labels)]
    data = {"corpus": {"units": units}, "questions": [
        {"id": "original-task-label", "question": request.get("task", "")},
        {"id": "corrected-legal-question", "question": query}],
        "targets": {key: targets for key in ("original-task-label", "corrected-legal-question")}}
    result = worker("retrieval", data, folder)
    texts = {u["id"]: u["text"] for u in units}
    for row in result["rows"]:
        for p in row["passages"]:
            if texts[p["unit_id"]][p["start"]:p["end"]] != p["text"]:
                raise ValueError("Query repair changed the source")
    return {"status": "QUERY_ROUTING_REPAIR_CHECKED_OFFLINE", "request": ref(requests[0]),
            "evidence": ref(folder / "output.json"), "query": query,
            "live_corrected_benefit": "UNTESTED", "limit": "Same-source development location check only"}


def run(folder, products):
    from scripts.legal_gap_tools import validate_graph
    from legalmath.translation.expressions import expression
    results = {}
    for arm, product in products.items():
        target = folder / arm
        target.mkdir(parents=True, exist_ok=True)
        query_result = query_repair(target / "query-repair", arm)
        if "dossier" not in product:
            paths = list((OUT / "live/products" / arm).glob("revisions/*/core/actions/*/interpretation/candidates.json"))
            if len(paths) != 1:
                results[arm] = {"status": "UNTESTED_NO_PRODUCT_CANDIDATES", "product": product,
                                "query_routing_repair": query_result}
                continue
            dossier = {"candidates": ref(paths[0])}
        else:
            dossier = read(check_ref(product["dossier"]))
        graphs = dossier.get("semantic_stage", {}).get("report", {}).get("reasoning", {})
        graph_rows = []
        for index, (identity, graph) in enumerate(sorted(graphs.items())):
            out = target / "graphs" / str(index)
            out.mkdir(parents=True, exist_ok=True)
            save(out / "product-graph.json", graph)
            theory, evaluation = graph["theory"], graph["evaluation"]
            row = {"settings_identity": identity, "source": ref(out / "product-graph.json"),
                   "semantics": evaluation["semantics"]}
            if theory["completion"] != "complete" or evaluation["completion"] != "complete":
                graph_rows.append({**row, "status": "UNSUPPORTED_INCOMPLETE_LOCAL_GRAPH",
                                   "evaluation": evaluation})
                continue
            case = {"id": "retained-product", "ids": [a["id"] for a in theory["arguments"]],
                    "attacks": [[a["source"], a["target"]] for a in theory["attacks"]]}
            try:
                validate_graph(case)
            except ValueError as exc:
                graph_rows.append({**row, "status": "UNSUPPORTED", "reason": str(exc)})
                continue
            external = worker("pyarg", {"cases": [case]}, out / "pyarg")
            native = out / "carneades"
            native.mkdir()
            save(native / "input.json", {"cases": [case]})
            command([OLD / "T2/attempt-1/carneades-adapter/trial", native / "input.json",
                     native / "output.json"], native, "run")
            other = read(native / "output.json")
            semantics, expected = evaluation["semantics"], evaluation["extensions"]
            matching = (external["cases"][0][semantics] == expected ==
                        other["cases"][0][semantics])
            graph_rows.append({**row, "status": "PASS" if matching else "FAILED",
                "pyarg": ref(out / "pyarg/output.json"), "carneades": ref(native / "output.json"),
                "exact_product_nodes_and_defeats": True, "legal_warrant": "NOT_ESTABLISHED"})
        candidates_path = check_ref(dossier["candidates"])
        candidates = read(candidates_path)
        encoded, unformalized, unsupported = [], [], []
        for identity, reading in candidates.items():
            formal = reading.get("formalization")
            if not formal:
                unformalized.append(identity)
            elif formal["result_type"] != "bool" or any(f["type"] != "bool" for f in formal["facts"]):
                unsupported.append(identity)
            else:
                encoded.append({"id": identity, "scope": expression(formal["scope"], "scope"),
                                "result": expression(formal["result"], "result")})
        boolean = (worker("boolean", {"readings": encoded}, target / "boolean")
                   if encoded else {"status": "UNTESTED_NO_SUPPORTED_READINGS", "readings": []})
        results[arm] = {"status": "PRODUCT_OUTPUTS_CHECKED" if "dossier" in product else "PARTIAL_PRODUCT_CANDIDATES_CHECKED",
            "dossier": product.get("dossier"),
            "query_routing_repair": query_result,
            "candidate_source": ref(candidates_path), "retained_candidates": len(candidates),
            "graphs": graph_rows, "boolean": boolean, "unformalized": unformalized,
            "unsupported_profiles": unsupported,
            "final_graph_status": "CHECKED_WHERE_SUPPORTED" if graphs else "UNTESTED_NO_FINAL_PRODUCT_GRAPH",
            "feedback_to_completed_live_trial": False,
            "limit": "Final computation checks only; full source meaning and legal sufficiency remain unestablished"}
    save(folder / "result.json", results)
    return {"results": ref(folder / "result.json"),
            "status": "FINAL_PRODUCT_COMPUTATION_CHECKS_RECORDED"}
