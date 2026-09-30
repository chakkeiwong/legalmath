# Two-case bond reader repair

Authorised 30 September 2026: thoroughly review and execute the Santander and
Unilever repair sequence. Baseline commit:
`dc4e424ab73bebc4503badd8666464eee388221c`. Worktree:
`.worktrees/bond-two-case`, branch `feature/bond-two-case-repair`. Preserve the
other campaign in the shared main checkout. Results belong under
`docs/implementation/bond-two-case-repair/`; source originals remain under
`docs/prospectus/`. The published baseline is copied to `baseline/` there.

## Research intent and evidence contract

Question: can the reader resolve a mandatory-conversion construction and an
edition-bound corporate source bundle without unsupported affirmative or
negative answers? Candidate: explicit copular and numbered-list conversion
relations, scoped polarity/holder-option handling, checked definitions and a
recovered Unilever source bundle. Comparator: the preserved v2 reader and
28-row report (12 positive, 14 negative, two unresolved).

Primary engineering criterion: construction-derived semantic obligations pass,
newly resolved rows carry replayable source witnesses, old-row changes are
explained, source tampering is rejected and independent formal/backend checks
pass. Counts of resolved rows and execution time are explanatory only. Wrong
edition, source damage, forged derivations and unsupported polarity or target
bindings veto promotion and trigger repair. Broken harness/environment or
invalid data veto dependent execution until repaired. An unfamiliar phrase or
remaining abstention rejects candidate coverage, not the research direction.

No human answer labels or model majority provide quality authority. Formal
premises and deliberately constructed transformations determine test
obligations. Backend agreement validates neither the English parser nor the
completeness of the legal sources. Passing cannot prove unrestricted English
interpretation, absence of all contractual loss mechanisms, current trading
eligibility, legal completeness or unknown-future generalization.

## Thorough review and assumptions

The initial plan needed three concrete refinements before implementation:

* The current sentence splitter separates the numbered items in Santander
  Condition 5.1 from their governing actor and modal. Adding a copular keyword
  rule alone would bypass the operative provision. Retain the list head and
  action spans together; reject an intervening actor, negated action or
  unsupported construction rather than transferring an unrelated obligation.
* A global holder-option test can suppress an unrelated mandatory action, and
  “not convertible at the holder's option” does not negate mandatory conversion.
  Test the scope of that negation and option in each relation.
* Unilever's recovered base must be bound by its edition and selected terms.
  Blank final-term forms cannot supply facts. Its separate trust agreements,
  incorporated financial reports and later amendments are not silently treated
  as a proved closed legal source set. Preserve that qualification.

| Choice | Provenance and role | Failure mode | Early diagnostic |
| --- | --- | --- | --- |
| Principal write-down or compulsory common-share conversion | User definition; baseline formal target | Coupon loss or preferred-share conversion counted as principal feature | Formal slot contrasts and four-state decision checks |
| Copular/list grammar | Explicit language families; hypothesis | Obligation/negation attaches to another action | Contrastive action, actor, polarity, option and class tests |
| Named share and security terms | Dated selected conditions; hypothesis | Other security or conflicting definition supplies a premise | Foreign section, undefined alias, conflicting definition mutations |
| Unilever 16 May 2025 edition | Final-term reference and recovered content-addressed asset | Newer base silently replaces applicable conditions | Cover/date markers plus original/extraction hashes |
| Programme form boundaries | Printed section headings; qualified source interpretation | Unselected blank option treated as actual issue term | Boundary markers and no binary fact from a blank form |
| Existing Python/JDK/Catala/Lean | Recorded baseline toolchain; convenience reuse | Shared editable environment imports main instead of worktree | Assert module ROOT and imported paths before running |
| Fresh challenge | Two additional source families after method freeze; hypothesis | Exposed cases counted as heldout or selective success reported | Predeclare acquisition protocol and retain every failed attempt |

Pre-mortem: the run could appear successful by fitting Santander's label,
ignoring Unilever's base, or counting both repaired cases as fresh validation.
Early construction tests, exact source dependency checks and preserved freeze
timestamps address those risks. The strongest residual risk is shared
interpretation logic; all real-English answers remain qualified.

Audit verdict: execute this revised bounded plan. No baseline tally is a target,
unexamined source assumptions are stated, no new tool installation or model spend
is needed, and repairs continue after expected candidate failures.

## Executable phases and refresh mechanism

All commands run from this worktree with `PYTHONPATH=src` and
`.venv/bin/python`. The environment points to the existing project virtualenv;
toolchain files are shared read-only. CPU only; no GPU framework is imported.
No random seeds apply. Every run preserves git commit, dirty method hashes,
commands, tool versions, data hashes, wall time, plan and output paths.

1. **Source and baseline.** Verify imports and sources, extract the recovered
   memorandum, identify dated references and form boundaries, create a new
   inventory, replay the baseline and record unresolved clauses. Never edit the
   frozen fresh inventory or old execution results.
2. **Specify and repair.** Write general construction and adversarial tests;
   record baseline failures. Implement witness and scope repairs. Run
   `PYTHONPATH=src .venv/bin/python -m pytest tests/prospectus/test_loss_absorption_two_case.py -q`.
   Preserve failed runs and explain each causal repair.
3. **Corpus and integrity.** Run the original 26 and repaired two cases in a
   combined new inventory using
   `PYTHONPATH=src .venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-reader-v2-repair/issue-inventory.json --output docs/implementation/bond-two-case-repair/corpus-001 --checks`.
   Run the full prospectus suite with JUnit output. Exercise altered source
   bytes, omitted dependencies, wrong edition/issuer, and missing/reordered
   pages. Fix failures and rerun into new numbered directories.
4. **Freeze and new sources.** Freeze all method, test and reporting files and
   the acquisition protocol. Acquire one additional bank capital issue and one
   corporate senior issue from previously uninspected issuer families, using
   public issuer or exchange documents and explicit edition binding. Retain
   download failures; report abstentions. Source discovery must not inspect
   expected classification labels. Stop after at most three candidates per
   category; missing sources limit coverage rather than invite label selection.
5. **Delivery.** Verify derivations and evidence against originals, compare
   every baseline row, rebuild the complete Markdown/CSV/JSON/PDF report and
   inspect rendered pages. Record qualifications, result/decision table,
   post-run red-team note, reset memo and the next justified phase. Commit only
   this task's changes and integrate without overwriting concurrent work.

After each phase write `phase-N-review.json` and refresh `next-phase.md` under
the result directory. A failed check writes a retained failure record plus a
causal repair before a new attempt. Final acceptance requires actual published
artifacts and completed tests, not a checklist or two expected labels.
