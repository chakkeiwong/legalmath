"""Instrument-independent, conditional transaction compliance.

This composes supplied interpretations; it does not discover all applicable law,
screen live lists, infer bank policy, or authorize execution. See the evidence
contract in docs/plans/bank-compliance-layers.md.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path


class Layer(str, Enum):
    SCOPE = "entity_jurisdiction_and_coverage"
    SANCTIONS = "sanctions"
    BANK = "bank_regulation_and_licensing"
    CLIENT = "client_and_account_controls"
    PRODUCT = "product_distribution_and_conduct"
    POLICY = "bank_policy_and_mandate"
    OPERATIONS = "settlement_custody_and_reporting"


class Status(str, Enum):
    SATISFIED = "SATISFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PROHIBITED = "PROHIBITED"
    UNSATISFIED = "UNSATISFIED"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime required")


def _nonempty(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Explicit nonempty identifiers required")


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class Context:
    instrument_id: str
    instrument_kind: str
    client_id: str
    booking_entity_id: str
    establishment_id: str
    service: str
    action: str
    effective_at: datetime
    known_at: datetime
    # References to the complete party/ownership/account facts, route and policies.
    # These are content hashes, not mutable database row names.
    facts_sha256: str
    route_sha256: str
    policy_sha256: str

    def __post_init__(self):
        _aware(self.effective_at)
        _aware(self.known_at)
        for key, value in asdict(self).items():
            if key.endswith("_sha256"):
                if (not isinstance(value, str) or len(value) != 64
                        or any(c not in "0123456789abcdef" for c in value)):
                    raise ValueError("Content SHA-256 required")
            elif not key.endswith("_at"):
                _nonempty(value)


@dataclass(frozen=True)
class Requirement:
    rule_id: str
    version: str
    layer: Layer

    def __post_init__(self):
        _nonempty(self.rule_id, self.version)
        if not isinstance(self.layer, Layer):
            raise ValueError("Unknown compliance layer")


def binding(context, requirements):
    """Any fact, service, time, route, policy or required-rule change invalidates reuse."""
    if not requirements or len({r.rule_id for r in requirements}) != len(requirements):
        raise ValueError("Distinct nonempty requirement inventory required")
    return _hash({"context": asdict(context), "requirements":
                  [asdict(r) for r in sorted(requirements, key=lambda r: r.rule_id)]})


@dataclass(frozen=True)
class SourceRef:
    path: str
    sha256: str

    def matches(self, root):
        root = Path(root).resolve()
        candidate = (root / self.path).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Evidence path escapes its archive")
        return candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest() == self.sha256


@dataclass(frozen=True)
class Finding:
    rule_id: str
    status: Status
    binding: str
    reason: str
    sources: tuple[SourceRef, ...]
    valid_from: datetime
    valid_until: datetime
    known_from: datetime
    # Source-supported duties remain distinct from the permission to trade.
    duties: tuple[str, ...] = ()

    def __post_init__(self):
        _nonempty(self.rule_id, self.binding, self.reason)
        if not isinstance(self.status, Status):
            raise ValueError("Unknown finding status")
        if not isinstance(self.sources, tuple) or not isinstance(self.duties, tuple):
            raise ValueError("Immutable source and duty tuples required")
        for value in (self.valid_from, self.valid_until, self.known_from):
            _aware(value)
        if self.valid_until <= self.valid_from:
            raise ValueError("Empty or reversed evidence validity interval")
        if self.status not in (Status.UNKNOWN, Status.CONFLICT) and not self.sources:
            raise ValueError("Conclusive findings, including non-applicability, need evidence")
        for duty in self.duties:
            _nonempty(duty)


def assess(context, requirements, findings, *, evidence_root):
    """Conjunction within a declared scope, never an unrestricted legal clearance.

    Source bytes and stipulated validity intervals are checked. Authenticity,
    faithful interpretation and completeness are separate source obligations.
    A non-applicability finding needs the same evidence as a satisfied rule.
    No PROHIBITED result is automatically translated into an asset-freeze duty.
    """
    expected = binding(context, requirements)
    inventory = {r.rule_id: r for r in requirements}
    grouped = {rule: [] for rule in inventory}
    for finding in findings:
        if finding.rule_id not in inventory:
            raise ValueError("Finding outside declared requirement inventory")
        grouped[finding.rule_id].append(finding)
    gaps = ["missing layer: " + layer.value for layer in Layer
            if layer not in {r.layer for r in requirements}]
    unresolved, prohibitions, unmet, duties, trace = [], [], [], [], []
    for rule, rows in grouped.items():
        if not rows:
            unresolved.append(rule + ": missing assessment")
            continue
        valid = []
        for row in rows:
            issues = []
            if row.binding != expected:
                issues.append("context or rule inventory changed")
            if not row.valid_from <= context.effective_at < row.valid_until:
                issues.append("outside recorded validity interval")
            if context.known_at < row.known_from:
                issues.append("evidence not yet known")
            if any(not ref.matches(evidence_root) for ref in row.sources):
                issues.append("source bytes changed or absent")
            trace.append({"rule_id": rule, "layer": inventory[rule].layer.value,
                          "status": row.status.value, "reason": row.reason,
                          "sources": [asdict(s) for s in row.sources], "issues": issues})
            if issues:
                unresolved.append(rule + ": " + "; ".join(issues))
            else:
                valid.append(row)
        statuses = {row.status for row in valid}
        if len(statuses) > 1 or statuses & {Status.UNKNOWN, Status.CONFLICT}:
            unresolved.append(rule + ": unresolved or conflicting evidence")
        if Status.PROHIBITED in statuses:
            prohibitions.append(rule)
        if Status.UNSATISFIED in statuses:
            unmet.append(rule)
        # Keep conflicting duty assertions visible; do not auto-execute them.
        for row in valid:
            duties.extend({"rule_id": rule, "duty": duty,
                           "assertion_status": row.status.value} for duty in row.duties)
    unresolved.extend(gaps)
    outcome = ("DO_NOT_PROCEED" if prohibitions else "REQUIREMENTS_NOT_MET" if unmet
               else "UNDETERMINED" if unresolved else "SATISFIED_UNDER_DECLARED_SCOPE")
    return {"outcome": outcome, "binding": expected,
            "may_proceed_under_declared_scope": outcome == "SATISFIED_UNDER_DECLARED_SCOPE",
            "prohibitions": sorted(prohibitions), "unmet_requirements": sorted(unmet),
            "unresolved": sorted(unresolved), "duties": duties, "trace": trace,
            "complete_legal_compliance": "NOT_ESTABLISHED", "human_quality_evidence": False}


def us_entity_under_586(*, organized_under_us_law, present_in_us):
    """31 CFR 586.307 for entities/presence, not every OFAC program's definition.

    A branch uses its legal entity's governing law. A separately incorporated
    subsidiary uses its own governing law, not its parent's governing law.
    US law/presence includes the regulation's territorial definition; no country
    name or corporate brand is treated as an automatic identity determination.
    Individual citizenship/residency and account identity require other inputs.
    """
    for fact in (organized_under_us_law, present_in_us):
        if fact is not None and type(fact) is not bool:
            raise ValueError("Boolean or unknown entity facts required")
    if True in (organized_under_us_law, present_in_us):
        return True
    if None in (organized_under_us_law, present_in_us):
        return None
    return False


CMIC_FACTS = (
    "designated_issuer", "covered_security", "restriction_in_force",
    "actor_us_person", "ultimate_party_us_person", "solely_divestment",
    "divestment_window_open", "applicable_ofac_authorization",
    "otherwise_permissible",
)


def cmic_check(observations, *, action, capacity):
    """Conditional CMIC restriction only (EO 14032, FAQs 899, 902, 1046, 1048).

    `specified_support` is ONLY a service within the inspected OFAC guidance;
    principal inventory dealing cannot use that route. `ultimate_party` includes
    either side and the ultimate beneficiary. Applicable authorization means
    every relevant condition, scope and date is established. Other sanctions,
    evasion and underlying illegality must be tested separately and feed
    `otherwise_permissible`; a license cannot override that premise.

    Dates/list membership are supplied interpretations, not inferred from today.
    A fund, derivative or depositary security needs its own exposure analysis.
    """
    if action not in ("buy", "sell", "hold") or capacity not in ("principal", "specified_support"):
        raise ValueError("Unsupported CMIC action/capacity: retain qualification")
    if set(observations) - set(CMIC_FACTS):
        raise ValueError("Unexpected CMIC fact (including a human quality label)")
    for value in observations.values():
        if value is not None and value != "conflict" and type(value) is not bool:
            raise ValueError("Boolean, unknown or conflict required")
    if "conflict" in observations.values():
        return {"result": "CONFLICT", "missing": [], "possible_results": []}
    missing = [key for key in CMIC_FACTS if observations.get(key) is None]
    outcomes = set()
    for values in product((False, True), repeat=len(missing)):
        w = {**observations, **dict(zip(missing, values))}
        us_party = (w["actor_us_person"] or w["ultimate_party_us_person"]
                    if capacity == "principal" else w["ultimate_party_us_person"])
        restricted = (action != "hold" and w["designated_issuer"] and w["covered_security"]
                      and w["restriction_in_force"] and us_party)
        exception = (w["applicable_ofac_authorization"] or
                     (w["solely_divestment"] and w["divestment_window_open"]))
        outcomes.add(w["otherwise_permissible"] and (not restricted or exception))
    return {"result": "UNDETERMINED" if len(outcomes) > 1 else "TRUE" if True in outcomes else "FALSE",
            "missing": missing, "possible_results": sorted(outcomes)}


def blocked_ownership_closure(directly_blocked, interests, *, program):
    """Proven blocked entities from exact direct stakes, under the 50% rule.

    Input: (owner entity ID, owned entity ID, rational fraction) tuples. Only
    supplied affirmative stakes propagate; an unreturned entity is NOT cleared.
    Do not multiply percentages through a blocked intermediate. This function
    is inapplicable to a solely NS-CMIC listing. Identity and ownership evidence
    remain external obligations; control without ownership is not inferred.
    """
    if program != "blocking_50_percent":
        raise ValueError("Blocked-person ownership propagation is program-specific")
    blocked = set(directly_blocked)
    for entity in blocked:
        _nonempty(entity)
    edges, totals = {}, {}
    for owner, owned, fraction in interests:
        _nonempty(owner, owned)
        if (isinstance(fraction, (float, bool)) or not isinstance(fraction, (int, Fraction))
                or not 0 <= fraction <= 1 or owner == owned):
            raise ValueError("Distinct entities and exact direct ownership fractions required")
        if (owner, owned) in edges:
            raise ValueError("Duplicate direct ownership edge")
        edges[owner, owned] = Fraction(fraction)
        totals[owned] = totals.get(owned, Fraction(0)) + fraction
        if totals[owned] > 1:
            raise ValueError("Direct ownership exceeds 100 percent")
    derivations = []
    while True:
        additions = []
        for owned in sorted(totals):
            stakes = [(owner, amount) for (owner, target), amount in edges.items()
                      if target == owned and owner in blocked]
            aggregate = sum((amount for _, amount in stakes), Fraction(0))
            if owned not in blocked and aggregate >= Fraction(1, 2):
                additions.append(owned)
                derivations.append({"entity": owned, "blocked_direct_owners": sorted(stakes),
                                    "aggregate": aggregate})
        if not additions:
            break
        blocked.update(additions)
    return {"proven_blocked": sorted(blocked), "derivations": derivations,
            "others": "NOT_CLEARED", "ownership_completeness": "NOT_ESTABLISHED"}
