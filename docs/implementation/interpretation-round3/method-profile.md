# Implemented method profile and boundaries

This is the implementation contract for the new assurance layer. The earlier
coverage audit describes P12 and remains historical evidence. Phase results and
live observations are recorded separately; this file defines what the code does.

## Source and semantic evidence

`sources.py` binds an input packet to raw source versions and exact extracted
character spans. The first extraction uses HTMLParser/pypdf; the second uses a
separate HTML tokenizer or Poppler. Both can still share a failure in the raw
source. Agreement therefore supports extraction consistency, not completeness of
all applicable law. Explicit references are acquired through the existing pinned
official-host fetcher. Prose-only references become authority needs and can be
resolved using exact catalog locators. Unavailable, ambiguous, stale or capped
references remain findings.

The PDF path compares extracted text; it does not implement OCR or verify text
against rendered page images. Both extractors can miss the same image-based
footnote or table. Exact coverage of the retained extraction therefore cannot
establish coverage of every visible mark in a PDF. This limitation is separate
from whether all incorporated legal authorities were acquired.

`semantics.py` defines an atomic claim as an actor, action, modal strength,
conditions, exceptions, time restrictions, relevance classification and exact
source evidence. Two fresh source-only calls extract claims before seeing any
candidate. An exact duplicate commitment can be combined; different commitments
are retained. A unit's mere presence or `CLAIMS` disposition cannot replace its
actual evidence and claim links. Separate lexical checks flag certain explicit
exception cues when both readers omit the corresponding feature. They are
targeted detectors, not general English parsers.

Assurance retains and checks a bounded number of proposals deferred by the legacy
search registration policy. It does not promote them into registered or approved
candidates. An unsupported expression is an explicit formalization finding; the
original reading stays in the claim/candidate denominator. Encodable siblings
continue to source checks and Java execution.

The fidelity critic receives the original source, source claims and a rendering
of each executable expression with its **used** fact definitions. Candidate prose
does not supply the executable meaning. A separately proposed output tag states
whether a true Boolean means compliance or prohibition. The critic checks source
support and representation in both directions. It returns `ENTAILED`,
`CONTRADICTED` or `NOT_ESTABLISHED`; deterministic validation enforces coverage and
authentic anchors, while entailment remains a model judgment. Additional source
restrictions omitted by both inventories are still a possible shared failure.

This adapts the evidence-bearing entailment task in ContractNLI (Koreeda and
Manning, sections 2.1 and 5.2) and source-facing checks discussed by Amrollahi,
Lopez and Barrett (sections 3–5 and Limitations). It does not import an NDA-trained
classifier or their empirical accuracy. The existing formal roundtrip remains
an additional consistency check with its own limitations.

## Structured arguments and cases

An argument names premises, parent arguments, an inference and a signed conclusion.
A signed proposition consists of an atom and a Boolean negation flag. The local
profile implements three attack types:

* `UNDERMINE`: an argument concludes the opposite of a named ordinary premise or
  assumption. Exception premises are handled through applicability/undercutting.
* `REBUT`: an argument concludes the opposite of a defeasible target conclusion.
  A strict final step cannot be directly rebutted; attack its premises or a
  defeasible supporting argument instead.
* `UNDERCUT`: an argument denies `applicable.INFERENCE_ID` for a defeasible
  inference. It challenges the inference's applicability without requiring the
  opposite substantive conclusion.

An attack on a supporting argument propagates to arguments that depend on it.
Ordinary premises without support block an argument. Unchallenged assumptions and
unexamined exceptions remain explicit conditional grounds; challenged assumptions
and established exceptions have distinct blocking effects. A rejected exception
requires source evidence, so absence is not silently treated as falsity.

Proposed preferences require evidence. Model-proposed preferences do not suppress
attacks automatically; a separately supplied accepted-preference hash enables only
conditional graph evaluation. Cyclic preferences are rejected. Cyclic support and
excess graph size remain unresolved. The resulting bounded defeat graph uses the
existing grounded/stable solver, with empty stable-extension sets handled without
vacuous acceptance. The result does not verify English premises or prune a reading.

The attack distinctions come from Prakken (2010), definitions 3.12–3.21. Premise
roles are adapted from Gordon, Prakken and Walton (2007), definition 10. This
implementation does not claim the complete ASPIC+ language/closure conditions,
rationality theorems, full Carneades dialogue or legal proof standards. These
models must not be identified solely because they share an abstract graph.

Case records contain provenance, factors and outcomes. Separate problem queries
name the target candidate and its own factors. Checked constructors produce
analogy, distinction, countercase and distinction-with-case proposals. A factor
must actually be shared before an analogy/countercase is offered. Differences
remain questions about materiality. Exact citations do not certify that the
model correctly classified a passage as precedent or extracted its factors.
Hypothetical examples remain labelled. No desired party victory is used as the
bank's objective. These are selected mechanisms motivated by AGATHA's sections
3–4; they are not a reproduction of its five-move adversarial theory game.

## Stage repair and program correspondence

The repair stages are dependency, extraction, interpretation, formalization and
Java execution. Changing an upstream stage invalidates dependent results while
retaining their bytes/history. Source-claim discrepancies can trigger new
source-only inventories; a candidate-code repair cannot fill a missing authority.
Every issued repair consumes its reservation, including failed or interrupted
calls. Identical evidence actions and unchanged candidate commitments do not
count as progress. Exhaustion preserves the unresolved question.

An optional derived correspondence binds two candidate hashes, a source packet,
common fact definitions, formulas deriving every original fact, output conventions,
source citations and explicit assumptions. Boolean common domains can enumerate
true, false, unknown and conflict. Date and numeric domains must be declared.
Every declared assignment is evaluated through the mappings and replayed in both
original generated Java classes. Output negation changes only known Booleans;
unknown, conflict and out-of-scope remain distinct. A domain cap is a limit result.
Even exhaustive agreement is conditional on the source/fact/output assumptions.

## Continuous operation and selective questions

The monitor fingerprints source and dependency versions, selected control,
implementation/provider/settings, fact schema and the explicit evaluation date. Changed fingerprints produce
new investigations. Missing dependencies, interrupted dispatch and explicit failed
investigations retain bounded retry history. A scheduler invokes the one-shot CLI;
this repository does not install a scheduler or establish an operational SLA.

Action selection uses explicit relative costs and the number of candidate pairs
a question could distinguish. It is a local scheduling heuristic inspired by
generalized binary search, not Nowak's query-complexity theorem: the complete
hypothesis-class and oracle assumptions are unavailable here. Cached answers bind
source, scope, assumptions, code/provider configuration and relevant candidate
meaning. A reused model diagnostic is not an additional independent vote.

The action selector accepts a proposed pair-separation count, but the current
integrated stage-repair scheduler assigns a unit gain to each actionable issue.
It therefore uses costs and deterministic tie-breaking rather than a calibrated
value of information. Residual questions are deduplicated by issue and scope;
they are not a proven minimum question set. Automatic construction and validation
of a question's partition of the live candidate set is further work.

The output distinguishes completed diagnostics, remaining source ambiguity,
unsupported representations and execution failures. Remaining questions preserve
their evidence and attempted actions. No external consultant is automatically
contacted or required by an exhausted budget. Neither automated agreement nor a
small question queue supplies a calibrated probability of legal correctness.
