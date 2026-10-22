# Note 27 storage failure

The source worker completed the source/transcript check, saved its original source
units, and then failed writing reading.json. The inherited save function permits
at most 2,097,152 bytes per file. The complete accumulated reading serializes to
2,250,892 bytes. The file was not created, and the production registry still has
the frozen baseline hash. Implementation and consumer stages therefore remain
blocked; no claim of delivery is justified.

The earlier full-graph preflight checked source consistency and candidate
admission in memory. It omitted actual serialization and source-worker writes.
The final review missed that distinction. This is a local harness/preflight gap;
it provides no evidence against the source reading or an external package.

Bounded diagnostic audit: inspect the exact failed write, measure the actual
serialization and test existing deterministic gzip round-trip support. No package
or production changes are involved. The diagnostic reproduced the limit and
verified that gzip stores the identical reading in 219,343 bytes. Its compact
reading hash is retained in failure-localization.json. The 2 MiB guard can remain
unchanged. A new reviewed attempt must use reading.json.gz consistently and run
the actual source worker against temporary outputs before admission, including
candidate freeze and baseline refusal. Preserve all images, transcript, source
checks, prior successful 041 and this failed attempt.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Reject attempt 042 delivery; repair serialization|Source agreement passed before write; delivery absent|Local size guard refused file|Other stages have not run|Coverage, seal, record, refresh; changed gzip storage attempt|Source error, external package unsuitability, successful product integration|

The candidate failed, not the direction. Independent coverage remains ready.
Remaining policy preparation is retained but cannot use failed 042 as a successful
answer comparator. It must follow the successful changed repair.
