"""Label accounting with distinct integrity, execution and review admission."""
from .contracts import digest
from .anchors import bind
import re

VALUES = {"YES", "NO", "UNKNOWN", "CONFLICT"}


def score(predictions, labels, cohort, identities, method_sha256=None, *, graphs=None, prediction_records=None,
          review_packet=None, review_key=None, execution_inputs=None):
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
    if execution_inputs is not None:
        from .prediction_execution import execute
        executed, executed_graphs = execute(cohort, execution_inputs)
        if any(r['method_sha256'] != method_sha256 for r in executed.values()):
            raise ValueError('Evaluated method differs from current execution')
        if prediction_records is not None and prediction_records != executed:
            raise ValueError('Supplied prediction records differ from current execution')
        if graphs is not None and graphs != executed_graphs:
            raise ValueError('Supplied source graphs differ from current execution')
        prediction_records, graphs = executed, executed_graphs
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
                   and isinstance(e["source_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", e["source_sha256"])
                   and isinstance(e["quote"], str) and e["quote"]
                   and type(e["start"]) is int and type(e["end"]) is int
                   and 0 <= e["start"] < e["end"] for e in row["evidence"]):
            raise ValueError("Label source occurrences required")
        if graphs is not None:
            if row["id"] not in graphs:
                raise ValueError("Label source graph missing")
            for source in row["evidence"]:
                bind(graphs[row["id"]], source)
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
    if prediction_records is not None:
        if graphs is None or set(prediction_records) != {c["id"] for c in cohort}:
            raise ValueError("Executed predictions require the frozen source graphs and cases")
        for case in cohort:
            record = prediction_records[case["id"]]
            report = record["report"]
            if (record.get("method_sha256") != method_sha256 or
                    report.get("report_sha256") != digest({k:v for k,v in report.items() if k != "report_sha256"}) or
                    report.get("request_sha256") != case.get("request_sha256") or
                    report.get("source_graph_sha256") != digest(graphs[case["id"]])):
                raise ValueError("Prediction execution/source binding changed")
            for q in case["questions"]:
                if by_prediction[(case["id"], q)]["value"] != report["questions"][q]["status"]:
                    raise ValueError("Prediction differs from executed service output")
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
    verified = execution_inputs is not None
    review_record = None
    if review_packet is not None:
        if not verified:
            raise ValueError("Review admission requires bound sources and executed predictions")
        from .review_records import admit
        review_record = admit(review_packet, review_key, cohort, identities, labels, graphs)
    report = {"status":"FINITE_DESCRIPTIVE_ONLY" if verified else "UNVERIFIED_LABEL_ACCOUNTING",
              "source_binding": "VERIFIED" if graphs is not None else "NOT_CHECKED",
              "prediction_binding": "RECOMPUTED_CURRENT_SERVICE" if verified else
                                    "INTEGRITY_ONLY" if prediction_records is not None else "NOT_CHECKED",
              "review_binding": review_record["status"] if review_record else "NOT_AUTHENTICATED",
              "review_record": review_record, "counts":counts,"cohort_sha256":cohort_hash,
              "method_sha256":method_sha256,"identities":identities,"labels_sha256":digest(labels),
              "predictions_sha256":digest(predictions),"scope":sorted(counts),
              "statistically_supported_ranking":False,"population_accuracy":None}
    return {**report, "evaluation_sha256":digest(report)}
