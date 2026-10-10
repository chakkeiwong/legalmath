# Worker recovery and native-read diagnostics, 11 October 2026

The local OCR model-path defect is repaired: every language-model target is
resolved within the declared source root before its bytes are accepted. The
eleven-step actual OCR/authored-XMI recovery sequence passes, including typed
failures and restoration of complete reports. The final sequence checks that
the resource change itself invalidates the receipt before adding a recovery
reason. Five pytest controls cover the model path behavior.

The actual PyMuPDF OCR worker also produces the same full output under strace
and a Bubblewrap mount profile as the protected current-method baseline.
The small boundary controls observe child and symlink reads and deny reads
outside the mounted case. These tools are locally usable. Production native
reuse remains vetoed because complete dependency binding is still absent.

Current-method regression and R0–R8 refresh completed successfully under
`validation-001/` in 3,219.332 seconds. Exact partitioned coverage accounts for
all 663 collected test identities, with no missing, unexpected, failed or
skipped tests. The twenty focused checks, all phases and 155 otherwise uncovered
tests pass. R4 took 3,144.351 seconds. Final verification checked all nine
retained manifests, the frozen method, every recovery receipt and equality of
R8 with final attribution. No new installed-package trial is claimed; earlier
installed results retain their historical methods.

The current engineering PASS receipts are R0/017, R1/015, R2/015, R3/013,
R4/013, R5/013, R6/013, R7/013 and R8/014. R1–R8 remain substantively PARTIAL;
external acceptance is NOT_ESTABLISHED and `program_complete` is false.
No validation remains active at this checkpoint.

## Evidence and decisions

| Work | Actual outcome | Decision and next action | What is not established |
|---|---|---|---|
| Model path attempt 001 | A same-byte outside-root symlink reached the missing-interpreter check | Reproduced local source-binding defect; repair each model target with `bound_path` | OS confinement or race freedom |
| Model path attempt 002 | All four original controls passed; outside-root symlink raised `ExtractionUnavailable` | Retain patch and five regression controls | OCR quality |
| OCR baseline 001 | Two independent launches passed in 1.291 seconds; two pages, words, blank page, image/runtime identities and six questions retained | Valid current-method baseline for this English fixture | Multilingual/table prospectus performance |
| Recovery 001 | Baseline executor and clean recomputation agreed, but expected `NO` differed from actual `UNKNOWN` | Probe omitted the explicit `exempt=True` observation; correct the oracle in a separate attempt | Cassis or downstream consumer failure |
| Recovery 002 | Seven comparisons passed, then mutation helper found no imported-schema relation | Helper used the wrong decoder for a draft-authored CAS; correct that helper | Corrupt protected XMI or package unsuitability |
| Recovery 003 | Eleven fresh computations and restorations passed in 14.941 seconds | Fresh recovery is evidenced; post-run audit requires pre-marker invalidation checks | Automatic detection of input change from this attempt alone |
| Recovery 004 | Eleven comparisons passed in 16.426 seconds, each changed resource made the receipt stale before the reason marker; 1,386,770 bytes retained | Accept this finite local recovery evidence and preserve all prior attempts | Environment-only invalidation or arbitrary native dependency closure |
| Native boundary 001 | Actual direct/child/symlink/changed-file and failed-lookup tracing passed; outside fixture reads denied under Bubblewrap; both real OCR outputs equal the baseline | Retain as local supported-tool evidence; keep `ReadContext.reusable=False` for native invocation | Production wrapper integration, exhaustive dependency binding or second-host portability |
| Current regression | All 663 unique tests covered; current valid R0–R8 engineering PASS receipts; frozen method and attribution verified | Commit the completed recovery work and continue the real-scan source/correction package | Legal acceptance or complete R1–R8 capability |

## What the recovery sequence actually checks

The sequence operates on isolated copies of the protected English PDF/model
and authored XMI/type system, plus a symlink to the pinned OCR interpreter.
The actual closure executor invokes the real OCR worker and Cassis adapter.
Each step is recomputed independently in another process and compared as a
complete service result or exact typed error. Immediate unchanged replay must
reuse its valid receipt. Restored resources must recover the original full
reports, including source evidence and all question records.

The steps are baseline; missing model; restored model; changed model; repaired
model; missing copied interpreter link; restored interpreter link; removed
authored exception link; restored relation; corrupt XMI; restored XMI. The
missing relation retains the supplied reviewed clause link and must therefore
raise `ValueError: Authored relations differ from supplied clause links`.
The baseline explicitly supplies `exempt=True`, giving Q1 `NO`; the scan's
unreviewed legal meaning remains `UNKNOWN`.

Attempt 004 records exactly one changed binding for each non-baseline step:
the model, the copied interpreter path or the authored XMI. That observation
precedes the recovery marker. Every phase receipt retains all its output
files, so its byte integrity can be independently verified after temporary
source copies have been removed.

## Attribution and limits

The implementation defect was in local model-path admission. The first two
sequence failures were in the new probe: an omitted observation and the wrong
schema decoder. The later marker issue limited the evidence that could be
drawn from a passing run. None establishes a fundamental package limitation.
The supported current PyMuPDF/Cassis paths pass the declared finite controls.

The tiny native worker demonstrates why the current reuse veto is needed.
Changing its undeclared file changes direct, symlink and child results while
`ReadContext.current` remains true for declared records; `reusable` correctly
remains false. The trace records those reads and failed lookups. Bubblewrap's
restricted profile denies the outside fixture reads while permitting the
declared file, and the same profile with the pinned Conda runtime can run the
real OCR worker without changing its output. The broad read-only runtime
mounts are still mutable host dependencies; proc/device access, failed lookups
and read/hash races are not a complete replay contract. The production
application has not adopted this diagnostic mount wrapper.

The strongest alternative explanation for executor/clean agreement is an
identically wrong worker. The known two-page inventory, page-image identities,
complete word geometry, authored-relation oracle and adverse controls limit
that explanation for these inputs. They do not measure unseen-document quality
or validate a legal interpretation. A changed required page, relation or full
runtime product would overturn the relevant pass. The weakest remaining
evidence is generalization beyond one host and this small fixed corpus.

## Retained execution locations

The reviewed plan is `docs/plans/prospectus-worker-recovery-2026-10-10.md`.
Every diagnostic directory contains `started.json`, `result.json` and a byte
manifest. Recovery 004 contains full per-step executor/clean products and
phase receipt outputs. Native 001 contains commands, versions, full worker
outputs and bounded traces. Exact commands, source and interpreter hashes,
CPU-only environment, data hashes, wall times and result paths are recorded
there. Random seeds are not applicable to the deterministic finite sequence;
the regression runner preserves the existing Hypothesis settings.

The next substantive local work is to freeze named real prospectus pages and
their critical text/row/link oracles for extraction and correction testing.
A future production native wrapper requires a separately reviewed immutable
runtime and dependency design; second-host portability and qualified legal
acceptance require their actual external inputs.
