# SFC circular translation: feasibility research

Date: 2026-09-21. Scope: public-source research and a reviewable design, not a
production implementation or a determination of the bank's legal obligations.

The question is whether SFC prose can be translated into a source-linked,
reviewable specification that supports deterministic execution and scoped
verification. Inspect representative official circulars, the local MathDevMCP
implementation, primary project documentation, and relevant technical papers.
Preserve inspected papers and circulars under `.localresources/`.

Skeptical plan audit: the supplied page covers product authorisation, which is
not a complete statement of a private bank's obligations. Do not infer the
bank's regulated entity, client classification, or business activities. Inspect
intermediary material where relevant. Treat publication dates, effective dates,
withdrawals and replacements separately. Source snapshots and technically
successful parsing do not establish legal completeness or correct interpretation.
Inspect technical sections of papers before borrowing their design claims.
Reuse MathDevMCP only for capabilities established by local code; its existing
mathematical workflows do not establish legal-rule support. No performance,
accuracy, or superiority comparison is planned. No customer data is needed.

The revised plan passes as bounded feasibility research. A useful result must
include an actual paragraph-level example, a separation of source interpretation
from software verification, a proposed intermediate representation, an account
of missing facts and exceptions, primary-source references, and a practical pilot.
If source access fails, record that limitation and avoid claiming the source was
read. Stop expansion after enough sources establish these design distinctions;
do not attempt an exhaustive circular corpus or library benchmark.

Assumptions: English sources are the initial research scope, not a legal rule
about language precedence. Any operational restriction proposed by the design
must be labelled bank policy rather than attributed to an SFC paragraph. A
sample's applicability must be resolved before it is used on a real transaction.

Planned outputs: `docs/sfc-rule-translator-design.md`, a source manifest and
local source copies. Any sample specification is provisional for human legal
and compliance review. No bank-system writes, production deployment, package
installation, or MathDevMCP modifications are part of this task.

The user additionally requested assessment of DynareMCP's proof/tree-search
work and ResearchAssistant. Inspect their current source and distinguish
historical MCTS-style workflow records from implemented proof checking.
ResearchAssistant's local `parse-pdf` CLI is available and is being used for
the circular annexes and two technical papers. Its outputs require manual
review; inspect material numerical and exception wording against rendered PDFs.
Read-only inspection of the adjacent repositories does not resume their
independent research programs or modify their mission state.

## Result and restart note

Completed the proposed design in `docs/sfc-rule-translator-design.md` and a
non-executable, unapproved paragraph-level example in
`examples/spi-financial-condition.json`. Retrieval references and source hashes
are in `.localresources/source-manifest.json`.

Inspected five circular bodies, both annexes of 23EC35, selected technical
sections of the Catala and British Nationality Act papers, relevant official
project documentation, Catala proof/verification source excerpts, and local
code from the three MCP projects. The SFC indexes retained only their first
100 records each. No comprehensive applicability or completeness assessment was
performed. The old tokenisation circular's explicit replacement notice is a
useful example of why historical sources cannot be treated as current defaults.

ResearchAssistant extraction command used for each of four PDFs:

```text
/home/chakwong/python/ResearchAssistant/scripts/ra-dev --root /home/chakwong/python/legalmath/.localresources/research-assistant parse-pdf --pdf <absolute PDF path>
```

Each extraction reported low confidence and manual review. Material SPI
threshold and FAQ wording was cross-checked on rendered pages. Web-tool calls
failed with upstream HTTP 502; direct public HTTPS retrieval succeeded. Two
additional literature candidates returned HTTP 403 and were not used.

Checks: the example parses as JSON; its PDF digest and two threshold amounts
match the source; all 41 retained source/derived file hashes match the manifest;
all relative links in the design resolve. The design was compiled to a six-page
PDF with Pandoc/XeLaTeX for rendered review. These are document checks, not legal
validation, a proof, a tested translator, or a performance result.

Recommendation: pilot one reviewed decision workflow with a typed rule
specification, source-linked tables, explicit missing information, independent
source-derived examples, and shadow execution. Reuse ResearchAssistant intake,
MathDevMCP formal checks, and DynareMCP investigation/change-management patterns.
Search scores cannot choose an authoritative legal interpretation. Runtime
execution should use fixed approved rules. A bounded work queue is the initial
design; an MCTS implementation would require a demonstrated search bottleneck.

No packages were installed, no adjacent repositories were modified, and no bank
or client data was accessed. Human review of the proposed interpretation and
reviewer interface remains part of a future pilot; it is not claimed here.
