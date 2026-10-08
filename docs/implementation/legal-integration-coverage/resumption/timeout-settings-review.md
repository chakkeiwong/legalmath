# Preflight correction to the reviewed timeout recovery

The initial timeout recovery implementation failed three local tests before any
live dispatch: ordinary product `Settings` deliberately caps timeout at 300
seconds. The conditional review v3 is preserved, but it never acquired passing
tests and was not executed. The new ledger remains at 39 calls. The local test
result was 54 passed and 3 failed; all failures exposed this same settings
validation mismatch.

Retain ordinary product settings and their 300-second bound. Define an explicit
`RecoverySettings` type in the continuation module with a maximum of 450
seconds. Construct it only for the review-bound recovery whose specification
requires that cap. The provider independently rejects an extended cap without
an exact request binding, and still clips every call to the original absolute
deadline. No validation is bypassed and no product default is enlarged.

The skeptical audit passes conditional on fresh tests. The newly discovered
problem was an implementation preflight mismatch, not evidence against the
unchanged legal target or the recovery hypothesis. The exact request, schema,
route, tool context, one-attempt limit and all substantive criteria remain as
documented in `timeout-recovery-review.md`. Tests explicitly retain the normal
300-second product bound, reject more than 450 for recovery, reject an unbound
extension, and verify original-deadline precedence.

Count this correction as implementation repair entry 6. The reviewed live
successor will use entry 7, superseding the earlier projected entry number in
the original timeout note. Seal review v4 and its source snapshot; keep v3 and
its failed preflight record. No new user allowance or time window is inferred.
