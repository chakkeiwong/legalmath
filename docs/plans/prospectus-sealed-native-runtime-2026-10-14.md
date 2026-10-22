# Sealed native inputs before runtime integration

The next question is whether the existing CPU OCR worker can execute from a
finite, hash-bound filesystem whose file bytes cannot change after verification.
Native-binding002 repaired trace interpretation; it did not fix mutable host
mounts. This is a changed mechanism within native-binding, preserving both prior
admissions. It does not bypass native-confinement's incomplete predecessor.

Use Linux memfd seals and Bubblewrap's --ro-bind-data: verify bytes copied into
memory, apply WRITE/GROW/SHRINK/SEAL seals, then let Bubblewrap copy those sealed
descriptors into read-only file mounts. Start with an empty namespace, no host
directory mounts, explicit directories, cleared environment, private network/PID
namespaces, a fresh procfs, minimal /dev and a writable temporary directory.
Remount the root read-only after setup. Root/proc/device/kernel behavior is an
explicit boundary, not an assertion that all computation inputs are file bytes.

The supported candidate is this installed Linux/Bubblewrap 0.6.1 and the existing
tfgpu Python/PyMuPDF CPU worker, with eng and por models. Do not install or change
the host environment. Retain exact file hashes, paths, permissions, declared
directory names, environment, argv, stdin and kernel/tool versions. A runtime
inventory proposed from the actual old trace is a starting candidate only:
closed execution and exact output comparisons test it. No trace count promotes
dependency completeness. Any missing runtime file requires an identified,
recorded inventory repair; never fall back to broad host mounts.

## Evidence contract and skeptical audit

Primary criteria: exact source hashes, page images, complete OCR text and word
geometry for the original two-page English scan and Portuguese2010 pages88–89,
plus complete question objects and source units from fresh matched downstream
consumers. Runtime provenance is allowed to differ and must reach the consumer.
Both consumer arms must consume their own actual worker output; retain any test
adapter explicitly and do not call that production integration. The existing
worker and source/interpretation code remain unchanged. A reusable optional
launcher and CLI may be added; no automatic selection or cache reuse promotion.

Boundary controls require sealed files to reject writes, shrink and growth;
wrong hashes, malformed/duplicate/escaping destinations and nonregular source
files to refuse; mutation of the host input after capture to leave the running
copy unchanged; direct/child/symlink reads of undeclared host files to fail;
host files created after capture to remain absent; declared files/root to reject
writes; inherited environment additions to remain absent; and network isolation
to be observable. Missing language models must refuse, not yield empty success.

All these checks are promotion criteria for the finite launcher only. Unequal
OCR/pages/questions, a leaked host path, mutable mounted bytes, corrupt manifests,
permission refusal or unsupported namespace capability veto this candidate.
Only corruption, changed admitted inputs, invalid comparisons or exhausted
reviewed repair bounds stop dependent work. An expected missing dependency
triggers the bounded inventory repair. Source/reader gaps veto legal or product
promotion, not this local engineering investigation. Runtime/file counts and
timing are explanatory only. No statistical ranking is intended.

Audit PASS: the comparator is actual complete output, not a successful launch;
negative paths and environment are controlled by construction and adverse
checks rather than merely enumerated from one trace. Sealed descriptors address
the identified verify/use file race. The kernel, Bubblewrap setup, CPU features,
procfs and devices remain explicit trust/runtime assumptions. A compromised
host or arbitrary hostile code is outside this finite reproducibility claim.
Passing these checks alone cannot authorize cache reuse, declare all source
families supported, prove cross-host portability or independent legal truth.

Defaults: Python/native versions and 300dpi come from the existing comparator,
not a tuning result. CPU hiding and one OCR thread preserve the original worker
policy. C.UTF-8/UTC, no user site and no bytecode writes are explicit runtime
hypotheses; first compare full English and Portuguese outputs. The file/command
limits below are resource bounds, not performance criteria. Fixed hash seed is
for reproducible enumeration, not scientific evidence. Same implementation in
both arms is a remaining correctness risk constrained by retained original
outputs and adverse controls, not removed by equality.

The checked local manuals are bwrap(1), memfd_create(2) and fcntl(2). Retain their
bytes/hashes and the sections on read-only descriptor copies, required seals,
root remount and environment clearing. --clearenv retains PWD: explicitly set
the working directory/PWD. WRITE alone is insufficient: GROW and SHRINK are
required too. Seal verification must happen before the child receives the file.

## Ordered execution and bounds

1. Review revision57, extending native-binding's cumulative admissions2→3 for
   this distinct runtime mechanism. Preserve all59 obligations,44 tasks and
   the two previous admissions. Freeze this plan and the previous evidence.
2. Implement an optional manifest/snapshot launcher with strict path/byte/size
   checks. Retain a closed candidate runtime and run focused boundary controls.
   Use actual OS operations, not mocks, for seals and namespace behavior. An
   outer sandbox namespace denial must be rerun in an approved trusted context;
   it is not evidence of a package defect. Do not alter host permissions.
3. Run one ordinary and one sealed OCR arm per source, retaining actual outputs.
   Allow at most two identified inventory/launcher repairs in this admission,
   each with a written diagnosis before the changed retry. Maximum twelve child
   process invocations including boundary controls and repaired OCR runs.
4. After OCR matches, run fresh downstream source/answer consumers for both arms
   in separate short stages. Compare complete questions, all source units and
   actual native provenance. Do not normalize unresolved identifiers.
5. Record the observed result and all failed commands, seal once, record and
   refresh the authority. Review any genuinely ready successor. A successful
   prototype still needs a reviewed task-specific acceptance and production
   integration before native-confinement or portability can close.

Every stage is bounded by120 seconds, uses a one-second tool yield and a retained
session identity. Each child is bounded by60 seconds. Runtime data is capped at
512MiB and2048 files; manifests/control outputs at30MiB; each captured stream at
20MiB. Exceeding a bound stops that stage. No repeated unchanged launch, network
request, dependency install, GPU initialization or external communication is
part of this experiment. Results go in the admitted native-binding attempt003,
with command, git identity, exact environment, CPU/seeds, wall time, source/method
hashes, result paths, decision table and post-run alternative explanation.
