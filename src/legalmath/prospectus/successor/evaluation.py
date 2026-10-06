"""Independent-label accounting. This module does not call the interpreter."""
from .contracts import digest

VALUES = {"YES", "NO", "UNKNOWN", "CONFLICT"}


def score(predictions, labels, cohort, identities):
    if not cohort or len({c["id"] for c in cohort}) != len(cohort):
        raise ValueError("Distinct frozen cohort required")
    if len(set(identities.get("readers", []))) < 2 or not identities.get("adjudicator"):
        return {"status": "BLOCKED_INDEPENDENT_REVIEW", "scores": None}
    if identities.get("implementer") in identities["readers"]:
        raise ValueError("Implementer cannot provide independent first reading")
    by_label, by_prediction = {}, {}
    for row in labels:
        key = (row["id"], row["question"])
        if key in by_label or row["value"] not in VALUES or not row.get("blinded"):
            raise ValueError("Invalid independent label")
        if set(row["readers"]) != set(identities["readers"]) or not row.get("evidence"):
            raise ValueError("Unreviewed or unbound label")
        by_label[key] = row
    for row in predictions:
        key = (row["id"], row["question"])
        if key in by_prediction or row["value"] not in VALUES:
            raise ValueError("Duplicate/invalid prediction")
        by_prediction[key] = row
    counts = {}
    expected = {(c["id"],q) for c in cohort for q in c["questions"]}
    if set(by_label) != expected or set(by_prediction) != expected:
        raise ValueError("Evaluation denominator differs from frozen cohort")
    for key in sorted(expected):
        c=counts.setdefault(key[1],dict(N=0,D=0,C=0,W=0,A=0,conflicts=0,undecidable=0,correct_positive=0,correct_negative=0))
        truth, pred=by_label[key]["value"],by_prediction[key]["value"]
        c["N"]+=1
        c["D"]+=truth in {"YES","NO"}
        if pred=="UNKNOWN":c["A"]+=1
        elif pred=="CONFLICT":c["conflicts"]+=1
        elif truth not in {"YES","NO"}:c["undecidable"]+=1
        elif pred==truth:
            c["C"]+=1
            c["correct_positive" if pred=="YES" else "correct_negative"]+=1
        else:c["W"]+=1
    for c in counts.values():
        c["useful_coverage"]=c["C"]/c["D"] if c["D"] else None
        c["wrong_supported_fraction"]=c["W"]/(c["C"]+c["W"]) if c["C"]+c["W"] else None
    return {"status":"FINITE_DESCRIPTIVE_ONLY","counts":counts,"cohort_sha256":digest(cohort),
            "statistically_supported_ranking":False,"population_accuracy":None}
