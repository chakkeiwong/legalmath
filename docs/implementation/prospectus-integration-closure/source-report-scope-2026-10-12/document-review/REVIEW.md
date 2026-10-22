# Section proof and source fidelity

The protected `before.tex` and `meaning.json` precede the additive revision.
Existing equations, citations, historical failures and limitations remain in
the section; the addition explains financial-audit versus committee versus
sustainability scope, Portuguese wording, internal dates and the optional
report-reading path. It introduces no new academic-literature claim.

`latexmk -xelatex -interaction=nonstopmode -halt-on-error review.tex` passed.
The isolated section proof has eight pages. Changed pages 4–5 were rendered
with the existing CPU-only PyMuPDF interpreter and visually inspected for
text/footnote clipping, source distinctions and paragraph continuity. No
clipping was observed on those pages. Isolated cross-section references remain
unresolved because the rest of the monograph is not included in this proof;
the proof is not a full-book build. The project `.venv` lacks PyMuPDF, so the
first rendering import failed and the existing research interpreter was used.

The technical narrative remains provisional pending human reader feedback.
Compilation and author self-review do not establish a human voice or
independent legal correctness.

After the independent Portuguese 2009 case exposed invalid geometry, the
section gained one paragraph explaining the actual failure and unresolved
producer mechanism. The final proof rebuilt successfully to nine pages.
Changed page 5 was rendered and inspected again: the new paragraph and source
footnote are readable with no clipping; the prior page-4 scope distinctions
remain unchanged. `build-final.log` and `rendered-text-final.txt` preserve that
final build. The proof remains isolated, not a full-monograph build.
