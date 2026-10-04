# Investigating a bank transaction from retained evidence

The public command retrieves factual documents, derives conditional findings,
checks the fixed obligation inventory and produces a qualified transaction
assessment. It also executes the retrieved facts through retained RuleIR or
Catala builds. No human quality labels, supplied expected answers or caller-
selected requirement lists are accepted by the investigation interface.

Run the reviewed program from the repository root:

```sh
.venv/bin/python scripts/run_bank_compliance_program.py
```

The program checks sources and tools, runs the focused regression, checks formal
equations and translation certificates, executes both targets and investigates
the retained public-document example. Each phase preserves an attempt receipt,
its inputs and outputs, and a refreshed next-phase plan. A failure records a
repair request and retains the failing evidence. After repair, rerun the same
command; a changed method or dependency prevents reuse of the earlier result.
Unchanged successful phases are reused only after their output hashes match.

The result is in
[`docs/implementation/bank-compliance-closure/summary.json`](../implementation/bank-compliance-closure/summary.json).
The `state.json` beside it identifies the current attempt directories. Earlier
attempts remain historical evidence. The engineering pass status does not clear
a transaction or assert complete legal coverage.

The later [eligibility gap-closure increment](../implementation/eligibility-gap-closure/README.md)
adds seven conditional product/issuer-power models, detailed HKMA broker-exception
premises, source-bound integration for UBS and the two UK prospectuses, executable
quotation references and Gregorian date evidence. It retains all fourteen bank
obligations. Its qualified reports do not close the missing licensing, private
account, policy or route evidence. The original program results above are
historical checkpoints; the later increment records its own attempts and checks.

## Inputs and actual execution

The [command interface](../../src/legalmath/transaction/__main__.py) provides
`example`, `evaluate`, `verify`, `execute-native`, `screen`, `refresh-feeds`,
`replay`, `freeze` and `observe`. Use its help for exact arguments:

```sh
.venv/bin/python -m legalmath.transaction --help
.venv/bin/python -m legalmath.transaction execute-native --help
```

An investigation request contains the supported jurisdiction/activity profile,
transaction context, capacity and source-registry hash. Fact, settlement-route
and bank-policy hashes resolve to actual JSON documents in a content-addressed
store. A fact assertion names a source document and an RFC 6901 field pointer;
its value is read from those bytes. The program rejects wrong types and retains
conflicting values. The truth of a supplied factual assertion remains distinct
from successful parsing and unchanged bytes.

The source registry records original content, provenance, known and effective
times, freshness, dependencies and amendments. Missing temporal evidence stays
unresolved. In particular, acquisition time does not establish a law's effective
date or continuing legal force. Public-source intake preserves the original
prospectus/legal-document bytes and references extracted text separately.

Fourteen obligations span all seven categories. Five currently evaluate sourced
conditional rule models: selected CMIC rules, selected bank program controls,
defined private-account diligence, existing SPI conditions and selected reporting
duties. Nine entries retain unimplemented rule families or unresolved coverage.
Additional formal calculations support entity classification, financial and
product conditions. The complete collection has eleven shared models.

Derived facts have an explicit dependency order. Account amounts determine the
financial condition before client qualification is evaluated. The threshold's
amount test needs a separate controls premise. SPI eligibility then determines
the premise used for streamlined procedures. An asserted derived result that
contradicts the calculation becomes a conflict. Failure of the sufficient
complex-bond condition does not establish that a product is non-complex.

`execute-native` accepts the same request, a reconstructed investigation receipt,
the store, an existing native phase directory, the target and the pinned JDK.
It verifies that each retained build implements the current model and compares
computed values with independent formal consequences. These builds use the
complete-input profile: unknown or conflicting facts cause abstention. An
unsupported action or capacity is recorded without applying the CMIC model.

## Sanctions data and transaction events

The retained [feed manifest](feeds/manifest.json) identifies complete downloaded
OFAC SDN and consolidated snapshots. The parser checks publication metadata,
identifiers and the declared record count; it rejects access pages and truncated
lists. It preserves multiple program designations on a single entry. Exact name
matches identify candidates for identity resolution. No exact match does not
establish that an entity or transaction is clear.

Refresh official snapshots with:

```sh
.venv/bin/python -m legalmath.transaction refresh-feeds
```

Downloads are staged and parsed before replacing an active file. Previous bytes
are retained under `feeds/history`. A changed snapshot changes the program's
input identity. Existing historical investigation stores remain immutable;
import new source versions into a new request before assessing the later date.
Corporate identity, beneficial ownership, all relevant programs and authorization
conditions require further sourced evidence.

A supplied ownership graph is read from a typed factual source and evaluated by
the existing exact blocking-rule calculation. Designations and ownership remain
explicit premises. An unreached entity is never cleared. The selector prevents
using this propagation for a solely NS-CMIC designation.

Lifecycle replay preserves ordered events and rejects duplicate identifiers with
different content. Fact, source, policy, route and corporate-action changes
invalidate the current assessment. Settlement at a later time requires a new
assessment. Duties distinguish rejection, blocking, reporting, rescreening and
disclosure; completion evidence does not prove actual performance. A business-
day calculation requires an explicitly retained calendar and refuses to extend
beyond its documented range. The supplied calendar is a factual premise, not a
default assertion about any jurisdiction's legal deadline convention.

## Evidence without human grading

The formal checks compare the actual shared expressions with independently
written equations over all declared Boolean values and nonnegative integer
amounts. Deliberate mutations expose incorrect thresholds and omitted sanctions
conditions. Lean checks preservation from the retained formal expression to the
shared model. Native generated cases separately check RuleIR and Catala against
an independent expression evaluator, with runtime replay and native interpreter
checks provided by the existing assurance component.

These checks have distinct limits. The translation certificate does not prove
English meaning or compiler correctness; finite native executions do not prove
every possible runtime execution. A preserved quotation is provenance, not an
entailment theorem. Both targets can agree on an incorrect legal interpretation.

`freeze` records method, inventory and prior source identities before `observe`
accepts new content. Changed code requires a new series. Novelty means new to
the declared source inventory; times are declared and not externally attested.
The present program begins a series and makes no claim of real future-document
accuracy. Generated amendment and unfamiliar-instrument cases are engineering
challenges, not future legal observations.

## Remaining implementation and data work

| Area | Implemented mechanism | Remaining requirement |
| --- | --- | --- |
| Evidence and inventory | Retrieved typed evidence; fixed obligation membership; dependencies, dates and amendments | Complete legal discovery, source authority and independently justified interpretation |
| Scope | Entity calculation, transaction roles and explicit applicability predicates | Evidence establishing actual entities/branches/capacities; broader jurisdiction/activity selection and conflicts |
| Sanctions | Official list parser, exact-name candidates, selected CMIC logic and conditional ownership propagation | Verified entity resolution, ownership completeness, other programs, exposure and exact authorization conditions |
| Bank/client rules | Selected sourced conditional program and private-account rules | Remaining licensing, prudential, account and local AML rule packs; actual control/account evidence |
| Products | Connected financial/client/threshold/SPI calculations and retained prospectus sources | Complete issue-document interpretation, issuer-law consequences, other instruments and corporate-action rules |
| Bank policy | Required policy/mandate sources and immutable snapshot binding | Genuine internal documents and their executable interpretations; supplying a document alone does not complete this layer |
| Operations | Typed event/duty replay, invalidation, bounded calendar arithmetic | Source-derived triggers, deadline conventions, actual settlement-route requirements and evidence of performance |
| Assurance | Formal equations, constructor preservation, native checks, adversarial cases and frozen observations | Universal source semantics, independent factual truth, exhaustive world-law coverage and real prospective observations |

The next implementation work should expand separately sourced rule families and
their applicability predicates, using this same evidence and execution path.
Unavailable private documents remain external inputs. Unsupported legal meaning
remains a qualified conclusion rather than an invented certificate.
