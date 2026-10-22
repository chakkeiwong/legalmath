# Review before method freeze

The first current suite passed46 tests in0.50s (runner wall0.5891s). It covered
admission/program/input changes, historical and outside paths, symlinks, sealed
and duplicate starts, method-set changes, actual receipt-byte corruption,
unexpected ledger reservations, failure/cancellation retention, attempted
subprocesses including swallowed refusal, and authority refusal to accept an
offline PASS. Its exact methods and report remain under validation/run-001.

Review found one reporting defect in the new test runner: a post-suite binding
failure set status FAIL but could retain the suite's zero exit code. The single
permitted repair sets a nonzero exit code on exceptions and adds an injected
real-runner regression. The second and final suite tests the repaired methods.
No native launch or package installation is involved.

The current preparation validator checks historical receipts with
require_current=False and compares their exact stored receipt/stream identities
to inventory123. It checks historical method snapshots against historical
hashes, not current code. This intentionally establishes historical integrity;
it does not establish current native compatibility. Current Python methods are
captured separately, compared after each stage, and tied to the new tests.

The only supported driver stages are offline preparation, five retained-P1
consumer comparisons and finalization. Fresh stages refuse before writes. The
authority has no active automatic validator for this partial package, and its
original completion registration is preserved verbatim. Thus passing this
package cannot close native-binding. A separately reviewed live implementation
and evidence-based registration remain necessary.

The guard handles reviewed Python subprocess paths; it is not a security
boundary against malicious code. The authority lock serializes these stages.
Canonical paths and symlinks are checked before writing; hostile concurrent
filesystem replacement, SIGKILL, power loss and unwritable storage remain outside
the guarantee. Complete retained object equality is the downstream criterion;
there is no field removal or post-hoc normalization.
