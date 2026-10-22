"""Retain the reviewed one-admission source-hash repair; no budget reset."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, write

authority = Authority(ROOT)
old = authority.spec()[0]
if old["revision"] != 1:
    raise ValueError("Revision preparation is one-time")
new = deepcopy(old)
new["revision"] = 2
new["budgets"]["native-cohort"]["maximum_new_attempts"] = 3
attempts = [e["attempt"] for e in authority.events() if e["kind"] == "ADMIT" and e["budget_key"] == "native-cohort"]
if len(attempts) != 2:
    raise ValueError("Expected both retained attempted admissions")
review = {"baseline": digest(old), "changes": "Correct original UTF-8 byte-hash convention; one additional bounded admission",
          "skeptical_audit": "Located serialization mismatch; original P1 and graph identities already passed. Preserve failed attempts and all source/acceptance criteria.",
          "evidence_contract": "Exact retained bytes, P1 identities and complete critical spans; no promotion of missing source families or legal acceptance",
          "scope_unchanged": True, "budget_unchanged": False,
          "review_note": "docs/implementation/prospectus-execution-authority/COHORT-HASH-REVIEW.md",
          "review_note_sha256": file_hash(authority.base / "COHORT-HASH-REVIEW.md"),
          "budget_revision": {"budget_key": "native-cohort", "previous_maximum": 2, "new_maximum": 3,
              "retained_attempts": attempts, "reason": "New worker hashed JSON string rather than original UTF-8 bytes",
              "next_discriminating_check": "Reconstruct source cohort with original byte hash and source bindings, then its downstream interface consumer",
              "stop_condition": "One 120-second admission; on failure continue independent source work without another extension",
              "same_scope_authorization": "User authorized review and execution of this local plan; no new external action, install or substantive scope"}}
write(authority.base / "proposals/0002.json", new, exclusive=True)
write(authority.base / "reviews/0002.json", review, exclusive=True)
print("Reviewed proposal 002 retained; cumulative prior admissions preserved")
