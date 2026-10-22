# Conditional entitlement accounting

The entitlement task traces how declared holding flags reach coupon transfers.
The current kernel accepts explicitly hypothetical entitled True/False values;
it does not determine entitlement from sale, clearing, record or ex-coupon
rules. It groups eligible accounts by legal holder. Ineligible input accounts
then disappear from the final calculation explanation. That is a reporting gap:
an empty transfer list cannot show whether no account was declared entitled or
an account was dropped. The sealed P5 input remains available but the returned
answer should expose the distinction directly.

Add declared holdings and event-scope accounting to the calculation explanation,
with explicit flags that legal entitlement, transfer effects and note form have
not been inferred. Preserve all existing calculations. Use the just-retained
Shell conditional scenarios with exact PDF identities. Compare the same positive
scenario against its pre-change answer and test no entitled holder, split
accounts for one holder, distinct holders, missing/unknown flags, duplicate
accounts, negative principal, missing required record event and wrong chronology.
The source-dependent global/definitive distinction remains in the accompanying
source review, not guessed by this kernel. Splitting a hypothetical global
recipient is an engineering counterexample, not a claim about real global-note
ownership or allocation.

Primary criterion is unchanged positive amount/event/source evidence and exact
input-account reconciliation; all excluded accounts must remain inspectable.
Adverse premise cases must return typed UNSUPPORTED with the specific cause.
Explicit record/ex-coupon inputs must never infer or override an entitlement
flag. A zero transfer total under all-False flags is a conditional calculation,
not proof that nobody has a legal entitlement.

Assumptions audit: holder grouping and PER_LEGAL_HOLDER rounding are inherited
engineering behavior, not a reviewed universal entitlement rule. Typed Boolean
flags and HYPOTHETICAL scope are intentional constraints. Missing actual
register, sale, settlement, presentation or event records prevents a real
entitlement conclusion but does not veto these conditional controls. No live
bank or clearing operations, fabricated facts or external messages are needed.

Skeptical audit PASS: do not promote event ordering to legal entitlement, and do
not treat a source citation as proof of an assumed balance. Source corruption,
lost accounts, changed positive payment or hidden promotion veto the run.
Independent source/form interpretation and actual client events remain
promotion blockers. Compare the current contract, not historical method hashes
after a legitimate later change; preserve prior manifests untouched.

CPU-only, imports pinned to this worktree, at most 120 seconds per command,
one-second yields and 20 MB evidence. Run focused finance regression checks and
actual source consumer comparisons, retain commands/environment/method/source
identities and results, then record/refresh and continue ready work.
