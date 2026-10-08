"""Bind seven reviewed prospectus citations; preserve unrelated scoped reviews."""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/"docs/monograph"
OUT=ROOT/"docs/implementation/prospectus-successor-2026-10-06/document-review"

JUDGMENTS={
"contractnli2021":"Sections 2–5 and Appendix A.1 support self-contained discontinuous evidence, distant exceptions, 607 NDAs/17 hypotheses and exclusion of scans/multicolumn PDFs. The manuscript explicitly declines accuracy transfer and absence inference.",
"connecting2023":"Sections 3–5 and appendices B/D/E support typed span/event arguments, downstream sensitivity and the empty-KB closed-world problem. Rejection of date imputation is a local design decision.",
"legalinterpretations2014":"Sections 3–4 separate textual sources, interpretations, context and authoritative selection. The paragraph proposes a bounded local use and does not claim automatic resolution.",
"aspic2010":"Sections 3/6 and the retained correction distinguish premise/conclusion/inference attacks and preference-dependent defeat. No universal consistency or automatic legal-priority claim is made.",
"catala2021":"Sections 4.1/4.4/4.5/6.1 support formal exceptions/conflicts and compiler-correctness scope; natural-language fidelity is not covered by that theorem.",
"dates2024":"Sections 2/3.2/4.3 support rounding-sensitive, non-associative period arithmetic. Calendars and contractual conventions remain separately supplied premises.",
"limits2026":"Sections 3–5 and Appendix A support translation/execution separation and unsupported-assumption examples. The retained version's inconsistent totals and manual corrections are disclosed; no ranking is adopted."
}


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    from scripts.bind_monograph_citation_claims import record_digest
    path=BOOK/"review/reader-facing/citation-occurrence-review.json"
    previous=json.loads(path.read_text())
    contexts=json.loads((BOOK/"review/reader-facing/citation-contexts.json").read_text())
    reading=json.loads((BOOK/"review/revision/citation-reading.json").read_text())["sources"]
    archive={r["key"]:r for r in json.loads((ROOT/"docs/papers/monograph-citation-archive.json").read_text())["sources"]}
    old=defaultdict(list)
    for r in previous["occurrences"]:
        old[(r["key"],r["context_sha256"])].append(r)
    OUT.mkdir(parents=True,exist_ok=True)
    baseline=OUT/"citation-review-before.json"
    if not baseline.exists():baseline.write_bytes(path.read_bytes())
    result,added=[],[]
    for context in contexts:
        key=context["key"]; h=sha(context["context_tex"].encode())
        matches=old[(key,h)]
        if matches:
            decision=deepcopy(matches.pop(0));decision["id"]=context["id"]
        else:
            if "02f-prospectus-delivery.tex" not in context["source"] or key not in JUDGMENTS:
                raise ValueError("Unreviewed changed context: "+context["id"])
            decision={"id":context["id"],"key":key,"context_sha256":h,
                "source_sha256":archive[key]["sha256"],"reading_record_sha256":record_digest(reading[key]),
                "decision":"supported_in_stated_scope","judgment":JUDGMENTS[key],
                "reviewer":"Codex author/executor following retained technical inspection; not independent adjudication",
                "additional_reading":"docs/implementation/prospectus-root-cause-2026-10-06/LITERATURE-REVIEW.md"}
            added.append(decision)
        result.append(decision)
    if any(v for v in old.values()):
        raise ValueError("Prior citation context removed")
    updated={**previous,"occurrences":result}
    path.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n")
    (OUT/"new-citation-judgments.json").write_text(json.dumps(added,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"added":len(added),"occurrences":len(result),"independent_review":False}))


if __name__=="__main__":main()
