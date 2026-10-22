# Repair Note 27 evidence storage and complete its delivery

Attempt 042 failed before production mutation: the complete reading serializes
to 2,250,892 bytes, exceeding the inherited per-file limit of 2,097,152 bytes.
Its source check had passed, but the preflight had not exercised actual file
writes. Preserve failed 042 and successful 041 unchanged. The sole authority
remains program.json and the original source-bes-dep-05 task and obligations.

The bounded repair uses the existing deterministic gzip writer and reader for
reading.json.gz. The measured compressed size is 219,343 bytes and the round trip
preserves the complete reading. Keep the 2 MiB per-file limit and total attempt
reservation. Every new reading reference, candidate freeze and consumer must use
the new path; historical 041 still uses reading.json. Reuse the authenticated
042 image/transcript preparation. The semantic mapping, units, dates, unknowns,
unprinted positions and interpretations are unchanged.

Question and comparator: can the exact Note 27 reading be stored and delivered
through the ordinary and installed consumers while preserving the complete
successful 041 answer? Failed 042 is the reproduced storage failure, not the
answer comparator. Primary criteria: a complete actual source-worker preflight,
lossless serialized reading, original image/transcript agreement and geometry,
full-graph admission, all source/consumer corruption refusals, full 041 answer
preservation and identical installed answer. Source counts, hashes and movement
arithmetic remain explanatory checks, not legal or financial proof. Wrong dates,
signs, units, table associations, source omission, lost earlier answers, accepted
corruption, failed round trip or wrong import veto the candidate. Invalid
authority, corrupt shared evidence and exhausted resources veto continuation.

Defaults audit: gzip is already supported by the checked writer/reader and prior
answer receipts; its risks are stale filenames, a changed object after loading,
and still-oversized compressed output. Exercise the actual source worker in a
fresh temporary directory, including source save, candidate construction,
candidate freeze, full-graph preflight and baseline refusal. Verify decoded
reading identity against 042's diagnosed compact hash. Do not substitute a toy
serialization test for that worker. Recheck wrong date, label, percentage, sign,
blank-to-zero and context rejection. Successful source preflight does not replace
the ordinary/installed delivery stages. The prior successful answer and source
hashes are reviewed baselines, authenticated again before admission. Runtime and
storage bounds are controls, not scientific performance defaults.

|Item|Needs success|Needs completion only|Recovery|Limit|
|---|---|---|---|---|
|A preserve 042 failure and inspect repair|Successful 041 and original evidence|042 coverage/seal/record|Correct unfrozen draft|One changed preparation|
|B actual source-worker/storage/adverse preflight and final review|A|None|Revise draft before admission|One complete preflight|
|C revise/admit and source|B and refreshed 042|None|Retain refusal|One revision/attempt|
|D implement, tests, ordinary, controls, package, installed|C and preceding success|None|Retain actual attribution|One each|
|E reconcile original requirements|Admission|Independent of C/D success|Record actual coverage|One|
|F seal, record, refresh and continue|None|C–E outcomes|Changed reviewed recovery if justified|One|

Proposed revision 406 and attempt 043 retain all 42 admissions and their cumulative
costs. New reservation: 1,200 measured seconds plus 60 control seconds, 128 MiB
including 2 MiB failure reserve, 360-second child timeout and 60-second package
build/install timeout. Charge retained and temporary preparation bytes and actual
preflight time. No unchanged retries or new network, OCR, model, GPU or subagent
work. Serialize authority, production and accounting, with one-second yields and
polling until each actual process exits. The policy 2.10–2.14 draft is independent
read-only preparation and must use the eventual successful 043 baseline.

Pre-mortem: an in-memory source check can pass while persistence fails, as 042
demonstrated. Running the actual source worker before freezing addresses that
specific gap. Other downstream failures still require attribution and preserved
evidence. The strongest remaining substantive uncertainty is a shared reading
error; original images and discriminating adverse controls address source
association, but cannot prove external legal/financial truth or automatic
extraction. A failed candidate does not reject the broader direction.

Draft skeptical audit: PASS for changed storage preparation. Wrong baseline,
stale file paths, missing stop conditions, incomplete source-worker preflight,
environment import origin and proxy promotion have explicit checks. Final audit
requires the actual source worker and source corruption checks to pass before
admission. No ordinary or installed delivery success is yet asserted.

Final skeptical audit: PASS for bounded 043 admission. The actual repaired source
worker ran in a fresh repository-local preparation directory so its real relative
source references, writer, reader and candidate freeze were exercised. It passed
in 9.131 seconds, including the full 48 rows, source context and original-graph
admission/refusal. Its compressed reading has exactly the diagnosed 042 compact
hash and 219,343 stored bytes. Wrong label, date, percentage, sign and blank-to-
zero mutations were refused. Production remained at the frozen 041 baseline.
Reviewed the complete runner diff: changes are persistence paths, authenticated
reuse, failure accounting and new attempt metadata; the source mapping and
interpretation are unchanged. Failed 042 is sealed, recorded and refreshed.
The two-MiB guard and all original acceptance obligations remain intact. Both
ordinary and installed delivery still have to pass.
