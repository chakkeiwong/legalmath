#!/usr/bin/env python3
"""Add the six author-reviewed citation contexts introduced by M06:26.

The script is intentionally source-specific.  It does not infer support from
word overlap: it reuses the already retained reading records and records the
reviewed scope, quotation and limitations for the exact new contexts.  Any
unexpected citation addition or missing reading record fails closed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/monograph"
REVIEW = BOOK / "review/reader-facing"
READING = BOOK / "review/revision/citation-reading.json"
ARCHIVE = ROOT / "docs/papers/monograph-citation-archive.json"


def record_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()


def context_digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    # Importing this module requires the document-review environment's PyMuPDF.
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_reader_facing_monograph import expand, BOOK as CHECK_BOOK, occurrences

    texts = {name: expand(CHECK_BOOK / f"{name}.tex", CHECK_BOOK)
             for name in ("technical-companion", "monograph")}
    current = [row for name in texts for row in occurrences(CHECK_BOOK / f"{name}.tex", CHECK_BOOK)]
    review_path = REVIEW / "citation-occurrence-review.json"
    review = json.loads(review_path.read_text())
    source = "docs/monograph/chapters/06g-proof-carrying-integration.tex"
    additions = [row for row in current if row['source'] == source]
    previous = [row for row in review['occurrences'] if row['id'].startswith(source+':')]
    unaffected = [row for row in review['occurrences'] if not row['id'].startswith(source+':')]
    expected_unaffected = Counter((row['key'], row['context_sha256']) for row in current if row['source'] != source)
    if Counter((row['key'], row['context_sha256']) for row in unaffected) != expected_unaffected:
        raise RuntimeError('An unrelated citation changed; separate review required')
    if {row["key"] for row in additions} != {
            "aspic2010", "carneades2007", "stipula2021", "stipulakey2025",
            "treeofthoughts2023", "lats2024"} or len(additions) != 6:
        raise RuntimeError("the expected six M06:26 citations were not the only additions")

    reading = json.loads(READING.read_text())["sources"]
    archive = {row["key"]: row for row in json.loads(ARCHIVE.read_text())["sources"]}
    scopes = {
        "aspic2010": "PDF pp. 4–9, Definitions 3.1–3.16: premise, strict/defeasible rule, undermining, rebuttal and undercutting distinctions.",
        "carneades2007": "PDF pp. 6–8 and 15–19, Definitions 5–10: ordinary premises, assumptions, exceptions, acceptability and proof standards.",
        "stipula2021": "Sections 2–5; PDF pp. 4–9 and 11–14: parties, assets, transitions, timed observations and behavioral equivalence.",
        "stipulakey2025": "Sections 3–4 and appendices A–B; PDF pp. 7, 9–10, 12–14, 16, 21 and 31–32, including the Java/JML/KeY translation limits.",
        "treeofthoughts2023": "PDF pp. 3–6 and appendices A–B; official breadth-first implementation and its bounded candidate selection.",
        "lats2024": "PDF pp. 4–6 and appendix A–D; UCT, feedback, rollback and the official MCTS implementation.",
    }
    judgments = {
        "aspic2010": "The cited definitions support the distinction between attacks on premises, conclusions and inference applicability. The local graph retains these as reasons, while the unresolved priority remains a local interpretation question.",
        "carneades2007": "The cited premise and exception definitions support recording ordinary premises, assumptions and exceptions separately. The book does not import a proof standard as a bank legal burden.",
        "stipula2021": "The cited language sections support explicit parties, state transitions, resources and behavioral equivalence as a possible formal backend. They do not establish faithful translation from an SFC paragraph.",
        "stipulakey2025": "The cited experiment supports studying a Java/JML/KeY backend for event-heavy duties. Reported verification remains conditional on the actual source files and replay; it is not evidence of English fidelity.",
        "treeofthoughts2023": "The cited search design supports separating generation, evaluation and bounded breadth. Its heuristic values do not establish legal completeness or correctness.",
        "lats2024": "The cited search design supports environment feedback and UCT-style scheduling when states are reversible. It is a prioritization method, not an oracle for legal meaning.",
    }
    new_reviews = []
    numeric_groups = []
    for row in review["occurrences"]:
        try:
            numeric_groups.append(int(row.get("review_group", 0)))
        except (TypeError, ValueError):
            continue
    group = max(numeric_groups, default=0) + 1
    for row in additions:
        key = row["key"]
        if not reading.get(key) or not reading[key].get("quotes"):
            raise RuntimeError("missing retained reading record: " + key)
        decision = {
            "id": row["id"], "key": key,
            "context_sha256": context_digest(row["context_tex"]),
            "source_sha256": archive[key]["sha256"],
            "reading_record_sha256": record_digest(reading[key]),
            "review_group": group, "decision": "supported_in_stated_scope",
            "judgment": judgments[key],
            "migration": "new M06:26 citation; author reviewed against the retained reading scope and quotation",
            "review_scope": scopes[key],
        }
        new_reviews.append(decision)
    history_path = ROOT / 'docs/implementation/proof-carrying-assurance/citation-review-history.json'
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    if previous and previous != new_reviews:
        history.append({'previous_records': previous, 'reason': 'M06:26 executed-evidence repair; source claims retain the reviewed scopes'})
        history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False)+'\n')
    review["occurrences"] = unaffected + new_reviews
    review["m06_26_addition"] = {
        "status": "AUTHOR_REVIEWED",
        "new_occurrences": [row["id"] for row in additions],
        "basis": "Exact source/context hashes and retained reading records; not independent legal adjudication",
    }
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")
    output = {
        "status": "PASS", "new_occurrences": [row["id"] for row in additions],
        "count": len(new_reviews),
        "review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
        "independent_legal_review": False,
    }
    (ROOT / "docs/implementation/proof-carrying-assurance/citation-review-repair.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
