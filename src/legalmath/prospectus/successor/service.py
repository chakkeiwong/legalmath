"""One supported intake-to-report path; default extraction remains conservative."""
from pathlib import Path
from .contracts import VERSION, QueryResult, digest, read, validate_request, write
from . import source_graph, contract_assembly, clause_graph, law_facts, financial_profiles


def assess(request, root, bank=None):
    bundle = validate_request(request)
    graph = source_graph.build(bundle, root)
    assembly = contract_assembly.assemble(graph, request.get("assembly"))
    construction = None
    if request.get("construction"):
        from .basf import construct, as_assembly
        from .contracts import bound_path
        spec = request["construction"]
        if spec["profile"] != "basf-option-i":
            raise ValueError("Unsupported construction profile")
        path = bound_path(root, spec["admission_path"])
        if digest(path.read_bytes()) != spec["admission_sha256"]:
            raise ValueError("Construction admission changed")
        construction = construct(graph, read(path))
        assembly = as_assembly(graph, construction)
    clauses = clause_graph.build(assembly, request.get("clauses"))
    dependencies = list(bundle.get("dependencies", []))
    for issue in graph["unresolved"]:
        dependencies.append({"id": issue["document"] + ":" + issue["reason"],
            "questions": ["Q1", "Q2"], "status": "UNRESOLVED"})
    supplied = request.get("reference_dispositions", {})
    for ref in graph["references"]:
        if supplied.get(ref["unit"] + ":" + ref["target"]) != "RESOLVED":
            dependencies.append({"id": ref["unit"] + ":" + ref["target"],
                "questions": ["Q1", "Q2"], "status": "UNRESOLVED"})
    questions = clause_graph.evaluate(clauses, assembly, request.get("scope", {}), dependencies)
    questions["Q4"] = law_facts.assess(bundle, request.get("law_bases", []), request.get("facts", []))
    questions["Q5"] = financial_profiles.assess(bundle, request.get("financial_scenario"))
    if bank is None and request.get("bank"):
        from ...transaction.evidence import Store
        from .contracts import bound_path
        bank = {"request": request["bank"]["request"],
                "store": Store(bound_path(root, request["bank"]["store"]))}
    if bank:
        from .integration import investigate
        questions["Q6"] = investigate(bundle, bank)
    else:
        questions["Q6"] = QueryResult("Q6", "UNKNOWN", unresolved=["Bank context/evidence store not supplied"]).json()
    result = {"version": VERSION, "instrument_id": bundle["instrument_id"],
        "request_sha256": digest(request), "questions": questions, "source_map": graph,
        "assembly": assembly, "selected_contract": construction, "clause_graph": clauses, "dependencies": dependencies,
        "mode": "ASSISTED" if request.get("clauses") is not None else "AUTOMATIC_BOUNDED",
        "independent_legal_acceptance": False, "may_execute_transaction": False}
    return {**result, "report_sha256": digest(result)}


def configure(parser):
    commands = parser.add_subparsers(dest="prospectus_command", required=True)
    assess_parser = commands.add_parser("assess", help="Assess a source-bound, explicitly scoped request")
    assess_parser.add_argument("--request", required=True)
    assess_parser.add_argument("--repository", default=".")
    assess_parser.add_argument("--output", required=True)


def dispatch(args):
    result = assess(read(args.request), Path(args.repository))
    write(args.output, result)
    return {"report": args.output, "report_sha256": result["report_sha256"],
            "questions": result["questions"], "may_execute_transaction": False}
