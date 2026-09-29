# Additional binary check on the frozen transfer replay

Question: does the already integrated Catala compiler path preserve the generated
live candidate on the same explicitly mapped transfer scenarios as the ordinary
Java backend? The exact baseline is the retained generated Java binary, Python
reference and cvc5 results from the margin replay. No candidate or expected answer
will be changed for this check.

Use `build_candidate(..., backend="catala")` with the existing pinned compiler,
upstream source and lock, then `verify_candidate` on the reference snapshots.
The primary criterion is full Catala/Python result and trace agreement under the
existing contract, plus status/type/value agreement with the ordinary Java and
cvc5 results. Wrong outputs, invalid traces, changed toolchain bytes or missing
results veto this comparison. Build time is explanatory only. Retain the
Catala source, generated Java, build manifest, commands and actual verification
results beside the transfer replay in P5.

Skeptical review: the existing 55-test Catala suite does not by itself prove that
this particular live-derived bundle was compiled through Catala. An explicit
build and invocation resolve that gap. Both backends still share RuleIR, input
meanings, structural validation, host code and parts of result/trace construction.
Agreement does not prove English meaning or whole-compiler correctness. No new
model calls, installation, external service or bank deployment is involved.

This changes only the P5 reference helper, which has not run yet and is separately
bound when that phase refreshes its plan. The active P4 implementation and inputs
remain fixed. A focused replay on the existing immutable margin snapshot will
precede P5. The final comparison remains conditional on the post-generation,
author-reviewed fact mapping and preserves all unmapped reference scenarios.

The focused replay passed all five margin scenarios through Catala and the
ordinary Java, Python and cvc5 paths. Full Catala/Python result and trace
verification passed. Evidence is in
`artifacts/interpretation/round12/diagnostics/transfer-reference-catala-02`.
The first diagnostic completed the compiler and conformance work but failed
while assembling the summary: `verify_candidate` returns a report and writes
the detailed results separately. The helper was corrected to read that retained
results file. The failed diagnostic remains preserved under the `-01` directory.
This was an integration error in report assembly, not a differing legal or
numerical result. P5 will repeat the complete reference route on the final live
snapshot and bind it in the phase manifest.
