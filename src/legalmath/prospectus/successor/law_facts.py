"""Execute declared source-bound legal rules on valid and knowledge timelines."""
from .contracts import QueryResult, timestamp
from .anchors import bind, fields, in_period
from .predicates import names, dispatch

BASIS_FIELDS = {"id", "authority", "jurisdiction", "edition", "source", "valid_from",
                "valid_until", "known_from", "known_until", "premises", "instrument_id"}
FACT_FIELDS = {"name", "basis_id", "instrument_id", "jurisdiction", "value", "source",
               "valid_from", "valid_until", "known_from", "known_until", "observed_at"}

def assess(bundle, bases, facts, graph=None, relation=None, *, predicate_engine="finite", ratio_facts=None,
           calendar_facts=None, law_explanation=None):
    if law_explanation is not None:
        from .explanations import validate_option, validate_expression, explain
        validate_option(law_explanation)
    if not isinstance(bases, list) or not isinstance(facts, list):
        raise ValueError("Legal bases and facts must be lists")
    if calendar_facts is not None and not isinstance(calendar_facts, list):
        raise ValueError("Calendar facts must be a list")
    for basis in bases:
        fields(basis, BASIS_FIELDS, BASIS_FIELDS - {"valid_until", "known_until"})
    if not bases:
        if facts or ratio_facts or calendar_facts:
            raise ValueError("Facts require a declared legal basis")
        return QueryResult("Q4", "UNKNOWN", unresolved=["No dated primary legal basis supplied"]).json()
    if len({b["id"] for b in bases}) != len(bases):
        raise ValueError("Duplicate legal basis")
    if len(bases) > 1 and relation not in {"ANY_SUFFICIENT", "ALL_NECESSARY", "ALTERNATIVE_READINGS"}:
        raise ValueError("Multiple legal bases require an explicit aggregation relation")
    calculations = {}
    if ratio_facts is not None:
        from .ratio_facts import derive
        for fact in facts:
            fields(fact, FACT_FIELDS, {"name", "basis_id"})
        calculations = derive(bundle, bases, facts, ratio_facts, graph)
    calendar_calculations = {}
    if calendar_facts is not None:
        from .calendar_facts import derive
        for fact in facts:
            fields(fact, FACT_FIELDS, {"name", "basis_id"})
        calendar_calculations = derive(bundle, bases, facts, calendar_facts, graph, ratio_facts=ratio_facts)
    effective, known = timestamp(bundle["effective_at"]), timestamp(bundle["known_at"])
    rows = []
    for basis in bases:
        fields(basis, BASIS_FIELDS, BASIS_FIELDS - {"valid_until", "known_until"})
        if not all(basis[k] for k in ("id", "authority", "jurisdiction", "edition")):
            raise ValueError("Named legal authority, jurisdiction and edition required")
        if basis["instrument_id"] != bundle["instrument_id"]:
            raise ValueError("Legal basis identifies a different instrument")
        authority_anchor = bind(graph, basis["source"])
        expr = {"all": basis["premises"]} if isinstance(basis["premises"], list) else basis["premises"]
        if law_explanation is not None:
            validate_expression(expr)
        required = names(expr)
        if not required:
            raise ValueError("Legal premises must contain facts")
        values = {n: set() for n in required}
        supports = {n: [] for n in required}
        evidence, excluded = [], []
        for fact in facts:
            fields(fact, FACT_FIELDS, {"name", "basis_id", "instrument_id", "jurisdiction",
                                      "value", "source", "valid_from", "known_from", "observed_at"})
            if fact["basis_id"] not in {b["id"] for b in bases}:
                raise ValueError("Fact refers to an undeclared legal basis")
            if fact["basis_id"] != basis["id"]:
                continue
            if fact["name"] not in required or type(fact["value"]) is not bool:
                raise ValueError("Unexpected or untyped legal fact")
            if fact["instrument_id"] != bundle["instrument_id"] or fact["jurisdiction"] != basis["jurisdiction"]:
                raise ValueError("Fact subject/jurisdiction mismatch")
            source = bind(graph, fact["source"])
            active = in_period(fact, effective, known) and timestamp(fact["observed_at"]) <= known
            if active:
                values[fact["name"]].add(fact["value"])
                evidence.append(source)
                supports[fact['name']].append({'kind': 'OBSERVATION', 'observation': dict(fact), 'source': source})
            else:
                excluded.append({"name": fact["name"], "reason": "Outside valid/knowledge/observation interval"})
        for calculation in calculations.get(basis["id"], []):
            if calculation["status"] in {"YES", "NO"}:
                values[calculation["name"]].add(calculation["status"] == "YES")
                evidence.extend([calculation["source"], calculation["numerator"]["source"],
                                 calculation["denominator"]["source"]])
                supports[calculation['name']].append({'kind': 'RATIO', 'calculation': calculation})
            else:
                excluded.append({"name": calculation["name"], "calculation": calculation["id"],
                                 "reason": "; ".join(calculation["unresolved"])})
        for calculation in calendar_calculations.get(basis["id"], []):
            if calculation["status"] in {"YES", "NO"}:
                values[calculation["name"]].add(calculation["status"] == "YES")
                evidence.extend([calculation["source"], calculation["start"]["source"],
                                 calculation["end"]["source"]])
                supports[calculation['name']].append({'kind': 'CALENDAR', 'calculation': calculation})
            else:
                excluded.append({"name": calculation["name"], "calculation": calculation["id"],
                                 "reason": "; ".join(calculation["unresolved"])})
        observations = {n: next(iter(v)) if len(v) == 1 else "conflict" if v else None
                        for n, v in values.items()}
        if not in_period(basis, effective, known):
            answer = {"status": "UNKNOWN", "missing": ["Authority outside recorded valid/knowledge interval"],
                      "witnesses": {}}
        else:
            answer = dispatch(expr, observations, engine=predicate_engine)
        missing = answer["missing"]
        rows.append({"basis": basis["id"], "status": answer["status"], "missing": missing,
                     "expression": expr, "premises": observations, "witnesses": answer.get("witnesses", {}),
                     "authority_source": authority_anchor, "fact_sources": evidence, "excluded_facts": excluded,
                     "reasoning": answer,
                     "actual_exercise": "NOT_ESTABLISHED", "open_end_proves_currentness": False})
        if basis["id"] in calculations:
            rows[-1]["calculations"] = calculations[basis["id"]]
        if basis["id"] in calendar_calculations:
            rows[-1]["calendar_calculations"] = calendar_calculations[basis["id"]]
        if law_explanation is not None:
            explanation = explain(expr, observations, engine=predicate_engine,
                                  authority_active=in_period(basis, effective, known))
            explanation.update(basis=basis['id'], authority_source=authority_anchor,
                premise_support={n: supports[n] for n in explanation.get('literals', {})})
            rows[-1]['explanation'] = explanation
    statuses = [r["status"] for r in rows]
    if len(rows) == 1:
        status = statuses[0]
    elif relation == "ALTERNATIVE_READINGS":
        status = statuses[0] if len(set(statuses)) == 1 else "CONFLICT" if "CONFLICT" in statuses else "UNKNOWN"
    else:
        observations = {f"b{i}": {"YES": True, "NO": False, "UNKNOWN": None, "CONFLICT": "conflict"}[s]
                        for i, s in enumerate(statuses)}
        status = dispatch({"any" if relation == "ANY_SUFFICIENT" else "all": list(observations)}, observations,
                          engine=predicate_engine)["status"]
    return QueryResult("Q4", status, rows, unresolved=sorted(set(x for r in rows for x in r["missing"]))).json()
