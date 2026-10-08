# S4 implementation review and causal repairs

6 October 2026. S3 verified before changes; 606 files frozen in the S4 baseline.
The revised plan separates fixed four-state evidence from positive recursive
heads, preventing an invalid monotonicity assumption. The generic inductive
leastness theorems compile under Lean 4.20.0.

Initial Lean construction checks exposed two elaboration issues: overloaded
Boolean equality did not unfold as the intended Nat.beq lemma, and finite list
membership/decidability were not inferred through named definitions. The first
was made explicit; after the two initial checks the generation plan is refined
to enumerate finite membership, unfold the exact fact predicate, and prove
closure separately for each actual rule rather than ask Lean to decide an
unrestricted quantifier over Rule.

Proof policy clarification: Lean's core propext and Quot.sound axioms are permitted
and reported by exact name; arbitrary axioms and sorryAx remain rejected. The
generic soundness/closure/leastness propositions themselves need no axioms.
This is a new registered scope, not reuse of the older no-axiom Boolean profile.
The use of standard logical axioms does not add a legal premise. Certificate
generation is always from validated numeric data and fixed code.

The proof checker never executes receipt-supplied code. Requested and Java-decoded
theories must agree, hashes and semantic indices are checked, derivation witnesses
must be ordered, and each returned set must be closed. The remaining trust
boundaries are the source-to-IR mapping, codecs, proof encoder, toolchain and
supplied legal/evidence premises; finite checks cannot make universal claims
about these components.


## Pre-execution skeptical review

The focused runtime suite passed 26 tests, including all four support codes,
400 small parent-graph/evidence combinations against closed-set enumeration,
seeded and unseeded cycles, alternative rules, joint parents, a 64-head chain,
maximum fact/parent arities, strict malformed-wire rejection, Unicode hashing,
missing/nonclosed outputs, decoded-input substitution and a rehashed forged
proof. The v4 actual-investigation suite passed seven tests in 62.72 seconds;
seven master dispatch tests also passed. These are engineering diagnostics,
not legal answer labels or an estimate of interpretation accuracy.

A post-kernel receipt check initially failed on an over-escaped Python regular
expression. The expression was repaired, successful Lean theorem output is now
required explicitly, and a fresh Java/Lean verification passed. No failed check
was converted into a completed receipt.

Baseline review: all source/evidence development computations are compared to
the frozen S3 result, not regenerated and silently relabelled as S3. The 606-file
snapshot and pre-edit S3 verification are hash-bound. Two existing source/test
files change: integration.py and test_master_resume.py. Additions implement
the new profile. pyproject.toml receives only the Lean/Java package resource
patterns; removing those exact additions must restore its pre-edit dirty SHA256
8206b263d4208b311205c79c07394311273e7979c3af87bffdcdac25a1e0f0c2.
No prospectus or unrelated assurance changes are authorized by this phase.

| Audit issue | Finding and disposition |
|---|---|
| Wrong baseline | S3 source inputs and conditional statuses are compared exactly; historical verifier is not rerun under new dependencies. |
| Proxy promotion | Tests and finite enumeration challenge implementation only. Each retained actual numeric result separately receives a kernel-checked sound/closed witness. |
| Hidden assumption | Fixed extensional evidence is essential. Dynamic negatives, recursive defeasible arguments, source-to-rule truth and codec/compiler correctness remain excluded. |
| Unfair comparison | Python iteration, Java agenda and independent closed-set intersection share only the stated numeric theory. No legal superiority ranking is made. |
| Stale context | Explicit v4 profile/context; new Java/Lean bytes and Lean executable bound to configuration. v2/v3 remain separately identified. |
| Environment mismatch | Installed Python, JDK and pinned Lean; CPU only, no installations or provider calls. Tool identities are retained. |
| Missing stop condition | Bounded IR, Java/Lean timeouts, 1200-second suite timeout, immutable failed attempts, lock, two causal failures before revised audit. |
| Uninformative artifact | Actual CompleteInvestigation and whole-stage replay retain original/decoded inputs, mappings, branch associations, binaries and regenerated proofs; source lowering is still qualified. |

The runtime checker validates retained hashes then rebuilds Java classes and
Lean code from trusted source and validated data. It never executes a proof
or command supplied by a receipt. A forged retained proof is rejected even if
its stored hash is changed to match it. Source labels and modalities stay in
the lowering map; numeric derivability cannot establish their legal meaning.

The new reading inventory preserves every one of the 35 originals and both
role records individually. All 32 unformalized readings stay unformalized.
The legacy S3 standards computation retains its original Python-layer
NOT_IMPLEMENTED marker; the additional v4 conditional_runtime receipt records
the new lowering and proof. The relation to legacy Boolean trigger formulas
remains NOT_ESTABLISHED. This avoids rewriting historical semantics.

Audit verdict: PASS_FOR_FIXED_S4_EXECUTION. Run the affected suite once under
the master handler, followed by eight retained recursive checks, the actual
v4 investigation and independent verification. A missing legal premise remains
a promotion veto; it does not invalidate the qualified engineering question.

The refreshed S5 plan must first inspect residual source-to-rule work. It may
freeze a prospective whole method only with real dates and stated sampling
rules. Current sources and synthetic examples cannot become future observations.
