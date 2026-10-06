"""Isolated executable specifications for the P0-P6 repair study.

No production successor entry point imports this module. These specifications
assume reviewed paragraph membership, contract choices, legal rules and identity.
They are deliberately small enough for exhaustive checks, not a PDF/legal engine.
"""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.semantics import possible_decision


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Unit:
    # (document edition hash, document id, unit id); paragraph is document-local.
    key: tuple
    paragraph: str
    text: str
    visible: bool = True


@dataclass(frozen=True)
class Span:
    key: tuple
    start: int
    end: int
    quote: str


def validate_span(span, units):
    unit = units[span.key]
    if not (type(span.start) is int and type(span.end) is int
            and 0 <= span.start < span.end <= len(unit.text)):
        raise ValueError("Invalid occurrence interval")
    if unit.text[span.start:span.end] != span.quote:
        raise ValueError("Changed source quotation")
    return unit


@dataclass(frozen=True)
class Rendered:
    text: str
    origins: tuple  # (source key, original character offset), or None for separator


def render_span(span, units):
    unit = validate_span(span, units)
    if not unit.visible:
        return Rendered("", ())
    return Rendered(span.quote, tuple((span.key, i) for i in range(span.start, span.end)))


def concatenate(parts, separator=""):
    text, origins = "", []
    for part in parts:
        if not part.text:
            continue
        if text:
            text += separator
            origins.extend([None] * len(separator))
        text += part.text
        origins.extend(part.origins)
    return Rendered(text, tuple(origins))


def paragraph(keys, units):
    members = [units[key] for key in keys]
    if not members or len({(u.key[:2], u.paragraph) for u in members}) != 1:
        raise ValueError("Paragraph membership must be explicit and document-scoped")
    parts = []
    for unit in members:
        start = len(unit.text) - len(unit.text.lstrip())
        end = len(unit.text.rstrip())
        if start < end:
            parts.append(render_span(Span(unit.key, start, end, unit.text[start:end]), units))
    return concatenate(parts, " ")


def coverage(keys, spans, units):
    covered = {key: set() for key in keys}
    for span in spans:
        validate_span(span, units)
        if span.key not in covered:
            raise ValueError("Evidence lies outside declared coverage domain")
        covered[span.key].update(range(span.start, span.end))
    return {key: all(i in covered[key] for i, c in enumerate(units[key].text)
                     if not c.isspace()) for key in keys if units[key].visible}


def relevant_unknowns(roots, edges, unresolved):
    """Reachability in a supplied complete, reviewed dependency graph."""
    reached, pending = set(), list(roots)
    while pending:
        key = pending.pop()
        if key not in reached:
            reached.add(key)
            pending.extend(edges.get(key, []))
    return sorted(reached.intersection(unresolved))


def question_coverage(declared, established):
    # Scope must be justified outside this function; missing entries stay incomplete.
    if set(established) - set(declared):
        raise ValueError("Undeclared question")
    return {q: "COMPLETE" if established.get(q) is True else "PARTIAL" for q in declared}


@dataclass(frozen=True)
class Text:
    span: Span


@dataclass(frozen=True)
class Sequence:
    children: tuple


@dataclass(frozen=True)
class Choice:
    key: str
    branches: tuple


def contract_variants(tree, selected, units):
    """Small reviewed AST: sequence, source text, choices. No bracket inference."""
    domains = {}
    def inventory(node):
        if isinstance(node, Text):
            validate_span(node.span, units)
        elif isinstance(node, Sequence):
            for child in node.children:
                inventory(child)
        elif isinstance(node, Choice):
            if not node.branches or node.key in domains:
                raise ValueError("Empty choice or duplicate choice identity")
            domains[node.key] = len(node.branches)
            for child in node.branches:
                inventory(child)
        else:
            raise ValueError("Unsupported construction; retain as unresolved")
    inventory(tree)
    if set(selected) - domains.keys():
        raise ValueError("Unknown choice")
    for key, index in selected.items():
        if type(index) is not int or not 0 <= index < domains[key]:
            raise ValueError("Invalid selected branch")
    missing = sorted(domains.keys() - selected.keys())
    count = 1
    for key in missing:
        count *= domains[key]
    if count > 4096:
        raise ValueError("Reference enumeration limit; production needs symbolic representation")
    def render(node, selection):
        if isinstance(node, Text):
            return render_span(node.span, units)
        if isinstance(node, Sequence):
            return concatenate([render(child, selection) for child in node.children])
        return render(node.branches[selection[node.key]], selection)
    variants = []
    for values in product(*(range(domains[key]) for key in missing)):
        selection = dict(selected, **dict(zip(missing, values)))
        variants.append(render(tree, selection))
    return variants, missing


def variables(expr):
    if isinstance(expr, str) and expr:
        return {expr}
    if not isinstance(expr, tuple) or not expr:
        raise ValueError("Invalid predicate")
    op, *args = expr
    if op == "not" and len(args) == 1:
        return variables(args[0])
    if op in ("and", "or") and args:
        return set().union(*(variables(arg) for arg in args))
    raise ValueError("Unknown operator or empty formula")


def boolean(expr, world):
    if isinstance(expr, str):
        return world[expr]
    op, *args = expr
    if op == "not":
        return not boolean(args[0], world)
    if op == "and":
        return all(boolean(arg, world) for arg in args)
    if op == "or":
        return any(boolean(arg, world) for arg in args)
    raise ValueError("Unvalidated predicate")


def decide(expr, observations):
    names = sorted(variables(expr))
    result = possible_decision(names, observations, lambda world: boolean(expr, world))
    return {"TRUE": "YES", "FALSE": "NO", "UNDETERMINED": "UNKNOWN",
            "CONFLICT": "CONFLICT"}[result["decision"]]


def feature(interpretations, contingencies, predicate):
    """For each reading, does SOME admissible contingency have the feature?"""
    if not interpretations:
        return "CONFLICT"
    answers = []
    for reading in interpretations:
        worlds = contingencies(reading)
        if not worlds:
            return "CONFLICT"
        answers.append(any(predicate(reading, world) for world in worlds))
    return "YES" if all(answers) else "NO" if not any(answers) else "UNKNOWN"


@dataclass(frozen=True)
class Dated:
    valid_from: int
    valid_until: int | None
    known_from: int

    def valid(self, effective, known):
        if any(type(x) is not int for x in (self.valid_from, self.known_from, effective, known)):
            raise ValueError("Reference uses integer instants, not implicit date conversions")
        if self.valid_until is not None and (type(self.valid_until) is not int
                                            or self.valid_until <= self.valid_from):
            raise ValueError("Invalid validity interval")
        return (self.valid_from <= effective
                and (self.valid_until is None or effective < self.valid_until)
                and self.known_from <= known)


@dataclass(frozen=True)
class Fact:
    name: str
    value: bool
    dates: Dated
    source: Span


def law(expr, basis_source, basis_dates, facts, effective, known, units):
    names = variables(expr)
    if not validate_span(basis_source, units).visible:
        raise ValueError("Invisible authority")
    if not basis_dates.valid(effective, known):
        return "UNKNOWN"
    values = {name: set() for name in names}
    for fact in facts:
        if fact.name not in names or type(fact.value) is not bool:
            raise ValueError("Unexpected or untyped fact")
        if not validate_span(fact.source, units).visible:
            raise ValueError("Invisible fact source")
        if fact.dates.valid(effective, known):
            values[fact.name].add(fact.value)
    observations = {name: (next(iter(vals)) if len(vals) == 1
                           else "conflict" if vals else None)
                    for name, vals in values.items()}
    return decide(expr, observations)


def exact(value):
    if type(value) not in (int, str) or isinstance(value, str) and not value:
        raise ValueError("Use integer or exact decimal/rational string")
    return Fraction(value)


def allocate(payload):
    """One explicit same-currency conversion, floor per legal aggregation id."""
    try:
        if not isinstance(payload, dict) or set(payload) != {"currency", "price", "holdings"}:
            raise ValueError("Invalid allocation fields")
        currency = payload["currency"]
        if not isinstance(currency, str) or not currency:
            raise ValueError("Explicit currency required")
        price = exact(payload["price"])
        if price <= 0 or not isinstance(payload["holdings"], list) or not payload["holdings"]:
            raise ValueError("Positive price and nonempty holdings list required")
        totals = {}
        for item in payload["holdings"]:
            if not isinstance(item, dict) or set(item) != {"holder_id", "currency", "amount"}:
                raise ValueError("Invalid holding fields")
            holder = item["holder_id"]
            if not isinstance(holder, str) or not holder or item["currency"] != currency:
                raise ValueError("Legal aggregation id and matching currency required")
            amount = exact(item["amount"])
            if amount < 0:
                raise ValueError("Negative amount")
            totals[holder] = totals.get(holder, Fraction(0)) + amount
        rows = []
        for holder, amount in sorted(totals.items()):
            shares = amount // price
            remainder = amount - shares * price
            rows.append({"holder_id": holder, "amount": str(amount), "shares": shares,
                         "remainder_value": str(remainder)})
        return {"status": "SUPPORTED_SUBCALCULATION", "rows": rows}
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return {"status": "INVALID_INPUT", "reason": str(exc)}


class Build:
    """Pure static DAG over JSON values; immutable snapshot for each build.

    All dependencies, code identities and environment values must be declared.
    This model cannot discover a Python function's hidden reads.
    """
    def __init__(self, tasks):
        # name -> (dependencies, task identity, tool/environment configuration, function)
        self.tasks = tasks
        self.cache = {}
        self.executed = []

    def run(self, target, inputs):
        snapshot = json.loads(json.dumps(inputs, allow_nan=False))
        active, complete = set(), {}
        self.executed = []
        def visit(key):
            if key in complete:
                return complete[key]
            if key in snapshot:
                if key in self.tasks:
                    raise ValueError("Key is both input and task")
                value = snapshot[key]
            else:
                if key in active or key not in self.tasks:
                    raise ValueError("Cycle or missing dependency")
                active.add(key)
                deps, code_id, environment, function = self.tasks[key]
                if len(set(deps)) != len(deps):
                    raise ValueError("Duplicate dependency")
                args = {dep: visit(dep) for dep in deps}
                signature = digest([code_id, environment,
                                    [(dep, digest(args[dep])) for dep in deps]])
                entry = self.cache.get(key)
                if entry and entry[0] == signature and entry[1] == digest(entry[2]):
                    value = entry[2]
                else:
                    # Copy prevents a task from changing its dependency values.
                    value = function(json.loads(json.dumps(args)))
                    self.cache[key] = (signature, digest(value), value)
                    self.executed.append(key)
                active.remove(key)
            complete[key] = json.loads(json.dumps(value))
            return complete[key]
        return visit(target)


CONTEXT_FIELDS = {"instrument_id", "instrument_kind", "effective_at", "known_at",
                  "jurisdiction", "purpose", "source_set_hash", "question_version"}


def integrate(context, rows, obligations, expected_obligations):
    """Identity-map case only; intentional context transformations need separate proof."""
    if set(context) != CONTEXT_FIELDS or any(value is None or value == "" for value in context.values()):
        return {"status": "REJECTED_CONTEXT"}
    if (len(rows) != 3 or {row.get("phase") for row in rows} != {"P3", "P4", "P5"}):
        return {"status": "REJECTED_PHASES"}
    for row in rows:
        if row.get("context") != context or row.get("payload_hash") != digest(row.get("payload")):
            return {"status": "REJECTED_CONTEXT"}
    if (len(obligations) != len(set(obligations))
            or set(obligations) != set(expected_obligations)):
        return {"status": "REJECTED_OBLIGATIONS"}
    return {"status": "BOUND_REPORT", "answers": [row["payload"] for row in rows],
            "transaction_clearance": False}


def admissible_evaluation(developer, readers, adjudicator, support, scored,
                          cohort_hash, report_hash, signoffs):
    independent = (len(readers) >= 2 and len(readers) == len(set(readers))
                   and developer not in readers and adjudicator != developer
                   and adjudicator not in readers)
    bound = all(s.get("cohort_hash") == cohort_hash and s.get("report_hash") == report_hash
                and set(s.get("scope", [])) == set(support) and s.get("author") != developer
                for s in signoffs)
    return bool(support and signoffs and independent and bound and set(support) <= set(scored))
