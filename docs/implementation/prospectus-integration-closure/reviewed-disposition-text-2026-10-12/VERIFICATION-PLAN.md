# Final evidence verification, 12 October 2026

Verify the saved repair result before starting the next source-scope change.
The comparator is the retained manifest/receipt hash, not a new test result.
Pass requires all referenced files to match, all nine selected receipts to be
internally valid and match the final status snapshot, and Python sources to
parse. Run `git diff --check` separately and retain its result. A mismatch
stops sealing and triggers investigation; never regenerate a historical hash
to make it pass. Syntax and hashes establish record integrity only, not legal
truth, source authenticity, runtime portability, or an independent reading.

Skeptical review: the earlier coordinator failed, so its result must remain
incomplete; the later combined status selects recovered receipts. This check
does not rerun completed consumers or silently upgrade substantive PARTIAL
criteria. Use stdlib parsing to avoid the shared-venv source import defect.
Hash referenced bytes, including downloaded sources; do not execute stored
acquisition or mutation scripts. Reviewed scope: repair package, Portuguese
2010 attempts and the eleven-page visual review. Missing referenced files,
hash changes or syntax errors are continuation vetoes for sealing only.

Command: `.venv/bin/python docs/implementation/prospectus-integration-closure/reviewed-disposition-text-2026-10-12/verify_evidence.py`.
Output: `verification.json`; then freeze package hashes after recording the
whitespace check. This is a deterministic integrity check, with no random seed,
GPU, network call, scientific ranking, or new legal acceptance claim.
