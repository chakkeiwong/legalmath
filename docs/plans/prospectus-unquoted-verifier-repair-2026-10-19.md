# Repair the unquoted-definition verifier before promotion

Attempt088 found the seven frozen naming events and preserved the complete
attempt087 answer. Its 128 targeted tests passed. The controls stage then failed:
the `drop-scope` mutation produced `TypeError` when the independent oracle indexed
`None`. The failure is in our verification harness. It neither invalidates the
retained ordinary execution nor establishes that all adverse controls passed.
Retain the attempt as failed; do not edit its frozen methods or retry its stage.

## Evidence contract and reviewed repair

Question: can a corrected verifier explicitly refuse incomplete or malformed
definition reports while accepting the unchanged, independently frozen source
readings? Comparator: the exact attempt088 ordinary answer, attempt087 prior
answer, original seven source expectations and the unchanged production files.
Primary criteria are explicit assertion failures for all twelve original
mutations, additional missing/wrong-type span controls, exact source verification
of the retained ordinary answer, and complete equality with a fresh installed
consumer. An unexpected exception is a harness failure, never a successful
refusal. No broad exception catch may turn a crash into an accepted control.

Add explicit dictionary/key checks before the original oracle dereferences each
required report/span. Keep the original verifier immutable and run its exact
source and prior-answer comparisons after these checks. Verify the profile
identity too. Regression tests must reproduce missing scope and exercise missing
term/value/condition/source projection and malformed rows, including a valid
control. The retained seven-source oracle remains the expectation; neither the
production recognizer nor its output generates replacement expectations.

Production and all inputs stay byte-identical. Reuse the retained ordinary CLI
execution only after checking its frozen input, method and output identities;
label this reuse explicitly. Build a new local wheel and run the actual installed
CLI in isolation. This distinguishes verifier repair from a candidate change and
avoids an unchanged expensive ordinary rerun. Counts and runtime explain the run;
they do not establish legal correctness or general recall. Source disagreement,
changed prior answers, altered production, accepted tampering, a verifier crash,
or imports outside the installed tree veto this result. Corrupt retained evidence,
frozen-method drift and the cumulative resource bounds veto this attempt.

Defaults audit: the original seven readings remain the reviewed baseline; field
shape checks are an engineering hypothesis tested with malformed reports. The
old oracle remains a substantive source check, not a total schema validator.
The twelve original mutations retain their meanings. Additional malformed-value
cases check failure handling rather than legal coverage. CPU-only execution and
no network are sufficient because this repair changes no external package.

Skeptical audit PASS: merely catching `TypeError` would disguise a broken harness;
explicit preconditions plus tests requiring `AssertionError` address the actual
failure. Reusing an ordinary answer would be misleading after any source or
production change, so every prior binding and production digest is checked.
Installed equality remains required. A repaired test harness does not close the
original reference task, the seven broader gap classes, or the whole build.

## Execution and continuation

Retain failed attempt088 and its actual commands, costs and outputs. Review
revision350 under the same original task and retain all88 prior admissions.
Keep the cumulative24000 accounted seconds and3584MiB including4MiB reserve;
forecast650seconds/96MiB and refuse preparation if it does not fit. Older
unmeasured authoring time remains UNKNOWN. No resource or obligation resets.

Run check, status, admit, tests, verify-retained, controls, package, installed,
seal, record and refresh. One-second tool yields, small outputs and polling of
the same session remain required. No subagents, network, GPU, commits or pushes.

After repair, return to substantive reference/definition work: reconcile the two
source-discovered amount declarations and their printed paragraph restrictions
with discovered uses and structural destinations, checking against the existing
reviewed binding matrix. The broad capital-reference use must remain unresolved;
the declaration heading must not become an operative use. Review that next
continuation before implementation. Real holdings and reader acceptance follow
the general build; external opinions are not prerequisites. ACTUS availability
limits its own trial, and CDM receiver/portability remain deferred.
