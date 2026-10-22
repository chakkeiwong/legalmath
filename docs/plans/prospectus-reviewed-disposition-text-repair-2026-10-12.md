# Reviewed disposition reading-text repair, 12 October 2026

## Question, baseline and trace

Does the real P2 construction product present the same selected text after a
reviewed role change as after an equivalent initial assembly disposition?
`contract_assembly.assemble` builds `continuous_text` from OPERATIVE and UNKNOWN
units. `admissions.dispositions` changes roles, unresolved units and status, but
does not rebuild that text. `service.construction_product` seals the resulting
assembly. Thus the displayed reading can disagree with the roles used by
`service.dependencies` and clause interpretation. The six existing roles do
not supply a reviewed taxonomy of annual-report types; changing UNKNOWN to
OPERATIVE cannot substitute for authenticating or interpreting those reports.

The exact comparator is an initial role supplied through `assembly.operations`
versus the same final role supplied through `reviewed_dispositions`. The real
BES footer is `bes-report-2009:p177:ocr27`; its existing image-bound HEADER
disposition provides a source-specific corroboration, not a new legal reading.

## Evidence contract and skeptical audit

Primary pass: a reviewed HEADER/INSTRUCTION/EXAMPLE disappears from continuous
reading text while remaining in raw and selected units; a reviewed OPERATIVE
or UNKNOWN unit enters reading text in selected order. Equivalent disposition
routes must agree. Raw text, provenance, unrelated selected units and the
caller-owned baseline assembly must remain unchanged. Existing stale-source,
stale-assembly and excluded-branch rejection remains mandatory.

A stale/mismatched saved source, changed oracle or failure of preservation is a
veto. Test counts/runtime explain engineering execution only. Neither passing
synthetic tests nor the retained footer case establishes legal correctness,
broader page coverage, report authenticity, independent acceptance or a new
report role. No package comparison or default OCR change is proposed.

Audit PASS for the bounded reproducer and conditional repair: the baseline is
the actual public P1/P2 service path, both transition directions are checked,
and direct-versus-reviewed agreement is observable behavior. The proposed
repair rebuilds one derived string from already admitted selected units; it
does not alter legal decisions. CPU only; no model/network calls. A failed
reproducer would cancel this proposed code repair and retain the diagnosis.

## Dependency map and commands

1. Add focused service regressions and run them on the unchanged implementation.
   A reproduced mismatch is required before step 2; a clean result means stop
   this repair branch and review the trace. Retain the result either way.
2. Rebuild the derived reading after reviewed role changes, then run the focused
   checks and the complete consumer test file. Allow one bounded correction if
   this focused repair fails; preserve red and green evidence separately.
3. Verify the saved BES source/image/header bindings and compare direct versus
   reviewed disposition using actual retained source units. This depends on
   valid source evidence but can proceed independently of synthetic-test success.
   It is a focused source/assembly consumer, not a rerun of the full eleven-PDF
   legal assessment.
4. Refresh the controller and execute any invalidated engineering phases in
   dependency order with saved logs and short polling. A failed phase blocks
   its success dependants only; independent phases and bounded recovery remain
   ready. Do not rewrite the previous passing receipts.
5. After completion of steps 1–4, update the substantive gap diagnosis and reset
   documents, recording source-scope questions that still require evidence.

Use `PYTHONPATH=/home/chakwong/python/legalmath/.worktrees/bond-gap-closure/src .venv/bin/python -m pytest tests/prospectus_successor/test_closure_consumers.py`
with a focused `-k reviewed_disposition` first. Save results under
`docs/implementation/prospectus-integration-closure/reviewed-disposition-text-2026-10-12/`.
Invoke the existing `scripts/prospectus_delivery.py closure` interface after
checking its exact subcommands. All edits stay in the prospectus worktree.
Each command returns a short result or a session ID; full logs go to files.

## Environment audit correction during execution

The first red run reproduced five reading-text failures. The first post-edit
run loaded `admissions.py` from the main checkout through the shared editable
venv and is INVALID as a test of the worktree repair. The loaded main module
is byte-identical to the retained pre-edit worktree module, so its direct
stale-reading counterexample is retained. Pin the absolute worktree `src` in
PYTHONPATH for subsequent diagnostics and verify the imported path before
interpreting them. This is an environment/setup defect, not failed repair
evidence. No dependency installation or alteration of main is required.

## Bounded correction after R4 integration evidence

R4 attempt-019: 384 pass, seven fail with `BASF scalar consumer changed its
reviewed construction`. The first fix wrongly assumed every assembly's reading
was the join of all readable units. BASF v1 retains a constructed Option-I
candidate while keeping other raw units available; its reviewed UNKNOWN to
OPERATIVE changes do not change reading membership. Rebuilding unconditionally
replaced the constructed candidate with all unknown raw text. This is our
implementation mistake, not a stale historical receipt or package defect.

Use the single bounded correction allowed in step 2: preserve the exact reading
when no unit crosses the OPERATIVE/UNKNOWN membership boundary. When membership
does change, require that the baseline reading equals the original ordered
selected-unit projection before rebuilding it. Reject a membership change to
a custom constructed reading unless an explicit source-bound reading map is
available; do not guess membership from string matches. Add cheap controls for
custom-reading preservation and rejection before rerunning affected phases.
The seven original failures and first repair snapshot remain retained. This
correction changes no historical source, review, construction or result.

Skeptical revision verdict: PASS for this bounded correction. The actual BASF
reading is now an explicit comparator. Tests must show that unchanged reading
membership preserves it byte-for-byte and that unsupported changes cannot
silently leak raw excluded-option text into it. The broader source-report
interpretation and custom-projection editing interfaces remain separate work.

## Final compatibility review before the changed-input ladder

The strict intermediate rejection also blocked genuine BASF notice/agent role
admissions (retained `basf-small.xml`: 16 pass, 38 setup errors). The follow-up
BASF compatibility candidate passes all 54 notice/agent tests. Its final review
removes an incorrect `rendered-contract.v2` exception: that is an AST render
result, not an assembly. Only BASF produces `assembled-contract.v1`, whose
`continuous_text` explicitly means its constructed candidate, separately from
the full role ledger. Preserve this field for v1 role reviews. For v2, rebuild
the joined reading on membership change, rejecting an unsupported custom
reading; preserve exact text when membership does not change.

The final focused suite includes both directions, selected order, retained raw
text and caller immutability, v1 custom-reading preservation (including equality
with the ordinary join), unchanged v2 membership, and custom-v2 rejection.
Two new fixture/boundary failures are retained separately; the corrected final
23-test consumer suite passes. This is an explicit compatibility boundary, not
an automatic editor for the BASF candidate. No historical review is rewritten.

Execute one final changed-input ladder, through the existing closure controller
with a small sequential coordinator in this result directory. It refreshes the
ready set after every phase and records progress, reuses current successful
receipts, never retries a failed phase unchanged, and continues independent
ready phases. Prior R4 runtime is about 43–50 minutes; the existing 4500-second
phase timeout applies. Tool calls yield promptly while logs stay on disk. Any
further substantive failure ends this bounded repair branch with retained
evidence; it does not justify an unreviewed additional repair ladder.
