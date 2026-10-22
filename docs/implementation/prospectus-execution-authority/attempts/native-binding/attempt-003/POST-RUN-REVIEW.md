# Exact result interpretation and execution-bound correction

Both original and current OCR comparisons pass, all complete question objects
and source units agree, all11 actual namespace controls pass, and the public CLI
feeds the existing retained hybrid interface without a test adapter. Its five
product-use comparisons pass. The consumer uses frozen assessment on freshly
computed P1–P5; pdftotext and the retained-image verifier remain unconfined.

The extra all_clauses_equal assertion in compare failed in both cases because
it included assembly_sha256. Source inspection shows clause_graph.build binds
digest(assembly), and contract_assembly.assemble binds digest(source_graph).
Runtime provenance changes that source graph, so the parent hashes must differ.
The failed assertion remains FAIL. A separate read-only diagnostic checks every
clause field and both parent links without rerunning the comparator or dropping
unresolved IDs. This is explanation, not retrospective acceptance of that run.

A second audit found a counting mistake. PRODUCT-USE-REVIEW counted nine explicit
worker/namespace invocations, two output-control subprocesses and one boundary
child as twelve. It omitted three pdftotext invocations in the Portuguese source
consumers. There were at least15 relevant execution/worker invocations under
that accounting, exceeding the stated ceiling12 by3. There were also controller,
pytest and CLI wrapper processes; a literal all-child-process ceiling would be
higher still. The driver only enforced its own nine launch markers and cannot
claim complete process accounting. The original plan and the mistaken product
review remain unchanged. This is our budget-accounting failure, not a package
failure or user-permission violation. No further native child is launched here.

The two allowed inventory/launcher repairs are exhausted. The finite evidence
remains useful but this admission does not satisfy its execution contract and
cannot be promoted. A subsequent reviewed revision must preserve these failures
and cumulative actual counts, explicitly define and intercept controlled process
launches, and verify the missing behavior under a bounded changed plan.

Code review also found a reusable-receipt gap: runtime.run records a file-manifest
digest and argv, but its public receipt omits stdin and stream digests and exact
current method/launcher/kernel identities. The experiment separately retains
these bytes; an arbitrary later CLI caller lacks that complete link. This is
a concrete implementation repair for the same native-binding task. It does not
justify rerunning identical OCR merely to obtain another PASS. A new finite
repair should check receipt tampering, child accounting, full parent lineage
and actual existing-product consumption with no inherited environment/mounts.

Decision: retain attempt003 as PARTIAL_WITH_FAILED_CHECKS and keep native-binding,
native-confinement and portability open. The result supports viability of sealed
file inputs for these two OCR cases. It establishes neither a fully integrated
runtime nor a fundamental problem with Bubblewrap/PyMuPDF/Tesseract.
