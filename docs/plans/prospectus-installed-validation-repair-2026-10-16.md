# Independently validate completed installed execution without repeating native calls

Installed010 is REJECT1137. Its final summary stage recorded115.07405699742958s
against a115s bound. The runtime returned PASS, but the strict independent
validator correctly rejected its timing. All eighteen installed commands, four
native reservations, five full replays, both source lifecycles/comparisons,
eleven profile controls, four lifecycle controls and three report attacks
completed below their limits. Twenty-eight tests passed. The23 preseal stages
took478.857641244s; unique storage was459,164,643bytes. The rejection is an
orchestration/timing defect, not an observed package or semantic failure.

The root cause is assigning the expensive whole-evidence summary the same short
deadline as a single lifecycle stage, and then using a post-context elapsed
measurement as the strict independent criterion. The Python timer did not enforce
that measurement exactly. Do not assert a more precise timing explanation that
was not instrumented. Do not alter old times, grant an old stage a retrospective
PASS, or rerun successful extraction. The old result and REJECT remain sealed.

Review one changed eleventh admission on the same native-confinement obligation,
explicitly revising the previous stop bound. The change permits only retained
validation and zero subprocess/native/network/OCR/GPU/install calls. Preserve
all ten admissions and76outer/twelve-native installed history; native-binding's
separate lower bound61 remains unchanged. No twelfth admission or automatic retry
follows. This is a new validation design, not an unchanged rerun of010.

Use five short stages: focused tests, retained-envelope, compare-fresh,
compare-retained and seal. Each has110s of work under timeout120 and a strict115s
recorded stage bound, with400s aggregate and32MiB new evidence including2MiB
failure reserve. The envelope must verify the exact retained rejection, all24
old stages and the unique timing overrun, with every actual installed/native
command still below its original limit. The two independent complete source
comparisons retain the original streams, narrow receipt comparator, reconstructed
OCR identity and actual consumer. Stage timing violations are recorded as FAIL.

Perform the complete independent whole-evidence check once during authority
recording, with210s internal and timeout240 including authority overhead. This
is the primary acceptance criterion. It must rerun the unchanged010 evidence
logic: all methods, package/dependencies,343-file profile,18commands/four native
reservations, installed imports, all controls, five whole replay comparisons,
two source graphs, complete consumers, receipt mappings and storage bounds.
The old115.074s summary is never used as proof of current acceptance.

The only edit to the existing installed script is one explicit task dispatch to
the new retained validator. Prove it byte-for-byte against010's frozen source;
refuse every other change to its complete method inventory. Load the exact
frozen evidence functions and provide the old method map only after that bridge
has verified the sole reviewed dispatcher insertion and all unchanged methods.
This is an explicit compatibility check, not a generic stale-method exception.
Neither production code, wheel nor the shared native dispatcher changes.

| Choice | Provenance and purpose | Failure mode and early diagnostic | Status |
| --- | --- | --- | --- |
| Actual010 executions and native017 complete baselines | Successful commands with retained streams/import proofs | Treating summary PASS as acceptance; require actual REJECT1137 and exact old stage audit | Reviewed retained comparator |
| Exact dispatcher-only method bridge | A separate validator needs an entry point | Broad stale-method waiver; tests refuse changed bytes or missing inventory | Reviewed bounded integration repair |
|110s work/115s recorded short stages | Overrun exposed a measurement margin problem | Delayed timeout reported PASS; explicitly fail when recorded work exceeds the bound | Reviewed orchestration correction |
|210s whole check/240s outer record | Existing independent bound and measured authority overhead | Repeating the whole check in a short stage; execute it once at record | Convenience bound with failure stop |

Skeptical audit: PASS for retained current installed acceptance. Actual full
answers and provenance remain the primary evidence; test totals and timings
are explanatory or resource vetoes. Missing or changed retained evidence,
wrong commands/imports, accepted counterexamples, unexplained source/answer
differences, extra calls or bound violations stop this attempt. No new source
coverage, portability, independent legal truth or whole-program completion
follows. The rejected orchestration candidate does not reject the package or
the integration direction. After actual acceptance, refresh and return to the
current recovery plan and the remaining substantive obligations.

Commands use `timeout 120 .venv/bin/python scripts/prospectus_installed_retained_validation.py --attempt ATTEMPT --stage STAGE`;
record uses timeout240 with stage record. Retain the actual command, commit,
environment, CPU-only identity, methods/source hashes, measured outcome and
independent authority event. Poll one running session at a time.
