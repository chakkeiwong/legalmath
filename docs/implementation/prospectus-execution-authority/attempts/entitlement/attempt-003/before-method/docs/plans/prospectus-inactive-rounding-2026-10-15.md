# Validate coupon conventions before entitlement filtering

## Question and retained scope

Can the admitted fixed-coupon consumers reject invalid declared rounding
conventions even when every supplied holding is excluded, while preserving
valid complete answers? This continues the original `entitlement` task and
G14, G15, E03 and RESIDUAL-04. Attempts 001 and 002 remain sealed. The proposed
third admission is an explicit cumulative extension from two to three, not a
retry or a reset of either earlier attempt.

Code tracing found that v1/v2 `PER_LEGAL_HOLDER` calls `rounded` only while
building transfers. No entitled holders means no call. `PER_CALCULATION_AMOUNT`
and v3 initial amounts already execute rounding before filtering. This is a
local validation hypothesis until the admitted pre-edit consumers reproduce it.
Also inspect the rounding parser's exact-rational refusal: a zero denominator
must yield the existing invalid-premise boundary, not an uncaught arithmetic
exception. No package, external service or legal construction is under test.

## Evidence contract and intent ledger

Baseline: snapshot current worktree methods, replay the sealed Danske
finance003 direct and selected v1 products, and retain pre-edit excluded-holder
answers and matched invalid/active controls. Replay Shell finance002 v3 global
and definitive direct/selected products unchanged. Use the retained Shell v2
scenario for a separately labelled hypothetical per-holder control. No source
extraction, OCR, document rendering, independent reading or new real client fact
is claimed.

Primary pass criteria: (1) valid P5 products and complete Q1-Q6 final answers
are exactly equal before and after, including valid empty transfers, excluded
accounts, evidence and conditional qualifications; (2) finite invalid rounding
inputs are refused regardless of entitlement; (3) direct consumers return
UNSUPPORTED and selected consumers raise ValueError at their existing boundary;
(4) the original v2/v3 controls and registered finance regressions pass. A test
count alone cannot establish any of these claims.

Repair triggers and promotion vetoes: an accepted invalid convention, leaked
numeric exception, changed valid amount/answer, lost source or excluded-account
explanation, or failed downstream comparison. One diagnosed changed repair is
allowed; retain its failure and never repeat an unchanged stage. Continuation
vetoes for this package: source/comparator corruption, missing required input,
unexplained method drift or exhausted stage/time/storage bounds. Test totals,
wall times and compression sizes are explanatory diagnostics only.

Passing establishes finite engineering validation, not actual entitlement,
settlement, legal correctness of supplied conventions, package completeness or
whole-program completion. Conditional source analysis remains possible without
client facts; actual clearing, account and event conclusions remain open.
Retain evidence under `attempts/entitlement/attempt-003/`, with the command and
environment manifest, before/after methods, source bindings, actual P5/answers,
adverse results, test XML, comparison, RESULT and NEXT-WORK notes.

## Skeptical audit and material assumptions

The initial idea of freezing every P1-P4 payload for all selected controls was
wrong: selected rounding lives in admitted P3 terms, not calculation premises.
For changed selected controls, reuse the original graph and assembled P2
payload, reseal P1 with the explicit counterfactual request, recompute selected
term admission and P3, and construct P4 consistently. Verify that source graph,
assembly and all non-rounding terms remain equal. This exercises the real P5
and final consumer without pretending that changed P3 is frozen. Unchanged
positive replays reuse the original P1-P4 explicitly.

The inherited exact quantity representation is a reviewed compatibility
requirement: integers and exact decimal/rational strings remain valid; Boolean
and float quantities remain invalid. Inspect its parser earliest with inactive
and active malformed controls, including a zero denominator. Do not broaden
numeric representations or invent a rounding default. HALF_UP and DOWN are
the existing supported rules; explicit positive quanta are required. Test both
rules with active and inactive holdings. A zero-valued validation call, if used,
is an algebraic domain check and must not create a payment or mutate the input.

Danske VP and Shell form, principal, calendar and entitlement premises remain
hypothetical. Printed definitive-note amounts do not establish VP payments.
Synthetic v1/v2 selected tests establish software branch coverage only. The
source-bound actual consumer controls remain the primary target. Cross-version
agreement is no independent legal oracle. No stochastic ranking is involved.

Skeptical audit: PASS after correcting the selected-term baseline and stating
the parser/refusal boundary, exact comparators and nonclaims. No unexamined new
financial default, installation, model call, GPU or network action is required.

## Executable sequence and cumulative bounds

1. Review and admit revision 103 under the same task and preserved history.
2. Run `baseline`: retain actual pre-edit reproductions and valid comparators.
   If the proposed gap does not reproduce, record that outcome and do not patch.
3. Validate the declared rounding domain before entitlement filtering; normalize
   malformed rounding parameters to ValueError without changing valid arithmetic.
   Add regression coverage for inactive/active v1/v2/v3 and both aggregations.
4. Run `candidate`, `adverse-direct`, `adverse-selected`, `legacy`, `tests`, and
   `verify` once each. Preserve complete actual answers for primary comparisons;
   do not substitute an isolated helper's result for downstream evidence.
5. Seal with a task-local evidence validator, record and refresh the authority;
   inspect and act on independent remaining routes in the same execution turn.

Exact command template from this worktree:
`timeout 120 .venv/bin/python docs/implementation/prospectus-execution-authority/attempts/entitlement/attempt-003/run_rounding.py <stage>`.
Use this worktree's src imports, CPU only with CUDA_VISIBLE_DEVICES=-1 before
imports, one-second tool yields and poll every returned session to completion.
Seven stages, at most 120 seconds each, one test invocation, at most 40 MB new
retained evidence, no unchanged rerun. At most one understood changed repair
uses a distinct explicitly recorded stage; no deadline or admission reset.
