# Competing interpretations: research and reuse audit

22 September 2026. The user asks for deliberate breadth in interpretation
hypotheses, followed by selective tree search, multiple surviving proposals,
scores and explicit uncertainty, drawing on case-law reasoning and DynareMCP.

## Evidence contract and skeptical audit

Question: how can a legal translator generate, preserve and discriminate
semantically different readings instead of prematurely committing to one?
Comparator: the current manually supplied single RuleIR interpretation and the
previous proposed interpretation review workflow. This is a literature/code
inspection and design task, not a live-model experiment or runtime rollout.

Success means a source-supported design with concrete generation operators,
candidate identities, pruning rules, search/stopping rules, argument/evidence
records and a separation between search utility and legal confidence. Inspect
technical sections of retained primary papers and the actual DynareMCP search
implementation before claiming reuse. A concrete SFC illustration must identify
assumptions and distinguish plausible readings from deliberately erroneous
mutants. No empirical performance or source-meaning proof will be inferred.

Audit: ordinary top-k generations can all repeat one reading; an MCTS reward
based on fluency, solver success or majority agreement can reinforce that error.
Unvisited branches are not refuted hypotheses. A precedent's outcome is not
automatically its holding; authority, issue, jurisdiction, date and distinguishing
facts matter. An aggregate numeric score must not override controlling authority
or masquerade as a probability. These are design vetoes, not reasons to abandon
multiple-hypothesis search.

Revisions required before adoption: preserve interpretation families and an
unexplored frontier, expose provenance of assumptions and case classifications,
make evidence-driven defeat revisable, and distinguish resource limits from
exhaustion. No MCTS tuning defaults are adopted from macroeconomics. Begin with
a deterministic diversity-preserving baseline; MCTS requires target-specific
evaluation before any default change. Audit PASS within this research scope.

## Assumption audit and outputs

The 23EC46 example is a development illustration, not a held-out legal test.
Independent compliance adjudication remains unavailable and cannot be invented.
Legal argumentation semantics supply conditional acceptance, not a unique legal
truth. Paper methods are design sources, not already validated dependencies.
DynareMCP inspection is read-only and does not resume its research campaigns.

Expected outputs: `docs/research/interpretation-search.md`, newly inspected papers
in `docs/papers` with the existing filename/manifest convention, and supporting
metadata/text under `.localresources/interpretation-search`. Record retrieval
failures and uninspected leads without promoting them to evidence. Preserve
application code, accepted execution records, and adjacent repositories.

## Research result

Completed the technical research note in `docs/research/interpretation-search.md`.
AGATHA is the closest inspected legal precedent: explicit theory constructors and
heuristic/adversarial search over case-law theories. ASPIC+ and Carneades explain
conditional acceptance, conflicting arguments and explicit assumptions. ToT,
LATS and generalized binary search supply candidate exploration and informative
query mechanisms, subject to the transfer limits documented in the note.

Eight inspected full texts were registered; the library has 47 PDF editions,
46 distinct works and 1,204 pages. ResearchAssistant discovery was used; its
local pdftotext adapter also parsed AGATHA, Carneades and ASPIC+. Publisher failures
for the 2016 statutory-interpretation paper remain a retrieval gap, not evidence
that its method was read. Paper identities, versions and publication metadata were
checked, including the AGATHA year discrepancy and the ASPIC+ correction.

DynareMCP provides reusable hypothesis/evidence/falsifier and frontier patterns.
Its inspected scheduler is priority-based; no general UCT engine was found in the
source/scripts. Inspected ToT/LATS and Carneades sources are algorithm/interface
references only. No external implementation was executed or installed. The note
specifies a deterministic diversity-preserving controller before optional MCTS,
retained undecided/deferred hypotheses, discriminating scenarios and separate
search/argument/probability fields. No numerical reward default was adopted.

Validation: all 47 PDF digests match the manifest; total PDF count/pages agree;
research/library local links were checked and a scheduler link repaired. Existing
execution-integrity checker passes for 119 source files, 36 evidence files,
24 protected originals and 67 original review inputs. Its 154-test count refers
to the preserved previous run, not a new test execution in this research task.
No application code, approved rule, deployment or paid-model run changed.
