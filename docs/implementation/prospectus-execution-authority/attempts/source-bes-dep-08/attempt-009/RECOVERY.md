# One changed recovery for the installed-output collision

The first installed command failed after 0.1145 seconds at `folder.mkdir`,
before consumer evaluation. The runner uses `installed` both for the package
installation and for result metadata, then incorrectly requires that directory
not to exist. The installed package and frozen production inventories still
match. This is a harness implementation failure, not a failed consumer or
evidence against a package.

Preserve the original runner, freeze, admission, failed command and all outputs.
The recovery uses the existing immutable `evaluate` implementation and writes
new result metadata into the already verified installation directory. It first
requires the full package inventory to match and every expected output file to
be absent. It runs the same isolated interpreter, checks every legalmath import,
and compares the complete answer and all controls with the frozen candidate.
No package is rebuilt or reinstalled. The new wrapper and its input hashes are
retained in this admitted attempt before execution.

Dependency: existing installation and original candidate must pass. This is one
changed recovery, not an unchanged retry or another admission. The original
600-second/256MiB limits still apply, including the failed command and recovery.
The child has 120 seconds and a unique installed-recovery log. On another
failure, preserve the result and continue independent original-task work; do
not repeat this recovery. No external action or production edit is involved.

Skeptical audit PASS: the collision is reproduced before evaluation, the target
package is independently inventoried, the comparator and substantive checker are
unchanged, and the new wrapper does not relax any financial, source or import
criterion. The only operational change is allowing result files to be written
beside an existing installation. The same successful isolated result is needed
before sealing. The inherited plan's prohibition on unchanged retries is
preserved, and no cumulative bound is reset.
