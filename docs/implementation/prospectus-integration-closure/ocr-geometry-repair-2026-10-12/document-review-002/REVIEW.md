# Isolated chapter proof after the geometry repair

Command: `latexmk -xelatex -interaction=nonstopmode -halt-on-error review.tex`,
run in this directory with output retained in `build-final.log`. Exit status 0;
the resulting PDF has nine pages. `source.tex` is the exact revised chapter
snapshot. `review.tex` uses the project's typography and inputs that chapter.

Rendered pages 5–6 were inspected at 90 dpi after rebuilding. The new audit and
committee paragraph starts together on page 6; its first line is no longer
stranded at the bottom of page 5. Text, footnotes and raw/assisted distinctions
are legible, with no visible clipping on the changed pages. The writer-cause
paragraph distinguishes the original unresolved diagnosis from the later
matched recognition/PDF evidence. The optional repair and unvalidated native
fix remain separate. Earlier renders are retained as earlier proofs.

One external reference, `sec:prospectus-delivery`, is unresolved in this isolated
proof because the referenced section is in another chapter. No full-monograph
build is claimed. Visual self-review supports the local pagination correction;
it does not establish a human-voice acceptance verdict. Reader-facing prose
remains provisional pending human review.
