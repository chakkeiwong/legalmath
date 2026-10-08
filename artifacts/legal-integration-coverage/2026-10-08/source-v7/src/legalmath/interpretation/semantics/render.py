"""All display layers consume the same versioned outcome and semantic branch."""
from .records import Outcome
from ...canonical import digest

def render(branch,outcome):
    status={"true":"conditionally true","false":"conditionally false","unknown":"unknown",
            "conflict":"conflicting","out-of-scope":"out of scope"}[outcome.value]
    if branch.proposal_id.startswith("demonstration.") and outcome.completion=="complete" and outcome.lowering=="supported":
        status={"true":"settled-triggered under declared premises","false":"settled-not-triggered under declared premises"}.get(outcome.value,status)
    qualifications=", ".join(outcome.reasons) or "none"
    text=f"{status}; {outcome.completion}; lowering {outcome.lowering}; qualifications: {qualifications}."
    return {"operative":text,"summary":text,"detail":{"outcome":outcome.model_dump(mode="json"),
        "clauses":[c.model_dump(mode="json") for c in branch.clauses],
        "assumptions":[p.model_dump(mode="json") for p in branch.assumptions],
        "unresolved":[p.model_dump(mode="json") for p in branch.unresolved]},
        "legal_correctness":"NOT_ESTABLISHED"}

def across_extensions(outcomes):
    if not outcomes: raise ValueError("No computed extension outcomes")
    first=outcomes[0]
    if any((o.query_id,o.branch_id)!=(first.query_id,first.branch_id) for o in outcomes):
        raise ValueError("Different query or branch")
    values={o.value for o in outcomes}; reasons=set().union(*(set(o.reasons) for o in outcomes))
    complete=all(o.completion=="complete" for o in outcomes)
    if {"true","false"}<=values:
        value="conflict";reasons.add("conflicting-extensions")
    elif len(values)==1: value=first.value
    else: value="unknown"
    if not complete: reasons.add("unfinished")
    return Outcome(query_id=first.query_id,branch_id=first.branch_id,value=value,
        completion="complete" if complete else "incomplete",
        lowering="unsupported" if any(o.lowering=="unsupported" for o in outcomes) else first.lowering,
        reasons=tuple(sorted(reasons)),extension_ids=tuple(sorted({e for o in outcomes for e in o.extension_ids})),
        witnesses=tuple(sorted({w for o in outcomes for w in o.witnesses})))

def decision_set(branches,outcomes,expected_ids):
    ids=[o.branch_id for o in outcomes]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected_ids) or set(ids)!={b.identity() for b in branches}:
        raise ValueError("Missing, duplicate or unexpected branch outcome")
    by_id={b.identity():b for b in branches}
    projections=[{"query":o.query_id,"value":o.value,"completion":o.completion,"lowering":o.lowering,
        "reasons":list(o.reasons),"scopes":[c.scope.model_dump(mode="json") for c in by_id[o.branch_id].clauses],
        "assumptions":[p.model_dump(mode="json") for p in by_id[o.branch_id].assumptions]} for o in outcomes]
    complete=bool(outcomes) and all(o.completion=="complete" and o.lowering=="supported" for o in outcomes)
    return {"profile":"legalmath.query-decisions.v1","branches":ids,
        "uniform_for_query_projection":complete and len({digest(p) for p in projections})==1,
        "completion":"complete" if complete else "incomplete-or-unsupported",
        "outcomes":[o.model_dump(mode="json") for o in outcomes],
        "comparison_excludes_legal_equivalence_of_objects_and_standards":True,"legal_correctness":"NOT_ESTABLISHED"}
