"""Fail-closed support register independent of campaign execution status."""


def assess(evaluation, support, signoffs):
    reasons=[]
    if evaluation.get("status")!="FINITE_DESCRIPTIVE_ONLY":
        reasons.append("Independent evaluation missing")
    if not support:
        reasons.append("No frozen supported scope")
    if not evaluation.get("counts"):
        reasons.append("No independently scored questions")
    if len({s.get("reviewer") for s in signoffs if s.get("accepted")}) < 2:
        reasons.append("Independent sign-offs missing")
    for question, counts in evaluation.get("counts",{}).items():
        if counts["W"] or counts["C"]==0 or counts["undecidable"] or not counts.get("correct_positive") or not counts.get("correct_negative"):
            reasons.append("Wrong, unsupported or no useful answers: "+question)
    return {"status":"BLOCKED" if reasons else "FINITE_ASSISTED_CANDIDATE",
        "remaining":reasons,"automatic_release":False,"may_execute_transaction":False,
        "support":support,"human_acceptance_required":True}
