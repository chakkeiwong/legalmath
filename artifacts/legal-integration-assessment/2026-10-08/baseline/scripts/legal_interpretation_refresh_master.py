"""Refresh the current program from verified revision-2 bytes without rewriting historical receipts."""
from pathlib import Path
import json
from scripts.legal_interpretation_s2_prepare import ROOT, DOC, sha, ref
MASTER = "docs/plans/legal-interpretation-master-program.md"
def main():
    archive=DOC/"revisions/revision-2"
    record=json.loads((DOC/"revision-2-archive.json").read_text())
    for row in record["files"]:
        if sha(ROOT/row["retained_path"]) != row["sha256"]: raise ValueError("Corrupt revision-2 archive")
    old=(archive/MASTER).read_text()
    replacements=[
    ("""Revision 2 — 6 October 2026. Status: **amended implementation specification;
product phases not executed**. Claude reviewed revision 1 and cleared P0/P1 for
bounded implementation, with blocking plan changes before P2, P6 and P8.
This revision incorporates those changes; it has not been re-reviewed by Claude.
See the [finding dispositions](../implementation/legal-interpretation-program/claude-review-response.md)
and [revision audit](../implementation/legal-interpretation-program/revision-2-audit.md).""",
    """Revision 3 — 6 October 2026. **Current execution specification.** P0–P8 and
S1 have executed with qualifications; S2 continues the authority and standards
investigation. Execution state and the next reviewed phase are selected by
[program-current.json](../implementation/legal-interpretation-program/program-current.json).
Phase completion records engineering work, not closure of the legal questions.

Claude's revision-1 review and the revision-2 response remain historical.
Revision 3 has a local skeptical audit; no new Claude review is claimed.
All 46 original substantive obligations remain OPEN_QUALIFIED. Legal correctness,
English fidelity and unrestricted future generalization remain NOT_ESTABLISHED.

Run `python3 -m scripts.run_legal_interpretation_master status` to inspect the
current program, `resume` to execute the implemented current phase, and `verify`
to check its selected receipt. The fixed runner uses no model providers.

Revision 2 and its validation files are preserved under
`docs/implementation/legal-interpretation-program/revisions/revision-2/`;
[the archive index](../implementation/legal-interpretation-program/revision-2-archive.json)
binds all 19 files. Do not regenerate historical revision-2 receipts against this
updated specification."""),
    ("through a planned `clauses.propose(...)`","through the implemented `clauses.propose(...)`"),
    ("""All following paths under `src/legalmath/interpretation/semantics/` and
`tests/interpretation/semantics/` are **planned new files**, not existing code.
The existing `assurance/semantics.py` remains a separate module.

| Planned module | Responsibility | Existing integration point |""",
    """The P0–P8 modules below now exist under
`src/legalmath/interpretation/semantics/` with corresponding tests.
S1 adds lossless `reconciliation.py` and `sourced.py` and a version-2 context
for actual investigation. S2 adds a conditional standards evaluator with distinct
source assertions, interpretive premises and scoped factual evidence.
The existing `assurance/semantics.py` remains a separate module.

| Module | Responsibility | Integration point |"""),
    ("""The [individual phase plans](legal-interpretation-program/README.md) give
implementation actions, inputs, expected interfaces, test commands, acceptance,
repair and continuation conditions. These are work instructions for an executor,
not evidence that any phase has run.""",
    """The [individual phase plans](legal-interpretation-program/README.md) retain
the original implementation instructions. Their completed execution is bound by
`artifacts/legal-interpretation-program/2026-10-06-offline-v1/completion-2.json`
(SHA256 `00787202085da9ee4942a34bf87252a9be5192fe1333075b843edede74bb788d`).
S1 is bound by `artifacts/legal-interpretation-program/successor-s1/attempt-2/result.json`
(SHA256 `75b6cfd2f361b7e28ebdac0cd742876831a2b5d5314ba82dc5328432b8993cdd`).

S1 passed 179 checks, preserved 35 readings and 70 role records, and bound
1,400 source-related claims. Three historical formulas ran six Java cases;
32 readings remained unformalized. Its actual CompleteInvestigation fixture
carried two semantic branches through four Java cases with typed objections.
These are development results; none establishes the source-to-rule interpretation.

### Successor phases

| Phase | Concrete work and required result | Current dependency |
|---|---|---|
| S1 | Individual reconciliation and source-bound argument structure; executed with qualifications. | P0–P8 completion-2 |
| S2 | Individually account for all 46 obligations; inspect official provisions, investigate obtainable judgments, and execute conditional standards with explicit missing premises. | S1 attempt-2; [reviewed S2 plan](legal-interpretation-program/S2-authority-and-standards.md) |
| S3 | Connect scoped observations and conditional standards through actual investigation; retain competing attachment readings and establish, or qualify, every sufficiency premise. | Verified S2 result and its refreshed next-phase plan |
| S4 | Extend supported theories and lowering, then independently check the declared semantics profile and serialization/runtime correspondence. | S3; retained unsupported branches and resource bounds |
| S5 | Freeze a new method and source window after development repairs; retain genuinely later official publications including unsupported and unfinished cases. | Stable S4 method; actual future source availability |

The current pointer distinguishes completed work from the next phase. Later phases
require refreshed audited plans; a title or successful unit test cannot select or
complete them. Larger recursive theories, source-to-rule sufficiency and future
observations are separate unresolved questions, not implied by S1's finite cases."""),
    ("""This revision uses zero new model/provider calls; Claude's supplied review is
separate retained input. The documentation task grants no provider allowance.
P0–P3's core development and synthetic checks require no live model or GPU. P4 first uses retained official
sources; missing judgments are acquired through a named, bounded official source
request. No crawling budget or new model allowance is granted by this plan.""",
    """This revision uses zero new model/provider calls. S2's reviewed acquisition
scope permits at most 24 public HTTP attempts, 12 MB per response, 30 seconds per
request and three redirects. Every attempted URL, query and failure is retained.
Official sources and an explicitly documented court-linked mirror are identified
separately; retrieval establishes neither authority nor source-to-rule sufficiency.
No dependency installation, GPU work, private data acquisition or model grant is
part of the fixed master runner."""),
    ("""- Verify this revised document package with
  `python3 -m scripts.check_legal_interpretation_revision`.
  This fixed local check does not execute phases or dispatch providers.""",
    """- Use `python3 -m scripts.run_legal_interpretation_master status|resume|verify`
  (one literal action per invocation) for current execution.
  `scripts.check_legal_interpretation_revision` is a historical revision-2
  generator: do not rerun it against the refreshed live files."""),
    ("""The program is an implementation specification with a machine-readable phase
manifest. It does not claim a new autonomous runner exists. Build and test the
product route in P6 using the existing complete investigator; add a narrow offline
CLI only if an actual integration need remains, and document it before use.""",
    """The master runner verifies historical identities, executes its fixed S2
implementation, preserves immutable attempts, verifies observed results and
publishes a refreshed next-phase plan before advancing the current pointer.
It never dispatches a provider or accepts arbitrary shell text. `resume` verifies
an already selected S2 result rather than silently repeating it. Unimplemented
later phases remain explicit work requiring their reviewed implementation.

The legacy phase manifest and operations wrapper retain revision-2 planning
labels for historical compatibility. Current phase status comes from the new
master pointer and runner, not those old labels."""),
    ("""maps F01–F12 to the amended plans, required implementation checks and outstanding
manuscript errata. P0/P1 can begin after their normal input preflight; P2/P6/P8
must implement and pass the added obligations before phase acceptance. No product
phase has run, and no new Claude approval is inferred.""",
    """maps F01–F12 to the amended plans, required implementation checks and outstanding
manuscript errata. The P0–P8 and S1 receipts preserve their execution results.
Their immutable outputs remain historical when later product code changes;
historical integrity is distinct from current-method reproducibility.
The [revision-3 audit](../implementation/legal-interpretation-program/revision-3-audit.md)
records the current plan audit and remaining limitations.""")]
    new=old
    for before,after in replacements:
        if new.count(before)!=1: raise ValueError("Refresh target mismatch: "+before[:90])
        new=new.replace(before,after)
    p=ROOT/MASTER
    if p.read_text() not in (old,new): raise ValueError("Unrelated master edits")
    p.write_text(new)
    indexes={
    "docs/plans/legal-interpretation-program/README.md":"""# Legal interpretation phase plans

The governing specification is [master revision 3](../legal-interpretation-master-program.md).
Inspect current execution with `python3 -m scripts.run_legal_interpretation_master status`.
The [current pointer](../../implementation/legal-interpretation-program/program-current.json)
selects the verified completed evidence and next reviewed phase.

P0–P8 executed under revision 2; their individual plans remain historical work
instructions. S1 executed individual reconciliation and sourced arguments with
qualifications. All 46 substantive obligations remain open.

Current bounded phase: [S2 authority and standards](S2-authority-and-standards.md).
Its verified result refreshes S3 before the next implementation begins.
Later work covers evidence-to-rule sufficiency and actual-route integration,
larger theories and runtime correspondence, and genuinely later source observation.

Run `python3 -m scripts.run_legal_interpretation_master resume` for the implemented
current phase and `python3 -m scripts.run_legal_interpretation_master verify` for
its selected result. These fixed operations make no provider calls.
""",
    "docs/implementation/legal-interpretation-program/README.md":"""# Legal interpretation execution

The [master program, revision 3](../../plans/legal-interpretation-master-program.md)
governs current work. [program-current.json](program-current.json) selects its
execution state. Use `python3 -m scripts.run_legal_interpretation_master status`,
`resume` or `verify` from the repository root.

P0–P8 completion-2 and S1 attempt-2 are historical qualified engineering results.
S2 investigates source authority and missing premises and adds executable
conditional standards. It does not reinterpret the 46 open obligations as closed.

The original Claude review, its response, and revision-1/revision-2 manifests
remain historical. [revision-2-archive.json](revision-2-archive.json) binds the
exact prior master, phase index, review and validation files. Do not rerun the
revision-2 manifest generator against live revision-3 files. The old phase
manifest and operations `status` retain historical planning labels.

The current runner retains source requests, immutable attempts, method identities,
checks, decisions and a refreshed next-phase plan. It preserves earlier source
packets and readings. No model-call allowance or new external action is inferred.
"""}
    for path,content in indexes.items():
        original=(archive/path).read_text();dest=ROOT/path
        if dest.read_text() not in (original,content):raise ValueError("Unrelated index edits")
        dest.write_text(content)
    print(json.dumps({"revision":3,"master":ref(p),"indexes":[ref(ROOT/v) for v in indexes]}))
if __name__=="__main__": main()
