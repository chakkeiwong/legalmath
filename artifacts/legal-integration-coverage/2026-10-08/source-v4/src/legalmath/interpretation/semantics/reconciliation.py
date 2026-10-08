"""Lossless per-reading reconciliation; comparisons never assert legal equivalence."""
from copy import deepcopy
from .records import SourceSpan, Premise, Clause, Scope, Interval
from ...canonical import digest
from ...errors import LegalMathError

PROFILE = "legalmath.retained-reconciliation.v1"

def spans(packet, question, quotes):
    units = {u["unit_id"]: u for u in packet["units"]}
    if len(units) != len(packet["units"]):
        raise LegalMathError("E_REFERENCE", details="Duplicate source unit")
    result = []
    for quote in quotes:
        unit = units.get(quote["unit_id"])
        text = unit["text"] if unit else ""
        if not quote["quote"] or text.count(quote["quote"]) != 1:
            raise LegalMathError("E_REFERENCE", details="Absent or ambiguous quoted source")
        start = text.index(quote["quote"])
        result.append(SourceSpan(source_hash=digest(packet), edition="retained edition; applicability unresolved",
            unit_id=unit["unit_id"], unit_hash=digest(text), locator=unit.get("locator", unit["unit_id"]),
            start=start, end=start+len(quote["quote"]), quote=quote["quote"],
            request_hash=digest(question), role="unknown"))
    return tuple(result)

def claims(operative):
    """Project explicit text fields; never infer a signed attack from prose."""
    rd = operative["reading"]
    yield ("reading.explanation", "assessment", rd["explanation"], rd["evidence"])
    repair = operative.get("candidate_repair")
    if repair:
        for i, row in enumerate(repair["dimensions"]):
            yield (f"candidate_repair.dimensions.{i}", "dimension", row["explanation"], row["evidence"])
        for i, row in enumerate(repair["premises"]):
            yield (f"candidate_repair.premises.{i}", "conditional-challenge", row["rationale"], row["evidence"])
    for field, kind, textfield in (("questions","critical-question","explanation"),
                                    ("obligations","open-obligation","answer")):
        for i, row in enumerate(operative[field]):
            yield (f"{field}.{i}", kind, row[textfield], row["evidence"])

def reconcile(packet, overlay, table, questions):
    grouped = {}
    for row in overlay["records"]:
        grouped.setdefault(row["reading_id"], []).append(row)
    if set(grouped) != set(table) or set(questions) != set(grouped):
        raise LegalMathError("E_REFERENCE", details="Reconciliation denominator differs")
    entries = {}
    for cid, records in sorted(grouped.items()):
        reading = records[0]["operative"]["original_reading"]
        nomination = table[cid]
        if nomination["reading_hash"] != digest(reading):
            raise LegalMathError("E_STALE_REVIEW", details="Reading nomination changed")
        if len({r["role"] for r in records}) != len(records):
            raise LegalMathError("E_REFERENCE", details="Duplicate role record")
        required={"reading_hash","category","rationale","pilot_clauses","relation",
                  "equivalence_not_established_with","qualifier"}
        categories={"allocation","allocation-and-conduct","allocation-and-adequacy","unresolved-discharge"}
        if (set(nomination)!=required or nomination["category"] not in categories or
                nomination["relation"] not in ("partial comparison","partial comparison; discharge alternatives unresolved")):
            raise LegalMathError("E_SCHEMA",details="Unknown comparison profile or relation")
        units={u["unit_id"]:u["text"] for u in packet["units"]}
        for comparison in nomination["pilot_clauses"]:
            if set(comparison)!={"proposal_id","clauses"} or comparison["proposal_id"] not in {
                    "responsibility.allocation","responsibility.conduct","responsibility.adequacy"}:
                raise LegalMathError("E_SCHEMA",details="Unknown pilot clause comparison")
            for raw in comparison["clauses"]:
                clause=Clause.model_validate_json(__import__("json").dumps(raw))
                if not clause.sources:raise LegalMathError("E_REFERENCE",details="Unsourced comparison")
                for source in clause.sources:
                    if source.unit_id not in units:raise LegalMathError("E_REFERENCE")
                    source.verify(units[source.unit_id],digest(packet),digest(questions[cid]))
        retained_claims = []
        for record in records:
            op = record["operative"]
            if op["original_reading"] != reading:
                raise LegalMathError("E_REFERENCE", details="Roles refer to different original readings")
            for path, kind, statement, quotes in claims(op):
                bound = spans(packet, questions[cid], quotes)
                retained_claims.append({"role":record["role"], "record_hash":digest(record),
                    "path":path, "kind":kind, "statement":statement,
                    "sources":[s.model_dump(mode="json") for s in bound],
                    "legal_support":"NOT_ESTABLISHED"})
        entries[cid] = {"candidate_id":cid, "reading_hash":digest(reading),
            "original_reading":deepcopy(reading), "records":deepcopy(records),
            "comparison":deepcopy(nomination), "claims":retained_claims,
            "source_warrant":{"statement":reading["distinction"],
                "sources":[s.model_dump(mode="json") for s in spans(packet,questions[cid],reading["citations"])]},
            "repair_records_present":sum(r["operative"].get("candidate_repair") is not None for r in records),
            "formal_equivalence":"NOT_ESTABLISHED", "legal_equivalence":"NOT_ESTABLISHED",
            "relation_status":"PROPOSED_PARTIAL_COMPARISON",
            "unencoded_relations":["No signed contrary is inferred from role prose or shared source citations."]}
    return {"profile":PROFILE, "packet_hash":digest(packet), "overlay_hash":digest(overlay),
        "questions_hash":digest(questions), "entries":entries,
        "reading_count":len(entries), "role_count":sum(len(v) for v in grouped.values())}

def validate_entry(entry, packet, cid, reading, question):
    if entry["candidate_id"] != cid or entry["reading_hash"] != digest(reading) or entry["original_reading"] != reading:
        raise LegalMathError("E_REFERENCE")
    # Reconstruct every projection from losslessly retained records, never trust cached claims.
    expected = reconcile(packet, {"records":entry["records"]}, {cid:entry["comparison"]}, {cid:question})["entries"][cid]
    if entry != expected:
        raise LegalMathError("E_INTEGRITY", details="Reconciliation projection differs from retained input")
    return entry

def enrich(branch, reading, entry=None):
    """Carry actual assumptions and questions; every extra clause remains proposed."""
    assumptions = list(branch.assumptions)
    unresolved = list(branch.unresolved)
    clauses = list(branch.clauses)
    for i, statement in enumerate(reading["assumptions"]):
        assumptions.append(Premise(id=f"legacy.assumption.{i}", statement=statement,
            status="unresolved", dependencies=()))
    for i, statement in enumerate(reading["questions"]):
        unresolved.append(Premise(id=f"legacy.question.{i}", statement=statement,
            status="unresolved", dependencies=()))
    if entry:
        for index, claim in enumerate(entry["claims"]):
            source_spans = tuple(SourceSpan.model_validate_json(__import__("json").dumps(s)) for s in claim["sources"])
            identity = "retained." + str(index)
            premise = Premise(id=identity, statement=claim["statement"], status="unresolved",
                dependencies=tuple(s.identity() for s in source_spans))
            unresolved.append(premise)
            clauses.append(Clause(id=identity, actor=branch.clauses[0].actor,
                action="consider retained "+claim["kind"], modality="UNCERTAIN",
                trigger="Interpretation and applicability unresolved", object=claim["statement"],
                standard="Proposed source relation; no sufficiency rule established",
                scope=branch.clauses[0].scope, sources=source_spans, relations=(premise,),
                assumptions=(), warrant=claim["role"]+" / "+claim["path"]))
        for record in entry["records"]:
            op = record["operative"]
            texts = [*op["reading"]["added_assumptions"], *op["reading"]["remaining_questions"],
                     *op["reading"]["required_program_repairs"]]
            repair = op.get("candidate_repair")
            if repair:
                texts += [*repair["added_assumptions"], *repair["unresolved_questions"], repair["relationship_explanation"]]
            for statement in texts:
                unresolved.append(Premise(id="retained.text."+digest(statement), statement=statement,
                    status="unresolved", dependencies=(digest(record),)))
    unique = {p.identity():p for p in unresolved}
    return branch.model_copy(update={"assumptions":tuple(assumptions), "unresolved":tuple(unique.values()),
                                     "clauses":tuple(clauses)})
