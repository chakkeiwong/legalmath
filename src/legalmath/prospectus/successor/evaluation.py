"""Independent-label accounting. This module does not call the interpreter."""
from .contracts import digest

VALUES = {"YES", "NO", "UNKNOWN", "CONFLICT"}


def score(predictions, labels, cohort, identities, method_sha256=None):
    if not cohort or len({c["id"] for c in cohort}) != len(cohort):
        raise ValueError("Distinct frozen cohort required")
    if len(set(identities.get("readers", []))) < 2 or not identities.get("adjudicator"):
        return {"status": "BLOCKED_INDEPENDENT_REVIEW", "scores": None}
    reviewers = identities["readers"] + [identities["adjudicator"]]
    if len(set(reviewers)) != len(reviewers) or identities.get("implementer") in reviewers:
        raise ValueError("Implementer, readers and adjudicator must be independent")
    if not identities.get("implementer") or not isinstance(method_sha256, str) or len(method_sha256) != 64:
        raise ValueError("Implementer identity and evaluated method hash required")
    cohort_hash = digest(cohort)
    by_label, by_prediction = {}, {}
    for row in labels:
        key = (row["id"], row["question"])
        if key in by_label or row["value"] not in VALUES or not row.get("blinded"):
            raise ValueError("Invalid independent label")
        if set(row["readers"]) != set(identities["readers"]) or not row.get("evidence"):
            raise ValueError("Unreviewed or unbound label")
        if row.get("cohort_sha256") != cohort_hash or row.get("adjudicator") != identities["adjudicator"]:
            raise ValueError("Label is not bound to this cohort and adjudicator")
        if not all(isinstance(e, dict) and {"source_sha256", "quote", "start", "end"} <= set(e)
                   and len(e["source_sha256"]) == 64 and e["quote"] and e["end"] > e["start"] for e in row["evidence"]):
            raise ValueError("Label source occurrences required")
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
    report = {"status":"FINITE_DESCRIPTIVE_ONLY","counts":counts,"cohort_sha256":cohort_hash,
              "method_sha256":method_sha256,"identities":identities,"labels_sha256":digest(labels),
              "predictions_sha256":digest(predictions),"scope":sorted(counts),
              "statistically_supported_ranking":False,"population_accuracy":None}
    return {**report, "evaluation_sha256":digest(report)}
