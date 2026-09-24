# Catala branch reset memo

Worktree: `/home/chakwong/python/legalmath/.worktrees/catala`.
Branch: `feature/catala-adapter`.
Base: pushed main commit `66d15b2aee8f0c00076ab1dd24334b5f80dac058`.

The user authorized committing/pushing main, creating this separate branch,
creating an eight-phase master program, reviewing it and executing it. Those
execution steps are complete. Main has a separate active worker; do not reset,
stash, stage or overwrite its later changes while continuing Catala work.

Read `execution-report.md` for the outcome. Final evidence is run 03: all eight
stages executed, 112 exact comparison cases pass, 82 actually execute Catala,
two mutations detected, four reference Java builds, package and separate Java
caller checks pass. The local regression suite passes 126 tests. Run 01 failed
on a missing diagnostic message; run 02 passed before final identity and reviewer
delivery improvements. Retain all three runs.

No default replacement or merge occurred. The adapter accepts draft mode and
four exact reviewed bundles only. Full RuleIR traces, arbitrary rule translation,
the existing transaction/release path and human reviewer benefit remain pending.
The next work is described in the execution report. Do not interpret the phase
PASS statuses as proof that those adoption requirements were fulfilled.

Toolchain: `.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala`.
Upstream source: `.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa`.
JDK: parent checkout's `.localresources/java-toolchain/jdk-17.0.20.1+1`.
Python: `/home/chakwong/python/legalmath/.venv/bin/python` with worktree `PYTHONPATH=src`.
The local JDK directory is an ignored symlink. No global toolchain changes.

`scripts/prepare_catala_toolchain.py` deliberately constructs a small environment:
removing only PATH or the obvious compiler variables was insufficient because
Conda also set build/host aliases. Earlier failed switches are ignored local
diagnostic material; the `catala-clean-1.2.1` switch is the accepted one.

The master runner requires the exact reviewed input hashes. Any substantive
change needs review and a renewed fingerprint, then a new output directory.
Program review is the implementing agent's skeptical review, not a human or
independent legal assessment. The two rendered PDFs were inspected provisionally.
