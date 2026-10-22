# BES p89 reviewed-region product consumer, 12 October 2026

The one-page diagnostic reproduced the exact English worker output. All four
PyMuPDF text/word sort views retained six of seven page checks and failed the
negative-assurance phrase. A supplied body corridor ending at 90% of page
width recovered seven of seven while retaining 15 sidebar words separately.
This identifies an ordering/region problem rather than failed recognition of
the body phrase. It does not justify a global 90% cropping rule.

Code trace: `admissions.structure` already calls
`layout_adapter.project_layout`, which binds region text to original word
offsets and preserves raw characters. `service.source_product` can consume
this reviewed layout packet. This capability was not used for the newly
recovered report page. Use it now with two explicit, image-reviewed regions,
body and sidebar, without changing source code or automatic defaults.
The schema field named `docling` is a supplied layout representation here;
do not claim the Docling model generated the regions or that its model ran.

Primary criterion: the actual product consumes both source-bound p89 regions
with zero rejected regions, the body projection matches all seven frozen page
spans, and every nonspace raw character belonging to a retained page-89 word
maps exactly once across the two regions. Native and OCR occurrences both stay
retained. Exact all-page raw units must equal the same-source no-layout product.
The raw source stream must still show the prior six-of-seven result so this
cannot be mistaken for modifying OCR. Region labels carry no legal scope.

Negative controls: a widened body region crossing the sidebar must fail its
unchanged exact candidate text; altered candidate characters must be reported
as rejected; overlapping body regions must lose admission for ambiguous source
ownership; a stale graph hash must be rejected by the real service. Merely
sealing a product is insufficient: `project_layout` retains failures, so
explicitly require no failures and the expected complete character partition.
All source/image/model/method drift and missing mapping are continuation vetoes.
Count/runtime are explanatory. Legal source completeness, automatic region
detection, general reading order, independent review and package superiority
are not concluded.

Default audit: 90% comes from this inspected image and is a SUPPLIED_REVIEW
geometry hypothesis, not a learned or general default. Same English model,
300 dpi, original PDF, selected pages and CPU runtime are comparator settings.
All word offsets and native units come from the product's actual source graph.
Independent page text spans come from the frozen image-reviewed oracle, so a
candidate derived from source words cannot pass solely by mirroring itself.
The mutation and overlap controls test the adapter's actual failure semantics.
Skeptical audit verdict: PASS for one bounded usage repair.

Run `timeout 180 .venv/bin/python
docs/implementation/prospectus-integration-closure/bes-original-acquisition/integrate_p89_regions.py`
from the prospectus worktree, deliberately hiding GPU devices before imports.
Retain request, raw and layout product hashes, complete region/character maps,
critical-span checks, all negative controls, original/image/model bindings,
commit and dirty method hashes, exact command/environment, elapsed time and
manifest in `reading-order/consumer-001/`. The actual P1 result is a supplied
source projection; no corrected eleven-document legal-answer request is
replaced. A later source-specific annotation/scoping phase may consume it under
its own reviewed contract, preserving uncertainty and independent acceptance.
