# Claude review of the legal interpretation program

6 October 2026. Reviewer: Claude (Fable 5.1), read-only. Scope: the frozen
review package bound by `handoff.sha256` (693 entries, all verified at the
start of this review), the seven frozen interface copies, the retained circular
26EC22, the research archive, and the rendered monograph section 6.40. No
subagent, model call, dependency installation, test run or product phase was
used or executed. No file other than this one was written.

## Verdict

**PASS_FOR_BOUNDED_IMPLEMENTATION**, covering P0 and P1 as written.

The verdict means the program is concrete and honest enough to start P0
(baseline binding and operative overlay) and P1 (typed records) without
revision. It does not cover P2, P6 or P8 as currently written: each has one
finding below marked blocking for that phase, and each must absorb its repair
at the plan refresh the master already requires before dependent execution.
This is a verdict about readiness for the next implementation step. It is not
a statement about legal correctness, English fidelity, or product release, and
reviewer agreement is not legal quality evidence under the controlling
requirement.

Three observations condition the verdict:

- The frozen interface copies are byte-identical to the current worktree
  files. Five of the seven differ from committed HEAD (translation model,
  source references, qualification adapter, complete investigator,
  observation module). The review applies to the frozen worktree versions; an
  executor must not assume the committed application matches them.
- HEAD has moved three prospectus commits past the commit recorded in
  `validation.json`. The handoff hashes still verify, so the reviewed files are
  unchanged.
- A later `execution/` directory, `scripts/legal_interpretation_ops.py` and
  its test were added on 6 October and are not in `handoff.sha256`. They were
  inspected only for conflict with the program (none found). This verdict does
  not cover them.

## Severity-ranked findings

### F01. The paragraph 14 / footnote 5 dispute is specified as a trigger dispute only

- Status: **blocking for P2**; nonblocking for P0, P1.
- Location: `docs/plans/legal-interpretation-program/P2-clause-scope-and-pilot-readings.md`
  item 3 and "Discriminating challenges"; master section 1 question 2;
  `docs/monograph/chapters/06m-legal-interpretation.tex` lines 12–21 and the
  figure at lines 231–253.
- Mechanism: the retained source gives footnote 5 a different object and a
  different standard from paragraph 14, not merely a missing request
  condition. Paragraph 14 reads "confirm and, upon SFC's request, demonstrate
  to the SFC's satisfaction the management and operational soundness of the
  tokenisation arrangement, record keeping of ownership and the integrity of
  the smart contracts". Footnote 5 reads "confirm and demonstrate to the SFC
  that, at a minimum, they comply with the requirements as set out in
  paragraphs 10 to 13 above and the smart contracts are not subject to any
  contract vulnerabilities or security flaws with a high level of confidence".
  The footnote changes the object (compliance with paragraphs 10 to 13 and
  absence of vulnerabilities), adds a standard ("with a high level of
  confidence", "at a minimum") and drops "to the SFC's satisfaction". The plan
  and the figure present two readings, A (request required) and B (standing
  demonstration duty). A third reading, C, treats the footnote as stating the
  minimum content of the paragraph 14 duties and inheriting paragraph 14's
  trigger structure. Under the no-request case, A and C agree on trigger
  status but differ on object and standard; A and B differ on trigger. The
  "uniform over retained branches" label of equation (6.14) depends on which
  of these are in the branch set, so omitting C changes the reported
  disagreement structure.
- Evidence: retained JSON `docs/papers/Circular on tokenisation of
  SFC-authorised investment products_SFC(2026).json`, paragraphs 14–16 and
  footnote 5, extracted and read in full for this review.
- Affected phases: P2 (branch inventory), P3 (argument vocabulary), P6
  (decision-set labels), P8 (coverage map).
- Smallest repair: in P2 item 3, decompose the 14/footnote-5 group along three
  explicit dimensions (trigger, object, standard) and require at least
  readings A, B and C in the inventory, each with its own source warrant. Add
  the discriminating challenge "footnote object or standard silently replaced
  by the paragraph's object or standard". The monograph needs only one
  sentence stating that the footnote also names a different object and
  standard, and that the figure isolates the trigger dimension alone. Replace
  "the preceding requirements" (line 18) with "paragraphs 10 to 13", since the
  footnote is attached to paragraph 14 and "preceding" is ambiguous.
- Establishing check: `test_pilot_readings.py` asserts that the retained
  branch inventory contains distinct object and standard records for
  paragraph 14 and footnote 5, contains a reading in which the footnote
  inherits the paragraph 14 trigger, and that the decision set for the
  no-request input is computed over all three.

### F02. Qualification identity has no slot for branch semantic settings

- Status: **blocking for P6**; nonblocking before P6.
- Location: frozen `src/legalmath/interpretation/assurance/qualification_adapter.py`
  lines 17–24 (`identity`), 27–50 (`run`), 53–80 (`verify`); frozen
  `complete_investigation.py` lines 205–220 and 309–318; P6 items 3, 4 and 6;
  master section 4 ("A reading branch is the relevant interpretation plus all
  semantic settings and assumptions").
- Mechanism: the existing identity hashes packet, reading, question,
  assignment status, qualification method manifest and the adapter file. Two
  branches that lower to the same legacy `Reading` but differ in semantic
  settings (grounded versus preferred, ordering choice, a priority premise
  present or absent) produce identical identities. `run` creates the output
  directory with `exist_ok=False`, so the second branch either collides or,
  if written elsewhere, cannot be told apart from the first by any retained
  receipt. The investigator's `verify` recomputes the same identity, so the
  dossier cannot show that both branches were evaluated. A decision set
  labelled "uniform over the retained, successfully evaluated branches" would
  then rest on receipts that do not identify the branches.
- Counterexample: branch A = reading R under grounded semantics; branch B =
  reading R under preferred semantics with priority premise p. Both lower to
  R. `identity(packet, R, q, status)` is equal for A and B.
- Affected phases: P6, P7 (invariants over branch accounting), P8
  (observation binding).
- Smallest repair: a new adapter profile (for example
  `legalmath.investigation-qualification.v2`) whose identity and
  `unresolved_premises` include a canonical branch hash covering semantic
  settings, assumptions and priority premises, with v1 left untouched for
  historical receipts. The integration route stores one qualification
  directory per branch hash.
- Establishing check: `test_integration.py` constructs two branches sharing a
  reading and asserts distinct identities, two retained receipts, and that
  `verify` fails if either branch directory is removed.

### F03. The observation machinery does not bind a semantics stage

- Status: **blocking for P8**; must be designed in P6.
- Location: frozen `src/legalmath/interpretation/assurance/investigation_observations.py`
  lines 29–86 (`method`), 128–259 (`check_stages`), 262–285 (`observe`);
  P6 item 3; P8 items 4–5.
- Mechanism: `freeze` binds `digest(method(runner))`; `check_stages` verifies
  the core, scoped, qualification and optional challenge stages against that
  bound method and raises `E_STALE_REVIEW` on any method difference. There is
  no key for an interpretation-semantics route. If P6 adds the route to the
  complete investigator without adding a `semantics` entry to `method()` and a
  corresponding stage check, a later window would freeze a method hash that
  does not bind the new layer, and `observe` would accept a dossier in which
  the semantics stage never ran. That is exactly the "claimed stage was never
  called" fault that P6 lists as a discriminating challenge.
- Second consequence, consistent with the plan but not stated in P8:
  `implementation_identity()` (integrated.py lines 20–23) hashes every
  `.py`, `.java`, `.json` and `.lean` file under `src/legalmath`. Any P6 code
  change therefore changes the method hash, and every pending task in an
  existing window becomes unobservable under the new code until `repair()`
  issues a new method version. P8 should say this explicitly so that an
  executor does not read the resulting `E_STALE_REVIEW` as a harness defect.
- Smallest repair: P6 adds a `semantics` key to `method()` (None when the
  route is disabled, otherwise the semantics profile, records version and
  reference-evaluator identity) and a semantics stage verification in
  `check_stages` that reads the retained branch outcomes and recomputes the
  decision set. P8 records the window-invalidation consequence.
- Establishing check: `test_observation_boundary.py` freezes a window with
  semantics enabled, then (a) observes a dossier lacking the semantics stage
  and expects `E_REFERENCE`, (b) observes a dossier whose semantics profile
  differs and expects `E_STALE_REVIEW`, (c) confirms that an older window
  frozen without semantics rejects the new runner.

### F04. P0's reuse preference and its future test path point in different directions

- Status: nonblocking; record the decision in P0's executed plan revision.
- Location: P0 item 4 and "Files and validation commands"; phase manifest
  P0 `future_tests`.
- Mechanism: P0 prefers reusing the existing post-review repair mechanism and
  makes `semantics/operative.py` conditional, while the manifest's only P0
  test is `tests/interpretation/semantics/test_operative.py`. I inspected the
  mechanism, `scripts/assurance_evidence_post_review.py` lines 50–136: it
  performs genuine field-level replacement with before/after/reason/kind
  change records, so reuse is feasible. But its replacement tables are
  hard-coded dictionaries keyed by reading identity inside the script, its
  qualifications list is a module-level constant, and the change record holds
  no predecessor hash, which P0 item 3 requires.
- Evidence: the four operative statements the gap audit cites were confirmed
  at `dispositions.json` lines 68356, 69791, 71613 and 80343 of the selected
  package. Recomputed denominators match the audit: 46 obligation entries, 70
  role records, 35 distinct reading identities, two roles of 35, no record
  with an accepted substantive repair.
- Smallest repair: P0 decides now for a small `semantics/operative.py` that
  reads a data-driven overlay table and emits change records in the same
  shape as the existing script plus a predecessor record hash, rather than
  editing the hard-coded dictionaries. The manifest test path then matches.
- Establishing check: `test_operative.py` applies the overlay to the four
  cited field paths, asserts originals and predecessor hashes are retained,
  and asserts a changed active pointer is detected before any overlay is
  written.

### F05. The expected pilot result under grounded semantics is the empty extension

- Status: nonblocking; clarify in P3 before execution.
- Location: P3 items 4–5 and "Acceptance and failure decisions"; master
  section 8 ("a blanket abstention fails its behavioral criterion").
- Mechanism: if readings A and B (and C after F01) are encoded as mutually
  rebutting arguments with no source-supported priority, the grounded
  extension of the contested conclusions is empty. That is the correct
  result, not resource exhaustion and not abstention. The plan's language
  could lead an executor to treat ∅ as failure, or to add a priority premise
  to obtain a non-empty extension, which is the silent-default failure the
  program exists to prevent.
- Smallest repair: P3 states that the expected grounded result for the pilot
  under missing priority is ∅ for the contested conclusions, that the
  preferred report is "in some extensions", and that the "useful computation"
  criterion is met by the per-branch consequences computed in P6, not by a
  non-empty grounded set.
- Establishing check: a fixture with two mutually rebutting arguments and no
  preference must yield grounded ∅, preferred {{A},{B}}, and a report of
  "contested" for both conclusions, from both the reference evaluator and
  the adapter.

### F06. Equation (6.14) and P6 item 4 do not define the outcome vocabulary

- Status: nonblocking.
- Location: `06m-legal-interpretation.tex` lines 306–329; P6 item 4.
- Mechanism: the exposition defines d_r(x) as a single declared duty outcome
  while P3 item 5 reports conclusions as being in all, some or none of the
  computed extensions. For a branch whose declared semantics yields several
  extensions that disagree, d_r(x) must be the "conflicting" value. The text
  allows this ("retaining unknown, conflicting or unsupported outcomes where
  appropriate") but does not say when each arises, and P6 does not enumerate
  the values that can appear in the decision set.
- Smallest repair: one sentence after equation (6.14) stating that a branch
  whose extensions disagree reports a conflicting outcome, and a fixed outcome
  vocabulary in P6 item 4 (for example: settled-triggered, settled-not-
  triggered, unknown-fact, conflicting-extensions, unsupported-lowering,
  unfinished).
- Establishing check: `test_rendering.py` renders each vocabulary value and
  asserts that the summary and operative field carry the same value as the
  detailed report.

### F07. Paragraph 10's responsibility decomposition names no footnote 1 dependency

- Status: nonblocking; P2 refresh.
- Location: P2 item 2; master section 1 question 1.
- Mechanism: paragraph 10 says providers "should remain and be ultimately
  responsible"; footnote 1 says the provider "should remain fully
  responsible, despite any outsourcing arrangement such as those envisaged
  under 6.8 of the Code on Unit Trusts and Mutual Funds" and points to Part A
  of the Appendix to the Tokenised Securities Circular "where applicable".
  "Ultimately" versus "fully" is itself a textual variation that bears on the
  retained-authority versus full-liability readings, and the UT Code 6.8
  cross-reference is an applicability premise. P2 inputs cover footnotes
  generically but the decomposition does not name these anchors.
- Smallest repair: P2 item 2 lists footnote 1, UT Code 6.8 and TSC Appendix
  Part A as explicit source relations of the responsibility branches, and adds
  "ultimately versus fully" as a discriminating challenge.
- Establishing check: `test_clauses.py` asserts the paragraph 10 clause record
  carries the footnote 1 relation and an unresolved applicability premise for
  the two cross-references.

### F08. Lowered models carry the legacy label `reviewer_interpretation`

- Status: nonblocking.
- Location: frozen `src/legalmath/translation/model.py` lines 447–449
  (`from_reading`).
- Mechanism: every model built from a retained-source packet is labelled
  `basis: 'reviewer_interpretation'` with the statement prefix "Unreviewed
  interpretation". A model derived from semantic records through this path
  inherits a field value that reads as a human-review provenance label, which
  the controlling requirement forbids as quality evidence.
- Smallest repair: `lower.py` passes an explicit basis value through a
  versioned path (for example `declared_semantic_branch`), or P6 documents
  that the legacy value means "proposed, not established" and the renderer
  never surfaces it as review provenance.
- Establishing check: `test_lowering.py` asserts the basis value and statement
  prefix on models produced from semantic records.

### F09. A second legacy bound: replay requires at most 16 candidates

- Status: nonblocking; add to master section 7.
- Location: frozen `complete_investigation.py` line 226 (`1<=len(candidates)<=16`)
  and line 248 (`execution_complete` requires replay).
- Mechanism: the master records the 16-node search limit but not the
  16-candidate replay limit. If branch inventories (up to 64) were ever
  written into `candidates.json`, replay would become unavailable and
  `execution_complete` false for the legacy route, without any semantics
  error being reported.
- Smallest repair: list this bound beside the 16-node bound and state that
  branches never enter the legacy candidate file.
- Establishing check: an integration test with more than 16 branches asserts
  `candidates.json` unchanged and replay still available.

### F10. P7's Lean ambition exceeds the registered certificate fragment

- Status: nonblocking; scope P7 before execution.
- Location: P7 item 2; `src/legalmath/interpretation/assurance/proof_certificate.py`
  lines 18–20 and 63.
- Mechanism: the registered checker supports Boolean literals, facts, not,
  and, or and if only, with a hard-coded Lean 4.20.0 toolchain path (present
  on this machine). Propositions about branch accounting or dependency
  invalidation fall outside that profile. Whether a new prelude can be
  registered without changing the existing profile is NOT_CHECKED.
- Smallest repair: P7 lists which propositions fall inside the existing
  profile and which require a new registered profile, and treats the latter
  as a separate deliverable.
- Establishing check: a kernel receipt for at least one proposition in each
  listed class, or an explicit "not proved" disposition.

### F11. Evaluative predicates remain declared inputs after the pilot

- Status: nonblocking; wording in master section 10.
- Location: P5 item 2; master section 10 row "Evidence-to-classification
  bridge".
- Mechanism: P5 derives only narrow predicates (recorded appointment,
  supervision event within an interval, record discrepancy, unresolved
  ownership assertion) and leaves retained responsibility, adequacy and
  proper records as evaluative claims. That is honest, and it means the
  executable pilot branches will still consume supplied evaluative judgments
  for those predicates, now labelled as unresolved evaluative standards. The
  gap-matrix row therefore closes as a qualification, not a repair.
- Smallest repair: say so in the row's "Required final qualification" column,
  so that a later result note cannot describe P5 as having closed the bridge.

### F12. Minor source-note imprecision on SARA-IE date completion

- Status: nonblocking.
- Location: `docs/research/legal-interpretation-reuse-2026-10-05.md` line 150.
- Evidence: the retained text (`information-extraction.txt`, section 3) states
  that when only the year is specified, start is the first day and end the
  last day of that year, and the code comment at `sara/models/ie.py:123`
  ("this will inflate probabilities") is confirmed. The phrase "a fallback
  year" was not located in the text extract; it may come from code not
  grepped here. Cite the exact sentence or drop the phrase.

## Phase-by-phase verdict

- **P0:** proceed. Inputs, counts and stale fields verified against the
  selected package. Record the F04 decision in the executed plan revision.
- **P1:** proceed. Import direction verified: the translation model imports
  `interpretation.contracts` and `interpretation.search.models` and nothing
  else from the package; `search/formal.py` imports the translation model
  lazily. A new `interpretation/semantics/` package is a different dotted path
  from the existing `interpretation/assurance/semantics.py`, so there is no
  collision, but the name proximity should be noted. The existing
  `AtomicClaim` vocabulary in that module (actor, action, modality enum,
  conditions, exceptions, temporal, evidence) is a candidate to align with
  rather than duplicate.
- **P2:** revise for F01 and F07 before execution.
- **P3:** proceed after the F05 clarification. The ASPIC+ correction is
  verified: a theory is well-formed only if a contrary of ψ implies ψ is not
  an axiom and not the consequent of a strict rule. PyArg's default last-link
  elitist ordering when no ordering is supplied is verified at
  `argumentation_theory.py` lines 333–346 of the pinned commit. The eight-
  argument exhaustive bound is a stated convenience.
- **P4:** proceed as written. Opinion roles, authority premises, the
  coverage-limited "no contrary case" rule and the missing-authority exit are
  all present. Licence findings verified: PyArg MIT, Carneades 4 MPL-2.0,
  eyecite BSD-2-Clause, Logical English Apache-2.0, CLERC MIT only at
  `retrieval/src/LICENSE` with no root licence and GitHub metadata
  `license: null`, SARA-IE no licence file and GitHub metadata `license: null`.
- **P5:** proceed as written, with the F11 wording.
- **P6:** revise for F02, F03, F06, F08 and F09 before execution.
- **P7:** proceed after the F10 scoping.
- **P8:** revise for F03's window-invalidation statement. The prospective
  machinery is sound as inspected: `freeze` requires machine qualification,
  `observe` rejects repaired windows and stages outside the admission
  interval, `report` marks incomplete observations.

Dependency graph: acyclic as declared; P4's dependence on P1–P3 and P5's on
P4's possibly-unresolved result are consistent. The backward repair loops
(P2 to P1, P7 to the owning phase) are bounded by the two-attempt limit in
master section 8. No legal-uncertainty condition was found that would stop
development: every uncertain-meaning outcome is routed to a qualified result.

## Material assumptions still unexamined

- That the retained candidate readings supply enough material for
  `clauses.propose` to nominate readings A, B and C without fresh generation.
  Not checked; the offline pilot may need a declared hand-entered reading
  with its own warrant, which P2 permits only as an "unrepresented concern".
- That PyArg's pinned commit runs under the project's Python and pydantic
  versions. Not checked; P3 records it.
- That a Hong Kong judgment relevant to paragraph 10 exists in the retained
  official collection. Not checked; P4's missing-authority exit covers it.
- That the four-valued support state survives the existing RuleIR scalar
  types (`bool`, `integer`, `money_hkd`, `date`). The grammar says unknown
  facts remain unknown, but "conflicting" has no scalar representation; P6
  item 2's rejection rule must cover it explicitly.
- That `implementation_identity()` scanning every `.json` under the package
  does not include volatile files. Not checked.

## Program defects versus legal questions expected to remain unresolved

Program defects (repairable by the executor): F01 through F12 above.

Legal questions the program is designed to carry as qualifications, not to
resolve: the meaning of "remain and be ultimately responsible" and its
relation to "fully responsible" in footnote 1; which of readings A, B, C the
SFC intended for paragraph 14 and footnote 5; the applicability of UT Code
6.8 and the Tokenised Securities Circular cross-references; the actual
assessment period; the evaluative standards for adequacy, proper records and
retained responsibility; legal versus beneficial title; the force of "should"
in a circular; and whether any judgment resolves any of these.

## Strongest alternative explanation and weakest evidence

If the program later reports agreement across branches and targets, the
strongest alternative explanation remains a shared mis-encoding at P2: every
engine, renderer and compiler faithfully reproducing the same wrong clause
structure. F01 is a concrete instance of how that happens, since a two-reading
inventory would make A-versus-B disagreement look like the whole dispute. The
weakest evidence in the package is the transfer of US, tax and structured-case
methods to the Hong Kong circular; nothing inspected tests that transfer.

## Files and source sections inspected

Program documents: `claude-handoff.md`; `product.md`;
`product-gap-audit-2026-10-05.md`; `legal-interpretation-master-program.md`
(all sections); phase plans P0–P8 and `README.md`; `phase-manifest.json`;
`program-review.md`; `documentation-review.md`; `validation.json`;
`commit-scope.md`; `legal-interpretation-reuse-2026-10-05.md`;
`legal-interpretation-reuse-review.md`.

Monograph: `06m-legal-interpretation.tex` in full; rendered PDF pages 280–287
(printed 245–252) inspected as images; `monograph.tex` executive-summary diff
against the protected baseline; `references.bib` entry `sfctoken2026`.

Code (frozen copies, byte-identical to the worktree): `contracts.py`,
`search/models.py`, `assurance/qualification_adapter.py`,
`assurance/source_references.py`, `assurance/complete_investigation.py`,
`assurance/investigation_observations.py`, `translation/model.py`; HEAD
diffs for the five that differ. Current worktree: `interpretation/__init__.py`,
`assurance/__init__.py`, `assurance/semantics.py` head,
`assurance/integrated.py` lines 20–33, `assurance/proof_certificate.py`
lines 1–20 and 63, `scripts/assurance_evidence_post_review.py` lines 1–136.

Sources and archive: the retained circular JSON (all 23 paragraphs and eight
footnotes); `aspic-correction.html`; PyArg `argumentation_theory.py` lines
330–365; licence files for PyArg, Carneades 4, eyecite, Logical English and
CLERC; GitHub metadata for SARA-IE, CLERC and PyArg; `carneades.txt` line
829; `clerc.txt` lines 171–174; `hallucination-tools.txt` lines 32 and 1449;
`information-extraction.txt` lines 168, 192–210 and 938; SARA-IE
`sara/models/ie.py` line 123.

Baseline package: `current-post-review-repairs.json`; `result.json`,
`dispositions.json` (entry count, roles, reading identities, four cited
lines) in the selected package; `obligation-evidence-map.json` entry count.

Post-handoff material inspected for conflict only: `execution/README.md`,
`setup-review.md`, `result.json`, `allow.rules`, `allowlist.json`.

## Next executable development step

Start P0 under its current plan from the repository root, with the F04
decision written into the executed plan revision before any overlay is
produced:

1. Re-verify the review package and recompute the baseline identities from
   the selected package (46 obligations, 70 role records, 35 readings); the
   active pointer must still select `post-review-repairs/a1ed4180b665d213f27d465f/`.
2. Build the overlay table for the four cited field paths and any others
   found by the same two patterns (acquired-source-unavailable; categorical
   request condition), preserving original text and predecessor hashes.
3. Implement `semantics/operative.py` and `tests/interpretation/semantics/test_operative.py`,
   then run exactly `.venv/bin/python -m pytest tests/interpretation/semantics/test_operative.py -q`
   plus the regression paths discovered from touched imports.
4. Refresh P1 from the result and, in the same revision, carry F01 and F07
   into P2, F02, F03, F06, F08 and F09 into P6, F05 into P3, F10 into P7 and
   F03 into P8, so that no later phase starts from the unrevised text.

No fresh user input is required for P0 or P1. Later inputs that will be
required and are not supplied by this review: a dependency decision for
PyArg at P3; a bounded official source request specification at P4; a new
registered Lean profile decision at P7. No provider allowance is implied by
anything in this review.
