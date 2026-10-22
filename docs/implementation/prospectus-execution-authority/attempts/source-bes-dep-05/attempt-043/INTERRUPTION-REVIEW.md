# Ordinary verification interrupted

The tool session 49029 returned exit code 143 without output. The ordinary
worker's log is empty and neither its final answer receipt nor stage result was
present. No matching worker survived the recovery inspection; the recorded
process identity no longer matched. The authority resume found no controller
worker running. Do not dispatch the same ordinary job again.

Source, implementation and all 41 tests passed. The compressed reading repair is
validated at source level; ordinary/installed delivery is not established. There
is no evidence identifying the termination cause. In particular, a memory limit,
host interruption, timeout or package defect has not been proved. The interrupted
duration is unavailable; accounting charges the full 360-second reserved child
bound conservatively. Fields inherited as measured time now include that upper
bound and must not be used as precise runtime measurements.

Code inspection finds a separate recovery weakness: one consumer command builds
both answers, compares all phases, runs source negatives and reconstructs every
historical composition before writing its first durable receipt. An interruption
therefore loses the entire command's progress. The next changed attempt should
retain bounded baseline, candidate, comparison, composition and corruption
results separately, authenticating each prerequisite and never treating partial
receipts as consumer success. Preserve the exact original answer hashes and
comparison; splitting work must not weaken acceptance. Independently complete
coverage before sealing this failure.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain interruption; change verification execution|Source/tests passed; consumer absent|Interrupted process and missing required receipt|Termination cause unknown|Coverage, seal, record, refresh; bounded resumable consumer plan|Successful Note 27 delivery or external package failure|

The candidate lacks consumer evidence; the source interpretation and package
suitability have not been invalidated. Policy drafts remain preparation and must
use the next successfully delivered Note 27 baseline, not failed 043.
