"""Conditional original-offering purchaser routes, never transaction clearance.

The source adapter validates retained bytes and explicit interpretation proposals.
It does not turn a quotation or a prospectus's registration into legal approval.
"""
from copy import deepcopy
from itertools import product
from pathlib import Path
import re

import z3

from ..canonical import digest
from ..transaction.engine import conditional
from .checks import symbolic
from .common import ROOT, read, sha, write
from .models import AT, make_model

DOSSIER = ROOT / "docs/prospectus/coco-cases"
FACTS = (
    "public_us_distribution", "restricted_144a_reg_s_distribution",
    "purchaser_is_qib", "own_account", "account_is_qib",
    "purchaser_is_us_person_reg_s", "us_beneficial_account",
    "offshore_transaction", "issuer_affiliate",
)
QIB = "(and purchaser_is_qib (or own_account account_is_qib))"
OFFSHORE = "(and offshore_transaction (not purchaser_is_us_person_reg_s) (not us_beneficial_account) (not issuer_affiliate))"
EXPRESSION = "(or public_us_distribution (and restricted_144a_reg_s_distribution (or " + QIB + " " + OFFSHORE + ")))"


def specification():
    return {"facts": [(k, "bool") for k in FACTS],
        "outputs": [("purchaser_route_pass", "bool", EXPRESSION)],
        "meaning": "Selected purchaser conditions in a declared original distribution: a public US distribution, or the specified 144A/Regulation S distribution with a qualifying institutional purchaser/account or the specified offshore non-US purchaser/benefit/non-affiliate premises. This is a conditional interpretation proposal, not all requirements of either exemption or offering. Registration effectiveness, seller obligations, all other selling restrictions, actual facts, currentness, natural-language meaning and transaction permission remain unproved."}


def model():
    return make_model("coco_purchaser_route", specification())


def independent(v):
    """Decision procedure written separately from the expression/AST evaluator."""
    if v["public_us_distribution"]:
        return True
    if not v["restricted_144a_reg_s_distribution"]:
        return False
    if v["purchaser_is_qib"]:
        if v["own_account"] or v["account_is_qib"]:
            return True
    for disqualifier in (v["purchaser_is_us_person_reg_s"], v["us_beneficial_account"], v["issuer_affiliate"]):
        if disqualifier:
            return False
    return v["offshore_transaction"]


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def safe_path(root, name):
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Source escapes archive root")
    return path


def verify_sources(sources, *, root=ROOT):
    pages = {}
    for key, source in sources.items():
        raw = safe_path(root, source["path"]).read_bytes()
        text = safe_path(root, source["text_path"]).read_bytes()
        if sha(raw) != source["sha256"] or sha(text) != source["text_sha256"]:
            raise ValueError("Changed retained source or extraction: " + key)
        data = read(safe_path(root, source["text_path"]))
        if data["source_sha256"] != source["sha256"] or data["page_count"] != source["page_count"]:
            raise ValueError("Extraction refers to another source")
        if len(data["pages"]) != data["page_count"] or [p["page"] for p in data["pages"]] != list(range(1, data["page_count"] + 1)):
            raise ValueError("Incomplete extraction page sequence")
        pages[key] = {p["page"]: normalized(p["text"]) for p in data["pages"]}
    return pages


def validate_dossier(dossier, sources, *, root=ROOT):
    if set(dossier) != {"schema", "scope", "scenario", "instruments", "legal_anchors", "qualifications"} or dossier["schema"] != "coco-purchaser-cases.v1":
        raise ValueError("Input-only source dossier required; no quality labels")
    pages = verify_sources(sources, root=root)
    anchors = list(dossier["legal_anchors"])
    ids = set()
    if not dossier["instruments"] or not dossier["legal_anchors"] or not dossier["qualifications"]:
        raise ValueError("Missing source or qualification inventory")
    for item in dossier["instruments"]:
        if set(item) != {"id", "source", "issuer", "coupon", "prospectus_date", "issue_date", "isins",
                        "minimum_usd", "increment_usd", "route_premises", "source_meaning", "edition_basis", "anchors"}:
            raise ValueError("Instrument proposals cannot contain quality labels")
        if item["id"] in ids or item["source"] not in sources:
            raise ValueError("Duplicate instrument or missing source")
        ids.add(item["id"])
        if set(item["route_premises"]) != set(FACTS[:2]) or any(type(v) is not bool for v in item["route_premises"].values()):
            raise ValueError("Explicit typed distribution premises required")
        if sum(item["route_premises"].values()) != 1:
            raise ValueError("Choose one declared distribution profile")
        if not item["edition_basis"] or item["source_meaning"] != "QUALIFIED_INTERPRETATION_PROPOSAL":
            raise ValueError("Source interpretation qualification required")
        if any(a["source"] != item["source"] for a in item["anchors"]):
            raise ValueError("Instrument anchor belongs to another prospectus")
        required = {"identity", "edition", "route", "denomination", "mechanism"}
        if item["route_premises"]["restricted_144a_reg_s_distribution"]:
            required |= {"account", "offshore"}
        if not required <= {a["role"] for a in item["anchors"]}:
            raise ValueError("Missing material source anchor")
        anchors.extend(item["anchors"])
        amount = dossier["scenario"]["principal_usd"]
        minimum, step = item["minimum_usd"], item["increment_usd"]
        if any(type(x) is not int or x <= 0 for x in (amount, minimum, step)):
            raise ValueError("Positive exact USD principal units required")
        if amount < minimum or (amount - minimum) % step:
            raise ValueError("Comparison order fails a declared denomination condition")
    for anchor in anchors:
        text = pages[anchor["source"]][anchor["page"]]
        excerpt = text[anchor["start"]:anchor["end"]]
        if not excerpt or sha(excerpt.encode()) != anchor["span_sha256"]:
            raise ValueError("Changed source span: " + anchor["claim"])
    investor = dossier["scenario"]["premises"]
    if set(investor) != set(FACTS[2:]) or any(type(v) is not bool for v in investor.values()):
        raise ValueError("Complete typed synthetic investor premises required")
    return {"documents": len(sources), "anchors": len(anchors), "instruments": len(ids),
            "status": "SOURCE_BYTES_AND_ANCHORS_CHECKED", "meaning_proved": False,
            "sources_hash": digest(sources), "dossier_hash": digest(dossier)}


def snapshot(case_id, values, *, source_ids=None):
    if set(values) != set(FACTS) or any(type(x) is not bool for x in values.values()):
        raise ValueError("Complete Boolean inputs required")
    evidence = {"/" + k: (source_ids or ["synthetic:" + case_id]) for k in FACTS}
    return {"id": case_id, "valid_at": AT, "known_at": AT,
        "snapshot": {"subject_id": case_id, "evidence": evidence, "facts": {
            k: {"type": "bool", "status": "known", "value": values[k], "evidence_ids": evidence["/" + k],
                "complete": True, "valid_from": AT, "valid_until": None, "recorded_at": AT} for k in FACTS}}}


def paired_cases(dossier, sources, *, root=ROOT):
    validate_dossier(dossier, sources, root=root)
    result = []
    for instrument in dossier["instruments"]:
        values = {**instrument["route_premises"], **dossier["scenario"]["premises"]}
        source = sources[instrument["source"]]
        c = snapshot(instrument["id"], values)
        # Source interpretation and fictional investor facts remain distinct.
        for k in FACTS:
            ids = (["interpretation-proposal:" + source["sha256"]] if k in FACTS[:2]
                   else ["synthetic-investor:" + digest(dossier["scenario"])])
            c["snapshot"]["facts"][k]["evidence_ids"] = ids
            c["snapshot"]["evidence"]["/" + k] = ids
        result.append(c)
    return result


def evaluate(case, *, stage="original_distribution", action="buy"):
    if stage != "original_distribution" or action != "buy":
        status, value = "UNSUPPORTED_SCOPE", None
    else:
        facts = case["snapshot"]["facts"]
        if set(facts) != set(FACTS):
            raise ValueError("Changed factual interface")
        from ..translation.policy import prepare
        boundary = prepare(model(), case["snapshot"], case["valid_at"], case["known_at"])
        if any(x["status"] == "conflict" for x in facts.values()):
            status, value = "CONFLICT", None
        elif any(x["status"] != "known" for x in facts.values()):
            status, value = "UNKNOWN", None
        else:
            if boundary["reason"]:
                status, value = "UNKNOWN", None
            else:
                values = {k: facts[k]["value"] for k in FACTS}
                if any(type(v) is not bool for v in values.values()):
                    raise ValueError("Boolean facts required")
                reference = independent(values)
                observed = {k: {"status": "KNOWN", "value": v} for k, v in values.items()}
                result = conditional(model(), observed)["purchaser_route_pass"]
                if result["status"] != "KNOWN" or result["value"] != reference:
                    raise ValueError("Formal consequence differs from independent decision procedure")
                status, value = ("PASS" if reference else "FAIL"), reference
    return {"case_id": case["id"], "scope": "SELECTED_US_ORIGINAL_DISTRIBUTION_PURCHASER_CONDITIONS",
        "status": status, "value": value, "input_hash": digest(case), "model_hash": digest(model()),
        "source_meaning": "NOT_PROVED", "actual_investor_facts": "SYNTHETIC",
        "other_selling_requirements": "NOT_ESTABLISHED", "may_execute_transaction": False}


def challenge_cases(dossier, sources):
    rows = paired_cases(dossier, sources)
    # Exhaust all investor premises for each real distribution profile, holding
    # non-affiliation fixed; affiliation is challenged separately below.
    for instrument in dossier["instruments"]:
        for i, bits in enumerate(product((False, True), repeat=6)):
            values = {**instrument["route_premises"], **dict(zip(FACTS[2:8], bits)), "issuer_affiliate": False}
            rows.append(snapshot(instrument["id"] + ".investor." + str(i), values))
    private = next(c for c in rows if c["snapshot"]["facts"]["restricted_144a_reg_s_distribution"]["value"])
    for i, bits in enumerate(product((False, True), repeat=3)):
        values = {k: v["value"] for k, v in private["snapshot"]["facts"].items()}
        values.update(purchaser_is_qib=bits[0], account_is_qib=bits[1], own_account=bits[2],
                      purchaser_is_us_person_reg_s=False, us_beneficial_account=False,
                      offshore_transaction=True, issuer_affiliate=True)
        rows.append(snapshot("affiliate." + str(i), values))
    for k in FACTS:
        for status in ("unknown", "conflict"):
            c = deepcopy(private); c["id"] = k + "." + status
            c["snapshot"]["facts"][k] = ({"type": "bool", "status": "unknown", "reason": "MISSING"}
                if status == "unknown" else {"type": "bool", "status": "conflict", "evidence_ids": ["disagreement:a", "disagreement:b"]})
            if status == "conflict":
                c["snapshot"]["evidence"]["/" + k] = ["disagreement:a", "disagreement:b"]
            rows.append(c)
    c = deepcopy(private); c["id"] = "stale-investor"
    c["snapshot"]["facts"]["purchaser_is_qib"]["valid_from"] = "2026-09-27T00:00:00.000000Z"
    c["snapshot"]["facts"]["purchaser_is_qib"]["valid_until"] = AT
    rows.append(c)
    return rows


def prove(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    v = {k: z3.Bool(k) for k in FACTS}
    # Complement-of-failure relation, independently expressed rather than
    # reparsing or copying the source expression.
    qib_failure = z3.Or(z3.Not(v["purchaser_is_qib"]), z3.And(z3.Not(v["own_account"]), z3.Not(v["account_is_qib"])))
    offshore_failure = z3.Or(z3.Not(v["offshore_transaction"]), v["purchaser_is_us_person_reg_s"],
                            v["us_beneficial_account"], v["issuer_affiliate"])
    expected = z3.Not(z3.And(z3.Not(v["public_us_distribution"]),
        z3.Or(z3.Not(v["restricted_144a_reg_s_distribution"]), z3.And(qib_failure, offshore_failure))))
    actual = symbolic(model()["rules"][0]["body"], v)
    solver = z3.Solver(); solver.set(timeout=10000); solver.add(actual != expected)
    (directory / "route-equivalence.smt2").write_text(solver.to_smt2())
    if solver.check() != z3.unsat:
        raise ValueError("Conditional route equation not proved")
    mutants = {
        "bank_qib_ignores_beneficial_account": z3.substitute(actual, (v["own_account"], z3.BoolVal(True))),
        "offshore_ignores_us_benefit": z3.substitute(actual, (v["us_beneficial_account"], z3.BoolVal(False))),
        "offshore_ignores_us_person": z3.substitute(actual, (v["purchaser_is_us_person_reg_s"], z3.BoolVal(False))),
        "offshore_ignores_affiliation": z3.substitute(actual, (v["issuer_affiliate"], z3.BoolVal(False))),
        "all_cocos_denied": z3.BoolVal(False), "all_cocos_approved": z3.BoolVal(True)}
    detected = []
    for name, mutant in mutants.items():
        s = z3.Solver(); s.set(timeout=10000)
        s.add(z3.Xor(v[FACTS[0]], v[FACTS[1]]), mutant != expected)
        if s.check() != z3.sat:
            raise ValueError("Mutation was not detected: " + name)
        witness = {k: z3.is_true(s.model().eval(v[k], model_completion=True)) for k in FACTS}
        if independent(witness) != z3.is_true(s.model().eval(expected)):
            raise ValueError("Mutation witness disagrees with independent procedure")
        detected.append({"mutation": name, "witness": witness})
    return {"equivalence": "UNSAT", "domain": "All 512 Boolean assignments of the nine declared premises",
        "smt_sha256": sha((directory / "route-equivalence.smt2").read_bytes()), "mutations": detected,
        "natural_language_entailment": "NOT_PROVED", "solver": z3.get_version_string()}


def attach_bank_investigation(route_result, bank_receipt):
    """A scoped pass cannot fill any unresolved bank obligation."""
    return {"offering_route": route_result, "bank_investigation": bank_receipt,
            "overall": "DO_NOT_PROCEED_UNDER_DECLARED_ROUTE" if route_result["status"] == "FAIL" else "QUALIFIED",
            "may_execute_transaction": False, "complete_legal_compliance": "NOT_ESTABLISHED"}
