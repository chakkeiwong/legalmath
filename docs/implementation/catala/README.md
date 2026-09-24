# Catala pilot

This branch adds two independently authored Catala definitions and a bounded
adapter for four frozen RuleIR bundle versions. One definition calculates the
SPI financial subcondition. The other tests synthetic defaults and exceptions.
RuleIR remains the independent reference and the current release engine.

The eight-phase plan is in `docs/plans/catala-adapter.md`; the executable is
`scripts/catala_master_program.py`. `program-review.md` records the audit and
`program-review.json` binds it to exact files. The master does not install tools
or access the network. The optional `prepare_catala_toolchain.py` builds an
isolated toolchain from previously downloaded official opam/Ninja binaries and
the pinned Catala source; its opam dependency downloads are explicit.

From the Catala worktree, the reviewed local execution command is:

```bash
PYTHONPATH=src /home/chakwong/python/legalmath/.venv/bin/python scripts/catala_master_program.py \
  --out artifacts/catala/run-01 \
  --catala .localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala \
  --upstream .localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa \
  --jdk /home/chakwong/python/legalmath/.localresources/java-toolchain/jdk-17.0.20.1+1
```

Use a new output directory for each attempt. If code, tests, profile, plan or
toolchain changes, review the changes and replace the review fingerprint before
execution. A different machine may produce a different compiler binary: source
pinning is retained, but its new binary and dependency inventory need review.

`legalmath.catala.runtime.evaluate_package` validates a draft request and invokes
the checked Java calculation package. The caller supplies the trusted package
manifest hash. The returned status distinguishes true, false, unknown, conflict,
out-of-scope and version errors; it also identifies which layer made the decision.
It includes source/version commitments and evidence identifiers but uses its own
source-map format, not a fabricated RuleIR trace. Production mode is rejected.

The compiled `CatalaPilotHost` accepts typed `scope`/`inputs` JSON after the Python
validation boundary. It is not a standalone raw-fact validation or transaction
authorization API. The current host/release interfaces remain the next integration
work, along with broader semantics and a human reviewer study.

Pinned source inspection: [Catala 1.2.1](https://github.com/CatalaLang/catala/tree/1.2.1),
[equal-consequence test](https://github.com/CatalaLang/catala/blob/1.2.1/tests/exception/good/two_exceptions_same_outcome.catala_en).
The implementation does not infer whole-compiler or legal correctness from the
upstream formalization or from this finite comparison.
