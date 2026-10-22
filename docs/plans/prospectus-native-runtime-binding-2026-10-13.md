# Native OCR input observation

Question: can the real OCR result retain the native libraries and selected
environment inputs that actually affected the worker, and can changed or formerly
absent paths be detected without claiming a complete native boundary?

The baseline is the current OCR worker: it hashes its PyMuPDF distribution but
inherits the parent environment and does not report the loaded system libraries.
Keep its execution behavior and reuse veto. Add a bounded observation module
which hashes regular files, resolved paths, absent lookups and a named set of
noncredential environment values. The worker will report mapped file identities
after OCR, plus its effective selected environment. These are observations, not
an immutable runtime, a sandbox or proof that every input was observed.

The primary criterion is exact equality of extracted pages/text/word geometry
and all downstream question results with the retained synthetic two-page scan.
New receipt metadata may change. Actual mapped native libraries must appear in
the consumer source graph. Separate finite controls must detect file edits,
deletion, symlink retargeting, a missing path becoming present and an environment
change. Compare an actual strace run with an untraced worker; retain successful
file and missing-path observations, with unresolved/proc/directory accesses
explicit. The positive source is synthetic engineering evidence, not a real
prospectus or independent gold. Real multilingual recovery follows separately.

The research intent is to repair input observability. A missing trace capability
blocks that subcomparison only; independent worker and mutation controls continue.
Lost text/geometry, corrupt bindings or changed answers veto the patch. A complete
native closure and cross-host currentness are not promotion claims. Missing
proc maps must be reported as unavailable, not silently converted to an empty
successful inventory. Reuse remains false for unconfined native invocations.

Assumptions: Linux proc maps are a late snapshot and may miss unloaded libraries,
data reads and races. A strace observation is finite and host-specific. The
environment list is explicit but incomplete; hash values instead of dumping the
host environment. Existing CPU-hiding and thread limits are inherited baseline
settings, not performance recommendations. No GPU, installation or live API is
needed. Hashing uses regular files only and refuses nonregular inputs.

Skeptical audit PASS with those limits: unchanged extraction is the comparator,
not a test count; actual consumer propagation is required. The probe cannot
close confinement or legal acceptance. Stop after the bounded controls or a
source/method corruption; record the real result and continue independent tasks.
Use one-second tool yields, at most 120 seconds per command and 30 MB evidence.
Retain commands, method/source/environment identities, results and a decision
table under the admitted native-binding attempt. Historical manifests stay sealed.
