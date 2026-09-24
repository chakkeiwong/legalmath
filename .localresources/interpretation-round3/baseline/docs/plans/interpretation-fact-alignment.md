# Fact correspondence after live interpretation search

## Question and evidence contract

Can the workbench compare differently named input facts without concealing a
changed definition, and present proposed semantic correspondences for explicit
review? The baseline is the accepted P8 output at the P9 implementation: 18 of
21 24EC50 comparisons and 15 of 24 23EC46 comparisons were incomparable. An
inspection of all stored nodes found **no** extra pair with literally identical
fact metadata up to renaming. Therefore increased automatic comparability on
these sources is not a pass criterion. Most differences require judgment.

The candidate mechanism has two paths. A total one-to-one match of identical
declarations (excluding only their names and list order) permits an explicit
symbol rename. Different meanings, references, units or judgment flags require
a separately stored proposal naming each assumption. Analysis of such a
proposal remains conditional even after a reviewer records a decision. Neither
path approves a circular interpretation or changes a completed search report.

The primary engineering criteria are: exact aliases preserve evaluation;
changed calendar conventions, actor definitions and hidden exceptions cannot
be automatically equated; mappings are total and injective; witnesses replay
against the **original** generated Java classes with separately named input
snapshots; stale source/candidate mappings are rejected; and conditional
evidence cannot enter unconditional behavioral groups or release decisions.
Also require authenticated proposal/review operations, a distinct meaning
reviewer, immutable review records, preserved original reports and portable
history. Full-suite acceptance follows focused checks and frozen P8 replay.

Java disagreement, stale hashes, dropped facts/conditions, a hidden conversion,
forged reviewer identity, lost uncertainty or an altered accepted history veto
acceptance and trigger repair. Source corruption or a broken replay baseline
stops dependent execution until repaired. Zero automatic new matches is an
expected substantive outcome, not a reason to loosen the matching rule.
Comparison counts, runtime, graph group counts and hypothetical agreement are
explanatory only. No legal accuracy, omission rate, model ranking, independent
human review or deployment readiness follows from this increment.

Artifacts: the existing master runner's new P10–P12 directories under
`artifacts/interpretation/round2/`, a frozen-pair diagnostic with review packets,
and `docs/implementation/interpretation-round2/fact-alignment-result.md`.
No live model calls are planned; the 41-of-100 reservation ledger must remain
unchanged. CPU Python 3.11 and the retained JDK 17 run in the trusted fixed
supervisor. The fixture is deterministic; model seeds are inapplicable because
stored responses are replayed without invoking a model.

## Skeptical audit and design corrections before implementation

* Comparing only newly generated, conveniently matching readings would be a
  wrong baseline. Replay every recorded P8 pair, retaining its original result.
* A high fraction of matched facts is a dangerous proxy for correctness.
  Require complete bijections; do not pad, project away or invent facts.
* Same spelling, similar prose, embedding similarity and shared citations do
  not establish equal meaning. None is sufficient for automatic correspondence.
* Renaming only the solver input would leave the actual Java input adapter
  untested. Translate the witness to each original vocabulary and replay both
  originals; compare their results to the normalized evaluation.
* A Boolean can mean either “prohibited” or “compliant”. Comparing tagged values
  establishes an encoded difference only. Review packets must show both full
  statements and require an explicit output-meaning assumption for conditional
  comparison. This increment does not implement output negation or claim to
  automatically resolve differing conventions.
* Completed search reports are immutable evidence. Post-search alignment
  proposals, analyses and reviews use separate records and hashes; they do not
  resolve old issues, replace the frontier or create release authority.
* API requests must not select a shell executable or provide a reviewer name
  as authority. Use the existing identity registry and server-configured JDK.
* Semantically different mappings may remain scientifically useful hypotheses.
  Keep their results explicitly conditional; an adverse result rejects or
  motivates revising that proposal, not the general search approach.

Audit outcome: proceed with the restricted correspondence design above. The
remaining unknowns are the actual truth of semantic correspondences, the
meaning of output values, and human reviewer qualifications. The implementation
must expose them rather than infer their resolution.

## Defaults and assumptions

| Choice and provenance | Justification | Failure mode and early check | Status |
|---|---|---|---|
| Literal metadata equality; follows the current conservative comparator | Changes naming without choosing a legal interpretation | Two indistinguishable unmatched declarations admit multiple permutations; reject ambiguous mapping | Reviewed engineering rule |
| Full bijection and same types; new restricted profile | No fact projection or silent coercion | Extra exception flag or many-to-one map; rejecting fixture | Reviewed restriction |
| Numeric/date units must match; no conversion library exists here | Equal stored scalars need a common unit convention | Months versus days or HKD versus cents; rejecting fixture | Reviewed restriction |
| Explicit assumptions for all changed metadata, including Boolean unit prose | Makes the hypothetical correspondence inspectable | A mapping changes scope without mentioning it; require per-link assumption and record field deltas | Proposal only |
| Existing comparison domains, probe limits and solver | Keep this increment about correspondence | Solver unknown or unsupported dates; preserve existing result class | Inherited with recorded limits |
| Frozen P8 sources; earlier development evidence | Tests the actual incomparability problem | Treating development results as held-out accuracy; forbidden conclusion | Development comparator |
| Independent reviewer role | Fits existing authority model | Local identities are not verified people; identity and legal-independence claims remain absent | Local workflow only |

## Why exact symbol renaming preserves the encoded computation

Let M map each left fact name to one right name, with a unique partner for every
declared fact on both sides. Replace right AST fact references M(x) by x;
do not replace substrings in formulas or change operators, literals or scope.
Given a left snapshot s, construct the right snapshot by copying the entire
tagged entry s(x), including unknown/conflict status and evidence, to M(x).
For a fact leaf the two lookups then return the same tagged value. Literal
leaves are unchanged. Each supported expression operator is a deterministic
function of its child values; induction on the finite AST therefore gives the
same tagged result for the normalized right rule and the original right rule
under the translated snapshot. The same argument applies to its scope.

This deduction concerns expression evaluation. Traces retain original names
and bundle hashes, and are separately checked. Literal metadata equality says
only that the declarations agree; it does not prove that either declaration
faithfully describes the bank's data or the English circular. A changed
declaration needs an explicit correspondence assumption, so its analysis cannot
inherit an unconditional interpretation claim from the renaming argument.

## Executable phases

| Phase | Implementation | Acceptance |
|---|---|---|
| P10 | Strict correspondence contracts, conservative alias discovery, AST rename, original Java replay, conditional comparison and distinguishing-question adaptation | Exact aliases including permutations; negative semantic changes; no mutation; original witness names; conditional results never cluster |
| P11 | Immutable proposals, conditional analyses and separate reviewer decisions; authenticated API; source/candidate binding and review packets | Forgery/staleness/rejection tests, archive replay, old report preserved, no release bypass |
| P12 | Replay all frozen P8 pairs; export all mismatch review packets and one explicitly hypothetical 24EC50 mapping; full regression and refreshed next plan | Original hashes preserved; all old differences retained; semantic mismatches stay incomparable; conditional result labeled; allowance unchanged; current suite passes |

Use the absolute approved runner with `refresh`, `review --note` and `run` for
each phase. Failed phases use an executed `repair --note` before review and
retry. Existing P0–P9 results must not be overwritten. P12 makes no mapping
proposal for 23EC46's different fact decompositions merely to improve counts.
It exports those differences for review. Qualified people and an adjudication
protocol are still required for the independent legal reference study.

## P12 pre-execution audit addendum: bounded comparison fallback

Inspection after P11 found that an UNKNOWN or UNSUPPORTED solver response can
fall through to boundary probes that ignore a caller-declared domain. For
example, `months >= 6` and `months > 6` agree on the declared known range 7–12,
but an unconstrained fallback probes 6 and can report DIFFERENT under the
range heading. That result would be wrong relative to the declared target.

The smallest diagnostic forces a solver timeout for that pair, plus a Boolean
pair restricted to false and an unsupported-solver response. Each must retain
the unresolved status without returning an out-of-domain witness. The
restriction is deliberately simple: a caller-declared domain receives no
unconstrained fallback after an unresolved solver response. Automatic complete
Boolean domains retain their existing finite probes, because every such probe
belongs to that domain. Neither fallback establishes equivalence.

Record the failing diagnostic, implement the guard, rerun the focused check,
and require the full P12 suite afterward. This repairs an inherited comparator
defect, not a failure of the correspondence hypothesis. It adds no model calls
or statistical comparison and does not change the frozen P8 baseline.
