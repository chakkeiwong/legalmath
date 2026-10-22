# Distinguish clause content from its changed construction binding

verify_scope.py exited1 after writing the visible-case result. The next assertion
compared the full clause product, including assembly_sha256. That digest must
change when the availability ledger is added to P2. Inspection found exactly
that field differs; the nodes and other clause fields remain equal. This was
a comparison-harness error, not a failed source-scope repair. Preserve the
original script and completed visible-case outputs.

The recovery uses the original script's case logic with three explicit changes:
verify and reuse already retained method snapshots; use the completed visible
case without recomputation; compare clause content excluding assembly_sha256
while verifying the new product's exact construction binding. All unfinished
cases execute normally under unchanged production methods. Record both commands
and the initial failure. No broader legal conclusion or duplicate successful
case follows. Audit PASS for this limited diagnostic correction.
