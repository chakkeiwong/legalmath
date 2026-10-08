"""Fail-closed support register independent of campaign execution status."""
from .contracts import digest


def assess(evaluation, support, signoffs):
    reasons=[]
    if evaluation.get("status")!="FINITE_DESCRIPTIVE_ONLY":
        reasons.append("Independent evaluation missing")
    if not support:
        reasons.append("No frozen supported scope")
    if not evaluation.get("counts"):
        reasons.append("No independently scored questions")
    report_hash = evaluation.get("evaluation_sha256")
    if report_hash != digest({k:v for k,v in evaluation.items() if k != "evaluation_sha256"}):
        reasons.append("Evaluation report is unbound or changed")
    questions = {s.get("question") for s in support}
    if questions != set(evaluation.get("counts", {})) or len(questions) != len(support):
        reasons.append("Supported questions differ from independently scored scope")
    readers = set(evaluation.get("identities", {}).get("readers", []))
    accepted = {s.get("reviewer") for s in signoffs if s.get("accepted") is True
                and s.get("reviewer") in readers
                and s.get("evaluation_sha256") == report_hash
                and s.get("cohort_sha256") == evaluation.get("cohort_sha256")
                and s.get("method_sha256") == evaluation.get("method_sha256")
                and s.get("support_sha256") == digest(support)}
    if len(accepted) < 2:
        reasons.append("Independent sign-offs bound to cohort, method, report and scope missing")
    for question, counts in evaluation.get("counts",{}).items():
        if counts["W"] or counts["C"]==0 or counts["undecidable"] or not counts.get("correct_positive") or not counts.get("correct_negative"):
            reasons.append("Wrong, unsupported or no useful answers: "+question)
    return {"status":"BLOCKED" if reasons else "FINITE_ASSISTED_CANDIDATE",
        "remaining":reasons,"automatic_release":False,"may_execute_transaction":False,
        "support":support,"human_acceptance_required":True}
