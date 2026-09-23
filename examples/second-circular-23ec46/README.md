# A second circular: 23EC46's gift restriction

This is a manually authored, unreviewed candidate for paragraph 10. It tests the
existing workbench on a different regulatory requirement. It does not implement
the whole circular or test an automatic natural-language translator.

Read [the result and verification method](../../docs/implementation/second-circular-verification.md).
The source-based [oracle](oracle.json) was frozen before [the candidate](gift-control.bundle.json)
was constructed. Its classifications and expected answers still require independent
compliance review. `source-fetched.json` matches the retained official source byte
for byte; `source.txt` is the application's exact derivative.

From the repository root, use the isolated Python 3.11 environment and retained
JDK 17:

```sh
.venv/bin/python examples/second-circular-23ec46/prepare.py
.venv/bin/python examples/second-circular-23ec46/verify.py \
  --out /tmp/legalmath-second-circular-new
```

The output directory must be new or empty. Verification checks 22 named scenarios,
all 729 T/F/U assignments to the six inputs, four compiled erroneous candidates,
source-anchor tampering and the unresolved-dependency review block. It uses the
actual generated policy class in each candidate JAR. No API call to an LLM occurs.
The accepted application's 154-test evidence is checked for unchanged file hashes;
this new example does not rewrite it.

The retained final run is
`artifacts/runs/second-circular-23ec46-final`. It contains full cases/results,
the candidate Java source/JAR, build and verification manifests, mutation outcomes,
source inventory, unresolved dependencies and a fresh local database. The candidate
is DRAFT with five unresolved issues; there are no approvals or releases.

TRUE means this gift prohibition is triggered. FALSE means only that the selected
prohibition is not triggered on the supplied facts. Neither FALSE nor OUT_OF_SCOPE
is permission to market a product. An additional-return arrangement's legal
classification is an input to be reviewed, not a fact inferred by this program.
