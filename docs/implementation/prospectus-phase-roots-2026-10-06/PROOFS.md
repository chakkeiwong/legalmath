# What the proposed repairs can prove

These are mathematical arguments about explicit algorithms and supplied
representations, accompanied by finite executable checks. They are **not
machine-checked proofs**, proofs of English/German interpretation, or proofs
that production P0–P6 has been repaired.

The [executable specifications](../../../scripts/prospectus_phase_reference.py)
and [checker](../../../scripts/check_prospectus_phase_reference.py) are isolated
from production. The checker uses independent truth-table and arithmetic
oracles where applicable. Its manifest records code hashes and environment.

## 1. Source coverage distinguishes occurrences

Let a verified source unit \(u\) have text \(s_u\), identified by document-edition
hash, document id and unit id. Accept an evidence span \((u,a,b,q)\) only if
\(0\leq a<b\leq |s_u|\) and \(q=s_u[a:b]\). Define

\[
 C_u=\bigcup_{(u,a,b,q)\in E}\{a,a+1,\ldots,b-1\}.
\]

A unit is fully covered in this reference iff all non-whitespace positions
belong to \(C_u\). Production must separately justify semantic roles and
excluded units; coverage alone is not meaning.

**Proposition.** Equal quotations at different positions cannot be confused.
A group crossing units covers the union of its constituent intervals.

**Proof.** Membership depends on \(u,a,b\), not searching for \(q\). Equal
strings at different intervals contribute different position sets. Union
accepts any number of spans in each unit. Omitting a repeated occurrence leaves
its positions uncovered unless another explicit span covers them. This removes
both first-occurrence searching and the single-unit restriction. □

Paragraph assembly concatenates known ordered line fragments with marked
separators. Each copied character retains its original unit/offset. Induction
on the number of fragments proves preservation. Repartitioning a sentence at
spaces leaves its normalized text unchanged, provided reading order and
paragraph membership are unchanged. All 64 partitions of the seven-word
fixture passed, including multi-unit coverage and character-map checks.
This proves neither automatic layout recovery nor OCR/dehyphenation accuracy.

## 2. Contract construction retains admitted alternatives

Consider a finite AST of source text, sequences and named choices. Assume unique
choice identities and correctly supplied alternatives/constraints from the
contract and final terms. The prototype assumes independent choices; production
must represent correlations rather than import that convenience assumption.

Let \(\Sigma\) be the nonempty admitted complete selections. Rendering
\(R(T,\sigma)\) copies a source leaf, concatenates sequence children and renders
the branch chosen by \(\sigma\). Invisible leaves contribute no text; production
requires an explicit reason for that exclusion. Unknown choices have no default.

**Proposition.** Enumerating all \(\sigma\in\Sigma\) retains every admitted
rendering, and every copied character maps to the corresponding verified source
character. A fixed selection preserves unchanged characters in sequence order.

**Proof.** Structural induction. Exact span validation gives the leaf case.
A sequence concatenates established child mappings. A choice renders its
selected admitted child, to which induction applies. Enumeration visits every
admitted selection, so none of those renderings is omitted. □

Six amount/currency selections passed, with invisible-source exclusion.
This does not prove BASF's brackets, substitutions or priorities were read
correctly. The prototype rejects unsupported AST types; Fields, References,
Overrides and automatic parsing remain production work. Amendment correctness
requires a specified precedence relation and a conflict result when it cannot
select a unique interpretation.

## 3. Relevance is graph reachability, not a global flag

Let \(G=(V,E)\) be a complete graph of selected-contract dependencies,
\(R_q\) the roots for question \(q\), and \(U\) unresolved nodes. The relevant
unresolved set is \(\operatorname{Reach}_G(R_q)\cap U\).

An unresolved node outside reachability cannot change this set. Every unresolved
node on a dependency path belongs to it by definition. A visited-set traversal
terminates on finite graphs, including cycles. Termination does not itself
provide an interpretation of cyclic legal definitions.

The reference shows an excluded header's Section 14 does not block repayment,
but connecting it through a required definition does. Completeness of \(G\)
and correctness of \(R_q\) are essential assumptions. An omitted edge, arbitrary
exclusion, model relevance score, or unverified RESOLVED string invalidates
the conclusion.

## 4. A false necessary premise cannot produce YES

Let \(P\) be finite Boolean facts, \(o\) consistent partial observations, and
\(W(o)\) all total Boolean assignments extending \(o\). For a reviewed formula
\(\phi\), define

\[
 A(\phi,o)=
 \begin{cases}
 \mathrm{YES},&\forall w\in W(o),\ \phi(w)=1,\\
 \mathrm{NO},&\forall w\in W(o),\ \phi(w)=0,\\
 \mathrm{UNKNOWN},&\text{otherwise}.
 \end{cases}
\]

Inconsistent observations return CONFLICT first. If future admissibility
constraints leave no worlds, report inconsistent assumptions rather than a
vacuous YES. The reused possible_decision has no constraint filter: its
consistent independent Boolean observation space is nonempty.

**Proposition.** YES/NO are sound for this representation. If a necessary
conjunct \(p\) is observed false, YES is impossible. A decisive result survives
consistent evidence refinement with a nonempty set of remaining worlds.

**Proof.** Enumeration visits every missing-fact assignment once. Structural
induction on atoms, negation, conjunction and disjunction establishes agreement
of the recursive interpreter with the formula truth function. YES thus means
truth in every completion; NO is symmetric. For \(\phi=p\land\psi\) and
\(o(p)=0\), every completion makes \(\phi=0\). Finally, refinement gives
\(W(o')\subseteq W(o)\); a constant truth value remains constant on a nonempty
subset. □

The checker considered **every Boolean function of one, two and three variables**
and all partial observations: 7,068 independent truth-table comparisons and
6,052 full completions of decisive answers. Negation, additional false premises
and contradictions were included. Finite checks support the general argument;
they are not a formal proof of Python or an arbitrary legal theory.

Conflicts are handled conservatively: a conflict in any declared relevant fact
blocks a definite answer even when a stronger analysis might show that fact
immaterial. This sacrifices completeness rather than inventing a resolution.

## 5. A contractual feature differs from an actual event

Let \(\mathcal C\) be admissible readings and \(\Omega_C\) nonempty admissible
contingencies for reading \(C\). For loss predicate \(L\),

\[
 F(C)=\exists\omega\in\Omega_C:L(C,\omega).
\]

A definite feature answer is YES if all readings have \(F(C)=1\), NO if all
have \(F(C)=0\), UNKNOWN otherwise. Actual loss evaluates \(L\) for dated
event observations.

**Counterexample to conflation.** Let \(L(C,\omega)\) equal the trigger value.
If admissible worlds include a true and a false trigger, \(F(C)=1\), while a
known trigger-false event has \(L=0\). The reference includes this example and
disagreement across readings. Empty reading/contingency sets return CONFLICT.

For admitted conversion outcomes \(S\), possible common shares means
\(\mathrm{common}\in S\); common-only means \(S=\{\mathrm{common}\}\), with
the stated nonempty outcome convention. The set
\(\{\mathrm{common},\mathrm{preferred}\}\) makes these different. Production
must also model election rights, compulsory conversion and conditional outcomes;
the reference distinction is not a full asset/election ontology.

## 6. Legal time and evidence time both constrain facts

Represent validity as \([v_0,v_1)\), with an explicitly open upper endpoint
allowed, and availability from \(k_0\). Admit a law/fact at effective time \(t\)
and knowledge cutoff \(k\) only if

\[
 v_0\leq t,\qquad(v_1=\infty\ \text{or}\ t<v_1),\qquad k_0\leq k.
\]

Source references must resolve to checked occurrences. Production additionally
requires subject, authority, jurisdiction and knowledge-time correction/retraction
history. The reference covers availability start, not full bitemporal history.

**Proposition.** A fact with \(t<v_0\) or \(k<k_0\) cannot affect a YES in the
reference law evaluator. An active false necessary conjunct prevents YES.

**Proof.** Admission is false in either temporal case, so the fact supplies no
truth value; its atom remains unknown unless another admissible source establishes
it. Contradictory admitted values produce conflict. Span validation prevents
unresolved source strings from reaching evaluation. The false-conjunct result
then follows from Proposition 4. □

675 finite interval/knowledge cases passed, including exact upper boundaries,
plus future law, malformed intervals, missing sources and conflict. Half-open
intervals are a computational convention: inclusive legal dates need a reviewed
conversion to instants. An open endpoint does not prove current authority.

## 7. Exact share allocation conserves the declared amount

For legal aggregation group \(h\), exact eligible amount \(A_h\geq0\), and
same-currency share price \(p>0\), assume a source-backed whole-share floor rule:

\[
 n_h=\lfloor A_h/p\rfloor,\qquad r_h=A_h-pn_h.
\]

**Proposition.** \(n_h\) is a nonnegative integer,
\(0\leq r_h<p\), and \(A_h=pn_h+r_h\).

**Proof.** The floor definition gives \(n_h\leq A_h/p<n_h+1\).
Multiply by positive \(p\), subtract \(pn_h\), and use the definition of \(r_h\).
Exact rational arithmetic avoids binary rounding changes at the boundary. □

1,690 amount/price triples passed, plus malformed shape/currency cases and
aggregation identities. Identity matters because
\(\lfloor6/10\rfloor+\lfloor6/10\rfloor=0\), but
\(\lfloor(6+6)/10\rfloor=1\). This proves the display-name substitution can
change allocations, not which aggregation a contract requires.

The remainder is an arithmetic value, not an entitlement to cash. Fraction
cancellation, compensation, settlement, FX, accrual, anti-dilution and calendars
require separate source-backed rules.

## 8. Explicit dependencies make cache reuse correct

Assume an acyclic graph of deterministic tasks
\(y_i=f_i(x_i,y_{\mathrm{parents}})\) and immutable input snapshots.
Every material read, imported rule, task definition and environment setting
is supplied or included in task identity. Assume exact comparison or
collision-resistant content hashes.

Reuse a recorded result only after parents are current, bound inputs/task
identities match, and the recorded output hash verifies.

**Proposition.** Every reused/computed value equals a fresh evaluation on the
same snapshot.

**Proof.** Induct on topological order. Inputs are unchanged. For a task, parents
equal fresh values by induction. Recalculation gives the desired value directly.
For reuse, equal inputs/task identity and determinism give the recorded value;
output verification detects ordinary corruption. □

The reference compares a connected P1–P6 graph with direct computation for
20 input combinations, then changes task identity, parser configuration and
cached output, and tests cycles. A parser change with identical output
legitimately permits early cutoff downstream.

Undeclared reads, mutable input, unversioned rules, nondeterminism or a lying task
identity invalidate the proof. Production needs complete capability-based inputs
or traced access and durable publication. The reference is only a pure static
DAG, without disk transactions. Freshness does not establish acceptance:
a current PARTIAL result may be reusable with an open repair obligation.

## 9. Integration and review are explicit joins

For identity-mapped questions, require P3/P4/P5 products with the same versioned
context, verified payload hashes, and exact expected bank obligation
identities/versions/premises before emitting the report.

**Proposition.** A mismatch in any compared required field or obligation set
cannot pass this validator.

**Proof.** Each equality is a necessary guard before successful return. A field
mismatch returns rejection. Set equality fails when an identity changes even
if cardinality stays 14. Copying answers preserves UNKNOWN. □

The reference mutates each of eight context fields, removes a phase, changes a
payload and substitutes a same-length obligation set. It does not establish
the factual accuracy of an agreed context or the legal completeness of the
expected obligations. Different contract/transaction dates need an explicit
reviewed transformation, not silent coercion or blanket equality.

Disjoint implementer/readers/adjudicator identities, inclusion of supported
questions in scored questions, and report/cohort/scope-bound signoffs are likewise
necessary guards. The reference rejects implementer-adjudication and unscored
Q5 support. It cannot establish human expertise, true blinding, independence,
label quality or future error rates.

## From proof to delivery

These arguments show how the structures remove specified algorithmic failure
modes under explicit premises. They do not show that installing a parser or
changing phase labels delivers the engine. Port the invariants into production,
replay the original failures, then test a reviewed real source-to-answer slice
and an independently labelled finite cohort. Production repair and independent
legal validation remain open.
