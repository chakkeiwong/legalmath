# Repair the final consumer after source-authority010

Authority revision380 and source-authority010 are the baseline. The attempt
failed with `NameError: source_chain is not defined` in the actual final consumer.
Its source-chain verifier was called inside `interpretation_product`, while its
result was used only inside `consume`. The 32 development tests exercised the
reader and checker directly and missed this integration error; the formal tests
and ordinary consumer exposed it. This is our wiring and test-coverage failure.
It is not evidence of a third-party package defect or invalid source reading.

## Question and evidence contract

Can the repaired final consumer verify and deliver the reviewed source-chain
report, refuse altered or missing reports after product hashes are recomputed,
and preserve complete legacy answers? Move verification into `consume` after
its own P2 verification. Keep the source reading, original documents, and
financial behavior unchanged. The baseline for the repair is the retained
failing service and attempt010 logs; the behavior comparator is the complete
finance013 answer/P5 for the three original Shell scenarios.

The primary criterion is successful actual consumption of those three source
pairs in ordinary and isolated installed runtimes, complete legacy answer/P5
equality, unchanged questions and assembly when the optional review is added,
source-qualified reports, and refusal of recomputed-hash forgeries. Before
freeze, run actual consumer regression tests including the acquisition-receipt
suite. A helper-only test is insufficient. The unchanged independent verifier
must use this recovery's frozen methods rather than revision380's service hash.

Wrong source edition/actor/qualifier, changed financial questions, incorrect
import origins, missing cases, accepted forged reports, or failed checks are
promotion vetoes and repair triggers. Counts and elapsed time explain coverage
and resources only. Corrupt common originals, invalid authority, exhausted
cumulative limits, or a second unexplained failure are continuation vetoes for
this bounded repair. No authenticity, first-publication, actual trustee
succession, operative source roles, whole-task or whole-build claim follows.

## Dependencies and bounded recovery

A: preserve the exact failing service, original runner and failure manifests;
recompute source010 costs without changing sealed evidence. B needs A success:
move the verifier and add tests through the final consumer. C needs B success:
run the focused reader/actual-consumer/acquisition tests before freezing.
D needs C success: freeze the changed candidate, retain every old admission,
review the original source-authority allowance10→11, revise and admit once.
E formal tests, F ordinary consumers, and G offline wheel are independently
ready after D, serialized because accounting is shared. H installed consumers
needs F/G success. I evidence verification needs E/F/G/H success. J reconciliation
needs E/F/G/H/I completion, including blocked dependants. K seal needs J success.
Record, refresh and inspect the original-source frontier after K. Continue
independent ready work. No unchanged retry and no checkpoint-based stop.

A second developer change requires a retained diagnosis and reviewed amended
plan before freeze. A formal failure blocks only its success dependants; J/K
still preserve the failure. Never edit attempt010, its frozen runner, source
review, plan, or input/results to make it pass. The new wrapper may reuse those
methods with explicit recovery paths; default arguments capturing the old path
must not direct new writes into revision380.

## Assumptions, limits and skeptical audit

The named optional source reading remains a bounded supported-domain mechanism.
Its original eight-image review is retained, not repeated or reclassified as
independent authenticity evidence. The current consumer supports frozen replay;
the acquisition suite also covers current validation without a new PDF extraction.
Exact complete-answer comparison is the regression baseline, not proof that
source interpretation is exhaustive. Independent report checks and source
qualifiers remain necessary. No numerical default or package version changes.

At recovery start, source010 recomputation gives known006+1540.2914366697335
accounted seconds and252214485bytes. Earlier/manual costs remain UNKNOWN.
Keep the original1900seconds/384MiB cumulative ceiling. Reserve at most220 new
measured seconds,60 conservative control seconds, and128MiB of new files,
including all proposals/revisions/admissions/package and a4MiB seal reserve.
Check projected combined storage before admission. No new PDF renders, network,
OCR, GPU, model calls, subagents, external messages, or branch operations.
CPU children hide GPUs. Tests and verifier have60second limits; ordinary and
installed consumers90seconds. Use one-second yields and original-session polls.

Preparation: `reviews/shell-source-chain-repair-381`; formal evidence:
`source-authority/attempt-011`. Fixed command prefix:
`.venv/bin/python -m scripts.prospectus_shell_source_chain_repair`.

Skeptical audit: PASS for this changed bounded repair. The actual failing
baseline and mechanism are identified; helper-only evidence cannot promote the
repair; complete source/financial comparators are preserved; frozen and installed
origins are checked; no old budget or history is reset; independent stages and
completion-only reconciliation are explicit. The strongest false-positive risk
is rerunning only reader tests or checking the old freeze against changed code.
The new actual-consumer tests and recovery-specific freeze address both before
formal admission. This audit authorizes repair work, not a passing result.
