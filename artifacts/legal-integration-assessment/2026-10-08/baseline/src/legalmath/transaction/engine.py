"""Derive conditional findings from retained evidence and the fixed catalog."""
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

import z3

from ..canonical import digest
from ..compliance import Context, Finding, Layer, Requirement, SourceRef, Status, assess, blocked_ownership_closure
from ..prospectus.checks import symbolic
from ..qualification.assurance import method_manifest as backend_methods
from . import VERSION, catalog
from .evidence import Registry, fields, facts, instant, sha


CONTEXT_FIELDS = set(Context.__dataclass_fields__)
DERIVED = {"transaction_purchase_or_sale", "principal_capacity"}
ACTIONS = {"buy", "sell", "hold", "cash_dividend", "stock_split", "dividend_reinvestment",
           "redemption", "conversion", "write_down", "transfer", "settlement"}
SUPPORTED_CMIC_ACTIONS = {"buy", "sell", "hold"}


def method_identity():
    package = Path(__file__).resolve().parents[1]
    files = {str(p.relative_to(package)): sha(p.read_bytes())
             for p in sorted(Path(__file__).parent.glob("*.py"))}
    files["compliance.py"] = sha((package / "compliance.py").read_bytes())
    # Reused product specifications and symbolic bridge are part of this method.
    for p in sorted((package / "prospectus").glob("*.py")):
        files[str(p.relative_to(package))] = sha(p.read_bytes())
    return digest({"version": VERSION, "files": files, "backends": backend_methods()})


def conditional(model, observations):
    variables = {f["name"]: z3.Bool(f["name"]) if f["type"] == "bool" else z3.Int(f["name"])
                 for f in model["facts"]}
    constraints = []
    issues, conflict = [], False
    for f in model["facts"]:
        name, typ = f["name"], f["type"]
        row = observations[name]
        if typ == "integer":
            constraints.append(variables[name] >= 0)
        if row["status"] == "KNOWN":
            constraints.append(variables[name] == row["value"])
        else:
            issues.append(name)
            conflict |= row["status"] == "CONFLICT"
    results = {}
    for rule in model["rules"]:
        if conflict:
            results[rule["id"]] = {"status": "CONFLICT", "value": None, "missing": issues}
            continue
        expression = symbolic(rule["body"], variables)
        possible = []
        for value in (False, True):
            solver = z3.Solver()
            solver.set(timeout=1000)
            solver.add(*constraints, expression == value)
            answer = solver.check()
            if answer == z3.unknown:
                possible = [False, True]
                break
            if answer == z3.sat:
                possible.append(value)
        results[rule["id"]] = {"status": "KNOWN" if len(possible) == 1 else "UNKNOWN",
                               "value": possible[0] if len(possible) == 1 else None,
                               "missing": issues}
    return results


def derive_facts(observations, model_map):
    """Check dependencies in teaching order; supplied derived claims cannot bypass them."""
    calculations = {}
    links = (("entity", "us_entity", "actor_us_person", False),
             ("product_financial", "financial_pass", "financial_pass", False),
             ("product_client", "client_qualifies", "client_qualifies", False),
             ("product_complex", "sufficient", "complex_product", True),
             ("product_threshold", "threshold_compliant", "threshold_compliant", False),
             ("product_eligibility", "eligible", "streamlined", False))
    for model_name, output, fact_name, affirmative_only in links:
        model = model_map[model_name]
        calculation = conditional(model, observations)
        calculations[model_name] = calculation
        derived, original = calculation[output], observations[fact_name]
        if affirmative_only and (derived["status"] != "KNOWN" or derived["value"] is not True):
            # Failure of a sufficient complexity condition never proves simplicity.
            continue
        status, value = derived["status"], derived["value"]
        if original["status"] == "CONFLICT" or (status == "KNOWN" and original["status"] == "KNOWN" and original["value"] != value):
            status, value = "CONFLICT", None
        source_ids = set(original["sources"])
        for fact in model["facts"]:
            source_ids.update(observations[fact["name"]]["sources"])
        source_ids.update(key for key, _ in catalog.specifications()[model_name]["anchors"])
        observations[fact_name] = {"status": status, "value": value, "type": "bool",
            "sources": sorted(source_ids), "issues": ["derived from " + model_name + "." + output],
            "truth_of_assertion": "CONDITIONAL_FORMAL_DERIVATION"}
    return calculations


def investigate(request, store):
    fields(request, {"profile", "context", "registry_sha256", "capacity"})
    fields(request["context"], CONTEXT_FIELDS)
    inventory = catalog.inventory(request["profile"])
    context_data = dict(request["context"])
    effective_at, known_at = context_data["effective_at"], context_data["known_at"]
    context_data["effective_at"], context_data["known_at"] = instant(effective_at), instant(known_at)
    context = Context(**context_data)
    registry = Registry(store, store.json(request["registry_sha256"]))
    # These three hashes now retrieve real objects, not opaque references.
    assertions = store.json(context.facts_sha256)
    route = store.json(context.route_sha256)
    policy = store.json(context.policy_sha256)
    fields(route, {"roles", "capacity", "currencies"})
    fields(policy, {"source_ids", "mandate_source_ids"})
    if (not isinstance(route["roles"], list) or not isinstance(route["currencies"], list)
            or not isinstance(policy["source_ids"], list) or not isinstance(policy["mandate_source_ids"], list)):
        raise ValueError("Typed route/policy collections required")
    if request["capacity"] not in {"principal", "specified_support", "unresolved"}:
        raise ValueError("Unsupported capacity")
    if context.action not in ACTIONS:
        raise ValueError("Unsupported transaction action")
    if set(assertions) & DERIVED:
        raise ValueError("Action and capacity are derived from transaction context")
    observed = facts(registry, assertions, {k: v for k, v in catalog.declarations().items() if k not in DERIVED},
                     effective_at, known_at)
    for name, value in (("transaction_purchase_or_sale", context.action in {"buy", "sell"}),
                        ("principal_capacity", request["capacity"] == "principal")):
        observed[name] = {"status": "KNOWN", "type": "bool", "value": value,
                          "issues": [], "sources": [], "truth_of_assertion": "CONTEXT_PREMISE"}
    requirements = [Requirement(r["rule_id"], r["version"], Layer(r["layer"])) for r in inventory]
    from ..compliance import binding
    bound = binding(context, requirements)
    model_map = catalog.models()
    calculations = derive_facts(observed, model_map)
    findings, limitations, dependency_ids = [], [], set()
    screenings = []
    from .sanctions import parse, candidates
    for source_id, source in registry.records.items():
        if source["kind"] != "sanctions":
            continue
        # Feed family is an explicit registry identifier, never inferred from
        # the shared XML root name or a successful HTTP response.
        family = {"ofac-sdn": "SDN", "ofac-consolidated": "CONSOLIDATED"}.get(source_id)
        if family is None:
            screenings.append({"source": source_id, "status": "UNSUPPORTED_FEED"})
            continue
        checked = registry.check([source_id], effective_at, known_at)
        dependency_ids.update(checked["sources"])
        try:
            parsed = parse(store.get(source["blob"]), list_kind=family)
            screenings.append({"source": source_id, "published_date": parsed["published_date"],
                "source_sha256": parsed["source_sha256"], "record_count": parsed["record_count"],
                "issues": checked["issues"], "parties": [
                    {"entity_id": r["entity_id"], **candidates(parsed, r["name"])} for r in route["roles"]]})
        except (OSError, ValueError, ET.ParseError):
            screenings.append({"source": source_id, "status": "INVALID_FEED"})
    ownership = {"status": "MISSING_OWNERSHIP_EVIDENCE", "others": "NOT_CLEARED"}
    if "ownership-observations" in registry.records:
        key = "ownership-observations"
        check = registry.check([key], effective_at, known_at)
        dependency_ids.update(check["sources"])
        source = registry.records[key]
        if source["kind"] != "facts" or source["media_type"] != "application/json":
            raise ValueError("Ownership needs a typed factual source")
        graph = store.json(source["blob"])
        fields(graph, {"directly_blocked", "interests", "program"})
        if (not isinstance(graph["directly_blocked"], list) or not isinstance(graph["interests"], list)
                or any(not isinstance(x, str) or not x.strip() for x in graph["directly_blocked"])
                or len(set(graph["directly_blocked"])) != len(graph["directly_blocked"])):
            raise ValueError("Ownership needs distinct entity identifiers and a list of interests")
        edges = []
        for edge in graph["interests"]:
            fields(edge, {"owner", "owned", "numerator", "denominator"})
            if type(edge["numerator"]) is not int or type(edge["denominator"]) is not int or edge["denominator"] <= 0:
                raise ValueError("Exact ownership fractions required")
            edges.append((edge["owner"], edge["owned"], Fraction(edge["numerator"], edge["denominator"])))
        closure = blocked_ownership_closure(graph["directly_blocked"], edges, program=graph["program"])
        # Convert rational trace values to a stable JSON encoding without loss.
        ownership = {"status": "QUALIFIED" if check["issues"] else "CONDITIONAL_FORMAL_RESULT",
            "source_sha256": source["blob"], "issues": check["issues"], "proven_blocked": closure["proven_blocked"],
            "others": "NOT_CLEARED", "identity_and_ownership_truth": "NOT_ESTABLISHED",
            "derivations": [{"entity": r["entity"], "aggregate": str(r["aggregate"]),
                "blocked_direct_owners": [[o, str(v)] for o, v in r["blocked_direct_owners"]]} for r in closure["derivations"]]}
    for requirement, row in zip(requirements, inventory):
        name = row["specification"]
        status, reasons, source_ids, anchors = Status.UNKNOWN, [], set(), []
        if name is None:
            reasons.append(row["scope"])
        else:
            d = catalog.specifications()[name]
            unsupported = name == "cmic" and (context.action not in SUPPORTED_CMIC_ACTIONS or request["capacity"] == "unresolved")
            calculation = ({"satisfied": {"status": "UNKNOWN", "value": None,
                "missing": ["unsupported action or capacity"]}} if unsupported else conditional(model_map[name], observed))
            calculations[name] = calculation
            applies = calculation.get("applies", {"status": "KNOWN", "value": True})
            result = calculation.get("satisfied", calculation.get("eligible"))
            if applies["status"] == "CONFLICT" or result["status"] == "CONFLICT":
                status = Status.CONFLICT
            elif applies["status"] == "KNOWN" and not applies["value"]:
                status = Status.NOT_APPLICABLE
            elif applies["status"] != "KNOWN" or result["status"] != "KNOWN":
                status = Status.UNKNOWN
            elif result["value"]:
                status = Status.SATISFIED
            else:
                status = Status.PROHIBITED if name == "cmic" else Status.UNSATISFIED
            for fact_name, _ in d["facts"]:
                source_ids.update(observed[fact_name]["sources"])
            for key, quote in d["anchors"]:
                source_ids.add(key)
                try:
                    if quote is not None:
                        anchors.append(registry.quote(key, quote))
                    elif key not in registry.records:
                        raise KeyError(key)
                except (OSError, KeyError, UnicodeDecodeError, ValueError):
                    reasons.append("missing or changed source anchor: " + key)
            check = registry.check(source_ids, effective_at, known_at)
            reasons.extend(check["issues"])
            source_ids.update(check["sources"])
            if unsupported:
                reasons.append("action/capacity outside the supported CMIC specification")
            if reasons:
                status = Status.UNKNOWN
            # Provenance and legal interpretation are separate, visible claims.
            limitations.append({"rule_id": requirement.rule_id, "source_meaning": "NOT_ESTABLISHED",
                                "fact_truth": "NOT_ESTABLISHED", "scope": d["meaning"], "anchors": anchors})
        if requirement.rule_id == "scope.parties":
            roles = set()
            for role in route["roles"]:
                fields(role, {"role", "entity_id", "name", "establishment_id", "jurisdiction", "source_ids"})
                if role["role"] not in {"booking", "advising", "executing", "custody", "payment", "issuer", "client", "beneficiary", "counterparty"}:
                    raise ValueError("Unknown transaction role")
                if not all(isinstance(role[k], str) and role[k] for k in ("entity_id", "establishment_id", "jurisdiction")):
                    raise ValueError("Explicit party identity required")
                if not isinstance(role["source_ids"], list) or not role["source_ids"]:
                    reasons.append("missing party evidence: " + role["role"])
                else:
                    source_ids.update(role["source_ids"])
                    reasons.extend(registry.check(role["source_ids"], effective_at, known_at)["issues"])
                roles.add(role["role"])
                if role["role"] == "booking" and (role["entity_id"] != context.booking_entity_id
                                                  or role["establishment_id"] != context.establishment_id):
                    reasons.append("booking role differs from transaction context")
            if not {"booking", "executing", "custody", "payment"} <= roles:
                reasons.append("incomplete transaction roles")
            if route["capacity"] != request["capacity"]:
                reasons.append("route capacity differs from request")
        if requirement.rule_id == "policy.internal":
            source_ids.update(policy["source_ids"] + policy["mandate_source_ids"])
            reasons.extend(registry.check(source_ids, effective_at, known_at)["issues"])
            if not policy["source_ids"] or not policy["mandate_source_ids"]:
                reasons.append("bank policy or account mandate unavailable")
        dependency_ids.update(source_ids)
        refs = tuple(SourceRef(str(store.path(registry.records[k]["blob"]).relative_to(store.directory)),
                               registry.records[k]["blob"]) for k in sorted(source_ids) if k in registry.records)
        # The compositor's interval is the evaluated instant's enclosing day;
        # actual source intervals have already been checked independently above.
        from datetime import timedelta
        findings.append(Finding(requirement.rule_id, status, bound,
            "; ".join(reasons) or "Computed conditional formal consequence; legal meaning remains qualified",
            refs, context.effective_at, context.effective_at + timedelta(microseconds=1), context.known_at))
    formal = assess(context, requirements, findings, evidence_root=store.directory)
    calculations["product_duties"] = conditional(model_map["product_duties"], observed)
    outcome = {"version": VERSION, "profile": request["profile"], "request_hash": digest(request),
               "method_hash": method_identity(), "inventory_hash": digest(inventory),
               "registry_hash": request["registry_sha256"], "inventory": inventory,
               "formal_assessment": formal, "calculations": calculations, "observations": observed,
               "sanctions_screenings": screenings,
               "ownership": ownership,
               "interpretation_limits": limitations, "dependencies": sorted(dependency_ids),
               "decision": "QUALIFIED", "may_execute_transaction": False,
               "catalog_coverage": "ALL_DECLARED_OBLIGATIONS_PRESENT",
               "complete_legal_coverage": "NOT_ESTABLISHED", "human_quality_evidence": False}
    outcome["receipt_hash"] = digest(outcome)
    return outcome


def revalidate(receipt, request, store):
    # Recompute rather than trusting a caller's green status or recomputed hash.
    current = investigate(request, store)
    if current != receipt:
        raise ValueError("Decision changed or receipt was forged; reassessment required")
    return current
