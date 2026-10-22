# Repair source text hashing using the production source constructor

Attempt078 rejected the complete original baseline while27 smaller cases passed.
The source contract at successor/contracts.py:TextUnit.json computes
digest(raw.encode()), whereas the assessor and hand-built fixture used
digest(raw). These are different byte sequences. All five inspected final-term
rows have correct byte hashes,identical raw/selected text and matching source
metadata. This is our implementation and test-fixture defect, not a source or
third-party package failure. Preserve077 and078 unchanged with their costs.

Change only the candidate text-hash input to UTF-8 bytes. Replace the flawed
synthetic copy test with a new retained test using the actual TextUnit constructor;
keep the old test as failed-attempt evidence. Add a counterexample substituting
the JSON-string hash. All original21 requirement tests remain. The independent
338expected inventory is unchanged. No source,answer,numbering or substantive
acceptance condition is weakened. Raw edition,interval,text,document,page and
mapped/direct representation checks remain mandatory.

Evidence contract: exact positive original baseline plus production-constructed
copy cases; complete expected report through the actual assessor and isolated
fresh wheel. Primary criterion is original identity and downstream evidence
preservation with seven open requirements. Missing identities,accepted forged
provenance,erased uncertainty,false completion or installed mismatch veto
promotion. Corruption,method drift or cumulative exhaustion veto continuation.
Runtime and test totals explain execution only. A failed candidate requires
reviewed repair; it does not disprove the research direction. No general recall,
historical-law correctness,actual-event truth,new full consumer run or original
task completion follows from a pass.

Skeptical audit PASS after tracing the actual TextUnit constructor. The earlier
fixture mirrored the wrong implementation assumption; the changed fixture now
uses the production source representation and a distinct wrong-format control.
The original full positive case remains the discriminating criterion. Inspected
five final-term rows all match the byte-hash convention. Wrong baseline,proxy
promotion,hidden defaults,stops,environment and meaningless success were checked.

Same task and79 cumulative admissions; retain all78 earlier costs/admissions.
The21600accounted-seconds/3200MiB limits including4MiB reserve remain unchanged;
forecast360seconds/64MiB. Older unmeasured time remains UNKNOWN. Use reviewed
revision340/check/status/admit,then install/tests/assessor/controls/package/
isolated-assessor/seal/record/refresh. No network,GPU,subagent,commit or push.
Short tool yields and original-session polling remain mandatory. Continue the
original selected-prose discovery work after this bounded implementation repair.
