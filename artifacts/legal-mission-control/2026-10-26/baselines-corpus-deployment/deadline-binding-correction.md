# Deadline binding correction

The independent provider preflight rejected the staged binding with E_AUTHORITY.
The exact root cause is time_authority.effective_deadline: the binding review
must equal the existing time-extension review. Replacing that field with the
local deployment review violated the inherited time authority, although neither
deadline nor grant changed. No active files were installed and no call was made.

The corrected binding retains the prior review field exactly. The deployment
review remains explicitly bound in baseline_corpus_repair and in bindings.
The service predecessor and binding predecessor both point to the exact prior
binding, so shared service-scope inheritance remains valid.

Skeptical revision: PASS for correcting this single staged binding field. It is
an identified defect in the uncommitted registration projection, not a grant
extension, failed model attempt or changed product candidate. Preserve the first
binding and original staged-identities receipt. The full master/mission check is
independent of this provider-binding-only change and continues against the same
program, state and mission bytes. Combine its explicit PASS with the corrected
provider preflight only after both finish; do not discard or reinterpret its
expected old-binding provider failure.

The corrected provider preflight passes: 6,471 calls retained, unchanged inherited
service scope, and central activation hold verified before any charge. The
original 8,100-call maximum, 288 spent replacements and 27 October 2026
13:15:09 Hong Kong effective deadline remain unchanged. Final installation
requires preserved checked identities and an installed mission refresh.
