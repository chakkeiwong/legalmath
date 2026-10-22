# Retained native trace events are now accounted for

The reusable trace diagnostic and hash-bound CLI preserve all 2,183 original
lines exactly once. The retained trace contains 1,659 successful path operations,
509 ENOENT operations on 438 distinct paths, 13 other failed operations and two
process-exit records. The original parser's 86 unexplained lines comprise 73
descriptor-based newfstatat calls (51 regular-file and 22 directory observations)
and 13 readlink EINVAL results. These failures remain failures, not missing-file
or file-content-read evidence.

Two distinct successful-operation paths were omitted by the earlier first-quote
parser: /etc/locale.alias and /usr/share/zoneinfo/Asia/Hong_Kong. Their names are
present in the retained decoded descriptors. The new parser preserves them
without consulting or resolving the current filesystem. The earlier 327
successful-operation paths and all 438 ENOENT paths remain; there are now 329
distinct successful-operation paths. These are operation observations, not a
new immutable dependency set.

The CLI consumes the real retained trace and returns exactly the library report.
A wrong expected hash refuses before writing output. Thirty-one focused tests
pass, covering descriptor/relative paths, symlink-sensitive '..', exact escaping,
empty-path semantics, truncation, unsupported calls, interruptions, unknown bases,
distinct readlink input/output paths and retention of every line. Unsupported
syntax stays explicit. No existing extraction, source graph or reuse policy
was changed. The original actual OCR pages/geometry and consumer bytes remain
hash-identical. No new OCR or P1–P5 run was performed or claimed.

The inspected local strace/stat/readlink manuals are retained with hashes.
The earlier reader command failed after printing stat/readlink excerpts because
it searched an unescaped roff option name; a bounded follow-up read the actual
escaped spelling. This was a documentation-reading error, not a package failure.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain trace-accounting repair | Every actual line and original path observation preserved; CLI and adverse checks pass | No silent ambiguity, dropped line, changed protected source or reuse claim | Other syscall/options syntax and untraced inputs | Use explicit unresolved event records in future admitted trace work | Complete native input closure, current host state, race freedom, confinement or portability |
| Keep native-binding partial | Two omitted successful-operation paths recovered and 86 unexplained events classified | Immutable supported runtime and full input coverage remain absent | Dynamic paths, environment omissions, transient libraries and runtime races | Review all independent remaining task routes; blocked native prerequisites remain binding | OCR or native package fully evaluated, legal answer improved, or authority completion |

The observed parser gap belongs to our code. No fundamental strace defect is
established. The strongest alternative explanation for a stronger coverage
claim is that file/process tracing omits relevant inputs and the one source
does not exercise optional code. A supported immutable runtime and broader
reviewed evidence would be needed to remove that limitation. A parser's complete
accounting of this finite log cannot do so. Native reuse remains false.
