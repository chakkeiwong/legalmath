"""Conditional formal specifications, never human-labelled legal answer keys."""
from itertools import product
from pathlib import Path

from ..interpretation.search.models import DIMENSIONS
from ..translation.model import from_reading
from .common import ARCHIVE, read, write
from .evidence import locate
from .semantics import CLASS_FACTS, SPI_FACTS

AT = "2026-09-28T00:00:00.000000Z"


def definitions():
    return {
        "complex": {
            "facts": [(k, "bool") for k in CLASS_FACTS],
            "outputs": [("sufficient", "bool", "(and bond (or perpetual subordinated contingent_conversion contractual_write_down))")],
            "meaning": "Sufficient example-list condition for a complex bond. False does not establish non-complexity. Every instrument feature is an explicit premise.",
            "source": "sfc-complex-products", "pattern": r"perpetual|subordinated|contingent"},
        "financial": {
            "facts": [("portfolio", "integer"), ("net_assets", "integer")],
            "outputs": [("financial_pass", "bool", "(or (>= portfolio (integer 4000000000)) (>= net_assets (integer 8000000000)))")],
            "meaning": "Individual SPI financial limb only. Nonnegative integer HKD cents; net assets exclude primary residence. Currency conversion and aggregation entitlement are external premises.",
            "source": "sfc-spi-annex-1", "pattern": r"40 million|80 million"},
        "client": {
            "facts": [(k, "bool") for k in ("professional_investor", "financial_pass", "knowledge_or_experience", "objectives_permit")],
            "outputs": [("client_qualifies", "bool", "(and professional_investor financial_pass knowledge_or_experience objectives_permit)")],
            "meaning": "Individual SPI qualifying limbs supplied explicitly, including non-conservative objectives and qualifying knowledge/experience. Does not decide these English predicates or cover corporate ownership rules.",
            "source": "sfc-spi-annex-1", "pattern": r"investment objectives|knowledge or experience"},
        "threshold": {
            "facts": [("gross", "integer"), ("maximum", "integer"), ("designated", "bool"), ("adding_funds", "bool")],
            "outputs": [("amount_condition", "bool", "(or (>= maximum gross) (and designated (not adding_funds)))")],
            "meaning": "Amount condition in nonnegative integer HKD cents. Gross includes leverage. Designated-account alternative assumes valid arrangements, deposited/transferred exposure treatment, monitoring and required reviews.",
            "source": "sfc-spi-annex-1", "pattern": r"8\.3|top-up"},
        "eligibility": {
            "facts": [(k, "bool") for k in SPI_FACTS],
            "outputs": [("eligible", "bool", "(and " + " ".join(SPI_FACTS) + ")")],
            "meaning": "Necessary declared SPI premises, all required together. Category knowledge is separate from general client competence. Consent covers written agreement without withdrawal; current assessment covers annual review. Other applicable requirements is a deliberately unresolved premise, not a default true value.",
            "source": "sfc-spi-annex-1", "pattern": r"written|annually|Product Categories|consent"},
        "duties": {
            "facts": [(k, "bool") for k in ("solicited", "complex_product", "streamlined", "offering_documents", "bond_summary", "explanation_requested")],
            "outputs": [
                ("suitability_matching_required", "bool", "(and (or solicited complex_product) (not streamlined))"),
                ("pdd_relief", "bool", "(and complex_product (not solicited) streamlined (or offering_documents bond_summary))"),
                ("explanation_required", "bool", "(and (or solicited complex_product) (or (not streamlined) explanation_requested))"),
                ("annual_complex_warning_relief", "bool", "(and complex_product (not solicited) streamlined)")],
            "meaning": "Selected suitability/SPI procedures only. Streamlined means all eligibility premises hold. Bond_summary means the product is a bond and sufficient permitted information is actually provided. Explanation_requested includes material queries. Relief does not remove other duties.",
            "source": "sfc-spi-annex-1", "pattern": r"10\.1|10\.3|11\.1|11\.4|11\.5"},
        "principal": {
            "facts": [("trigger", "bool"), ("principal", "integer"), ("dividend_declared", "bool"), ("distribution", "integer")],
            "outputs": [("full_write_down", "integer", "(if trigger (integer 0) principal)"),
                        ("preferred_principal", "integer", "principal"),
                        ("paid_distribution", "integer", "(if dividend_declared distribution (integer 0))")],
            "meaning": "Synthetic mechanism controls in a single currency: complete permanent write-down cancels principal on trigger; cancelling a non-cumulative distribution leaves principal unchanged. A write-down is not inferred for any issuer. Conversion/restoration have independent exact rational tests.",
            "source": None, "pattern": None},
    }


def make_model(name, spec):
    text = spec["meaning"] + " Formal expressions: " + "; ".join(o[2] for o in spec["outputs"])
    packet = {"source_key": "synthetic.prospectus." + name, "authority": "SYNTHETIC_FIXTURE",
              "selected_slice": "Explicit conditional specification, not certified legal meaning",
              "units": [{"unit_id": "p1", "locator": "formal specification", "text": text, "normative": True, "span": None}],
              "dependencies": [], "family_ids": list(DIMENSIONS)}
    reading = {"local_id": name, "family": "scope", "subject": "Conditional prospectus calculation",
               "statement": text, "distinction": "Formal consequences under explicit premises",
               "citations": [{"unit_id": "p1", "quote": text}], "assumptions": [], "questions": [],
               "formalization": {"version": "2", "types": [], "helpers": [],
                   "facts": [{"name": n, "type": t, "meaning": "Explicit premise " + n,
                              "unit": "Boolean or integer minor currency units, as specified",
                              "source_unit_ids": ["p1"], "requires_judgment": False} for n, t in spec["facts"]],
                   "outputs": [{"id": n, "result_type": t, "scope": "true", "result": e} for n, t, e in spec["outputs"]]}}
    return from_reading(reading, packet, AT, profile="complete.v1",
                        coverage=[{"unit_id": "p1", "status": "INTERPRETED", "reason": "Declared formal fixture"}],
                        dimensions=[{"dimension": d, "status": "PROPOSED", "source_unit_ids": ["p1"],
                                     "explanation": "Synthetic engineering specification"} for d in DIMENSIONS])


def values_for(name, spec):
    names = [f[0] for f in spec["facts"]]
    if name == "complex":
        return [dict(zip(names, v)) for v in product((False, True), repeat=len(names))]
    if name == "financial":
        return [dict(portfolio=p, net_assets=n) for p in (0, 3999999999, 4000000000, 4000000001)
                for n in (0, 7999999999, 8000000000, 8000000001) if p == 0 or n == 0]
    if name == "threshold":
        return [dict(gross=g, maximum=100, designated=d, adding_funds=a)
                for g, d, a in product((99, 100, 101), (False, True), (False, True))]
    if name == "principal":
        return [dict(trigger=t, principal=p, dividend_declared=d, distribution=6)
                for t, p, d in product((False, True), (0, 100), (False, True))]
    if name == "duties":
        return [dict(zip(names, v)) for v in product((False, True), repeat=len(names))
                if sum(v) in (0, 1, len(names)-1, len(names))] + [
                    dict(zip(names, (False, True, True, True, False, False))),
                    dict(zip(names, (False, True, True, False, True, True)))]
    return [dict.fromkeys(names, False), dict.fromkeys(names, True)] + [
        {k: k != missing for k in names} for missing in names]


def cases_for(name, spec):
    cases = []
    for i, values in enumerate(values_for(name, spec)):
        evidence = {"/" + n: ["generated:" + name + ":" + str(i) + ":" + n] for n, _ in spec["facts"]}
        snapshot = {"subject_id": "synthetic-" + name, "evidence": evidence, "facts": {
            n: {"status": "known", "type": t, "value": values[n] if t == "bool" else str(values[n]),
                "evidence_ids": evidence["/" + n], "complete": True, "valid_from": AT,
                "valid_until": None, "recorded_at": AT} for n, t in spec["facts"]}}
        cases.append({"id": name + "." + str(i), "snapshot": snapshot, "valid_at": AT, "known_at": AT})
    return cases


def candidate_cases(reports):
    """Backend inputs are possible completions, never asserted document truth."""
    cases, qualifications = [], []
    template = cases_for("complex", definitions()["complex"])[0]
    from copy import deepcopy
    for report in reports:
        for answer, values in report["formal_sufficient_condition"]["witnesses"].items():
            case = deepcopy(template)
            case["id"] = "candidate." + report["document"] + "." + answer
            snapshot = case["snapshot"]
            snapshot["subject_id"] = report["document"]
            for key, value in values.items():
                eid = "conditional-completion:" + report["source_sha256"] + ":" + key
                snapshot["facts"][key]["value"] = value
                snapshot["facts"][key]["evidence_ids"] = [eid]
                snapshot["evidence"]["/" + key] = [eid]
            cases.append(case)
            qualifications.append({"case": case["id"], "document": report["document"],
                                   "source_sha256": report["source_sha256"],
                                   "premise_status": "HYPOTHETICAL_COMPLETION_OF_CANDIDATE_INTERPRETATION",
                                   "legal_decision": "NOT_ESTABLISHED"})
    return cases, qualifications


def build_specifications(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    bindings, counts = {}, {}
    for name, spec in definitions().items():
        model = make_model(name, spec)
        cases = cases_for(name, spec)
        write(directory / (name + ".model.json"), model)
        write(directory / (name + ".cases.json"), cases)
        claims = []
        if spec["source"]:
            doc = read(ARCHIVE / "text" / (spec["source"] + ".json"))
            claims = [{"source": spec["source"], "source_sha256": doc["source_sha256"], **c}
                      for page in doc["pages"] for c in locate(page, spec["pattern"])]
            if not claims:
                raise ValueError("No source binding for " + name)
        bindings[name] = {"specification": spec, "quotations": claims,
                          "entailment": "NOT_ESTABLISHED", "rule_completeness": "NOT_ESTABLISHED"}
        counts[name] = len(cases)
    write(directory / "source-bindings.json", bindings)
    return {"models": len(counts), "cases": counts, "total_cases": sum(counts.values()),
            "authority": "Explicit formal premises; quotations are provenance, not legal certification"}
