# B4 pre-execution audit: paired evaluation and its real limits

The question is whether independent readers, search and source assurance reduce
unsafe accepted interpretations while still returning useful answers. Comparator
arms are a single reader, isolated readers, the existing bounded search, and the
existing assurance engine. Source bytes, assessment time, task, maximum call/byte/
time budgets and source availability must be equal across arms. Actual consumption
may differ and must be reported. No arm may see the hidden labels or peer output.

Separate two target quantities: detecting explicitly seeded English changes, and
matching independently supported legal outcomes. A seeded defect label does not
answer the complete underlying legal question. Public worked examples with explicit
outcomes can supply outcome evidence; developer/model-written expected answers
alone cannot. A development-family case cannot be relabelled as held out.

Freeze case/source/family identities and labels before dispatch. Retain every arm
and case, including failure, missing output and abstention. Pair comparisons by
source family rather than treating paraphrases of one circular as independent
samples. Report unsafe acceptance, correct acceptance, abstention and missing
judgments together. Confidence intervals describe the declared sampling assumption;
they do not turn a convenience sample into a bank-wide error bound. Stop promotion
on source/budget mismatch, contamination, missing outcomes or unexecuted arms.

PASS WITH LIMITS for harness implementation and deterministic negative controls.
The remaining authorized live allowance is 22 calls. The current full assurance
path needs at least seven model actions before any repair. Four equal-cap arms
at that minimum require a worst-case reservation of 28 calls for just one case,
and at least 56 for a clean/altered pair. The complete predeclared comparison
cannot be admitted within 22 calls. Do not run selected arms, cap away source
checks, reset the ledger, or call scripted fixtures a live comparison. Preserve
an explicit UNDER_BUDGETED empirical status and continue independent B5 engineering.

The engineering harness must demonstrate that it refuses insufficient allowances,
leaked labels, missing pairs, changed source hashes and unequal resource ceilings.
Uncertainty tests include all-abstain and a deliberately worse treatment so that
the reporting logic cannot manufacture an improvement. An evaluation can be
complete as an engineering exercise while empirical promotion remains blocked.

No population accuracy or review-cost reduction is currently established. A funded
study needs a predeclared target corpus/sampling scheme, independent outcome
evidence where obtainable, family-level replication and a budget tied to that
design. B4's mechanics do not require commissioning an external legal consultancy.

## Uncertainty calculation used by the harness

For each circular family average the unsafe-acceptance indicators within an arm,
then subtract the baseline family's average. The resulting paired difference
\(X_i\) lies in \([-1,1]\); variants within a family are not independent trials.
For an independent family, let \(g(t)=\log E\exp(t(X_i-E X_i))\).
We have \(g(0)=g'(0)=0\), and \(g''(t)\) is the variance under exponential
tilting. Any distribution on an interval of length two has variance at most one
(centre at the interval midpoint and use variance no larger than mean squared
distance from that midpoint). Integrating twice gives \(g(t)\leq t^2/2\).
Independence and the exponential Markov inequality then give
\(P(\bar X-E\bar X\geq r)\leq\inf_{t>0}\exp[-ntr+nt^2/2]
=\exp(-nr^2/2)\). Apply the same argument to the negative tail. A union bound
over unsafe acceptance and useful coverage for three baseline comparisons yields
simultaneous radius \(r=\sqrt{2\log(12/\alpha)/n}\). Intersect intervals with
\([-1,1]\). Without independent family sampling this remains a conditional
calculation and cannot support a population ranking. With one development family
the intervals are uninformative, as they should be.

The local two-case fixture uses a reviewed convenience cap of eight calls per
arm, giving a 64-call reservation, and a 5% simultaneous error parameter only to
test the reporting arithmetic. These are not promoted study defaults. Useful
coverage means a correctly accepted finite-scenario answer, so abstaining on
everything cannot satisfy its non-inferiority criterion. Actual wall time is
recorded and exceeding the shared ceiling vetoes promotion; provider deadlines
and Java subprocess timeouts bound their respective stages.
