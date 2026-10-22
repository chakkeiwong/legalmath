# Prefreeze implementation review

The first focused run passed15 checks; five preflight cases all failed at the
shared synthetic request's missing authority description. The production
validator correctly refused the incomplete request before native launch.
Repair the fixture with an explicit synthetic authority and rerun the changed
checks. Retain prefreeze-tests.xml; this is no native experiment or package
failure.

Capture preserves source file modes through the existing snapshot API. The
installation driver must therefore prepare private copies of retained blobs
with each declared444/555 mode; the immutable old blobs must not be chmodded or
hardlinked for mutation. The resulting manifest must equal the old declarations
plus exact installed worker/native_inputs paths and necessary directories.
Record the private copies as temporary build material, not as a new source.

Installation command accounting counts every Popen observed in the supervising
driver, including venv's ensurepip launch. Native source children are counted
inside the installed command using a separate shared ledger. Internal pip/build
forks are not asserted to be enumerated; both counters are explicit supervised
lower bounds. No package/module code is installed into the worktree interpreter.
