"""Rebind citation reviews after source line shifts or explicit prose repair.

The focused repetition repairs do not add or remove citation commands. This
script carries existing author decisions to new occurrence identities only
after checking source/key multiplicity. Exact context matches are carried
mechanically; the three changed Catala contexts have explicit source-grounded
author-review text below.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/monograph/review/revision"
BASELINE = ROOT / ".localresources/monograph-repetition/baseline/docs/monograph/review/revision"


def context_digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def source_key_group(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    result: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        result[(row.get("source", ""), row["key"])].append(row)
    return result


CONTEXT_REVISIONS = {
    "The literature turns that mechanism into a review question.":
        "The revised literature paragraph attributes the conflict behavior of two applicable Catala exceptions to the retained sections 3--4 reading. Its source-trace review question and the LegalMath design consequence are explicitly separated.",
    "A source-linked exception needs two things at once:":
        "The revised Catala paragraph attributes source-adjacent authoring and exception semantics to the retained sections 2--4 reading. The banking-profile question is presented as a local design consequence.",
    "Apply that distinction to the SPI explanation requirement.":
        "The revised SPI paragraph uses Catala's source-linked style as motivation and explicitly identifies missing-evidence treatment as a local banking-profile choice. The retained sections 2--4 reading supports the attribution.",
    "Write the guard explicitly rather than splitting the two conditions into":
        "The revised SPI example cites Annex 1 paragraph 10.3 for the boundary between the explanation exception and the separate offering-document duty. The retained source reading supports that legal anchor; the combined guard and missing-evidence behavior are local design choices.",
}


def main() -> None:
    inventory = json.loads((REVIEW / "inventory.json").read_text())
    current = inventory["citation_occurrences"]
    baseline_claims = json.loads((BASELINE / "citation-claims.json").read_text())["occurrences"]
    baseline_reviews = json.loads((BASELINE / "citation-occurrence-review.json").read_text())
    old_groups = source_key_group(baseline_claims)
    new_groups = source_key_group(current)

    if len(current) != len(baseline_claims):
        raise RuntimeError(f"Citation count changed: baseline {len(baseline_claims)}, current {len(current)}")
    if set(new_groups) != set(old_groups):
        missing = sorted(set(old_groups) - set(new_groups))
        added = sorted(set(new_groups) - set(old_groups))
        raise RuntimeError(f"Citation source/key groups changed; missing={len(missing)} added={len(added)}")

    old_review_by_id = {row["id"]: row for row in baseline_reviews["occurrences"]}
    if len(old_review_by_id) != len(baseline_reviews["occurrences"]):
        raise RuntimeError("Baseline citation review has duplicate identities")

    rebound = []
    changed_contexts = []
    repeated_groups = 0
    for key in sorted(new_groups):
        new_rows = sorted(new_groups[key], key=lambda row: (row["line"], row["id"]))
        old_rows = sorted(old_groups[key], key=lambda row: (row["line"], row["id"]))
        if len(new_rows) != len(old_rows):
            raise RuntimeError(f"Occurrence multiplicity changed for {key[1]} in {key[0]}")
        if len(new_rows) > 1:
            repeated_groups += 1
        # Source order is the stable identity for repeated uses of one key.
        for current_row, old_row in zip(new_rows, old_rows):
            decision = deepcopy(old_review_by_id[old_row["id"]])
            decision["id"] = current_row["id"]
            decision["key"] = current_row["key"]
            decision["context_sha256"] = context_digest(current_row["context_tex"])
            if decision["source_sha256"] != old_review_by_id[old_row["id"]]["source_sha256"]:
                raise RuntimeError(f"Unexpected source review mutation: {current_row['id']}")
            if current_row["context_tex"] != old_row["context_tex"]:
                matches = [
                    (marker, judgment)
                    for marker, judgment in CONTEXT_REVISIONS.items()
                    if marker in current_row["context_tex"]
                ]
                if len(matches) != 1:
                    raise RuntimeError(f"Unreviewed changed citation context: {current_row['id']}")
                marker, judgment = matches[0]
                decision["judgment"] = judgment
                decision["context_revision_reason"] = marker
                changed_contexts.append(current_row["id"])
            rebound.append(decision)

    rebound.sort(key=lambda row: next(i for i, item in enumerate(current) if item["id"] == row["id"]))
    result = deepcopy(baseline_reviews)
    result["occurrences"] = rebound
    result["context_migration"] = {
        "from": "protected 282-page checkpoint",
        "basis": "source path and citation key multiplicity, with source-order pairing for repeated keys",
        "baseline_occurrences": len(baseline_claims),
        "current_occurrences": len(current),
        "changed_contexts": len(changed_contexts),
        "changed_context_ids": changed_contexts,
        "repeated_context_groups_carried_by_source_order": repeated_groups,
        "independent_support_review": "retained author/executor source reading, with explicit author review for the changed Catala contexts; no independent legal adjudication",
    }
    (REVIEW / "citation-occurrence-review.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps({
        "status": "PASS",
        "occurrences": len(current),
        "changed_contexts": len(changed_contexts),
        "changed_context_ids": changed_contexts,
        "repeated_context_groups_carried_by_source_order": repeated_groups,
    }, indent=2))


if __name__ == "__main__":
    main()
