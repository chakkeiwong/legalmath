# Monograph review and rewrite program

23 September 2026. User-authorised scope: A(1–8), critical review of this
program (B), execution (C), and an evidence-based completion review (D).

## Purpose and protected baseline

Revise `docs/monograph/monograph.tex` and its included chapters so a compliance,
legal, operations or engineering reader without prior formal-methods knowledge
can follow the complete argument. The reader must distinguish an interpretation
of a regulatory requirement, a formal specification, the program implementing
it, and authority to use that program in a bank. The product concerns Hong Kong
private banking and the SFC/HKMA sources already used by the book. This scope is
inferred from the manuscript; no wider jurisdictional completeness is assumed.

The baseline is the current 232-page unified manuscript, not either of the
earlier 66- or 153-page documents. Freeze all TeX, bibliography, PDF, prior
preservation records and relevant policies under
`.localresources/monograph-revision/baseline`, with SHA-256 identities and the
git commit. Preserve all concepts, mathematical assumptions, derivations,
examples, citations, uncertainty statements and findings. Page count is only a
truncation alarm. Maintain the typography and at least the baseline page count
unless the user approves a justified exception. Do not remove substantial
duplication without first informing the user and receiving direction. Retain
potentially duplicative passages while review proceeds.

## Evidence contract and skeptical pre-execution review

The question is whether the revised book meets each of the eight requested
standards, and what its evidence supports about legal use of the product.
The comparator is the hash-bound current manuscript and actual repository code,
not an idealised future product. Primary criteria are the eight rows below;
none may be substituted by build success, page count, citation count, test
count, a model opinion, or a MathDevMCP report labelled successful.

The initial plan audit found four material risks and revised the program before
execution: (1) 232 pages already contain examples and six figures, so the task
is to repair sparse teaching support, not assume none exists; (2) the existing
paper library does not by itself archive all regulatory, software and local
citations; (3) preserving equations does not verify their truth; (4) the product
has executed and proposed components that must be assessed separately. This
program therefore inventories occurrences, retains source quotations, invokes
MathDevMCP on the actual expanded mathematical text, and checks implementation
claims against code. No paid experiments, live model study, deployment, or
communication to third parties is authorised or required by this program.

| Diagnostic | Role and consequence |
|---|---|
| Missing concept, lost qualifier, unapproved substantial deletion | Acceptance veto; repair against baseline |
| Missing source or unchecked claim | Citation acceptance veto; continue other work, record affected claim |
| MathDevMCP unavailable or unresolved finding | Mathematics acceptance veto; diagnose tool access and continue independent work |
| Incorrect legal scope, stale law, untested implementation claim | Legal-use acceptance veto; correct text and identify required evidence |
| Hash mismatch/corrupted baseline | Continuation veto for dependent edits until repaired |
| LaTeX errors, clipping, unresolved citations | Delivery veto; repair and rebuild |
| Page and figure counts, prose pattern matches | Explanatory diagnostics; never proof of readability |
| Missing independent human reading/legal approval | Final acceptance remains pending; does not stop authorised provisional drafting |

Default audit: unchanged A4/12-point typography is the existing baseline;
two-page diagram intervals interpret the user's explicit request; major
concepts are inventoried from actual sections/equations rather than inferred
from chapter count; corporate authors use their organisation name in the
requested filename convention. These are implementation choices, not empirical
claims about learning or safety. Detect misleading choices early by inspecting
rendered pages, long figure-free intervals, source title pages, and representative
claim occurrences. All numerical examples added for teaching must be labelled
synthetic and checked arithmetically.

## Work sequence and acceptance criteria

1. **Preservation.** Freeze and inventory the whole manuscript. Build a literal
   chapter/section/subsection/equation hierarchy, citation occurrences, labels,
   examples and figures. Read in chapter order; record actual confusion and
   duplicate candidates. Map revisions to baseline units. Check all removed or
   changed substantive material, rather than relying on token overlap.
2. **Literature.** Inspect existing reading notes and primary technical text;
   examine foundational alternatives, related work, corrections, recent citing
   work and important omissions. Preserve source-support, metadata, backward
   and forward search, claim-support and omission records. Unavailable citation
   metrics are `not available`, never zero. Identify coverage limits explicitly.
3. **Product design.** Compare described requirements with implemented schemas,
   runtime, tests and release controls. Record concrete gaps, affected banking
   decisions, severity, repair and a testable acceptance condition. Add the
   resulting substantive analysis to the book.
4. **Legal robustness.** Examine authority, scope, source version, interpretation,
   missing/conflicting evidence, dates, calculation, review identity, release,
   data provenance, access, confidentiality, incident response and rollback.
   Verify current public legal sources with their issuing bodies. Distinguish
   design evidence, executed tests and legally authorised production use.
5. **Citations.** For every cited document retain an inspectable local copy
   under `docs/papers` using `Title_FirstAuthorSurname(year).extension`; corporate
   and local sources use their corporate author. Preserve existing filenames
   as needed for compatibility. Bind a manifest to hashes and source URLs.
   For every citation occurrence retain the manuscript claim, inspected source
   page/section, a short exact quotation, its location, the support judgment,
   and any limitation or correction. Do not manufacture evidence of reading.
   Keep quotation lengths bounded; full documents are locally retained for audit.
6. **Mathematics.** Run MathDevMCP capability diagnostics, then document audits
   covering all displayed mathematics and an inventory of mathematical claims
   made in prose. Retain exact requests, tool version, reports and backend
   results. Classify each finding and resolve concrete errors in the manuscript.
   Supplement symbolic checks with derivations/counterexamples where the tool
   abstains. Never report a parser or CAS pass as complete mathematical proof.
7. **Prose.** Apply the three policies in `~/python/claudecodex/policies` and the
   scholarly writing skills. Teach in the field's language, introduce notation
   before use, retain qualifications and keep execution bookkeeping in sidecars.
   Record chapter regression, cumulative reading after chapters 2/4/6/8/10,
   and final document review. Human acceptance remains explicitly pending until
   supplied by a real target reader.
8. **Diagrams and examples.** Add native TikZ diagrams that explain decisions,
   dependencies, timelines, counterexamples and uncertainty at the point of
   use. Each major concept needs a concrete example. Measure the rendered body
   (excluding title/contents/bibliography) for figure-free runs: target at least
   one substantive diagram in each two consecutive body pages, with any
   exception individually reported, not hidden by an overall average. Retain a
   concept-to-example-to-figure map; decorative repetition does not satisfy it.

## Review, commands, and retained results

Create a small structure/evidence validator, not an autonomous authoring system.
Its inventory and acceptance report must fail closed on missing evidence and
must not fabricate semantic judgments. Use existing document build/check
commands, ResearchAssistant local extraction when available, MathDevMCP's CLI
from its installed environment, and bounded public-source retrieval. Record
actual commands, environments, tool commits, duration and outputs in
`docs/monograph/review/revision/` and its execution manifest. Use CPU only;
GPU work is unnecessary. Random seeds and benchmark uncertainty are not
applicable to this document audit; illustrative probability calculations are
not stochastic comparisons.

After each chapter, compile or perform the smallest pertinent check, inspect
its rendered pages and repair errors. Finish by building the canonical PDF,
checking preservation and compatibility, binding all final hashes, and writing
an eight-row result table with `met`, `partly met`, or `not met`, exact evidence,
remaining limitations and next action. A blocker in one row does not excuse
unfinished independent work in another. The strongest alternative explanation
for a polished book is that repeated unsupported assumptions merely became
easier to read; the source and implementation audits must test that possibility.

## Review disposition before execution

**Proceed with the staged audit and provisional revision.** The plan preserves
the correct baseline, separates diagnostic counts from acceptance, names stop
conditions, protects existing work, and leaves legal and human acceptance with
the appropriate reviewers. The likely largest workload is claim-level reading
across 76 references and approximately 232 pages; completion may only be claimed
from actual retained evidence, never by filling a checklist with generic text.
