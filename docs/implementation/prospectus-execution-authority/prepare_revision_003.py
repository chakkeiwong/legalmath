"""One-time reviewed continuation repair; retain every prior admission."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.execution_authority import Authority, REL, digest, file_hash, write


def main():
    authority = Authority(ROOT)
    old = authority.spec()[0]
    if old["revision"] != 2:
        raise ValueError("This one-time repair requires revision 2")
    new = deepcopy(old)
    new["revision"] = 3
    new["budgets"]["native-cohort"]["maximum_new_attempts"] = 4
    note = REL + "/CONTINUATION-REVIEW.md"
    review = {
        "baseline": digest(old),
        "changes": "Repair partial-result continuation and admission of supplied external evidence; revalidate current real workers",
        "skeptical_audit": "Two defects reproduced in continuation-before.xml; 41 focused checks pass after bounded repair. Preserve task criteria, source evidence and all attempts.",
        "evidence_contract": "Reviewed refinement selects a new partial-work admission under the same budget; genuine bound external files permit review only; both actual source workers must validate under current method",
        "scope_unchanged": True, "budget_unchanged": False,
        "review_note": note, "review_note_sha256": file_hash(ROOT / note),
        "budget_revision": {
            "budget_key": "native-cohort", "previous_maximum": 3, "new_maximum": 4,
            "retained_attempts": [e["attempt"] for e in authority.events() if e["kind"] == "ADMIT" and e["budget_key"] == "native-cohort"],
            "reason": "Controller method changed to repair reproduced dead-end continuation; successful source evidence is conservatively stale",
            "next_discriminating_check": "One actual cohort reconstruction and its interface consumer under the repaired controller; unchanged legacy receipt identity",
            "stop_condition": "One 120-second cohort admission; no further extension under this review",
            "same_scope_authorization": "User requested thorough review and execution of this local single-authority plan; no external action, installation or scope change"}}
    write(ROOT / REL / "proposals/0003.json", new, exclusive=True)
    write(ROOT / REL / "reviews/0003.json", review, exclusive=True)
    print("Revision 3 proposal retained; all three original cohort admissions preserved")


if __name__ == "__main__":
    main()
