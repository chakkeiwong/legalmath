"""Connected phase products, with a separate installed consumer."""
from pathlib import Path
from .contracts import VERSION, QueryResult, digest, read, validate_request, write, bound_path
from . import source_graph, contract_assembly, clause_graph, law_facts, financial_profiles
from .anchors import bind

PRODUCT_VERSION = "prospectus-product.v2"


def seal(stage, bundle, inputs, payload):
    body = {"version": PRODUCT_VERSION, "stage": stage, "bundle_sha256": digest(bundle),
            "inputs": inputs, "payload": payload}
    return {**body, "sha256": digest(body)}


def verify(product, stage, bundle=None, inputs=None):
    if product.get("version") != PRODUCT_VERSION or product.get("stage") != stage:
        raise ValueError("Wrong phase product version/stage")
    if product.get("sha256") != digest({k:v for k,v in product.items() if k != "sha256"}):
        raise ValueError("Phase product content changed")
    if bundle is not None and product["bundle_sha256"] != digest(bundle):
        raise ValueError("Phase product belongs to another question/source bundle")
    if inputs is not None and product["inputs"] != inputs:
        raise ValueError("Phase product parent bindings changed")
    return product["payload"]


def source_product(request, root):
    bundle = validate_request(request)
    return seal("P1", bundle, {"request": digest(request)},
                {"request": request, "graph": source_graph.build(bundle, root)})


def construction_product(source, root):
    payload = verify(source, "P1")
    request, graph = payload["request"], payload["graph"]
    bundle = validate_request(request)
    verify(source, "P1", bundle, {"request": digest(request)})
    for document in bundle["documents"]:
        if digest(bound_path(root,document["path"]).read_bytes()) != document["sha256"]:
            raise ValueError("Source bytes changed after intake: " + document["id"])
    construction = None
    if request.get("construction"):
        from .basf import construct, as_assembly
        spec = request["construction"]
        if spec["profile"] != "basf-option-i":
            raise ValueError("Unsupported construction profile")
        path = bound_path(root, spec["admission_path"])
        if digest(path.read_bytes()) != spec["admission_sha256"]:
            raise ValueError("Construction admission changed")
        construction = construct(graph, read(path))
        assembly = as_assembly(graph, construction)
    else:
        assembly = contract_assembly.assemble(graph, request.get("assembly"))
    return seal("P2", bundle, {"P1": source["sha256"]}, {"assembly": assembly, "selected_contract": construction})


def dependencies(request, graph, assembly):
    result = list(request["bundle"].get("dependencies", []))
    operative = {u["unit"]: u for u in assembly["units"] if u["role"] in {"OPERATIVE", "UNKNOWN"}}
    documents = {u["source"]["document"] for u in operative.values()}
    for issue in graph["unresolved"]:
        if issue["document"] in documents:
            result.append({"id": issue["document"] + ":" + issue["reason"], "questions": ["Q1", "Q2"], "status": "UNRESOLVED"})
    supplied = request.get("reference_dispositions", {})
    if set(supplied) - {r["id"] for r in graph["references"]}:
        raise ValueError("Unknown reference disposition")
    raw_units = {u["id"]: u for u in graph["units"]}
    edges = []
    for ref in graph["references"]:
        referencing = operative.get(ref["unit"])
        if referencing is None:
            referencing = next((u for u in operative.values() if any(
                p.get("source", {}).get("unit") == ref["unit"] for p in u.get("character_map", [])
                if isinstance(p.get("source"), dict))), None)
        if referencing is None:
            continue
        decision = supplied.get(ref["id"])
        resolved = False
        if decision:
            if not isinstance(decision, dict) or not decision.get("reason") or decision.get("source_sha256") != ref["source_sha256"]:
                raise ValueError("Reference disposition must bind occurrence edition and reason")
            targets = decision.get("targets", [])
            if not targets or any(t not in raw_units or not raw_units[t]["visible"] or t not in operative for t in targets):
                raise ValueError("Reference targets must be available operative source units")
            resolved = True
        result.append({"id": ref["id"], "questions": referencing["questions"],
                       "status": "RESOLVED" if resolved else "UNRESOLVED",
                       "targets": decision.get("targets", []) if decision else []})
        kind = decision.get("kind", "reference") if decision else "reference"
        from .reference_closure import KINDS
        if kind not in KINDS:
            raise ValueError("Unsupported reference kind")
        authority = decision.get("authority") if decision else None
        if authority is not None:
            from .anchors import bind
            bind(graph, authority)
        for target in (decision.get("targets") if decision else None) or [None]:
            edges.append({"id": ref["id"], "from": ref["unit"], "to": target, "kind": kind,
                          "resolved": resolved, "authority": authority})
    from .reference_closure import close
    for question in ("Q1", "Q2"):
        roots = {u for u, row in operative.items() if question in row["questions"] and u in raw_units}
        for row in operative.values():
            if question in row["questions"]:
                roots.update(p["source"]["unit"] for p in row.get("character_map", [])
                             if isinstance(p.get("source"), dict) and "unit" in p["source"])
        closure = close(raw_units, edges, roots)
        if closure["unresolved"]:
            result.append({"id": "reference-closure:" + question, "questions": [question],
                           "status": "UNRESOLVED", **closure})
    return result


def interpretation_product(source, construction, interpretation=None):
    payload = verify(source, "P1")
    request, graph = payload["request"], payload["graph"]
    bundle = request["bundle"]
    if interpretation is not None:
        from .anchors import fields
        fields(interpretation, {"clauses", "scope", "observations", "reference_dispositions", "predicate_engine", "predicate_constraints"})
        request = {**request, **interpretation}
    selected = verify(construction, "P2", bundle, {"P1": source["sha256"]})
    assembly = selected["assembly"]
    clauses = clause_graph.build(assembly, request.get("clauses"))
    deps = dependencies(request, graph, assembly)
    questions = clause_graph.evaluate(clauses, assembly, request.get("scope", {}), deps, request.get("observations"),
        predicate_engine=request.get("predicate_engine", "finite"), predicate_constraints=request.get("predicate_constraints", ()), source_graph=graph)
    return seal("P3", bundle, {"P1": source["sha256"], "P2": construction["sha256"]},
                {"clauses": clauses, "dependencies": deps, "questions": questions,
                 "interpretation_input": interpretation, "scope": request.get("scope", {})})


def law_product(source, interpretation, cases=None, law_input=None):
    payload = verify(source, "P1")
    request = payload["request"]
    verify(interpretation, "P3", request["bundle"])
    if law_input is not None:
        from .anchors import fields
        fields(law_input, {"law_bases", "facts", "law_relation"}, {"law_bases", "facts"})
        request = {**request, **law_input}
    question = law_facts.assess(request["bundle"], request.get("law_bases", []), request.get("facts", []),
                               payload["graph"], request.get("law_relation"))
    return seal("P4", request["bundle"], {"P1": source["sha256"], "P3": interpretation["sha256"]},
                {"question": question, "cases": cases or [], "law_input": law_input})


def financial_product(source, construction, interpretation, cases=None, scenario=None):
    request = verify(source, "P1")["request"]
    verify(construction, "P2", request["bundle"], {"P1": source["sha256"]})
    verify(interpretation, "P3", request["bundle"], {"P1": source["sha256"], "P2": construction["sha256"]})
    supplied = scenario if scenario is not None else request.get("financial_scenario")
    question = financial_profiles.assess(request["bundle"], supplied, verify(source, "P1")["graph"])
    return seal("P5", request["bundle"], {"P2": construction["sha256"], "P3": interpretation["sha256"]},
                {"question": question, "cases": cases or [], "scenario_input": supplied})


def consume(products, root, bank=None, include_artifacts=False):
    source, construction, interpretation, law, financial = [products[p] for p in ("P1", "P2", "P3", "P4", "P5")]
    data = verify(source, "P1")
    request, graph = data["request"], data["graph"]
    bundle = validate_request(request)
    verify(source, "P1", bundle, {"request": digest(request)})
    if graph["bundle_sha256"] != digest(bundle):
        raise ValueError("Source graph bundle changed")
    for document in bundle["documents"]:
        if digest(bound_path(root,document["path"]).read_bytes()) != document["sha256"]:
            raise ValueError("Source bytes changed after intake: " + document["id"])
    selected = verify(construction, "P2", bundle, {"P1": source["sha256"]})
    semantic = verify(interpretation, "P3", bundle, {"P1": source["sha256"], "P2": construction["sha256"]})
    if semantic["clauses"]["assembly_sha256"] != digest(selected["assembly"]):
        raise ValueError("Interpreted assembly differs from selected contract")
    legal = verify(law, "P4", bundle, {"P1": source["sha256"], "P3": interpretation["sha256"]})
    amounts = verify(financial, "P5", bundle, {"P2": construction["sha256"], "P3": interpretation["sha256"]})
    questions = {**semantic["questions"], "Q4": legal["question"], "Q5": amounts["question"]}
    if bank is None and request.get("bank"):
        from ...transaction.evidence import Store
        bank = {**request["bank"], "store": Store(bound_path(root, request["bank"]["store"]))}
    if bank:
        from .integration import investigate
        questions["Q6"] = investigate(bundle, bank, graph)
    else:
        questions["Q6"] = QueryResult("Q6", "UNKNOWN", unresolved=["Bank context/evidence store not supplied"]).json()
    scope = semantic["scope"]
    declared = [q for q in scope if q in {"Q1", "Q2", "Q4", "Q5", "Q6"}] or ["Q1", "Q2"]
    completeness = {q: {"complete": bool(scope.get(q, {}).get("complete")) and
                              not questions[q]["unresolved"] and questions[q]["status"] not in {"UNKNOWN", "UNSUPPORTED"},
                        "unresolved": questions[q]["unresolved"]} for q in declared}
    questions["Q3"] = QueryResult("Q3", "COMPLETE" if all(v["complete"] for v in completeness.values()) else "PARTIAL",
                                  completeness, quantifier="Declared questions: " + ", ".join(declared)).json()
    result = {"version": VERSION, "instrument_id": bundle["instrument_id"], "request_sha256": digest(request),
              "questions": questions, "consumed_products": {p: products[p]["sha256"] for p in products},
              "law_cases": legal["cases"], "financial_cases": amounts["cases"],
              "mode": "ASSISTED" if semantic["clauses"]["origin"] == "assisted-proposal" else "AUTOMATIC_BOUNDED",
              "independent_legal_acceptance": False, "may_execute_transaction": False}
    if include_artifacts:
        result.update(source_map=graph, assembly=selected["assembly"], selected_contract=selected["selected_contract"],
                      clause_graph=semantic["clauses"], dependencies=semantic["dependencies"])
    return {**result, "report_sha256": digest(result)}


def assess(request, root, bank=None):
    p1 = source_product(request, root)
    p2 = construction_product(p1, root)
    p3 = interpretation_product(p1, p2)
    return consume({"P1": p1, "P2": p2, "P3": p3, "P4": law_product(p1, p3),
                    "P5": financial_product(p1, p2, p3)}, root, bank, include_artifacts=True)


def configure(parser):
    commands = parser.add_subparsers(dest="prospectus_command", required=True)
    for name, arg in (("assess", "--request"), ("consume", "--products")):
        p = commands.add_parser(name)
        p.add_argument(arg, required=True)
        p.add_argument("--repository", default=".")
        p.add_argument("--output", required=True)


def dispatch(args):
    root = Path(args.repository)
    if args.prospectus_command == "consume":
        manifest = read(args.products)
        products = {}
        for stage, row in manifest["products"].items():
            path = bound_path(root, row["path"])
            if digest(path.read_bytes()) != row["sha256"]:
                raise ValueError("Stored product bytes changed: " + stage)
            products[stage] = read(path)
        bank = manifest.get("bank")
        if bank:
            from ...transaction.evidence import Store
            bank = {**bank, "store": Store(bound_path(root, bank["store"]))}
        result = consume(products, root, bank)
    else:
        result = assess(read(args.request), root)
    write(args.output, result)
    return {"report": args.output, "report_sha256": result["report_sha256"],
            "questions": {q: r["status"] for q, r in result["questions"].items()}, "may_execute_transaction": False}
