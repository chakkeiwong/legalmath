# Expanded technical reading and software inspection

Read with `reading-notes.md`, which retains the original 24-work analysis and
all seven requested seeds. This file adds the missing foundational and adjacent
mechanisms. Full texts and exact editions are in `manifest.json`. Sections listed
below were inspected for the stated use; this is not a claim that every page of
every appendix was read or that published experiments were reproduced.

## Default and normative logic

**Antoniou, Billington, Governatori and Maher, Representation Results for
Defeasible Logic (2000 preprint; 2001 journal DOI).** Read §2.1–2.3's rule
categories and proof conditions, and the transformation problem stated in §§3–5.
The four tags distinguish definite/defeasible derivation from a demonstrated
failure to derive, not factual truth/falsehood. The positive defeasible rule
requires a supporting strict/defeasible rule, no definite contrary conclusion,
and defeat/inapplicability of each opposing rule. Different supporters may
counter different opponents: team defeat. A defeater blocks support for an
opponent but does not itself establish its head. The paper's transformation
results have modularity/incrementality qualifications; we do not import a generic
incremental-compilation theorem. Transfer: specify the exact exception semantics.
RuleIR nested defaults are intentionally not an implementation of this theory.
Discriminating case: two competing same-valued exceptions conflict in RuleIR;
an arbitrary defeasible or decision-table engine might behave differently.

**Makinson and van der Torre, Input/Output Logics (2000).** Read §§2–4, especially
§3.1's `Cn(G(Cn(A)))` definition, Example 1 and §3.2's SI/AND/WO characterization
with its compactness/induction argument. Normative output is not in general
reflexive and should not inherit unrestricted contraposition. The variants differ
in disjunctive input and reuse. Borrow fact/output separation, not the entire
calculus: opening an obligation does not insert its fulfillment as an observed
fact. No production solver or paper theorem replay is claimed.

**Governatori et al., Computing Strong and Weak Permissions in Defeasible Logic
(2012 preprint).** Read §§2–3 on weak/strong permissions and modal rules; §4's
finite extension and transformation algorithm; §5 Theorems 30–32 with their
size/hash-table assumptions and preservation argument; §6 Definition 33.
Weak permission is explicit negative defeasible provability of an opposite
obligation, not an unrestricted license to treat any absent database row as
permission. Defeaters and explicit permissive rules have different consequences.
The stated linear bound concerns their finite theory representation. Transfer:
OUT_OF_SCOPE, unknown and failure to derive prohibition cannot authorize a trade.
The theory is a design reference; no SPINdle implementation has been installed.

**Governatori and Rotolo, Logic of Violations (2006).** Read §§2–3's reparation
intuition and nonclassical connective, the obligation/violation definitions and
examples in §§4–5, and the paradox discussion's distinction between a violation
and cancellation by exception. The ordered connective is not ordinary Boolean
OR; repair does not mean the primary action was timely. Transfer: immutable
breach plus subsequent performance. Full contrary-to-duty consequence/reparation
reasoning is deferred. The journal PDF says 2006; a migrated index's 2018 date
must not replace its publication year.

## Process compliance and versions

**Hashmi, Governatori and Wynn, Normative Requirements for Regulatory Compliance
(2016).** Read §3's definitions of force, punctual/persistent obligations,
preemptive/non-preemptive achievement, maintenance, compensation and perdurance;
examined the framework-comparison discussion. The `Force` function is an input
to this framework, not a natural-language applicability extractor. Use the
taxonomy to choose an explicit profile and reject unsupported duty kinds.
The extracted display in Definition 14 appears inconsistent with the surrounding
maintenance-obligation prose/diagram; it is not copied as an implemented formula.
This proposal uses only the unambiguous taxonomy and gives its own timing rule.
No runtime monitor from this paper is adopted.

**Governatori et al., Semantic Business Process Regulatory Compliance Checking
Using LegalRuleML (2016).** Read §§3.1–3.3, source-context association examples
for the 2012/2016 telecommunications code, PCL normative labels, process
annotation/trace algorithm, and §4's pilot evaluation/lessons. A context maps
source provisions to rules, allowing unchanged rules across editions while
retaining paragraph correspondence. The algorithm accumulates task effects,
derives/carries duties and checks fulfillment/violation/compensation over traces.
The authors explicitly condition correctness on appropriate interpretation and
complete annotations. Missing a triggering effect can hide a duty entirely.
Their six-week pilot includes about two weeks of manual mapping, 176 normative
statements from about 100 paragraphs plus definitions and process workshops.
These are the authors' reported case-study quantities, not our staffing estimate.
Transfer: clause inventory, dependency closure and versioned mappings are first
class work. No Regorous deployment or benchmark was reproduced.

## eFLINT: distinguish language versions and actual artifacts

**van Binsbergen et al., eFLINT (2020).** Read §§3–5: declarations, actions/events,
duties, scripts, invariants, implementation/actor interfaces and the GDPR example.
Action-compliance and duty-compliance are independent. Observed disabled actions
still cause state changes and violations, enabling ex-post assessment. Type
enumeration differs for finite versus open-ended types. The KYC/data-sharing
example with ABN AMRO and ING uses small selected specifications; it is not a
bank-wide deployment claim. Borrow fact qualification, occurrence versus
permission, and source/evidence/runtime separation. Earlier official Haskell
README was inspected in v1; no environment was installed.

**Esterhuyse, Müller and van Binsbergen, Stable Model Semantics (2025).** Read
§§4–7's state/Core-eFLINT encoding, §6.2 typing, §6.3 normal-form restrictions,
Definition 7 translation, and §8's 108 scenario pairs/43 specifications with
Examples 9–11. Default reasoning deliberately differs from the old interpreter;
no stable model and multiple stable models are meaningful distinct outcomes.
The evaluation is behavioral agreement where intended, not a proof of global
equivalence with the previous implementation. Model-search performance is not
validated for SFC workloads. Transfer: pin semantics; construct negative/default
tests; never select one stable model silently as the legal answer.

Official artifact version 2 (Zenodo 15470286) was downloaded. Inspected README,
`src/Language/EFLINT/Clingo.hs` (state/holds/enabled/action/duty-violation rules),
the test driver and `.same`/`.diff` conventions. The README documents ignored
no-model cases and a cyclic-aggregation compilation bug, plus untested later
agreement articles. These exclusions qualify coverage. The compiler and
benchmarks were **not run**. ResearchAssistant parsed the retained PDF separately;
its JSON is in `.localresources/literature-v2/metadata/eflintstable-ra-parsed.json`.

## Stipula beyond the original paper

**Laneve, Parenti and Sartor, Legal Contracts Amending with Stipula (2023 author
manuscript).** Read §§2–4's lightweight language and higher-order transition,
§5's static/runtime amendment restrictions, and §6's agreement extension.
Amendment changes declarations and memory, with explicit remove/add/run behavior;
an acceptance predicate and constraints can restrict it. Borrow explicit
migration and re-approval questions, not executable hot-patching. No imported
claim about Italian law or UNIDROIT is treated as Hong Kong legal authority.
The 2024 *Programming Contract Amending* chapter is a separate retrieval lead;
the filename and bibliography do not pretend this is that edition.

**Laneve, Liquidity analysis in resource-aware programming (2023 journal;
October 2022 author preprint).** Read Definitions 1–4, the symbolic type/effect
construction, §§4–5's abstraction and two algorithm approaches, Theorem 4's
substitution/overapproximation proof in Appendix B, and the start of Appendix C's
sufficient-condition proof. Resource liquidity concerns escape from permanently
trapped program assets under stated behavior assumptions. Stronger sufficient
criteria and bounded exploration differ in precision and cost. It is not market
liquidity, funding liquidity or an adversarial strategic guarantee. Borrow the
habit of specifying liveness quantifiers and bounds; no liquidity engine in MVP.

**Laneve, The Stipula Platform (2026 indexed chapter; author manuscript 2025).**
Read language/example execution, §§4–5 editor/type inference, §6 unreachability
and §7 liquidity. The unreachable-clause method abstracts logical time, uses
linear traces and falls back to untimed reasoning for cyclic clauses. The
liquidity account assumes cooperative strategyless behavior, bounded exploration
for its more precise analysis and availability of reachable clauses. It says the
liquidity implementation is still under development. Official workbench/source
inspection from v1 remains applicable only to its recorded commit, not automatically
to every later paper feature. Borrow review/explanation patterns and named
property checks. Do not assert all described tools are production-ready.

## Other language and evaluation communities

**Sharifi et al., Symboleo (2020).** Recovered the author preprint from the link
in the official University of Ottawa repository. Read §§II–IV's ontology,
domain/body language, sale-of-goods example, obligation/power statecharts,
temporal predicates and three displayed axioms; checked §VI's future-work scope.
Creation via trigger is distinct from activation via antecedent; powers can
suspend/terminate obligations. The paper reports a preliminary Prolog example
and references 27 axioms, only three present in the PDF; ancillary links remain
anonymized. Borrow lifecycle distinctions, not an uninspected full axiom set.
The old editor README points to a newer combined project. The model-checker
README gives nuXmv commands. Source examples/documentation were inspected, but
no nuXmv run or Symboleo2SC compiler claim was established. The later journal
paper's attempted publisher PDF returned HTML and remains a gap.

**L4 software.** Official `legalese/l4-ide` README, repository tree and
`doc/reference/regulative/DEONTIC.md` inspected. The repository includes Haskell
core/service, an IDE, generated schemas, traces and a regulative type with
actor/action/deadline and success/breach continuations. MUST/MAY/SHANT differ.
These are documentation/source-structure observations, not conformance evidence.
The 2023 *Deontics and Time in Contracts* paper (Watt, Goodenough, Wong;
10.3233/FAIA230954) was identified; IOS/SMU retrieval failed. No paper theorem is
borrowed. It is a priority comparator against the fixed RuleIR tests, not an
unexamined mandatory dependency.

**Guha et al., LegalBench (2023 v1).** Read task taxonomy/design, evaluation
methodology, Appendix B limitations, task/metric descriptions including SARA,
and rule-application evaluation/answer-guide protocol. Legal experts assess
correctness and inference adequacy separately. Classification uses balanced
accuracy; numerical SARA accepts values within 10%, which is inappropriate for
our exact financial boundaries. US/English, long-document and ambiguity limits
prevent transfer of aggregate accuracy. Borrow independent answer guides and
task-specific error categories. No benchmark rerun or model ranking is asserted.

## How these sources change the prototype

The additions settle architectural choices rather than merely expanding the
bibliography. `semantics.md` distinguishes known/unknown/conflict, uses named
defaults, separates duty histories and fixes date policies. `contracts.md`
preserves source versions and two times; `work-packages.md` counts annotation and
review effort. `decisions.md` connects each choice to a source and a case that
could falsify the transfer. No new paper is used to claim automated legal
interpretation or unrestricted verification. Remaining retrievals are explicit
in `coverage.md`, including Lawsky, the L4 paper, later Symboleo and selected
recent Catala-citing works.
