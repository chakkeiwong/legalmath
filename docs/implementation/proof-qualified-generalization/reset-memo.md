# Reset memo: proof-qualified generalization

28 September 2026. Controlling user requirement: humans must never be used for
quality purposes. No human answer keys, adjudication, ratings, approval or
acceptance gates. Prove the scoped proposition with machine checks or issue an
explicit qualification. Generalization to unseen inputs and future situations
is a core product goal. Human-benefit and institutional deployment are excluded.

Implemented package: `legalmath.qualification`. Public commands:
`legalmath rules assure`, `legalmath rules verify-assurance`, and
`python -m legalmath.qualification freeze|admit|repair|report`. The Python
`prospective.observe` API verifies actual proof and runtime evidence before
recording an observation; it does not accept quality grades.

The route accepts shared v1/v2 models, independently parses the original formal
expressions, runs Lean on a regenerated constructor-preservation proposition,
executes RuleIR and direct native Catala, and compares supported complete inputs
against independent exact expression evaluation. Unsupported partial/reference
domains remain qualified. All candidate/backend rows and source uncertainty are
retained. Current report claims about legal meaning and unknown future legal
generalization remain NOT_ESTABLISHED.

The generated campaign discovered negative scale accepted by the shared model
but rejected by RuleIR's nonnegative-numerator schema. The reviewed repair in
`translation/ruleir.py` lowers negative scale to zero minus positive exact scale.
It preserves old nonnegative output identities. Integer sign and exact-domain
lemmas live in `qualification/Lowering.lean`; actual runtime tests cover nested
signs, indivisibility and large inputs.

Final evidence: `artifacts/proof-qualified-generalization/2026-09-28/attempt-02`:
four models, 31 backend-case checks, 175 outputs, two supported constructor proofs,
amendment/stale-revision rejection and explicit 41-input resource rejection.
The failed first campaign is preserved. No machine-generated repaired challenge
is represented as untouched confirmation. Final regression: 284 passed, no skips,
669.24 seconds, method hashes unchanged; three supplemental observation checks
passed separately. Offline wheel packaging includes the checked Lean source.

The future window has no observations. Its commitment, dates and source/method
limits are in results.md. Repaired or already-used sources cannot become fresh
confirmation. Local clocks and self-contained hashes do not authenticate sources;
retain event heads externally. Future interpreter model/provider/prompt versions,
complete acquisition and original-question alignment need explicit additional
binding before a source-quality claim.

Concurrent main contains substantial uncommitted assurance/manuscript work.
Do not stage it wholesale, revert it, consume its model allowance or claim this
increment completed that campaign. The two edited shared entry/protocol documents
retain their surrounding work. Historical human-reference proposals are
superseded, not rewritten into new evidence. No monograph or PDF was rebuilt in
this increment. See remaining-work.md for the technical extensions and their
specific closure criteria.
