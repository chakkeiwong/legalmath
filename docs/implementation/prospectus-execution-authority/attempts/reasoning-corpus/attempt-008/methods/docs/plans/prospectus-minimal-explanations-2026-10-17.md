# Source-linked subset-minimal conditional explanations

## Question and authority

Continue reasoning-corpus (G06, G07, PACKAGE-05) from authority revision235.
The recorded007 corpus established bounded conditional decisions, not minimal
explanations. Law008/009 added calendar arithmetic and corrected assistance
labels. The next question is whether the actual Q4/final consumer can identify
one subset-minimal set of supplied Boolean premises sufficient for its YES or
NO conclusion, retaining the authority and observation/calculation sources.
This is a general-build repair, not actual-holdings analysis. External advisers,
private documents, receiving-system CDM and portability are not prerequisites.

## Definition, derivation and literature

Fix a supplied Boolean expression E and its relevant observed Boolean literals O.
An explanation S is a subset of O such that every total Boolean assignment
extending S gives E the reported value v. It is subset-minimal if no proper
subset is sufficient. This does not mean minimum cardinality, uniqueness,
causation, legal correctness of E, or truth/currentness of the observations.

Use the deletion procedure in Ignatiev, Narodytska and Marques-Silva (2019),
Abduction-Based Explanations for Machine Learning Models, AAAI33, pp1511-1519,
definitions1-2 and Algorithm1 (pp1512-1514). Retain the actual paper locally.
The paper treats constraint representations of predictors; our application is
a separately justified specialization to the already declared finite Boolean
domain. Its model encoding, NN experiments and runtime results are not evidence
about our legal engine. Algorithm2 concerns minimum cardinality and is not
implemented. Evaluation/discussion (pp1515-1518) explicitly illustrates order
dependence and that logically correct explanations may be unhelpful to people.
The official-author code search and any inspected code must be recorded; do not
claim replication of the paper's implementation or use uninspected packages.

Start with O only after the existing finite evaluator reports YES/NO. In sorted
fact-name order, delete a literal iff the remaining facts still force v. This
preserves sufficiency. If removing l once permits a counterexample, removing
additional assumptions cannot eliminate that counterexample. Thus every retained
literal remains necessary at the end; any proper subset omits at least one of
them and is insufficient. Retain an explicit opposite-valued counterexample for
each single deletion. The empty explanation is valid for tautologies or
contradictions; relevant explicit conflicts still dominate simplification.

## Implementation boundary

Add opt-in law_explanation = subset-minimal.v1 to request/P4 overlay. Leave every
absent-option output exactly unchanged. Integrate into each Q4 basis row and
the ordinary final consumer, not a detached report. State per-basis scope and
retain original cross-basis aggregation/alternative readings. Bind every
retained literal to all active supporting source observations or successful
ratio/calendar computations, retaining original authority source. No invented
observation; inactive/future/conflicting observations cannot become explanations.
UNKNOWN, CONFLICT, inactive authority, >12 facts and explicit Z3 use get typed
non-explanation reasons. No Z3/core-minimality claim. Reject invalid option types.

Only existing production files law_facts.py, service.py and contracts.py may
change, plus a new successor/explanations.py. Do not change the strict existing
reasoning certificate schema or use the production evaluator as its own oracle.

## Evidence contract and default audit

Baseline: original source-bound006 and calendar008 inputs, corrected complete
answers from009, and current production hashes at preparation. Primary pass:
each emitted explanation independently sufficient and subset-minimal, each
deletion witness valid, each retained source matches actual active evidence,
and the explanation reaches actual P4 and final current/frozen consumers.
All old answers without the option must be byte-equivalent as JSON values.
For option-enabled answers, only Q4 per-basis explanations, the P4 identity,
and their exact downstream digests may differ. Compare full projected objects,
never loosely omit arbitrary keys.

Independent oracle: existing independently parsed bitset truth tables, augmented
in a separate checker with independent world/witness checks. Exhaustively check
a predeclared four-fact expression corpus and all Boolean/unknown/conflict
assignments; use explicit 12/13-fact, depth/node, empty, negative, unused-fact,
multiple-explanation and unequal-cardinality cases. Inject nonminimal and
insufficient sets, missing/false witnesses, wrong conclusions/identities and
source misbindings. Test request and overlay semantics and malformed options.

| Choice | Provenance/status | Failure mode; earliest diagnostic |
| --- | --- | --- |
| Twelve-fact domain | Existing finite route, reviewed bound | Wider unsupported formula; 13-fact refusal |
| Sorted deletion | Algorithm1 specialization, convenience choice | Mistaken shortest/unique claim; unequal-cardinality example |
| All active source supports per literal | Existing timeline/derived-fact inputs | Inactive or wrong-value source included; independent source reconstruction |
| One per-basis explanation | Bounded optional feature | Mistaken aggregate explanation; explicit scope field and alternative-reading test |
| Independent bitset checker | Existing certificate implementation | Shared evaluator bug; no production evaluator import, malicious certificates |

Promotion vetoes: any unsound/nonminimal explanation, bad/missing source binding
or witness, changed legacy answer, hidden conflict, forged acceptance, untested
consumer or mismatch between frozen code and executed code. These reject this
candidate and trigger diagnosis/reviewed repair. Continuation vetoes for this
run: corrupted baseline/source, resource exhaustion, changed admission inputs,
or failed harness validity. Counts/timing are explanatory only. No whole-task,
installed/native/runtime or legal-truth acceptance follows.

## Skeptical audit and execution

PASS after correcting two material design risks: 'smallest' was imprecise
(subset-minimal is the exact claim), and this task's live production inputs
would invalidate admission during edits. Before revision/admission, retain exact
byte snapshots of the three files to be edited and replace only those input
paths with their snapshot paths; preserve their mapping/hashes. All other
inputs and immutable history remain. Freeze all production and test/runner
methods after implementation and before the single test start; retain the
allowed diff. Admission authorizes this recorded transition, not arbitrary
method drift. Proof and downstream tests address the real question; smoke
success and literature citations cannot substitute for them.

Prepare reviewed revision236, keeping all59 obligations/44 tasks and all seven
reasoning admissions. Increase the same cumulative admission limit7 to8 for
this discriminating explanation test, never reset it. Retain historical costs
as UNKNOWN where unmeasured. New incremental allowance:600 measured seconds,
64MiB including preparation/snapshots/results and2MiB failure reserve;60 seconds
preparation and110 per stage, one test start, no new native/model/GPU calls or
installations. Literature retrieval is a bounded preparatory source read.

Then implement/freeze; run tests, independent corpus, original/calendar actual
consumers in separate bounded stages; inspect results; write result/decision
table and run manifest; seal, record, refresh. Failures are immutable. Commands
use one-second tool yields and existing-session polling; no detached processes.
Continue substantive gaps before the final current installed/native/runtime/
recovery/authority validation batch. Update the stale law009 continuation text.
