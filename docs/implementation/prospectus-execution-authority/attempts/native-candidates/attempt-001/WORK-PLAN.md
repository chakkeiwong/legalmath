# Bounded direct-callback candidate and native-build prerequisite

The accepted callback interface preserves 266 words and 1,409 nonspace
characters from the original Portuguese 2009 page 177. The installed native
writer, strict intake and optional unknown-geometry intake remain the exact
comparators. The newly retained table and rotated-label pages are additional
development cases; no recognition callbacks for them have yet been retained.

Research intent: test whether a separately labeled callback-to-page prototype
can preserve every observed character and expose the known colon to the actual
spatial consumer without borrowing the generated PDF's corrupt position.
Candidate A remains the isolated tagged native-writer patch; candidate B is
the explicit callback adapter. This attempt does not substitute a Python
writer replay for a compiled candidate A.

## Skeptical audit and evidence contract

The main risks are confusing pixels with page points, treating the padded
recognition width as the original page width, adding a false page offset,
silently losing words at callback boundaries, and interpreting single-page
success as general OCR/layout acceptance. Check the original PDF's crop box,
rotation and 300 dpi rendering against the retained raster before applying
any coordinate transform. The prototype accepts only that unrotated,
origin-zero, non-deskewed page, using points = pixels × 72/300. Raster ceil
padding is not a justification to stretch coordinates by page_width/pixels.
All boxes must lie inside the original page; clipping is forbidden.

Primary criterion for this prototype: exact original event-index accounting,
word sequence equal to the retained generated-PDF words, exact 1,409-character
sequence, finite original-page boxes, and successful actual projection of the
colon using its callback rectangle. The optional baseline must continue to
refuse that spatial projection. This is a useful finite diagnostic, not full
task acceptance. Source/model/library/raster mismatch or unsupported rotation
invalidates the run. Lost characters, false positions or altered qualifiers
veto candidate promotion. Missing real vertical/bidirectional and independent
readings veto promotion to those families; they do not veto this investigation.
Runtime and word counts are explanatory only. Adverse controls must refuse
wrong callback identity, image identity, event accounting and page transforms.

Defaults: 300 dpi, preprocessing and the callback ABI come from the already
matched native trace, not from a new convenient OCR configuration. The actual
interpreter and native-library identities are checked and retained. One word
per diagnostic source unit avoids merging character direction with line axis;
it makes no claim about general reading order. The prototype lives in this
attempt; it changes neither the installed library nor production intake.
Audit verdict: proceed under the finite contract. Do not call it production
integration or a completed native remedy.

Candidate A preflight: the retained evidence includes the tagged writer and
recognition source files but no matching complete native build manifest.
A filename search of accessible `/tmp` found no MuPDF source archive or build;
unrelated protected system temp directories were not inspected. This does not
prove a build is impossible or that MuPDF is unsuitable. A matched clean
tagged source/dependency checkout, unpatched build reproduction, isolated
axis patch and actual PDF comparison are still required. No arbitrary system
library replacement is a valid shortcut. Retain this prerequisite explicitly.

Commands (120-second bounds, one-second tool yields):

1. `timeout 120 /home/chakwong/miniconda3/envs/tfgpu/bin/python docs/implementation/prospectus-execution-authority/attempts/native-candidates/attempt-001/check_transform.py`
2. `timeout 120 .venv/bin/python docs/implementation/prospectus-execution-authority/attempts/native-candidates/attempt-001/callback_candidate.py`

The first command must establish a valid transform before the second runs.
Keep complete results in this attempt, deliberately hide GPUs, and record
seeds as not applicable. No new recognition, network call or install is
needed for this diagnostic. On source invalidity stop its dependent probe;
on a candidate failure retain it and move to its named repair or independent
source work. Full acceptance requires fresh bounded ABI execution on the
larger cohort, downstream correction/report consumers, matched A/B evidence
and a task-specific validator.
