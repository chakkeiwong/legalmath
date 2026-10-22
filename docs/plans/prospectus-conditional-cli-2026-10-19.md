# Make verified conditional profiles available through the installed CLI

## Reproduced gap and objective

The ordinary consume function accepts explicit default,majority,amount,duration,
cutoff,payment,rating and voting profiles. Its installed tests call that Python
function directly. Inspection of service.configure/dispatch and assess on
2026-10-19 shows that neither CLI route forwards profiles. Therefore direct
Python integration does not establish user-facing CLI integration. This is a
local product-route gap,not a defect in the financial or legal packages.

Make an explicit hash-bound profile manifest available to the installed consume
CLI. Preserve the fresh assess route: its products differ from frozen profiles,
so accepting such a profile there would require a separate preparation protocol.
Do not silently claim that new request intake is automatically covered.

## Candidate and assumptions

Add optional --conditional-profiles and --conditional-profiles-sha256 to consume
only. Require both together. The manifest has a version and a finite list of
named profiles. Each row carries a supported name,repository-relative path,
file SHA256 and semantic profile SHA256. Reject unknown or duplicate names,
missing hashes,malformed JSON,path escape,file drift and semantic drift. Resolve
paths through existing bound_path. Dispatch passes verified profiles and pins
to the existing consume kwargs in established order. Per-profile source and
complete preceding-answer checks remain authoritative; the loader does not
rewrite or manufacture those hashes to make incompatible profiles fit.

Support existing comparative/default_f/majority/amount/duration/cutoff/payment/
rating/votes names. No manifest means existing behavior. Explicit empty manifests
refuse. A manifest is user-supplied conditional analysis,not a source of facts.
Keep actual-event refusal and existing question statuses unchanged.

## Evidence contract and skeptical audit

Baseline: completed attempt051 full answer and prior CLI without profile options.
Primary: actual installed CLI output with the bound manifest equals the complete
Python-produced baseline answer;no-profile CLI remains unchanged. Validate exact
arg routing and pinned file/semantic identities with focused tests. Actual CLI
controls must refuse changed manifest/file/profile,unknown names and escaping
paths. A successful argparse or mocked dispatch test alone is insufficient.

Promotion vetoes: unpinned profile,changed baseline,unexpected answer delta,
incompatible profile accepted,missing old CLI route or noninstalled imports.
Continuation vetoes: source corruption,missing baseline,exhausted reviewed bounds
or broken verification. No actual legal conclusion,automatic profile generation,
fresh-request profile support or whole-build completion follows. Runtime and
counts are explanatory. This is deterministic interface verification.

Skeptical audit PASS for consume-only scope. Binding profiles to a fresh answer
without first knowing its products and prior-answer digest is circular; silently
rebinding would destroy the provenance check. Thus fresh assess is explicitly
excluded from this candidate. Existing complete-answer pins detect omitted or
reordered predecessors. No controller rewrite,network,external adviser or extra
package install is needed beyond the local offline wheel verification.

## Sequence and bounds

Finish and seal051 before preparing this revision. Retain its actual costs,
failure050,and all59obligations/44tasks. Reproduce missing CLI options with a
bounded parser diagnostic;freeze candidate,manifest,tests and comparison plan;
review same-task authority refinement;check/status/admit;install;focused tests;
ordinary CLI;adverse CLI;offline wheel and installed CLI;seal;record;refresh.

Measured051 costs are8886.079seconds and1093217592bytes. The actual CLI takes
stored JSON products totaling162972303bytes,and its complete answer is27363016
bytes. Retaining products,ordinary/plain/installed output,package and revision
snapshots exceeds the old1152MiB bound. Explicitly revise cumulative026 storage
to1536MiB including4MiB reserve,and time9600 to10800seconds for three complete
consumer comparisons plus checks. Forecast<=850additional measured seconds and
<=400MiB. Preserve every prior cost and unknown manual time. Admission51 to52.
Never reset the count by renaming the phase. Any forecast miss requires a
reviewed change before further work,not silent expansion.
Stage<=210seconds,child<=195seconds,one-second command yield and session polling.
No new GETs. Return to source-specific statutory eligibility and broader original
coverage after this real integration blocker is resolved.
