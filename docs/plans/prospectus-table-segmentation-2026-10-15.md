# Discriminate table OCR usage failure on the original raster

The frozen whole-page baseline is page-coverage/attempt-004:1033 words retained
exactly by the importer,15 of20 exposed controls mismatch,including1.57% read
as157%. All four titles are absent. Legal outcomes remain unknown/partial.
The original raster,20 controls,baseline worker words and complete answers are
sealed. This is a recognition/segmentation failure of the current usage; a
fundamental package limit has not been established.

Question: does isolating the same frozen regions,with explicit border/scale
handling,change these errors without modifying recognized strings? Compare
the actual existing full-page OCR with two fixed arms using the same PyMuPDF
runtime and English model: exact integer crop plus10 white pixels on all sides
at original pixel scale; that same crop with each original pixel repeated3x
in each dimension,then30 white pixels on all sides. These are two predetermined
diagnostics,not an open tuning search. Retain the whole crop pixels unchanged
inside the white pad; do not erase rules,threshold,repair punctuation,use a
numeric whitelist,inject reference strings or replace blanks with zeros.

Engineering pass: source/raster/model/runtime identities match;all20 regions
are accounted in each arm;exact crop/scale/pad bytes and reversible coordinate
maps are retained;worker raw text and words reach a separate review consumer;
the frozen full hybrid answer is unchanged. Primary sample criterion for an
arm to remain a candidate for further validation: all18 printed literals and
both empty regions match exactly. A mixed result triggers a localized further
diagnosis,not automatic promotion or package rejection. Report every mismatch
and any regression from the baseline. Neither better sample counts nor timing
establish general superiority,table structure,independence or default readiness.

The review consumer must explicitly keep crop output outside the source graph,
show the raw source layer and candidate readings together with transformation
and word locations,and withhold cell acceptance. It must refuse altered image,
crop/model/packet identity or a promotion/completeness claim. A full-table
interpretation requires a later explicit schema and independent complete cell
inventory; this diagnostic does not invent one.

Research intent and assumption audit:

| Choice | Provenance and role | Failure mode | Earliest diagnostic |
|---|---|---|---|
| Existing300dpi English model | Unchanged baseline | Tiny glyphs and table rules mislead segmentation | Whole-page baseline already retains exact wrong strings |
| Frozen20 region boxes | Exposed agent image inspection | Box can clip glyphs or include rules | Retain and inspect crop contact sheet before OCR |
| Ten-pixel white pad | Convenience hypothesis to isolate page boundary | Segmentation still omits short lines | Compare unscaled crop with whole-page baseline |
| Threefold pixel replication | Hypothesis about glyph size;not new source detail | Upsampling amplifies noise or changes recognition | Compare same crops at1x/3x and retain all regressions |
| Exact string matching | Predeclared literal screen | Whitespace joining differs from printed spacing | Preserve raw words and full text;no textual cleanup |
| Same embedded OCR API | Installed official source inspected | Page segmentation modes are not exposed | Preserve the API source excerpt;make no claim to have tested PSM tuning |

Skeptical review: PASS for this bounded mechanism test. The failure is reproduced
before import,and the candidate changes image presentation rather than legal
logic. The key weakness is exposed geometry;therefore the sample cannot support
an accuracy estimate or acceptance. A candidate failure is a promotion veto,
not a claim against OCR generally. Corrupt inputs,missing streams,incomplete
region accounting,invalid transformation or exhaustion of the explicit limits
are continuation vetoes for this package. No new resolution/model family/default
is selected. API inspection confirms pdfocr_tobytes only exposes compression,
language and tessdata;direct Tesseract/PSM is absent here and remains unevaluated.

Bounds: one new cumulative page-coverage admission4-to5,retaining all four
attempts. At most two supervised native reservations: one batch worker with40
OCR operations,plus one documented diagnostic/trusted retry spare. Historical
reservation lower bound67. Worker60seconds,each stage120seconds,stream64MiB,
new evidence300MiB,one local implementation repair. No network,installation,
external API,model purchase or GPU use. Crops and OCR inputs exclude reference
literals;matching occurs after native output is retained. Use the existing
sealed native snapshot extended only with this helper,raster and crop specs.
Use the already authorized bounded table wrapper with one-second tool yields.

Stages: prepare and crop inspection;worker;compare and actual review consumer;
adverse controls;seal,record,refresh. Commands use
`.venv/bin/python -m scripts.prospectus_rotated_table_ocr segment-<stage>`.
The wrapper delegates these finite stages to scripts/prospectus_table_segments.py.
All input/output/method identities,wall times,full answers and attribution remain
in page-coverage/attempt-005. After a partial result continue an independent
source/meaning task;no automatic third crop variant or repeated exposed tuning.
