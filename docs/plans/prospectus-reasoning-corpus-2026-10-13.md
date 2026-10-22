# Bounded Boolean reasoning comparison

The admitted reasoning-corpus task tests the implementation's Boolean decisions
and retained explanations. It does not test whether supplied English-to-logic
readings are legally complete. The prior tests mainly exercise a two-variable
correlation and one 13-fact conjunction. Expand to conjunction, disjunction,
mixed signs, negation, tautology, contradiction and implication at the 12/13-fact
boundary, with open, determined, irrelevant and conflicting observations.

Use a separately implemented exhaustive bit-vector oracle with direct formula
functions. It must not call production names/evaluate/possible_decision or Z3 to
compute expectations. Predeclare every formula and scenario before execution.
Compare the production finite engine (up to 12 distinct facts), the explicit
Z3 engine and actual P4-to-answer consumption. Check witnesses against the
separate formula functions and observations. Test source-bound named correlated
and inconsistent premises, verifying unsat-core sufficiency by enumeration;
do not assume core minimality. Exercise construction and clause paths with
larger formulas, and preserve typed domain exhaustion above supported limits.

Source contract: generated formula/fact files are clearly synthetic engineering
sources. They supply source identities for testing the service, not purported
legal authority or client facts. The two retained CJEU conditional rules remain
separate source-reading evidence from law-applicability; no new legal reading
is inferred from a larger synthetic corpus. Independence here means a separate
software oracle, not independent legal adjudication.

Primary criterion is exact status equality within the declared domain, valid
counterexample/witness assignments, sufficient inconsistent cores, exact source
anchors and explanations preserved through the actual answer. The finite
engine's 12-fact refusal and Z3's 256-fact refusal are expected typed limitations,
not incorrect Boolean answers. Default routing remains finite; this comparison
does not justify a default change. Timing and case counts are explanatory only.

Assumption audit: the 12 and 256 limits and 1-second-per-check Z3 timeout are
inherited explicit contracts, not capacity estimates. The corpus crosses the
small limit but is deliberately tractable for exhaustive enumeration. The
closed Boolean vocabulary is an engineering domain; missing evidence remains
open over its completions, and explicit relevant conflict takes priority over
tautological simplification. The smallest checks distinguish witness validity,
unsupported-domain handling, and interpretation mistakes. No stochastic ranking
or unrestricted complexity claim follows.

Skeptical audit PASS after correcting the prior test-oracle pattern: the new
reference cannot reuse production predicate evaluation. Source authenticity,
legal formalization and explanation minimality remain promotion vetoes. Source
corruption, a wrong checkout, absent solver, mismatched Boolean output or missing
diagnostics veto this run and trigger a bounded repair. Expected finite refusal
does not stop the Z3 route or subsequent independent tasks.

Run CPU only with GPU intentionally hidden, pinned worktree imports, 120-second
commands and one-second yields. Retain formulas/expectations before calls,
method/source hashes, git/environment, actual reports, wall time, result and
next action in the admitted attempt. Use at most 20 MB of new evidence. After
recording, refresh and continue the next ready task without a checkpoint handoff.
