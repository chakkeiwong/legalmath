# Mathematical audit and dispositions

The manuscript's mathematical assertions have been reviewed as definitions,
conditional deductions, source-reported results, or implementation obligations.
These classes require different evidence. None proves fidelity to regulatory
English. MathDevMCP inspected all 37 equation labels in the expanded source;
there are 35 displayed environments because one contains three labelled rows.
The exact final input digest is in `mathdevmcp-final.json`.

Sixteen algebraic/numerical obligations and a Lean file containing fifteen
theorems were submitted through MathDevMCP. Fifteen algebraic checks establish
the stated identities; the deliberately wrong old independent-error comparator
is rejected. Lean accepts the supplied file without placeholder proofs. An
initial proof attempt for integer division failed because the chosen tactic did
not use the division theorem; the retained correction invokes that theorem.
This was a proof-script failure, not a counterexample to Euclidean division.

| Labels or claim | Classification and disposition | Evidence and remaining limit |
|---|---|---|
| `gift-body` | Defined gift subcondition under an explicitly selected interpretation | Source paragraph and teaching truth cases; not full trade authorization |
| `case-domain-size` | Correct count of six independently enumerated ternary input slots | MathDevMCP: 729; not 729 independent legal provisions |
| `preservation-chain`, `refinement` | Specification of a desired preservation property | Definitions, domain and projection stated; a whole compiler proof is not claimed |
| `universal-benefit`, `existential-benefit` | Distinct quantified specifications | Lean `exists_not_forall`; a finite counterexample refutes their general equivalence, not either chosen legal reading |
| `component-exception`, `offer-exception` | Different scopes for an exception | Lean `component_offer_difference`; two components, one discount |
| `boolean-grammar` | Definition with nonempty argument lists | Explicit grammar; parser conformance is a separate engineering obligation |
| `financial` | Correct OR and inclusive thresholds for the stated wealth subcondition | Annex 1 and boundary example; definitions of qualifying wealth still govern inputs |
| `or`, `kleene-and`, `kleene-or`, `kleene-not`, `knownness` | Correct strong-Kleene truth/falsity encoding | Lean exhaustive constructors plus injectivity and exclusion of the inconsistent fourth bit pair |
| `unknown-tautology` | Correct failure of classical excluded-middle evaluation at unknown | Lean `unknown_excluded_middle`; does not reject classical logic on fully known Boolean inputs |
| `difference-query`, `counterexample` | Correct satisfiability question for differing projected outputs | Same typed domain required; solver `unknown` is not unsatisfiability |
| `no-open-release`, `ensemble-release` | Required safety invariants, not universal runtime theorems | Complete inventory, legitimate authority, exact version and atomic transition assumptions; selected tests only |
| `performance-window`, `timely` | Chosen half-open timing convention | Boundary explicitly excluded; Lean checks deadline self-inequality; other legal timing profiles need separate semantics |
| `io` | Accurate simple-minded input/output definition | Makinson/van der Torre, technical definitions and examples; consequence closure and input treatment matter |
| `asset-transfer`, `escrow-deposit` | Conservation identities under feasible nonnegative transfers | MathDevMCP algebra and Lean natural-number transfer theorem; cash flow is not itself discharge of every legal duty |
| `uct` | Defined exploration heuristic with positive visit counts | Separate handling of unvisited children; no legal-search convergence guarantee |
| `disagreement-question` | Weighted count of separated candidate pairs | Unit weights yield a literal count; equal nonunit weights scale it by their square (text corrected) |
| `semantic-entropy` | Entropy of a normalized finite distribution | Zero-mass convention added; uniform three-class example checked; fixed class count matters for comparisons |
| `common-error` | Correct mixture probability given conditional independence | Total probability yields q+(1-q)p^m; marginal r=q+(1-q)p; fair comparator r^m, not p^m |
| `ensemble-variance` | Correct covariance expansion | m variances and m(m−1) ordered covariances; feasible correlation and nonzero variance stated; Bernoulli restrictions may be stronger |
| `budget-guard` | Defined action limits | Counts are nonnegative integers; concurrent reservation needs atomic implementation |
| `exact-scale` | Correct quotient/remainder identity for positive divisor | Lean `integer_division`; overflow and chosen rounding policy remain implementation concerns |
| `transition` | Definition of a versioned deterministic state transition | Determinism assumes identical admitted event sequence, version and initial state |
| `zero-errors` | Correct one-sided binomial bound under IID trials | Inversion of (1−p)^n=alpha; explicit n≥1 and 0<alpha<1; clustered tests do not meet IID automatically |
| `conformal-quantile`, `conformal-set` | Correct inclusive split-conformal construction | Source method plus rank argument: k≥(n+1)(1−alpha), hence (n+1−k)/(n+1)≤alpha; infinite endpoint preserved; exchangeability/fixed score required |
| `cost` | Correct continuous cost intersection for K>0 and M>A | MathDevMCP substitution; ceiling gives first whole change count; cost model supplies no saving when M≤A |

The four structural-tool requests for further formalization concern the
universal-benefit example, the two Kleene rows and knownness. The Lean declarations
above provide bounded, independently checked dispositions for those requests.
The original structural report is retained unchanged; it is not relabelled as a
proof certificate. The legal meaning of the universal predicate remains an
explicit modelling decision.

Fifteen further prose claims were submitted to MathDevMCP's literature/local
assumption audit. `mathdevmcp-prose-audit.json` preserves every request and
response. That tool compares supplied records by assumption identity; it does
not read or prove the source theorem. Each transfer to an actual bank product
remains `applicability_unreviewed`. The book reports the source result within
its own setting or presents a conditional illustration. This disposition covers
compiler preservation, dates, reachability, stable models, repair minimality,
compliance complexity, defeasible permissions, binary search, conformal coverage,
semantic entropy, search heuristics, roundtrip equivalence, SMT comparisons,
release invariants and binomial inference.

The source audit also found a concrete wrong formula: membership in Definition
14 of Hashmi et al. marks a fully maintained duty as violated. Adjacent prose
and Figure 3.5 require non-membership. The rendered source page and Lean
counterexample are retained. Copying the printed formula would be wrong relative
to its stated maintenance target. The manuscript now warns at the point of use.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain corrected exposition | All displays reviewed; bounded checks pass with expected comparator rejection | No unresolved counterexample to the corrected local mathematics; product-transfer assumptions unreviewed | Faithful legal formalization and whole-runtime proofs | Independent legal interpretation and targeted implementation proof where deployment needs it | No theorem that LegalMath is legally correct, production safe, or statistically accurate |

Strongest alternative explanation: correct formulas could encode a wrong legal
meaning. A legally adjudicated counterexample would overturn the selected
interpretation without contradicting the arithmetic. The weakest evidence is
transfer from supplied teaching assumptions to the actual institution, data and
human decisions; that transfer has deliberately not been certified.
