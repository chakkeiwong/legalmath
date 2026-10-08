"""Fixed-evidence positive Horn closure, distinct from defeasible arguments.

A fixed evidence code is admitted only when it has positive support and no
negative support. Derived heads are positive tokens; nonmembership is not negation.
"""
from itertools import product
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ...canonical import canonical, digest, loads
from ...errors import LegalMathError
from .records import Record, Hash, Text

PROFILE = "legalmath.conditional-horn.v1"
Index = Annotated[int, Field(ge=0, le=1023)]
Code = Annotated[int, Field(ge=0, le=3)]
STATES = {"unknown": 0, "true": 1, "false": 2, "conflict": 3}


class Rule(Record):
    id: Text
    head: Index
    facts: tuple[Index, ...] = Field(max_length=32)
    parents: tuple[Index, ...] = Field(max_length=32)


class Program(Record):
    profile: Literal["legalmath.conditional-horn.v1"] = PROFILE
    context_hash: Hash
    fact_ids: tuple[Text, ...] = Field(max_length=1024)
    codes: tuple[Code, ...] = Field(max_length=1024)
    heads: tuple[Text, ...] = Field(min_length=1, max_length=64)
    rules: tuple[Rule, ...] = Field(max_length=64)

    @model_validator(mode="after")
    def indices(self):
        if len(self.fact_ids) != len(self.codes):
            raise ValueError("Fact/state arity mismatch")
        for values in (self.fact_ids, self.heads, tuple(r.id for r in self.rules)):
            if len(set(values)) != len(values):
                raise ValueError("Duplicate semantic identity")
        for r in self.rules:
            if r.head >= len(self.heads) or any(p >= len(self.heads) for p in r.parents):
                raise ValueError("Head index outside vocabulary")
            if any(f >= len(self.codes) for f in r.facts):
                raise ValueError("Fact index outside vocabulary")
            if len(set(r.facts)) != len(r.facts) or len(set(r.parents)) != len(r.parents):
                raise ValueError("Repeated antecedent")
        return self


def decode(data):
    try:
        value = loads(data)  # Reject duplicate JSON keys before model decoding.
        if not isinstance(value, dict) or set(value) != {"profile", "context_hash", "fact_ids", "codes", "heads", "rules"}:
            raise ValueError("Exact versioned wire fields required")
        return Program.model_validate_json(canonical(value))
    except (ValueError, TypeError) as exc:
        raise LegalMathError("E_SCHEMA", details=str(exc)) from exc


def reference(program):
    """Synchronous iteration; the Java evaluator uses an agenda instead."""
    reached = set()
    for _ in range(len(program.heads) + 1):
        next_set = reached | {r.head for r in program.rules
            if all(program.codes[f] == 1 for f in r.facts) and set(r.parents) <= reached}
        if next_set == reached:
            return sorted(reached)
        reached = next_set
    raise LegalMathError("E_INTEGRITY", details="Finite monotone closure did not stabilize")


def closed_set_oracle(program):
    """Independent least-closed-set intersection, bounded to eight heads."""
    if len(program.heads) > 8:
        raise LegalMathError("E_RESOURCE_LIMIT", details="Exhaustive oracle limited to eight heads")
    closed = []
    for flags in product((False, True), repeat=len(program.heads)):
        subset = {i for i, included in enumerate(flags) if included}
        valid = True
        for r in program.rules:
            if any(program.codes[f] != 1 for f in r.facts):
                continue
            if all(p in subset for p in r.parents) and r.head not in subset:
                valid = False
                break
        if valid:
            closed.append(subset)
    return sorted(set.intersection(*closed))


def witnesses(program, reached):
    """Reject unsupported cycles and incomplete results; produce derivation order."""
    if type(reached) is not list or any(type(h) is not int for h in reached):
        raise LegalMathError("E_SCHEMA")
    if reached != sorted(set(reached)) or any(h < 0 or h >= len(program.heads) for h in reached):
        raise LegalMathError("E_REFERENCE")
    target = set(reached)
    proved, order = set(), []
    while proved != target:
        progress = False
        for i, r in enumerate(program.rules):
            if r.head in target - proved and all(program.codes[f] == 1 for f in r.facts) and set(r.parents) <= proved:
                proved.add(r.head)
                order.append({"head": r.head, "rule": i})
                progress = True
        if not progress:
            raise LegalMathError("E_INTEGRITY", details="Unsupported head or unseeded cycle")
    for r in program.rules:
        if all(program.codes[f] == 1 for f in r.facts) and set(r.parents) <= target and r.head not in target:
            raise LegalMathError("E_INTEGRITY", details="Returned result is not closed")
    return order


def lower(scoped):
    """Lower checked S3 premise states, never infer evidence truth from prose."""
    rows = scoped["evaluation"]["results"]
    definitions, states = {}, {}
    for row in rows:
        for p in row["premises"]:
            key = p["requirement"]["id"]
            if key in definitions and (definitions[key] != p["requirement"] or states[key] != p["state"]):
                raise LegalMathError("E_REFERENCE", details="Shared premise meaning/state differs")
            definitions[key], states[key] = p["requirement"], p["state"]
    names = sorted(definitions)
    heads = [r["rule_id"] for r in rows]
    indices = {name: i for i, name in enumerate(names)}
    value = {"profile": PROFILE, "context_hash": digest(scoped), "fact_ids": names,
        "codes": [STATES[states[n]] for n in names], "heads": heads,
        "rules": [{"id": r["rule_id"], "head": i,
            "facts": [indices[p["requirement"]["id"]] for p in r["premises"]], "parents": []}
            for i, r in enumerate(rows)]}
    program = decode(canonical(value))
    expected = [i for i, r in enumerate(rows) if r["status"] == "CONDITIONALLY_DERIVED"]
    if reference(program) != expected:
        raise LegalMathError("E_INTEGRITY", details="S3/declared-Horn semantic mismatch")
    mapping = {"input_hash": digest(scoped), "program_hash": program.identity(),
        "facts": [{"index": i, "requirement": definitions[n], "state": states[n]} for i,n in enumerate(names)],
        "heads": [{"index": i, "rule_id": r["rule_id"], "rule_hash": r["rule_hash"],
            "question": r["question"], "consequence": r["consequence"], "modality": r["modality"]}
            for i,r in enumerate(rows)],
        "source_meaning": "NOT_ESTABLISHED", "legal_correctness": "NOT_ESTABLISHED"}
    return program, mapping
