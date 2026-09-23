# Unified monograph reset memo

22 September 2026. The user requested a single coherent book combining the
product proposal and interpretation monograph, with content preservation and
page counts. That document task is complete as an author draft.

## Current result

Canonical source/PDF: `docs/monograph/monograph.tex` and `monograph.pdf`.
The book has 232 pages, ten chapters and 76 cited references. The old
`docs/proposal/proposal.tex` includes the canonical entry point; the standard
build copies the canonical PDF byte-for-byte to `docs/proposal/proposal.pdf`.
Both entry points were independently compiled and all pages compared in text
and pixels. Original pages were 66 and 153 (219 combined).

The user’s preservation priority was applied without forcing the combined book
under the earlier 200-page estimate. The original monograph’s typography remains
12-point A4. Integration is thematic within ten chapters, not concatenation.
There is one introduction, contents and bibliography. The SPI transaction is
followed by the 23EC46 uncertainty case. The Java chapter retains the early demo
and explains the actual MVP interface. Chapter 8 now covers complete execution,
W-to-T task mapping, all T dispositions and the current API, followed by the
proposed E tasks. The 27-page ensemble chapter remains intact.

## Preservation and change discipline

Both original documents and prior reviews are frozen under
`.localresources/unification/baseline`, with 68 files in its manifest. Do not
modify that baseline. `docs/monograph/review/unification/source-retention.json`
records all 207 original source units, their locations, exact editorial edits
and hashes. The human-readable `content-map.md` links the originals to final
printed pages. Twenty explicit edits in fourteen units correct status,
interfaces, references and a long filename; headings and bridges are separately
recorded. The original 33 equation environments, 18 listings, six figures,
119 labels and 76 cited sources are retained.

`.localresources/unification/assemble.py` is a one-time integration tool reading
the frozen originals. Do not rerun it blindly after editing generated chapters;
it would overwrite later changes. Future substantive edits should update the
explicit preservation record and checker evidence. Numbered fragments under
`docs/proposal` are historical inputs, not current authoring files.

## Validation and evidence boundary

Run `python3 scripts/build_unified_monograph.py` from the repository root to
build, synchronize PDFs, validate citations/pages/source retention and write
the proposal compatibility validation. The existing system Python has PyMuPDF.
The final build/check record is `.localresources/unification/build-delivery.log`.
The delivery manifest binds current sources and reports without hashing itself.

Automated document and preservation checks pass. The runtime’s 119 protected
input identities remain unchanged, including its previously recorded browser
harness repair. No app tests or live-provider experiment were run for this merge.
The existing design-contract result remains bound to unchanged contracts.
Twenty-nine selected final pages have normal-resolution author reading evidence,
with page-by-page hashes and transfers only for byte-identical prior renderings.
All 232 pages have extraction/bounds and entry-point pixel comparison checks.
The final candidate has eleven nonfatal longtable shrinkage notices and 36
underfull box notices; no overfull box, missing character or undefined reference
remains. These are not claimed to be a warning-free build or continuous reading.

Independent legal, technical and reader acceptance remain pending. The earlier
154-test execution belongs to the retained MVP evidence. The ensemble E01–E14
is specified, not implemented; no legal-completeness guarantee follows from
agreement, preservation or compilation. No Claude review was invoked.
