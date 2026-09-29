# Continuation environment repair

C5 attempt 1 stopped at `ModuleNotFoundError: No module named 'fitz'` after
its qualification tests passed. The application environment deliberately uses
`pypdf`; the manuscript environment provides PyMuPDF. A second uninstalled
dependency, BeautifulSoup, was also present in the same source-recheck path.
Neither dependency was necessary for the source inventory. The repair uses the
existing application PDF/HTML extractors and records their identities. Missing
expected source text now raises an explicit reference failure.

The same audit found that C7 selected the application interpreter for manuscript
checks and selected pdfLaTeX for a manuscript using `fontspec`. C7 now invokes
the existing manuscript builder, which uses XeLaTeX, settles both volumes'
references and checks/export links. A separate recorded interpreter probe must
find PyMuPDF before the build. No application dependency or scientific default
changes.

Successful C0–C4 receipts remain intact but become stale after implementation
edits. The runner distinguishes revalidation of an intact successful receipt
from repair of a failed receipt. Both consume the existing three-attempt bound;
neither deletes the predecessor or resets a live budget. A failed or corrupted
receipt still requires a bound repair note and an executed passing reproducer.

Skeptical audit: these repairs address reproducible environment mismatches and
an inaccurate retry classification. They do not change legal labels, formal
domains, model budgets, source editions or any acceptance criterion. The focused
reproducer must execute the real residual-source inventory in `.venv`, verify
the separate document interpreter and test failed/stale receipt handling.
Only after it passes may C5 be retried. Prior successful phases are rerun against
the repaired implementation before live execution.
