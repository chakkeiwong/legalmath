# Actual OCR on the missing rotated cohort tables

Baseline: authority86,page-coverage003 reports four visible required tables on
the278-page Adriano/Hypo original's PDF page84 as unavailable. Native Poppler
retains only three characters on that page. The source,original rotation90,
120dpi image and four region boxes are retained. Image inspection confirms
four cohort tables: two Time to Default and two Prepayment Rates tables with
year rows2000–2008,quarter columns and grey unfilled trailing regions.

Question: does the existing explicitly selected-page CPU OCR route add usable
source-bound words in all four required regions through actual P1–P5 consumers,
and what specific cell/number/label errors remain? The comparator is the exact
page-coverage003 native-only products and full answer. Keep every native unit
and add an explicit OCR layer using the existing hybrid.v2 profile; never infer
that text presence establishes whole-table or whole-page coverage.

Primary engineering criterion: execute the actual hybrid source and downstream
consumer,retain exact original/page/image/model/runtime identities and every
word,account for all four required regions,compare full native-only/hybrid
answers and preserve unknown legal results. A positive extraction is useful
only if source-bound labels/numbers can be inspected; missing or wrong cells
remain gaps. The region diagnostic should report unreviewed retained words
rather than matched transcription when no complete reading exists.

Use a separately retained300dpi rendering from the same original page,verify
its hash against the OCR worker raster and visually inspect representative
top/bottom/edge regions. Before reading OCR output, freeze a small visible
literal control set from that image: table titles,year/quarter headers,and
clearly legible percentage cells,including a printed zero. Grey unfilled
positions have no numeric reference and must not become zero by default.
The exposed control set is a diagnostic sample,not a complete independent
cell transcription or an accuracy estimate. Preserve each observed mismatch
with its original image/position and OCR words; do not silently correct OCR.

Assumptions and defaults: existing300dpi English model is the product baseline,
not a newly tuned optimum. Rotation comes from original PDF metadata; do not
rotate synthetically. Hybrid.v2 is chosen to preserve text but withhold invalid
boxes rather than discard an entire page; any invalid geometry remains visible.
The four boxes are the retained image-review regions,not automatic table
detection. A high word count and matched sample do not certify table structure.

Skeptical audit: PASS for a finite real-product diagnostic. The actual blocker
is native-only missing table content,so invoking the existing OCR route is a
direct test of the missing capability rather than another control-plane detour.
Changing to a learned table model or tuning resolution requires a later reviewed
comparison; this package does not claim a package limitation from one baseline.

Bounds: page-coverage cumulative admission3-to4 retains all prior attempts.
At most four supervised native reservations,three planned: one native text
extraction,one selected-page OCR and one render-only command. A fourth may
only serve a documented sandbox prerequisite/trusted retry or discriminating
diagnostic; no automatic retries. Historical visible reservation lower bound64.
Use existing native-binding008 sealed runtime plus original source and render
helper,existing pinned English model and Python3.11. Run trusted when necessary
because prior evidence showed the outer sandbox blocks Bubblewrap namespace
creation. This does not grant permissions; request the exact wrapper prefix
through the tool if required. No network,install,model/API or GPU calls.

Each stage has120seconds,each native call60seconds,64MiB stream cap,total
350MiB new evidence. Use one-second yields and retained sessions. Stages:
prepare,render,source,construct,diagnose,compare. Render and source may be
separate tool calls;freeze image controls between render and source. At most
one preserved local implementation repair. Corrupt source/image,missing native
streams,exceeded bounds or a second failure ends this package and triggers
independent work. OCR errors veto promotion but motivate later targeted repair.

Retain all inputs,images,worker output,P1–P5,full answers,region reports,actual
controls,run manifest and decision table in page-coverage/attempt-004. Seal,
record,refresh. Distinguish our integration/usage failure,poor OCR on this case,
missing reference reading and proven package limitations. Only the first three
can normally be resolved by this bounded baseline run.
