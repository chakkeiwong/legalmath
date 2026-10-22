# One bounded artifact-storage repair

The matched diagnostic finished before a stop signal was needed: 98.066 seconds,
18 actual refusals and complete protected-answer equality. Its functional
result is PASS, but its writer failed the 20 MiB storage constraint. Measured
retained files totaled 34,399,453 bytes before this repair. The writer copied
the full original source graph into four source-control files. No test or
consumer failure occurred, and no fresh native extraction ran.

Treat the storage result as an artifact-engineering failure, not evidence
against cell consumption or an external library. Do not rerun successful
diagnostics. Use the single permitted corrective validation to replace only
those four newly generated duplicate files with lossless references. Preserve
the original matched script, its actual PASS, all timings, all changed inputs,
and this cap violation. Do not rewrite the original plan to conceal the failure.

Each reference names `after-products.json.gz` P1 as its baseline and stores
the exact changed source unit (or removed ID), changed graph digest and full
control-product hash. Reconstruct all four complete objects, reproduce the
original pretty JSON and gzip encoding, and verify original uncompressed and
compressed SHA256 before replacing any redundant file. Store all four original
byte hashes and sizes. Only this turn's unsealed duplicate products may be
replaced; no earlier attempt is touched. Verify the final complete evidence
size fits 20 MiB. The initial peak-storage bound remains failed in the result.

One CPU-only repair command has a 120-second limit and no subprocesses.
Expected output: `storage-repair.json` plus four `source-control-*-reference.json`
files and an executable restoration script. This repair must not change
production, protected answer content or any diagnostic outcome. A byte
restoration mismatch stops the repair and preserves the original files.
