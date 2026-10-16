# Existing methods for bounded legal context

This is a source/code review answering which established methods and software
can implement overlapping reading and bridges between pieces. It supplements
the capacity resolution design; it does not authorize production changes,
package installation, a new repair attempt or model calls.

Pre-review contract: compare overlapping chunking, parent/window retrieval,
hierarchical map/reduce and graph retrieval against the existing product's
repeated common context. Inspect official method documentation and implementation
where available. For papers materially informing the recommendation, retain
local copies and inspect method, evaluation and relevant appendices. Separate
documented software behavior, paper findings and untested suitability for our
four questions, 46 obligations and 35 readings. No generic benchmark or retrieval
receipt establishes exhaustive legal support or a current product repair.

Skeptical audit: PASS for read-only review. The current mission admits bounded
offline product evaluation with zero model calls and zero repair attempts.
OpenAI's public documentation currently returns HTTP 403 even in trusted
execution; no inaccessible page will be described as inspected. Other sources
can be reviewed independently. The design question concerns an established
engineering method, not proof that arbitrary chunking preserves all reasoning.
Any library recommendation remains a candidate pending target-specific tests.

## Findings

Long-document processing under a bounded model context is an established
engineering problem. Overlapping chunks, restoration of surrounding or parent
context, hierarchical aggregation, and retrieval across related passages all
have existing implementations. The product should use these as concrete
baselines. Repeatedly compressing the same global payload is an incomplete
response to the problem diagnosed in the preceding capacity assessment.

The user's windows 0–50, 25–75 and 50–100 provide complete positional coverage.
They do not put a rule at position 10 and an exception at position 90 into the
same request. That connection requires a later comparison using both passages.
The standard architecture is therefore chunking plus retrieval or aggregation;
overlap alone is only one part. Covering every input position also does not
prove that a model recognized every legally consequential relationship.

| Method | Inspected implementation | What it supplies | What remains for this product |
| --- | --- | --- | --- |
| Overlapping chunks and retrieval | OpenAI Python SDK declarations for vector stores and Responses File Search | Configurable chunk size/overlap; search filters, result counts and ranking, including semantic/keyword fusion configuration | Exhaustive source review, distant dependencies and legal interpretation are not guaranteed by relevant-hit retrieval |
| Sentence-window retrieval | LlamaIndex `SentenceWindowNodeParser` plus `MetadataReplacementPostProcessor` | Retrieve a sentence, then supply its surrounding sentences to the model | Use the replacement step; merely storing window metadata does not deliver it. Distant exceptions require further retrieval |
| Parent retrieval | LangChain `ParentDocumentRetriever`; LlamaIndex `AutoMergingRetriever` | Search small pieces and restore their larger parent context; LlamaIndex can also fill an intervening node | Bound expanded parents, preserve source IDs and explicitly locate remote relationships |
| Hierarchical map/reduce | LlamaIndex `TreeSummarize` | Repack to prompt capacity, process batches and recursively combine results; supports structured outputs | Supply every mandatory piece and retain failed or unresolved pieces. Generic summaries do not preserve every legal distinction |
| Thematic hierarchical retrieval | RAPTOR paper and author implementation | Cluster related chunks, summarize clusters recursively, retrieve leaves and/or higher-level summaries | Qualify legal recall and retrieve original supporting passages; summaries can introduce errors |
| Graph retrieval and global synthesis | Microsoft GraphRAG paper and implementation | Extract entities/relationships, construct community summaries and combine partial answers | Qualify graph extraction, legal relationships, indexing cost and evidence loss; global synthesis filters/ranks information |

The inspected OpenAI SDK explicitly documents a default maximum chunk size of
800 tokens and 400 tokens of overlap. The ratio matches the user's proposal.
The same declaration requires overlap not to exceed half the chunk size. This
is a verified statement about the SDK's documented API parameters, not a live
service test or a recommendation that 800/400 is optimal for these legal sources.
Tokens and the product's existing byte limit are different measures; both need
accounting, including prompt, schema and output reservations.

The File Search declaration describes searching uploaded files through vector
store IDs and exposes filters, ranking controls and up to 50 returned results.
It is an existing managed retrieval option. The current product's `CodexProvider`
uses a fresh tools-disabled route: enabling this API facility requires an actual
provider integration and cannot be accomplished by changing a chunk-size field
on the current wrapper. No named LlamaIndex, LangChain, RAPTOR or GraphRAG
integration was found in the inspected product source, tools register and
dependency declaration. This is not a claim about all packages installed on the
machine.

## Literature and implementation limits

Sarthi et al., *RAPTOR: Recursive Abstractive Processing for Tree-Organized
Retrieval* (ICLR 2024; retained arXiv v1), describe recursive embedding,
clustering and summarization in section 3. Related passages can join the same
cluster without being adjacent in the original document. The author code retains
child IDs and implements both layer-wise and collapsed-tree retrieval with
token bounds. Section 4 evaluates NarrativeQA, QASPER and QuALITY. Appendix E
reports hallucinations in 6 of 150 inspected summaries, with no discernible
effect on the authors' reported QA results. That finding is no assurance about
retaining a legal exception. Appendices B–F and I were inspected for clustering,
retrieval, summarization and layer effects. No target-specific ranking follows.

Edge et al., *From Local to Global: A GraphRAG Approach to Query-Focused
Summarization* (retained arXiv v2, February 2025), describe chunk-level extraction,
graph communities and global map/reduce in section 3. Sections 4–6 evaluate
global questions over podcast and news corpora using model-judged measures,
including comprehensiveness and diversity. Appendix G supplies their statistical
comparison procedure. Section 6.1 explicitly identifies domain generalization
and fabrication-rate comparison as further work. These are different targets
from source-faithful legal interpretation.

The inspected GraphRAG global reducer discards zero-scored points and admits
ranked points until its token budget is reached. Invalid map results can produce
empty/zero-scored output. Those are real software behaviors requiring explicit
missing-coverage reporting in an exhaustive legal review. GraphRAG is a useful
candidate for distant relationships; its name does not establish complete
coverage. The paper also evaluates a source-text map/reduce comparator, so a
graph is not a prerequisite for testing hierarchical synthesis.

The LangChain code inspected is the tagged 0.3.27 implementation, not a verified
current import path. LlamaIndex and OpenAI files were fetched from their public
main branches; RAPTOR files from the author's master branch. GraphRAG source
was pinned to commit `5faaaf4f5685fa2056fa8c3bf9342cb089f2942f`. All inspected
files and both papers are retained under
`.localresources/legal-context-methods-2026-10-12/`; `source-manifest.json`
records exact URLs, SHA-256 hashes, sizes, paper versions and inspection scope.
The OpenAI guide endpoints returned HTTP 403 even on trusted retries; the
inaccessible guides are not the basis for the API claims above.

## Recommended product design

Use LlamaIndex's window/parent expansion and hierarchical processing as the
first implementation candidate. LangChain parent retrieval is an alternative,
not an additional prerequisite. The choice is based on the inspected component
fit, not a measured superiority claim. Keep OpenAI File Search as an optional
managed retrieval alternative; evaluate RAPTOR or GraphRAG if the simpler
method misses consequential distant relationships.

1. Preserve original documents with stable document, paragraph and span IDs.
   Split at meaningful legal boundaries under a tokenizer-aware budget, with
   overlap. Treat the overlap width as a hypothesis and test boundary cases.
2. Read every mandatory source piece in bounded requests. Record structured
   rules, conditions, exceptions, definitions, authorities, quotations and open
   references against their source IDs. Retain a separate record of coverage
   and failures; a retrieved top-k subset cannot stand for this full pass.
3. Use retrieval and parent/window expansion to obtain the original passages
   needed for each question. Explicitly resolve references and seek contrary
   authority or exceptions, including nonadjacent passages.
4. Review connected findings together in bounded batches and combine their
   results hierarchically. Keep required obligations outside lossy summaries,
   and report unresolved links. Independent source pieces can proceed despite
   another piece failing; final affected conclusions depend on that failure.
5. Validate consequential conclusions against their original supporting and
   contrary passages. Keep all four questions, 46 obligations and 35 readings
   individually visible. Avoid reconstructing the entire raw dossier in a
   final request: that would recreate the current failure.

This changes how evidence reaches the model while preserving the source store.
It cannot promise unlimited exact reasoning through arbitrary compression.
The generic machinery exists; source-faithful legal extraction, dependency
selection and answer evaluation remain our integration responsibility.

Before promotion, compare against the retained current route and ordinary
overlapping retrieval on the same sources and questions. For cases that fit,
include a full-source comparator. Predeclare checks for boundary-crossing rules,
remote exceptions and definitions, conflicting authority, quotation/locator
fidelity, unresolved facts and complete obligation handling. Measure every
stage's real prompt/output size and call cost. A fitting prompt or successful
summary is an engineering screen; the primary criterion is preservation of the
source-supported answer under reviewed legal cases, with no consequential
omission or unsupported conclusion. Missing source coverage, fabricated support
or changed legal conclusions veto promotion. Finite test success does not prove
all English interpretation problems solved.

## Review disposition

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Source review complete; established components are suitable implementation candidates | Mechanisms confirmed in retained source and relevant paper sections | No source-review invalidity; OpenAI guide access unavailable and SDK/runtime distinction explicit | Actual legal recall, source fidelity, full-route capacity and cost remain untested | Design one bounded integration comparison using window/parent retrieval plus full structured reading and hierarchical combination | No repair executed, no legal closure, no package efficacy ranking and no fully evaluated tool |

Post-review audit: the strongest alternative explanation is that the dominant
failure remains extraction or legal reasoning rather than request capacity.
Passing capacity checks would not settle that explanation; the matched answer
tests must discriminate it. A simpler full-context route, if actually qualified,
could also make hierarchy unnecessary for some inputs. The weakest evidence is
target suitability: this review inspected methods and code but ran no legal
evaluation. No default overlap, merge threshold, summary prompt or graph
configuration is promoted from a library example.

No model calls, installations, production changes or new repair reservations
occurred. Detour 17 stays settled; 41/400 historical calls and the expired
deadline remain unchanged. All original legal questions remain open, the 224
premise records / 407 subparts remain retained, and zero of six selected tools
is fully evaluated on the original answers. This result supplements the capacity
design without changing sealed predecessors or creating execution authority.
