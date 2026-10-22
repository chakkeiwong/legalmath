# Attribution review before the new ladder

The first revision updated G07's changed service hash after checking that
finite/Z3 routing is unchanged, and extended G08 with actual report-scope
consumption. Its preflight then correctly rejected G20's old controller hash:
R4 now adds `test_report_scope.py` and its selection token. The first revision
is retained as `attribution-intermediate.json`; do not rerun the mutation script.

Review of G20: the R4 job adds the new file and OR selection; every previous R4
test remains selected. No bindings, validity logic, admission limits, phase
ordering or timeout is weakened. Update only this named controller hash, record
the new optional-test admission, and rerun the read-only attribution preflight.
This failure concerns our evidence-maintenance step, not a package limitation.
The prior sealed controller receipts remain historical evidence until the new
ladder finishes.
