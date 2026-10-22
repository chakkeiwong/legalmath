# Account for the retained OCR trace without certifying runtime closure

Question: can a reusable trace diagnostic preserve every retained event, resolve
descriptor-bound path observations, distinguish ordinary readlink EINVAL from
missing-file evidence, and leave genuinely unsupported events explicit?
This is a native-binding continuation within its second original admission.
It does not enter the blocked native-confinement/interfaces program.

## Baseline and evidence contract

The comparator is native-binding attempt001's sealed worker.trace, parser in
run_native.py, positive-trace-inputs.json and negative-lookups.json. The trace
contains2183 lines. Its parser inspects only the first quoted argument, skips
unquoted lines and leaves73 newfstatat and13 readlink events unclassified.
Those counts are explanatory; parsing every retained line does not prove that
strace observed every input or that the host was immutable.

Read installed strace, stat and readlink manual sections and retain their exact
bytes/hash with the run. They describe decoded descriptor paths, AT_EMPTY_PATH
and EINVAL; no new package or remote documentation is required. The current
failure is our parser's loss of syscall context, not a strace package failure.

Add a finite reusable diagnostic and a command-line consumer. It must bind the
trace bytes and report every line exactly once with original text/line number.
For supported calls it records syscall, PID, return/error, path argument role,
descriptor base and observed object type when present. Keep raw lexical paths;
do not normalize symlink-sensitive '..' through the current filesystem. Resolve
relative *at paths only from an explicit absolute decoded base. Plain relative
paths without a known base stay unresolved. AT_EMPTY_PATH refers to the decoded
descriptor, not an empty file name. readlink EINVAL is a failed operation,
not successful content-read evidence or an ENOENT observation. Truncated paths,
unfinished/resumed calls, unknown syscalls and ambiguous arguments stay explicit.
Never infer that a successful stat/open read file content.

Primary pass criterion: exact raw-line accounting; preserve every supported
baseline path/ENOENT observation; explain the86 retained omissions by source
semantics; adverse inputs cannot become successful path claims; the installed
CLI produces the same report as the library and refuses a changed trace hash.
Retained actual OCR pages/geometry and final questions remain hash-protected.
This offline observation consumer is additional engineering evidence, not new
OCR, a fresh P1–P5 assessment or a completed source task.

Hard vetoes: altered sealed input, dropped/duplicated lines, inferred missing
path on EINVAL, repaired-looking truncation, or any native reuse/closure claim.
Unknown unsupported event forms are repair diagnostics and remain visible.
No performance ranking, scientific comparison or legal inference is planned.
Artifacts: admitted attempt002 trace report, matched comparison, tests, CLI
positive/refusal results, exact methods, manifests, RESULT and next-route review.

## Assumptions and skeptical audit

The supported grammar comes from the retained command (-f -yy -s4096 with
file/process calls) and local installed manuals; arbitrary strace options are
not assumed equivalent. A decoded path is a contemporaneous reported name,
not immutable bytes or proof of path identity. Retained success and error
outcomes are classified without querying the live filesystem. Unsupported
escaping/relative bases remain unresolved. Counts cannot promote reuse.

Skeptical audit PASS for finite accounting only: the original parser and actual
trace are the baseline, no easy successful scan replaces them, and meaningful
adverse cases target the ambiguous grammar. Downstream effect is a more precise
native-input diagnostic; no claim that this changes a legal answer or completes
native closure. If the report adds no observations beyond existing paths, say
so rather than claiming additional dependency coverage.

Run bounded stages with timeout120, one-second yields, small outputs, CPU only,
worktree src pin and at most5MB new evidence. No installs, network, GPU, host
policy changes, new OCR invocation or git writes. Preserve historical seals.
Seal once, record/refresh and inspect other justified independent routes.
