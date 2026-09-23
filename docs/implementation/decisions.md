# Design decisions and literature transfers

These decisions choose a prototype; they do not assert that a custom language is
universally better than an established legal language. Revisit a choice only with
the listed discriminating evidence, keeping the reference semantics fixed.

| Decision | Chosen mechanism and reason | Inspected source | Alternative / reopening criterion |
| --- | --- | --- | --- |
| D01: one small interpreter | Acyclic typed expressions with explicit T/F/U and conflict precheck; few dependencies and direct source traces | Catala §§3–5; eFLINT 2025 §§6,8 demonstrate why “same language” does not guarantee same defaults | Catala/L4 as core if an adapter reproduces every conformance case including missing data and versioning with less maintained code |
| D02: explicit exceptions | Nested defaults; multiple active siblings conflict even when values coincide | Catala default calculus; Antoniou et al. §2 has different team-defeat semantics | General defeasible priorities only when an SFC case cannot be represented clearly and the defeat semantics is specified/reviewed |
| D03: separate duties | Consent and one non-preemptive achievement profile; immutable breach assessments | eFLINT 2020 §§3–5; Hashmi et al. Definitions 10–17; Governatori–Rotolo §§2–5 | Stipula/eFLINT/ASP for richer event semantics after required temporal fragment and translation tests are settled |
| D04: no absence-based permission | A passed subcondition is not trade authorization; absence of a prohibition is not positive permission | Input/output logics §3; strong/weak permissions §§2–3 | Introduce explicit permission/prohibition language only with reviewed conflict and closed/open-world policies |
| D05: date policy explicit | Calendar anniversary needs leap policy; business days deferred | Monat et al. §§2–4 | Date library default cannot settle what a circular means; add calendars only with an owned versioned holiday source |
| D06: source identities | Hashes, exact spans, two assessment times, explicit replacement edges | LegalRuleML 2021 §4; Governatori et al. 2016 §3.2 | XML/LegalRuleML export later; no claim that JSON is standards-conformant without validation |
| D07: bounded SMT | Explicit knownness, nonempty declared domain, counterexample replay, honest UNSUPPORTED | ContractCheck §§4–5; ARc algorithm 1; LINC failure analysis | Lean/F* proof layer only for stable semantics worth mechanizing; solver success alone does not prove source fidelity |
| D08: tests before drafting | Fixed boundary cases, independently authored source inventory, operator mutations | CUTECat methodology; Connecting Statutory Reasoning appendices; Jurayj manual program construction | LLM-generated cases can extend but cannot define the sole gold standard |
| D09: immutable amendment | New bundle hash and approval; historic replay preserved | LegalRuleML contexts; Stipula higher-order amendment §§4–6 | No runtime hot-patching of released rules in MVP; explicit migration needed for outstanding obligations |
| D11: Java deployment | Deterministic emitter plus Java 17 support library; Python authors and independently checks | User target requirement; local SPI-Demo1 compiled demonstration; Stipula–KeY is a separate verification-model precedent | Reopen target Java version/integration when the bank provides its actual interface; preserve semantics and compiled conformance |
| D10: local storage/UI | SQLite + content hashes + server-rendered source/rule/case view | Engineering choice for a small public corpus | Postgres/enterprise IAM when multi-user concurrency, bank retention or access control requirements demand them |

## Package disposition

**Direct prototype dependencies:** Python standard library; JSON Schema validator;
Pydantic/FastAPI for transport; SQLite; Poppler/PDF parser; optional Z3. Record
actual versions in W00. These are proposed full-product dependencies. The narrow
Java demo uses the existing JSON Schema installation at build time and a locally
checksummed Temurin JDK 17; its JAR has no third-party runtime dependencies.

**Adapters after the reference slice:** Catala for default-aware computation and
concolic tests; L4 for legal-language authoring, traces and generated decision
services; DMN/Drools for decision-table integration; LegalRuleML for interchange.
An adapter must explicitly reject unsupported semantics. DMN Unique, Any and First
hit policies are different; exporting an exception conflict as First changes meaning.

**Design references or optional comparisons:** Stipula/KeY for stateful contracts,
reachability and verification; eFLINT/Clingo for normative positions and scenarios;
s(CASP)/s(LAW) and Logical English for explanations and nonmonotonic logic;
OpenFisca for parameterized calculation and dated legislation; OPA for operational
policy distribution; Cicero/Concerto/Ergo for executable contract templates;
Blawx for visual defeasible rules; SPINdle/Regorous for defeasible process reasoning.
Do not infer that every paper's research tool is maintained, supported, or available
under a bank-compatible license. Original source/documentation inspections and
retrieval limits are recorded in the literature notes.

## Existing local projects: precise boundaries

Repository snapshots inspected during the source study:
MathDevMCP `655a9ef` prefix; DynareMCP `4bac9` prefix; ResearchAssistant `9c0008f`
prefix. Resolve full commit IDs again when implementing; adjacent repos may change.
No adjacent repository was modified or tested as part of the proposal.

MathDevMCP's `high_level_workflows.py` distinguishes structural and proof evidence;
`lean_check.py` checks named targets and rejects admitted proofs;
`derivation_branch_controller.py` explicitly describes a non-MCTS controller;
`resumable_tree.py` supplies resumable hashed search states. Borrow exact-target
evidence and resumability. A legal sentence is not automatically a Lean theorem.
The adapter packet must contain RuleIR hash, typed encoding, theorem, assumptions,
proof text, toolchain version and checker output. A certificate listing files or
dependencies is not a proof of that theorem.

DynareMCP's `decision_kernel.py`, `audit/source_graph.py`, `audit/ir_diff.py` and
`audit/mathdev_sidecar.py` offer structural decision records, source tracking,
change analysis and sidecar separation. Its economic-model semantics do not apply
to regulations. The historical `overnight_ucb100_2026_05_19` study is evidence of
UCB-guided investigation, not a legal proof search result. Use a frontier of
candidate interpretations, unresolved obligations and discriminating cases;
reward verified progress/reviewer information under a fixed budget. Search score
never approves a rule and repeated model agreement is not independent evidence.

ResearchAssistant's `scripts/ra-dev` exposes discovery, paper downloads, citation
queries and PDF parsing. It was used for discovery here; metadata-provider failures
and direct-download fallbacks are retained. W09 invokes its CLI with an explicit
project-local root, source hash and output path. Validate the subprocess's JSON
and preserve extracted text alongside the original PDF. Parsing confidence is a
triage signal; a source page check resolves a disputed symbol or qualifier.

## Initial assumptions to monitor

The finite expression fragment, exact cents, no FX arithmetic, conservative
conflict closure, two reviewer roles, synthetic local identity, resource budgets,
30-task evaluation size and twelve-week schedule are proposed choices. Their
provenance and failure modes are explicit in the semantics/backlog. They become
bank defaults only after the relevant owner reviews them. A cheap early test is
the W03 financial-condition walkthrough: if reviewers cannot resolve the input
definitions, improve the evidence model before expanding automatic translation.
