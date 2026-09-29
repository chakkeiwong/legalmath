# Round 11: multiple-assurance execution plan

Date: 2026-09-25  
Owner: LegalMath engineering  
Scope: local, public-source engineering evidence for the SFC circular pipeline

## Research and engineering question

Can independently implemented evidence routes expose omissions or semantic
changes in a circular-to-Java control before a proposal is released for
institutional review? The round tests source recovery, competing
interpretations, formal evaluation, generated Java behaviour, and mutation
resistance as separate claims. It does not treat agreement among software
components as proof that an English interpretation is legally correct.

## Evidence contract

| Item | Declared contract |
|---|---|
| Baseline | Existing round-10 public-source issue runner plus the deterministic assurance, search, reliability, evaluation, and operations suites in this repository. |
| Primary pass criterion | Every required route either produces a replayable result or records an explicit unavailable/uncertain result; no material discrepancy is silently accepted; generated Java passes contract, boundary, and mutation checks. |
| Veto diagnostics | Missing source route; page-level source disagreement; uncovered material source unit; unresolved candidate disagreement; solver unknown or cross-solver mismatch; Java compile/runtime mismatch; stale input hash; malformed or missing evidence. |
| Explanatory diagnostics | Parser confidence, OCR quality, route scores, runtime, mutation count, candidate ranking, and coverage percentages. These cannot promote a phase. |
| Repair trigger | Any veto, stale artifact, failed test, unavailable mandatory route, or changed input. Repair must be executed and recorded before retry. |
| Continuation veto | Corrupted source, broken harness, missing required local input, or exhausted repair budget. A failed candidate route alone is not a direction veto. |
| Artifact | `artifacts/interpretation/round11/` phase manifests, raw route outputs, hashes, repair records, and refreshed next-phase plans. |
| Non-claims | A pass is engineering evidence only. It does not establish legal correctness, SFC approval, English semantic equivalence, production readiness, or that independent counsel can be removed. |

## Default and assumption audit

| Choice | Provenance and reason | Failure mode and early diagnostic | Status |
|---|---|---|---|
| CPU-only execution | Reproducible local route; this work uses no numerical GPU kernel | A hidden accelerator could change a learned route; manifest records CPU-only and no model call is enabled | Reviewed baseline |
| Existing round-10 runner as comparator | Frozen repository evidence and public-source bounded run | It may share extraction or prompt assumptions with a new route; route-family labels and independence notes are required | Comparator |
| ResearchAssistant parser | Local code already used for PDF archival and has explicit low-confidence/manual-review states | It may omit equations, citations, or visual layout; preflight and per-page reconciliation expose this | Reused route, not oracle |
| Docling/Tesseract/solver tools | Open-source routes surveyed in `docs/research/assurance-open-source-tools.md` | Installation or version drift; lock and import checks are mandatory | Candidate routes |
| Majority agreement | Not used as a correctness rule | Correlated routes can repeat one omission; discrepancy and common-mode risk remain explicit | Prohibited shortcut |
| Local Catala pilot | Pinned executable and two authored definitions in the Catala worktree | Pilot covers a small RuleIR slice and cannot prove whole-circular equivalence | Optional independent route |
| Three repair attempts per phase | Existing supervisor convention | Repeated retries could hide a design flaw; each attempt is immutable and the budget is hard | Reviewed control |

## Phase contract

1. **M0 documentation.** Add a self-contained assurance chapter section, tool
   contracts, concrete failure trace, and limits to the monograph. Build and
   run reader-facing, canonical structure/citation and bounded mathematics
   checks. External references resolve only through explicitly declared local
   companion documents. The existing Lean v4.29.1 toolchain is pinned so checking
   a theorem does not depend on a lookup of the latest release.
2. **M1 preflight/install.** Record existing tools and, only after explicit
   approval for the exact allowlisted command, install optional Python tools in
   the isolated assurance environment and extract Ubuntu OCR packages into a
   project-local sysroot without sudo or system installation. A
   failed installation remains evidence; it is not converted to a pass.
3. **M2 source routes.** Re-run the LegalMath, ResearchAssistant, layout/OCR,
   and optional Docling routes on retained SFC PDFs and compare page and source
   unit hashes. The route report preserves raw excerpts and missing fields.
4. **M3 formal routes.** Cross-check supported Boolean candidate bodies with
   cvc5 and the existing Z3/Java comparison. Compare clingo and exhaustive Python
   stable-extension semantics on every directed graph up to three nodes.
5. **M4 evaluation and Java faults.** Run Inspect deterministic hidden-target
   evaluation and the PIT/JUnit Boolean and threshold pilot. The generated Java
   backend is also checked in the full regression phase.
6. **M5 regression and synthesis.** Run the existing multiple-candidate/tree
   search, challenge, Java and entire regression suite. Join current evidence,
   preserve uncertainty and regenerate the successor plan. Repair/refresh is
   enforced between all phases, not postponed until the end.
   Post-completion synthesis binds the accepted M5 manifest and all predecessors;
   it is separate from the summary produced while M5 is still running.

## Pre-mortem

The most dangerous false success is correlated omission: all text-based routes
miss a footnote, then the ensemble reports unanimity. The source phase therefore
requires a visual/OCR route or an explicit unavailable veto and retains page
images/hashes. A second false success is solver agreement on a fixture that does
not encode the disputed English clause; every formal artifact states its scope.
A third is a Java test that exercises only the happy path; mutation tests must
kill changed polarity, missing exception, boundary, and stale-version mutants.
Finally, an installation can succeed while the tool is incompatible with the
repository; imports, version capture, fixture smoke tests, and route-level
outputs are required before promotion.

## Exact execution boundary

The master program is `scripts/run_assurance_master.py`. Its commands are
listed in `docs/implementation/interpretation-round11/allowlist.json` and are
matched as exact fixed argument vectors; shell strings, unknown executables, paths
outside the repository or approved local tool roots, and network/model calls
are rejected. The no-network commands may run in the normal environment. The
single installation command is separately authorization-gated because it may
access package indexes, public layout weights, Ubuntu package downloads and
Maven jars. The program uses no sudo and changes no system package. No arbitrary
package name or shell command is accepted. Phase M0 uses the pre-existing
PyMuPDF document interpreter at `/home/chakwong/miniconda3/envs/tfgpu/bin/python`
without importing a GPU framework or changing that environment.

## Review record required before each phase

The program writes `next-plan.json` after every phase and rebinds the substantive
author review in `design-review.json` to current input hashes before execution.
This mechanical rebinding is not a fresh independent review. When a phase fails,
the operator records actual changes and regression evidence with `repair`; the
program executes its fixed focused regression and refreshes the same phase.
Semantic source discrepancies trigger two evidence actions and remain unresolved.

## Planned commands

```text
python scripts/run_assurance_master.py audit
python scripts/run_assurance_master.py preflight
python scripts/run_assurance_master.py refresh M0
python scripts/run_assurance_master.py run M0
python scripts/run_assurance_master.py install M1   # exact elevated approval required
python scripts/run_assurance_master.py execute
```

The program may execute `repair Mx --note ...` and `refresh Mx` between retries;
it may not skip a predecessor, silently increase installation scope, or
reinterpret a missing route as a successful route.

## Final skeptical audit and repairs

The additional canonical checks on 25 September exposed a legacy checker that
did not resolve the monograph's explicit `externaldocument` references. All nine
reported targets exist in the technical companion, and the reader-facing
two-document check already validated them. The repair resolves only documents
declared by the main source and still rejects missing sources or labels. No
manuscript passage was deleted or rewritten to hide the failure.

The standalone mathematics check initially hit a ten-second Lean timeout while
the unpinned launcher looked up a latest release. The same unchanged Lean source
then verified. The executor now pins the previously successful, installed
v4.29.1 toolchain and preserves the exact bounded obligation results inside each
document attempt. This checks the written formal statements, not the English
interpretation or the validity of the illustrative probabilistic assumptions.

M5's second attempt stalled in an existing Starlette TestClient startup under
the filesystem/network sandbox. Its stack trace and interrupted attempt remain
retained. The repair is to use the already approved absolute trusted runtime
vector, not to change or omit the API test. A fresh full regression is required.

The final-report review also found a timing issue: M5 cannot hash its own final
manifest while its summary command is still running. A post-completion report
now validates and binds every accepted phase, preserves every unresolved source
issue, and refreshes the successor plan with M5 included. A focused regression
rejects incomplete or stale evidence and checks that unresolved issues survive
finalization. These repairs pass the pre-run audit because they strengthen the
evidence binding and leave the engineering/interpretation distinction intact.
