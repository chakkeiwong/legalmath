# Bounded result-inspection repair

The actual consumer produced and retained both final answers, then the harness
failed at `actual["dependencies"]`. Code inspection confirms that consume's
ordinary final-answer API omits the dependency payload unless include_artifacts
is requested; dependencies belong to P3.payload. This is our diagnostic API-use
error, not a source, method or package failure. Preserve the original script,
failure, timing and both actual answers.

One bounded repair will rebuild P1/P2 from the exact saved request and graph,
recompute P3 once, and require each reconstructed product hash to equal the
hash already present in the retained final answer's consumed_products. Reuse
the completed answers; do not repeat download, extraction or final consumption.
Inspect P3.dependencies and the final questions' unresolved entries separately.
Run the planned adverse controls and retain results in new repair files.

The evidence question and comparator are unchanged. A reconstructed-product
hash mismatch vetoes this repair. Keep the same 120-second command ceiling,
one-second yields and source/method bindings; no admission or cumulative
authority budget is reset. The completed consumer invocation remains evidence
only if its exact product identity is recovered. If this repair fails, retain
that blocker and continue independent source work after recording it.
