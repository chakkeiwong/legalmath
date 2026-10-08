"""Execute declared source-bound legal rules on valid and knowledge timelines."""
from .contracts import QueryResult, timestamp
from .anchors import bind, fields, in_period
from .predicates import names, decide

BASIS_FIELDS = {"id", "authority", "jurisdiction", "edition", "source", "valid_from",
                "valid_until", "known_from", "known_until", "premises", "instrument_id"}
FACT_FIELDS = {"name", "basis_id", "instrument_id", "jurisdiction", "value", "source",
               "valid_from", "valid_until", "known_from", "known_until", "observed_at"}

def assess(bundle, bases, facts, graph=None, relation=None):
    if not isinstance(bases, list) or not isinstance(facts, list):
        raise ValueError("Legal bases and facts must be lists")
    for basis in bases:
        fields(basis, BASIS_FIELDS, BASIS_FIELDS - {"valid_until", "known_until"})
    if not bases:
        if facts:
            raise ValueError("Facts require a declared legal basis")
        return QueryResult("Q4", "UNKNOWN", unresolved=["No dated primary legal basis supplied"]).json()
    if len({b["id"] for b in bases}) != len(bases):
        raise ValueError("Duplicate legal basis")
    if len(bases) > 1 and relation not in {"ANY_SUFFICIENT", "ALL_NECESSARY", "ALTERNATIVE_READINGS"}:
        raise ValueError("Multiple legal bases require an explicit aggregation relation")
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
        required = names(expr)
        if not required:
            raise ValueError("Legal premises must contain facts")
        values = {n: set() for n in required}
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
            else:
                excluded.append({"name": fact["name"], "reason": "Outside valid/knowledge/observation interval"})
        observations = {n: next(iter(v)) if len(v) == 1 else "conflict" if v else None
                        for n, v in values.items()}
        if not in_period(basis, effective, known):
            answer = {"status": "UNKNOWN", "missing": ["Authority outside recorded valid/knowledge interval"],
                      "witnesses": {}}
        else:
            answer = decide(expr, observations)
        missing = answer["missing"]
        rows.append({"basis": basis["id"], "status": answer["status"], "missing": missing,
                     "expression": expr, "premises": observations, "witnesses": answer.get("witnesses", {}),
                     "authority_source": authority_anchor, "fact_sources": evidence, "excluded_facts": excluded,
                     "actual_exercise": "NOT_ESTABLISHED", "open_end_proves_currentness": False})
    statuses = [r["status"] for r in rows]
    if len(rows) == 1:
        status = statuses[0]
    elif relation == "ALTERNATIVE_READINGS":
        status = statuses[0] if len(set(statuses)) == 1 else "CONFLICT" if "CONFLICT" in statuses else "UNKNOWN"
    else:
        observations = {f"b{i}": {"YES": True, "NO": False, "UNKNOWN": None, "CONFLICT": "conflict"}[s]
                        for i, s in enumerate(statuses)}
        status = decide({"any" if relation == "ANY_SUFFICIENT" else "all": list(observations)}, observations)["status"]
    return QueryResult("Q4", status, rows, unresolved=sorted(set(x for r in rows for x in r["missing"]))).json()
