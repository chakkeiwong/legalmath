# Reviewed disposition reading repair

The ordinary assembled reading now follows reviewed occurrence roles. Moving
an occurrence to HEADER, INSTRUCTION or EXAMPLE removes it from the reading;
moving it to OPERATIVE or UNKNOWN adds it in selected order. Raw text, source
maps and the caller-owned assembly remain intact. The final focused consumer
suite passes 23 tests, including custom-reading boundaries, and the actual
retained BES footer replay passes.

BASF v1 gives `continuous_text` a different meaning: it is the separately
constructed Option-I candidate, while the unit ledger also retains other raw
source evidence. A supplied role review preserves that candidate. Unsupported
membership changes in a custom v2 reading reject until an explicit reading
map exists. This repair does not implement editing of the BASF candidate.

## Failures retained and attribution

| Attempt | Observed result | Cause and response |
| --- | --- | --- |
| Initial five public-service regressions | Five fail, prior test passes | Stale derived reading after supplied role change |
| First post-edit run | Same five fail | Shared editable venv imported main; INVALID for worktree fix; main module bytes equal retained pre-edit module |
| Pinned worktree consumer suite | 16 pass | Ordinary reading defect repaired |
| Focused BES probe attempt 1 | Stops before consuming source | Harness expected PASS instead of phase-specific REVIEW_PREPARATION_PASS; exact enum corrected, original failure retained |
| Focused BES probe attempt 2 | PASS; 231 OCR units retained, 230 UNKNOWN | Reproduces old footer mismatch and repaired equality with initial HEADER disposition |
| R4 attempt-019 | 384 pass, seven fail | First repair wrongly replaced BASF candidate with all readable raw ledger units |
| Strict intermediate BASF probe | 16 pass, 38 setup errors | Rejecting every custom reading-membership change also blocked actual supplied BASF notice/agent roles |
| BASF compatibility probe | 54 pass | Preserve the separately constructed v1 candidate |
| New cheap compatibility controls | Two initial failures, retained | A coincidentally equal v1 reading still needs preservation; one fixture was not actually custom |
| Final focused consumer suite | 23 pass | Both role directions, selected order, raw provenance, v1 preservation and custom-v2 rejection checked |
| Final footer replay | PASS | Final module reproduces direct HEADER reading on retained real OCR occurrences |

These are our implementation, harness and environment mistakes. They do not
show a fundamental failure of Tesseract, PyMuPDF, Docling or another package.
All current R0–R8 engineering receipts now PASS, verified together in
`final-current-status.json`. R4 has 398 passes. The first coordinator's
`final-ladder/result.json` remains incomplete: R8 tests passed but attribution
could not import `scripts` because repository root was absent from that nested
coordinator's path. A module-entry recovery then correctly rejected the old
`admissions.py` attribution hash. The four affected attribution entries were
reviewed against final code/results, the old review retained, and preflight
and new R8/022 passed. Both invalid R8 attempts remain sealed. No prior result
is relabeled as evidence for the final code.

## Source-scope findings and next work

`SOURCE-SCOPE-TRACE.md` identifies actual P1, P2, disposition, clause and
dependency paths. The four new English report pages have 230 UNKNOWN OCR
occurrences and one reviewed footer. Construction roles do not represent the
difference between an Audit Committee report, sustainability limited assurance
and a financial audit opinion. P1 layout projection is also not automatically
a P2 selected reading. The next repair needs a separate source-report contract
and actual downstream consumer, retaining subject, criteria, assurance level,
addressee, reliance limits and translation priority as exact source facts.

The Portuguese 2010 original has now been acquired and its actual P1 consumer
and supplied-region reading verified; see
`../bes-original-acquisition/portuguese-2010/RESULT.md`. This closes the missing
local Portuguese source for that two-page comparison. It does not establish
issuer-edition authentication, first publication or historical availability.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Repair ordinary reading refresh | Final focused tests, actual BES footer and current R0–R8 PASS | Raw/provenance/stale-input checks preserved | Generalization beyond tested consumers | Separate source-report contract and downstream consumer | Legal correctness |
| Preserve BASF v1 candidate | 54 real targeted checks PASS; final focused boundaries PASS | Custom v2 changes without map reject | General custom reading editor absent | Keep candidate contract explicit | All reading formats unified |
| Retain report evidence as conditional | Source/images and spans retained | No authenticity/date promotion | Full report-scope consumer absent | Review exact contract and test mixed report types | Independent acceptance |

Post-run red-team: the strongest alternative explanation for a green local
test was loading the wrong checkout; import paths are now explicit. The first
broader failure also exposed an unexamined assumption about the field's meaning
across assembly versions. The final behavior states that distinction explicitly.
An untested consumer using custom v2 text remains a limitation; it will reject a
membership change rather than silently alter a constructed reading.
