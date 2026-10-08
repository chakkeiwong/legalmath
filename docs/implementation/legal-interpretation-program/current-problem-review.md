# Reassessing the legal interpretation problem

6 October 2026. This review responds to the concern that the program keeps
appending phases without settling the product problem. It examines the completed
S4 evidence, all 35 retained statements and distinctions, all 46 obligations and
their requested evidence, the three existing formulas, and the source-to-rule,
standards, observation and integration code. It is an initial problem review;
it is not a new literature survey or a fresh adjudication of the source law.

**The concern is justified.** The engineering work is real, but it has not
established a solution to the interpretation question that motivated it. The
program's next-step mechanism reliably records another implementation phase.
It does not require evidence that the next capability is what prevents an
answer to the original question. S4's runtime proof is useful and valid within
its stated scope. Its success does not establish that recursive inference was
the limiting factor in any of the 46 legal obligations.

## What the product is actually doing

The original paragraph 10 readings ask whether a Product Provider has retained
responsibility or fulfilled a substantive responsibility requirement throughout
an assessment period. The S2 rule named p10-responsibility asks a different
question: whether the specified scope carries a proposed responsibility duty.
Its consequence is “Retain ultimate responsibility …”, not “This provider has
satisfied that responsibility”.

That rule requires an applicability premise, a Product Provider premise and an
expressly assumed source-to-rule interpretation. S3 transports those premises;
S4 proves the consequences of their numeric encoding. The implication is useful,
but the rule deliberately does not select a discharge test. See
[s2_data.py](../../../scripts/legal_interpretation_s2_data.py),
especially inventory/add and p10-responsibility;
[standards.py](../../../src/legalmath/interpretation/semantics/standards.py);
and the
[S4 result note](../../../artifacts/legal-interpretation-program/successor-s4/attempt-1/result-note.md).

There are at least four distinct questions:

| Question | What would answer it | Current position |
|---|---|---|
| Which requirement applies to this actor, product and period? | Applicable sources, capacities, dates, conditions and justified interpretation | Conditional duty rules exist; key premises remain supplied. |
| What does the requirement demand? | A defensible interpretation of retention, conduct, outcome, object, standard and exceptions | Competing proposals remain. |
| Has this actor fulfilled that requirement? | The chosen or conditional standard plus relevant evidence across the assessment scope | No established full discharge test or actual arrangement evidence. |
| What legal consequence follows? | A separate rule connecting the finding to a consequence under applicable law | Neither Boolean satisfaction nor SHOULD supplies this by itself. |

The next program must retain these questions separately. Passing an earlier row
cannot silently answer a later one.

## The counts do not describe independent problems

The 35 reading identities have four existing comparison categories: 13 allocation,
eight allocation-and-conduct, three allocation-and-adequacy and 11 unresolved-
discharge. These groupings organize investigation; they do not prove the readings
equivalent. Differences in actors, time, exceptions and the three responsibility
subjects must survive any comparison.

The original obligation register has 14 time, 14 definition, 14 authority and
four output questions. Its role responses directly reference 14 original reading
identities. Another 21 alternative readings are retained in the larger inventory.
This does not show the alternatives were lost. It shows that “46 obligations”
cannot, by itself, be treated as a coverage guarantee for all 35 readings.

There are 224 missing-premise entries, containing 222 distinct verbatim strings.
Many describe related legal and factual questions in different words. A string
count is neither a count of independent problems nor proof that two requests can
be merged. Each request also needs challenge: an earlier agent asking for
“necessary and sufficient criteria” does not establish that law supplies an
exhaustive Boolean test.

Only three readings have formulas. All 13 fact declarations across those three
formulas carry requires_judgment=true, including scope and responsibility facts.
Names such as responsibility_retained, arrangement_sound and
ownership_records_proper encode the very judgments still in dispute. The formulas
compute conditional relationships among judgments; they do not independently
make those judgments. Expanding Boolean support cannot resolve their meaning.

The accompanying
[problem inventory](follow-up/problem-inventory.json)
preserves every original identity and hash and adds provisional research links.
It neither alters the originals nor closes any obligation. A keyword-based scan
was considered as a navigation aid and discarded as a classification method:
“treatment”, for example, often concerns remediation rather than case treatment.

## What remains uncertain, and what kind of work it calls for

| Problem | Present evidence | Work that could change the answer |
|---|---|---|
| Paragraph 10 retention, conduct and outcome | Rival statements are preserved; current rule establishes only a conditional duty | Compare the precise interpretive arguments and the situations in which they differ; trace every normative assumption. |
| Paragraph 14 / footnote 5 | The retained passages differ in request wording, objects and standards; A/B/C remain proposals | Compare attachment, object and standard independently; establish what extra premise would select or relate them. |
| Applicability, capacity, date and modality | Source versions are retained; actual conditions and assessment scope remain unresolved | Build the specific applicability chain, separating source availability from application to a product. |
| Evidence to legal evaluation | Narrow recorded events can be computed; adequate supervision and proper records still need a criterion | Trace one observable fact to each evaluative proposition; expose every missing sufficiency rule. |
| Time, ownership and incidents | Provider succession, legal title, finality and remediation require further rules and facts | Distinguish the missing temporal or property rule from the missing chronology or transaction evidence. |
| Case authority | Earlier work retained Gatecoin reasons and role distinctions, with transfer limits | Check a particular source proposition and material-fact relationship before using it for a target inference. |
| Execution | Conditional Boolean and positive Horn execution have bounded checks and proofs | Reuse them; extend only for a reproduced representation or execution failure relevant to a selected question. |

A missing contract, appointment date or incident history is not an English-parser
bug. A missing legal standard is not fixed by inventing a threshold. A disputed
attachment is not fixed by adding an authoritative-looking proof to one supplied
reading. An unsupported language construct is a coding problem only after we
state what semantics we want that construct to have.

The retained Gatecoin source findings describe exchange-insolvency questions,
customer terms, consent and trust relationships. They do not establish the SFC
paragraph 10 discharge standard. This review inspected those retained findings
and the local use of them, not the full judgments anew; fresh substantive case
inferences require the full-reasons check stated in the follow-up program.
Likewise, the earlier literature dossier is a useful index, not fresh evidence
that a particular method will solve this problem.

## A concrete question to organize the follow-up

Use the disputed outsourced-registrar example already present in the readings.
Suppose, conditionally, that the provider retains effective powers, exercises
competent supervision, experiences a material records defect, and remedies it
promptly. Under an allocation proposal, a conduct proposal and an outcome
proposal, which conclusion follows about paragraph 10 itself? Which part of
each answer depends on the source interpretation, which on a standard, and which
on evidence about the arrangement?

These are assumptions for distinguishing proposals. They are not labeled client
facts or a legal answer key. In particular, “competent” and “material” must be
expanded or left as explicit judgments; otherwise the example repeats the
opaque-predicate problem.

This question reaches the central distinction across the retained inventory.
The paragraph 14/footnote 5 and case-transfer questions provide bounded companion
checks of different mechanisms. Their inclusion prevents the whole program from
becoming a hard-coded solution to one paragraph. None is an unseen-source test.

## What a useful stopping point looks like

The product goal remains justified interpretation with explicit qualification
where needed. We do not replace that goal with permanent abstention. For a
specific question, the product should compute every supported conditional
consequence, show where plausible readings differ, identify source and evidence
dependencies, and state exactly why a stronger answer is unavailable.

A bounded investigation can finish with an irreducible disagreement or an
identified external input. That is different from declaring English correctness
solved. The follow-up must also be able to conclude that an interpretation
mechanism is inadequate, that an acquired source cannot discriminate the rivals,
or that a proposed feature would not help. Those conclusions end a work item;
they should not automatically generate another implementation phase.

S4 remains the verified engineering baseline. Its selected master and result
bytes are preserved. The
[follow-up program](../../plans/legal-interpretation-problem-led-follow-up.md)
defines a finite diagnosis, one selected intervention and an explicit decision
about subsequent scope.
