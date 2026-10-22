# Partition the unchanged validated input from interpretation

The v3 candidate command exited 124 at 120 seconds without a P3 artifact. The
complete current baseline P3 and answer passed; 45 focused tests passed. The
command includes `scope.admit`, which regenerates and validates the complete
packet and converts earlier notice edges, followed by full P3 construction.
There is no stage timing to attribute this second timeout more precisely.

The previous review required a new decision after another timeout. That
condition has fired. Preserve the failed invocation. Authorize one stage
partition, with no further product changes: first compute and retain the
validated interpretation input plus exact P1/P2 IDs and method hashes; next
load that frozen input and run P3; next consume the same P3. Each stage keeps
the original 120-second maximum. No source, target, question, comparator or
acceptance condition changes. Completed current v3 baseline artifacts are
reused with their original identities rather than re-executed.

An input or method mismatch vetoes downstream execution. If any isolated stage
times out, retain the result as an execution blocker; do not add another local
repair or repeat it unchanged in this admission. Independent source/extent
controls remain allowed. This is a reviewed harness partition after a combined
command failed, not evidence that the product or package has failed correctness.
The retained timings must state that the earlier timed-out prefix was repeated;
no claim of improved runtime follows from finishing shorter commands.

Audit: pass for this one partition. Its artifacts answer whether the existing
optional target schema works on the exact complete source review and preserves
the latest baseline. The original strict comparison still decides correctness.
