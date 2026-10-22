# Portuguese 2008 reports consumed; semantic automation remains open

The actual P1/P2/P3/final-answer path consumed three complete-page development
readings: the consolidated audit (PDF pages 245–247), individual audit
(248–249), and committee report (250–251). Original images establish these
boundaries. Before OCR, the seven pages supplied only 223 native footer
characters. The existing pinned Portuguese worker recovered 2,121 words in
13.33 seconds. The strict v1 geometry profile accepted this case; no optional
geometry relaxation or product-code change was needed.

The reports now produce conditional supplied-scope answers. The consolidated
audit refers to EU-adopted IFRS. The individual audit refers to Banco de
Portugal's adjusted accounting standards, explicitly retaining the exceptions
under Avisos 1/2005 and 4/2005. The audits are dated 25 February 2009; the
committee's concurrence is dated 26 February 2009. These findings are about
what the retained reports say, not independent adjudication of the accounts.

All 15 engineering checks passed. Fourteen adverse inputs were rejected,
including the wrong edition, changed quote, omitted middle page, inconsistent
report category, invented date, promoted publication date, omission of the
committee and transfer of consolidated criteria into the individual reading.
A missing conclusion withheld a complete scope finding in the actual final
answer. The matched instrument questions, assembly and dependencies are
unchanged. The full consumer comparison took 43.69 seconds.

Two additional probes expose the boundary of the supplied-semantics design.
An exact quote of 13 March 2008, which concerns a different committee action,
can be supplied as the report date. An exact fragment of the individual
audit's IFRS wording can omit the following NCA exceptions. Structural span
validation accepts both. The image-reviewed facts reject those readings, but
the engine does not independently establish that semantic judgment. This is
an implementation capability gap for automatic interpretation, not a failure
of PyMuPDF/Tesseract to supply these words. `semantic-limits.json` retains the
probes. They motivate semantic date-role and accounting-qualification checks
in the existing relation-discovery work, without claiming a new repair done.

Raw OCR still contains accent and punctuation errors, noisy corporate footers
and signature regions. `development-readings.json` records the observed
differences. Exact retained-character accounting means all retained source
characters were consumed, not that every image character was recognized.
Publication, historical availability and edition authenticity remain UNKNOWN.
The inherited bundle dates/identifier are development request context; they
are not evidence of an instrument's legal position or report availability.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the three supplied report results | All downstream and preservation checks pass | Corruption controls reject; source/method identities unchanged | OCR fidelity outside inspected body spans; independent reading | Task-specific acceptance review/validator; preserve raw/image differences | Full automatic interpretation or independent legal acceptance |
| Keep date and qualification semantics under explicit review | Both misleading exact-span probes accepted structurally | Automatic semantic promotion veto remains | Generality beyond these two probes | Use these counterexamples in relation-discovery work | Native-package unsuitability |
| Continue the authority's next ready task | Actual result retained | No execution-continuation veto | Program-wide gaps remain | Review image/vector/table page coverage | Whole-program completion |

Commands, environment, git identity, source/model/method bindings and wall
times are retained in `page-inspection.json`, `ocr-started.json`,
`ocr-result.json`, `source-result.json`, `consumer-started.json` and
`consumer-result.json`. All commands used one-second tool yields and retained
sessions. CPU only; GPU intentionally hidden. Seeds are not applicable to
this deterministic retained-source comparison.

Post-run review: the strongest alternative explanation for apparently good
results is that supplied classifications hide automatic semantic weaknesses.
The two accepted misleading-span probes demonstrate exactly that risk. An
independent reading or a semantic verifier detecting those probes would
change the acceptance position. This evidence validates a conditional
development path; a reviewed task-specific authority validator has not yet
accepted the full task. Record partial work honestly and continue execution.
