# Verification failure retention repair

The final15 focused tests pass in0.274seconds. The initial14 tests passed in
0.281seconds before the reviewed subprocess-guard correction. Both method
versions and actual stage records remain retained. No child process ran.

The wrapper now retains failures from the validator, method capture and
post-checks as FAIL with the actual error, method snapshots and an output
manifest. Cooperative SIGTERM produces exit124; KeyboardInterrupt produces
exit130; ordinary validator errors produce exit1. Successful evidence remains
PASS pending the authority's independent acceptance check. Duplicate,
completed, changed-input, changed-program and outside-path calls refuse before
altering existing attempt evidence. A source, method or program change during
verification vetoes a successful candidate. The retained-only guard refuses
ordinary subprocess creation and restores the caller's Popen function.

The original wrapper's static success narratives contained historical test,
source and process totals. The repaired narrative derives its verdict from the
actual current check and leaves detailed evidence in verification.json; it
does not repeat historical numbers as current achievements.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Retain wrapper repair | 15 real wrapper tests, including exceptions, SIGTERM, mutation and refusal, pass | No observed loss of manifest or accidental launch | Fixtures do not establish actual historical validator behavior | Run the unchanged retained validator once and inspect its actual failure manifest | Native extraction is current or native-binding is complete |
| Preserve native rejection | Existing validator and historical snapshots unchanged | Stale current method inventory must remain a veto | Actual refusal reason is not yet observed here | Read the subsequent result.json and authority event | A fundamental package defect |

Diff review compared the final wrapper with its protected pre-edit snapshot.
Only this script and its new focused tests changed. The native extraction
driver, validator, source methods and all historical attempts are untouched.
The strongest alternative explanation is that a real validator or filesystem
failure behaves differently from these fixtures. The single actual check
addresses the former. An unwritable directory, hard kill or power loss remains
outside the guarantee; this repair does not claim hostile-code containment.
