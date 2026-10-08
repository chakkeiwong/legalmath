"""Source-bound review intake and a frozen, bounded independent-case challenge."""
from collections import defaultdict
from pathlib import Path
import re
import zipfile

from . import master_control as c, evidence_closure as ec
from .closure_sources import require, reviewer, check_quote, admission
from .loss_absorption_reader import analyze_issue, load_document
from ..transaction.evidence import instant


def clause_audit(folder, data, rows, baseline, reviews):
    require(isinstance(reviews, list), "Clause reviews must be a list")
    issues = {i["id"]: i for i in data["issues"]}
    actual = {(r["id"], e["id"]): e for r in rows for e in r["evidence"]}
    before = {(r["id"], e["id"]): e for r in baseline for e in r["evidence"]}
    grouped = defaultdict(list)
    for (issue, key), e in actual.items():
        if e["disposition"].startswith("unresolved"):
            group = c.digest({k: e[k] for k in ("document", "source_sha256", "start", "end", "quote")})
            grouped[group].append({"issue_id": issue, "evidence": e})
    audited, seen = [], set()
    for review in reviews:
        required = {"issue_id", "evidence_id", "issue_binding", "evidence_binding", "reviewer",
                    "reviewed_at", "reason", "anchors", "expected_disposition"}
        require(set(review) == required, "Unexpected or incomplete clause review")
        key = (review["issue_id"], review["evidence_id"])
        require(key in actual and key not in seen, "Unknown, retired or duplicate clause review")
        seen.add(key)
        item = actual[key]
        require(review["issue_binding"] == c.digest(issues[key[0]]) and review["evidence_binding"] == c.digest(item),
                "Clause review scope, bytes or disposition changed")
        reviewer(review["reviewer"])
        require(instant(review["reviewed_at"]) <= instant(c.now()), "Future clause review")
        require(review["reason"] and review["anchors"] and isinstance(review["expected_disposition"], str),
                "Clause adjudication needs source reasoning")
        for anchor in review["anchors"]:
            check_quote(anchor, data["documents"], c.ROOT)
        matched = review["expected_disposition"] == item["disposition"]
        audited.append({"issue_id": key[0], "evidence_id": key[1], "review_sha256": c.digest(review),
                        "status": "MATCHES_RECORDED_REVIEW" if matched else "SEMANTIC_REPAIR_REQUIRED",
                        "reviewer_role": review["reviewer"]["role"], "actual": item["disposition"],
                        "expected": review["expected_disposition"]})
    changes = [{"issue_id": key[0], "evidence_id": key[1], "before": before.get(key), "after": actual.get(key),
                "reviewed": key in seen} for key in sorted(set(before) | set(actual))
               if before.get(key) != actual.get(key)]
    c.write(folder / "clause-groups.json", [{"id": k, "bindings": v} for k, v in grouped.items()])
    c.write(folder / "clause-reviews.json", audited)
    c.write(folder / "disposition-changes.json", changes)
    remaining = []
    if grouped:
        remaining.append("G31: unresolved constructions still need controlling-source adjudication and demonstrated semantic repairs")
    if any(r["status"] == "SEMANTIC_REPAIR_REQUIRED" for r in audited) or any(not r["reviewed"] for r in changes):
        remaining.append("G03-G09/G31: changed or disputed dispositions require source review, a counterexample and a tested reader repair")
    return {"status": "WAITING_EVIDENCE" if remaining else "QUALIFIED",
            "unresolved_records": sum(len(v) for v in grouped.values()), "unique_source_spans": len(grouped),
            "reviewed_records": len(audited), "changed_records": len(changes), "remaining": remaining,
            "repairs": ["Executed clause review intake and audited every changed or removed disposition"]}


def validate_protocol(protocol, data):
    fields = {"cohort", "cases", "selection_rule", "no_substitution", "exposure_audit",
              "adjudicator", "rubric", "criterion", "request_budget", "nonclaims"}
    require(isinstance(protocol, dict) and set(protocol) == fields, "Incomplete challenge protocol")
    require(re.fullmatch(r"[a-z0-9-]{1,60}", protocol["cohort"]), "Invalid challenge cohort")
    require(protocol["criterion"] == "ALL_SELECTED_ADJUDICATED_ZERO_CONTRADICTIONS" and
            protocol["no_substitution"] is True, "Explicit error, abstention and substitution criterion required")
    reviewer(protocol["adjudicator"])
    require(protocol["adjudicator"]["role"] in {"independent_adjudicator", "human_legal_reviewer"},
            "An independent source adjudicator is required")
    for field in ("selection_rule", "exposure_audit", "rubric", "nonclaims"):
        require(isinstance(protocol[field], str) and protocol[field].strip(), "Missing protocol field: " + field)
    cases = protocol["cases"]
    require(isinstance(cases, list) and cases and len({i["id"] for i in cases}) == len(cases), "Unique selected cases required")
    exposed_ids = {i["id"] for i in data["issues"]}
    exposed_issuers = {i["issuer"].casefold() for i in data["issues"]}
    for case in cases:
        require(set(case) == {"id", "issuer", "family", "url", "mechanism_stratum"}, "Complete challenge case identity required")
        require(case["id"] not in exposed_ids and case["issuer"].casefold() not in exposed_issuers,
                "Challenge case or issuer family already exposed")
    require(type(protocol["request_budget"]) is int and protocol["request_budget"] > 0, "Predeclared request budget required")


def challenge(folder, current, data):
    from . import closure_phases as phases
    protocol = phases.optional("challenge.json", None)
    if protocol is None:
        c.write(folder / "challenge-readiness.json", {
            "exposed_issues": [{"id": i["id"], "issuer": i["issuer"]} for i in data["issues"]],
            "method_sha256": c.digest(ec.method()), "unseen_cases_evaluated": 0,
            "known_selection_problem": "Danske Bank is already exposed; it cannot be called a fresh issuer family"})
        return {"status": "WAITING_PROTOCOL", "remaining": [
            "G30/G31: exact unexposed cases, independent source adjudicator and approved separate acquisition budget are absent"]}
    validate_protocol(protocol, data)
    require(protocol["request_budget"] <= ec.policy().get("max_challenge_requests", 0),
            "Challenge acquisition budget has not been approved")
    target = ec.DATA / "challenges" / protocol["cohort"]
    freeze_path = target / "freeze.json"
    evidence = phases.optional("challenge-evidence.json", None)
    adjudications = phases.optional("challenge-adjudication.json", [])
    if not freeze_path.exists():
        require(evidence is None and not adjudications, "Cannot freeze after challenge evidence was opened")
        target.mkdir(parents=True, exist_ok=True)
        archive = target / "method.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stream:
            for path in ec.method():
                stream.write(c.ROOT / path, path)
        c.write(freeze_path, {"method": ec.method(), "protocol_sha256": c.digest(protocol),
                "at": c.now(), "archive_sha256": c.sha(archive)}, exclusive=True)
    freeze = c.read(freeze_path)
    require(freeze["method"] == ec.method() and freeze["protocol_sha256"] == c.digest(protocol),
            "Frozen method or selection changed; this exposed cohort requires a new untouched successor")
    require(c.sha(target / "method.zip") == freeze["archive_sha256"], "Frozen method archive changed")
    external = {c.relative(freeze_path): c.sha(freeze_path), c.relative(target / "method.zip"): freeze["archive_sha256"]}
    if evidence is None:
        return {"status": "WAITING_EVIDENCE", "external_outputs": external, "remaining": [
            "G30/G31: method and selection frozen; selected source evidence and independent adjudication are still absent"]}
    require(isinstance(evidence, dict) and set(evidence) == {"documents", "issues", "unavailable", "admissions"},
            "Complete challenge evidence ledger required")
    selected = {i["id"]: i for i in protocol["cases"]}
    issues = {i["id"]: i for i in evidence["issues"]}
    unavailable = evidence["unavailable"]
    require(len(issues) == len(evidence["issues"]) and set(issues).isdisjoint(unavailable) and
            set(issues) | set(unavailable) == set(selected), "Every selected case must remain in the denominator")
    require(all(isinstance(reason, str) and reason for reason in unavailable.values()), "Unavailable cases need reasons")
    exposed_hashes = {d["sha256"] for d in data["documents"].values()}
    for doc in evidence["documents"].values():
        load_document(doc, c.ROOT)
        require(doc["sha256"] not in exposed_hashes, "Exposed source reused as fresh evidence")
        receipt_path = (c.ROOT / doc["acquisition_receipt"]).resolve()
        require(receipt_path.is_relative_to(c.ROOT.resolve()), "Receipt escapes checkout")
        receipt = c.read(receipt_path)
        require(receipt.get("status") == "RETAINED" and receipt.get("sha256") == doc["sha256"] and
                receipt.get("original", receipt.get("body")) == doc["original"] and
                instant(receipt["at"]) > instant(freeze["at"]), "Challenge PDF must be acquired after freeze")
        external[c.relative(receipt_path)] = c.sha(receipt_path)
    judgments = {j["issue_id"]: j for j in adjudications}
    require(len(judgments) == len(adjudications) and set(judgments) <= set(issues), "Duplicate or unknown adjudication")
    results = [{"id": key, "status": "UNAVAILABLE", "reason": reason} for key, reason in unavailable.items()]
    for key, issue in issues.items():
        require(issue["issuer"] == selected[key]["issuer"], "Challenge issuer changed")
        relevant = [r for r in evidence["admissions"] if r.get("issue_id") == key]
        for sel in issue["documents"]:
            review = [r for r in relevant if r["document"] == sel["id"]]
            require(len(review) == 1, "Fresh source needs one exact admission review")
            admission(review[0], issue, evidence["documents"], c.ROOT, review[0]["assessment"])
        row = analyze_issue(issue, evidence["documents"], c.ROOT)
        c.write(folder / "cases" / (key + ".json"), row)
        judgment = judgments.get(key)
        status = "UNADJUDICATED"
        if judgment is not None:
            require(set(judgment) == {"issue_id", "issue_binding", "documents_binding", "reviewer", "reviewed_at",
                    "answer", "anchors", "reason", "independent_of_classifier"}, "Incomplete adjudication")
            require(judgment["reviewer"] == protocol["adjudicator"] and judgment["independent_of_classifier"] is True,
                    "Independent adjudication required")
            require(judgment["issue_binding"] == c.digest(issue) and judgment["documents_binding"] ==
                    c.digest({s["id"]: evidence["documents"][s["id"]] for s in issue["documents"]}),
                    "Stale adjudication")
            require(freeze["at"] < judgment["reviewed_at"] <= c.now() and judgment["reason"] and judgment["anchors"],
                    "Adjudication needs dated source reasoning")
            require(judgment["answer"] is None or type(judgment["answer"]) is bool, "Invalid adjudicated answer")
            for anchor in judgment["anchors"]:
                check_quote(anchor, evidence["documents"], c.ROOT)
            status = "ABSTAIN" if row["answer"] is None or judgment["answer"] is None else (
                "AGREEMENT" if row["answer"] == judgment["answer"] else "CONTRADICTION")
        results.append({"id": key, "status": status, "answer": row["answer"]})
    c.write(folder / "challenge-results.json", results)
    passed = all(r["status"] == "AGREEMENT" for r in results)
    return {"status": "QUALIFIED" if passed else "WAITING_EVIDENCE", "external_outputs": external,
            "bounded_case_criterion_passed": passed, "selected": len(selected),
            "remaining": [] if passed else ["G30/G31: selected cases remain unavailable, unadjudicated, abstained or contradicted"],
            "population_accuracy": "NOT_ESTABLISHED", "independence": "RECORDED_ATTESTATION; IDENTITY_NOT_AUTHENTICATED"}


def human_review(folder, current, review):
    from .closure_phases import previous
    versions = {p: current["phases"][p]["receipt_sha256"] for p in ec.DEPENDENCIES["S7"]}
    packet = {"versions": versions, "remaining": [gap for p in ec.DEPENDENCIES["S7"]
              for gap in previous(current, p).get("remaining", [])],
              "review_requested": ["source applicability", "controlling language", "calculations", "actual facts", "use and date"],
              "human_acceptance": False, "may_execute_transaction": False}
    binding = c.digest(packet)
    status = "WAITING_HUMAN"
    if review is not None:
        require(set(review) == {"packet_binding", "reviewer", "qualifications", "independence", "scope", "assessment",
                "decision", "reason", "reviewed_at", "attestation"}, "Incomplete human review")
        require(review["packet_binding"] == binding, "Human review identifies obsolete versions")
        reviewer(review["reviewer"])
        require(review["reviewer"]["role"] == "human_legal_reviewer" and review["independence"] is True and
                review["qualifications"] and review["scope"] and review["reason"], "Qualified independent human required")
        require(review["decision"] in {"ACCEPT", "REJECT", "UNRESOLVED"} and instant(review["reviewed_at"]) <= instant(c.now()),
                "Explicit dated human decision required")
        require(review["assessment"] == previous(current, "S1").get("assessment"), "Human assessment dates changed")
        proof = review["attestation"]
        path = (c.ROOT / proof["path"]).resolve()
        require(path.is_relative_to(c.ROOT.resolve()) and path.is_file() and c.sha(path) == proof["sha256"],
                "Retained attestation missing or changed")
        attestation = c.read(path)
        require(attestation == {k: v for k, v in review.items() if k != "attestation"}, "Attestation content does not match review")
        packet["recorded_review"] = review
        packet["review_attribution"] = "SUPPLIED_HUMAN_ATTESTATION"
        packet["human_acceptance"] = review["decision"] == "ACCEPT"
        status = "QUALIFIED" if packet["human_acceptance"] else "WAITING_HUMAN"
    packet["packet_binding"] = binding
    c.write(folder / "human-review-packet.json", packet)
    return {"status": status, "human_acceptance": packet["human_acceptance"],
            "scope": review["scope"] if review else None,
            "remaining": [] if packet["human_acceptance"] else [
                "G32: independent human legal acceptance for exact versions, dates and use is absent or unresolved"],
            "review_packet": c.relative(folder / "human-review-packet.json")}


def source_work_review(orders, reviews, data, current):
    """Close a named work order only under recorded source-bound judgment."""
    from . import closure_phases as phases
    require(isinstance(reviews, list), "Source work reviews must be a list")
    by_gap = {r["gap"]: r for r in orders}
    issues = {i["id"]: i for i in data["issues"]}
    seen = set()
    for review in reviews:
        require(set(review) == {"gap", "requirement_binding", "reviewer", "reviewed_at", "reason",
                "issue_bindings", "closure_bindings", "anchors"}, "Incomplete source work review")
        gap = review["gap"]
        require(gap in by_gap and gap not in seen, "Unknown or duplicate source work review")
        seen.add(gap)
        order = by_gap[gap]
        require(review["requirement_binding"] == c.digest(order) and review["reason"], "Source work requirement changed")
        reviewer(review["reviewer"])
        require(instant(review["reviewed_at"]) <= instant(phases.dates()["known_at"]), "Review not known at assessment")
        require(review["issue_bindings"] and set(review["issue_bindings"]) == set(order["issue_ids"]) == set(review["closure_bindings"]),
                "Every affected issue needs a current closure binding")
        admitted = set()
        for key, binding in review["issue_bindings"].items():
            require(key in issues and c.digest(issues[key]) == binding, "Wrong issue selection for source work")
            closure = c.read(c.ROOT / current["phases"]["S1"]["directory"] / "issues" / (key + ".json"))
            require(c.digest(closure) == review["closure_bindings"][key] and closure["open_references"] == 0
                    and closure["admissions"] and not closure["admission_problems"] and not closure["orphaned_decisions"],
                    "Source work still has invalid admissions or open dependencies")
            admitted.update(closure["admissions"])
        require(review["anchors"], "Source work needs controlling-source reasoning")
        for anchor in review["anchors"]:
            require(anchor["document"] in admitted, "Source work quote has not been admitted")
            check_quote(anchor, data["documents"], c.ROOT)
        order.update(status="SATISFIED_UNDER_RECORDED_REVIEW", review_sha256=c.digest(review),
                     legal_completeness="NOT_ESTABLISHED", human_acceptance=False)
    return orders
