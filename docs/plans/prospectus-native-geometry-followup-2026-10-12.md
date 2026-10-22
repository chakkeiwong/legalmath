# Native OCR geometry: compare remedies against the located writer failure

## Current evidence and question

The optional product repair has passed its actual Portuguese 2009 consumer,
four matched prior consumers and the finite R0–R8 ladder. It preserves text and
image identity while withholding unusable geometry. The original strict
profile remains strict. This completed repair is a comparator, not a reason to
repeat the same tests without a changed method.

The native callback gives an in-page six-pixel colon box, while fresh PDF
production reproduces a 506.376-point advance. The inspected MuPDF 1.27.2
writer first groups three isolated characters horizontally, then allows a later
vertical join to change the group's rendering axis. The saved sequence and
binary32 calculation explain the observed `21099 Tz`. See the sealed direct
recognition and writer-mechanism evidence and `NATIVE-WRITER-REVIEW.md` in
`ocr-geometry-repair-2026-10-12/`. The first writer replay retains its failed
expectation about which character joined vertically; it is not a successful
end-to-end native-patch test.

Question: can either an explicit group-axis correction or a direct-recognition
adapter supply reliable positions without losing characters, legal qualifiers,
source identity or supported reading order? The native candidates have not yet
been implemented or admitted to production. Valid recognition boxes on one page
do not establish a complete adapter, and corrected scale arithmetic alone does
not establish correct PDF output.

## Skeptical review and evidence contract

The baseline ladder is the pinned native writer, the existing strict product
profile, and the optional unknown-geometry profile. Candidate A preserves an
established group axis separately from character writing direction. Candidate B
consumes direct recognition geometry with explicit word, line, character and
image provenance. Neither candidate may silently replace the installed library
or the default profile. A is tested in an isolated native build; B needs an
explicit versioned worker contract before product use.

Primary acceptance requires actual production of the candidate's output and
actual product consumption on a frozen cohort. Required invariants are exact
raw-character accounting, retained negations and qualifications, source/image
identity, finite ordered positions, and unchanged matched legal answers where
the evidence is unchanged. On the reproduced page, the colon must remain within
the source image without clipping, deletion or fabricated coordinates.

False locations, omitted words, broken vertical/bidirectional text, changed
qualifiers or silently resolved legal unknowns veto candidate promotion. A
missing required layout family vetoes promotion to that family, not further
bounded investigation. Source/model/library mismatch, corrupt evidence, a
changing running method or an unsafe native ABI invalidates the experiment and
stops dependent runs. Runtime, counts and aggregate span scores explain behavior;
they do not rank packages or establish legal correctness. The evidence is
deterministic development evidence; stochastic superiority is not being tested.

Audit verdict: the mechanism supports these candidate hypotheses, but a
single-page replay does not support immediate native replacement. Freeze the
cohort and the candidate interfaces before implementation. An absent standalone
Tesseract executable does not block the retained native diagnostic, and another
identical OCR call would add no discriminating evidence. Retain every failed
candidate; revise only after naming what changed and why it answers the failure.

## Assumptions to test early

| Choice | Provenance and status | Failure mode | Earliest discriminating check |
| --- | --- | --- | --- |
| MuPDF 1.27.2 / PyMuPDF 1.27.2.2 | Installed, hashed reproduction baseline | Different native library makes the comparison irrelevant | Hash the loaded version-suffixed library and reproduce saved PDF words |
| 300 dpi and integer grayscale/padding | Inspected native writer; matched baseline | Different recognition input masquerades as a geometry repair | Compare source raster, model bytes, preprocessing and exact callback sequence |
| Separate established group axis | Hypothesis from the retained mixed-axis transition | Legitimate vertical or bidirectional layout is damaged | Freeze both true vertical groups and horizontal groups adjacent to vertical marks |
| Direct callback boxes | Candidate input, not reviewed product geometry | Callback lifetime, Unicode assembly, coordinate transform or order is wrong | Subprocess ABI probe, multibyte characters, raster-to-page conversion and complete accounting |
| Existing English/Portuguese readings | Development comparators | Tuning to exposed cases masquerades as general accuracy | Keep exposed cases labeled; require a separate, independently reviewed cohort for acceptance |

## Ordered packages and transitions

1. **Freeze coverage and candidate interfaces.** Start from already retained
   Portuguese 2009, English 2009 audit/committee and both 2010 assurance cases.
   Add source-bound ordinary text, mixed columns, tables, right-margin legal
   text, rotations, true vertical writing and bidirectional text. List missing
   families explicitly; use labeled synthetic diagnostics only for engineering
   controls, never as substitutes for real legal pages. Freeze complete
   qualifications, numbers, dates and expected image regions before running a
   candidate. Retain original-language 2008 audit coverage as a separate source
   task; the PDFs are already downloaded. Record native dependency and ABI
   identities, and the expected adapter schema, before candidate implementation.
2. **Test candidate A in isolation.** Preserve the installed runtime. Build the
   inspected tagged writer plus the smallest axis-state patch in an isolated
   directory. First require actual PDF reproduction of the known failure on
   the unpatched build, then compare the patched PDF. A Python replay can
   diagnose the patch but cannot replace this native test. Stop the dependent
   comparison if a matching build cannot be established; continue independent
   cohort/source work and record the exact build blocker.
3. **Test candidate B in isolation.** Keep native calls in a bounded child
   process. Bind raw callback events to raster/source/model/library hashes;
   specify coordinate conversion, word boundaries, Unicode and reading order.
   Require exact accounting before implementing a separately selected product
   adapter. Do not infer a word box by stretching text across a grouped line.
4. **Run matched actual consumers.** Use the same frozen pages, raster/model
   bytes and reviewed questions for baseline and each viable candidate. Retain
   changed raw text as a new source version, never rewrite historical P1.
   Exercise spatial consumers and correction maps as well as final answers.
   Continue a planned repair after a candidate failure unless experiment
   validity or safety, rather than candidate quality, has failed.
5. **Review, adopt narrowly, refresh.** Separate our contract/ABI/usage failures,
   native writer defects, recognition errors and missing evidence. Adopt only
   the tested optional scope. Bind changed code and evidence to new controller
   receipts, refreshing between phases. Require fresh independent review and
   wider source evidence before default promotion or legal acceptance.

Each package needs a frozen command, actual interpreter/library identities,
timeout, before/after hashes, result, decision table and next-action reason.
Write results under a new `native-geometry-followup-2026-10-12/` package. Keep
implementation, geometric validity and legal interpretation in separate notes.
Use the worktree source on `PYTHONPATH`, and hide GPUs for CPU work. No required
dependency is installed or source fetched merely because this plan names it;
investigate the existing runtime/corpus first and request a narrow approval
only if actual permissions require it. Tool calls yield after one second,
logs stay in files, and progress reports summarize completed evidence.

## Other master-program work remains visible

Independent ready work is broader image/vector/table review, Portuguese 2008
report consumption and source-specific scope review. Source authenticity,
historical publication, fourteen onward-source dependencies, native read
confinement, second-host portability and qualified unexposed readings remain
separate obligations. The native experiment cannot close them. Missing client
facts do not prevent conditional source analysis; missing independent review
blocks acceptance, not authorized local preparation.

The next justified native action is package 1, not a production switch. Native
candidate execution is pending the frozen coverage/interface record. The
optional integration repair is complete; the whole prospectus program is not.
