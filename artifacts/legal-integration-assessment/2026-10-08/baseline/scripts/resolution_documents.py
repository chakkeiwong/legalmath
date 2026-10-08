"""Preserve the unified monograph and explain conditional invariant decisions."""
import os
import re
import subprocess
from resolution_support import *


def run(out):
    phases=read(OUT/'phase-results.json')
    get=lambda p:read(ROOT/phases[p]['manifest']['result_path'])
    live,pdf,new,verification=(get(p) for p in ('R3','R4','R5','R6'))
    book=ROOT/'docs/monograph';base=read(DOC/'baseline.json')
    for name,h in base['monograph'].items():
        old=(OUT/'manuscript-baseline'/Path(name).name).read_text();current=(ROOT/name).read_text()
        if name.endswith('/06-ensemble.tex'):
            if current.replace('\n\\input{chapters/06d-invariant-decisions}\n','')!=old:
                raise LegalMathError('E_INTEGRITY',details='Existing ensemble chapter changed')
        elif sha(ROOT/name)!=h:raise LegalMathError('E_INTEGRITY',details=name)
    text=r'''
\section{A decision can agree before its interpretations do}
\label{sec:invariant-decisions}

Consider a suspicious transaction report sent at 02:00 on 2 February 2026.
One retained reading begins the new channel requirement at the start of that
calendar day; another uses the stated operational launch at 09:00. An engineer
cannot erase this difference by calling both dates ``2 February''. At 10:00,
however, the two start conditions agree. That agreement can be useful even
while the interpretation of the earlier interval remains unresolved.
\cite{sfcstr2026}

The relevant question must first be fixed. Whether a submission method requires
an electronic certificate is different from whether a particular certificate
satisfies the requirement. Whether an original filing triggers resubmission is
different from whether a report's entire history contains a triggering filing.
The system records the actor, assessment unit, temporal basis and meaning of
each Boolean result with its source passages. It compares alternatives only
when those descriptions match. Shared names for facts are insufficient: the
definitions, types and units must also match. An independently checked mapping
would be needed to compare different vocabularies.

Let $H$ be the nonempty set of retained readings for that one question. Let $x$
denote the supplied facts, with their evidence and dates. For each reading
$h\in H$, the executable rule returns a Boolean, an out-of-scope result, or an
unresolved result. Write $E_h(x)$ for this result. The decision procedure reports
a known Boolean $b$ only under the following condition:
\begin{equation}
  \begin{split}
    D_H(x)=b \quad\Longleftrightarrow\quad &H\ne\varnothing\ \text{and}\\
    &\forall h\in H:\ h\text{ is executable and }E_h(x)=b,
    \quad b\in\{\mathrm{true},\mathrm{false}\}.
  \end{split}
  \label{eq:retained-unanimity}
\end{equation}
An unencoded reading therefore blocks a known result. An unknown input or a
conflicting fact blocks the result unless the rule itself determines its answer
without that input under the existing three-valued semantics. If every reading
places the transaction outside scope, the response says that explicitly; it
does not turn absence of applicability into a false compliance finding.

The logical guarantee is narrow but exact. Suppose the intended interpretation
$h^*$ belongs to $H$, the shared facts have their stated meanings, and each
evaluator implements its reading correctly. If the procedure returns $b$,
then every member of $H$ returned $b$; substituting $h^*$ yields
$E_{h^*}(x)=b$. The conclusion follows without a probability model or a majority
vote. Its first premise remains a substantive interpretive question. If all
readers overlook the same exception, $H$ can contain only mistaken readings.
Consequently, the returned result identifies its source edition and retained
reading set and states that its agreement is conditional on them.

The 02:00 example illustrates why disagreement is information. With all other
conditions fixed, the two start readings can yield different scope results;
the response carries both outcomes. At 10:00, their timing difference no longer
affects this decision. This does not settle certificate performance, XML-schema
conformity or any other question. Those questions need their own readings and
facts. A source amendment invalidates current assurance; the retained old
edition can still be used for a separately identified historical replay.

\subsection{Preserving the questions a decomposition cannot answer}

Some earlier STR proposals deliberately had no formula. One refused to equate
having an electronic certificate with using it in whatever technical manner
the reporting system requires. Another separated the instruction to arrange
an XML technical test from an unsupported requirement to have passed that
test before filing. These are useful distinctions, not malformed strings.

A new proposal may separate a trigger from performance, or an event from its
report history. The parent remains in the record. Every parent statement,
assumption and question receives an explicit treatment identifying which child
preserves it or why it remains unresolved. A fresh context examines the actual
compiled children's controlled-language meanings against the parent and source.
The child's successful compilation supplies no reason to remove a still
unencoded parent from the relevant interpretation set.

Report history exposes a consequential asymmetry. One evidenced triggering
event establishes that a trigger exists, even when the rest of the history is
incomplete. Finding no trigger in a partial history does not establish absence.
The implementation therefore needs an explicit history-completeness fact.
Similarly, a timestamp adapter requires an explicit timezone. Under the stated
Hong Kong local-time assumption it preserves the blackout interval, the
calendar-day start and the 09:00 operational start as separate facts. Neither
adapter invents a deadline for resubmission.

The public JFIU materials and the cited gifts FAQ are acquired as distinct
authorities. Retrieval helps only to the extent that an inspected passage
answers the question. The FAQ's discussion of product-category promotions does
not itself supply a dominant-character test for an indivisible package of
discounts and other benefits. Technical XML specifications described as supplied
separately cannot be reconstructed from a model's recollection. These missing
premises remain named source dependencies.~\cite{jfiu2026transition,sfcgiftfaq}

\subsection{Following a fresh proposal into Java}

The next development example uses the official JSON for SFC circular 23EC52,
frozen before its accepted fresh model proposals. Its paragraph 28 and footnote
7 discuss the virtual-asset de-minimis trigger for fund managers and distinguish
tokenised securities from the relevant virtual assets.~\cite{sfctokenised2023}

The input interface supplies a
fund-manager classification, the stated virtual-asset investment objective,
and intended virtual-asset investment as basis points of gross asset value.
The objective and asset classifications are supplied facts requiring judgment;
the experiment does not claim to derive them automatically from contracts.
The numerical examples use exact whole basis points. An operational adapter
must preserve finer precision or return an unknown input; rounding an exposure
up to a threshold would change the legal question.

Before requesting a formula, the author freezes cases immediately below, at
and above the stated threshold, an objective-only case, tokenised-only and
mixed-exposure cases, and missing-input cases. These expected answers are kept
out of generation and review prompts. Two methods receive the full circular:
one extracts duties and conditions; the other rewrites the selected question
in controlled language. Each accounts for every supplied source unit and
records other provisions as separate or unresolved questions. Both methods
currently use the same model family, which leaves common errors possible.
The supplied packet contains the complete circular body and its footnotes;
its separate appendix and referenced legislation remain external dependencies.
Accounting for the supplied text therefore does not establish full coverage
of all incorporated authority.

Each returned executable proposal is compiled unchanged through RuleIR into
Java. A generated Java class embeds the entire retained set and calls every
policy before applying Equation~\eqref{eq:retained-unanimity}. Its response
contains the individual outcomes and hashes of the question, source packet,
facts and reading set. The API returns a conditional draft decision; it does
not authorize a bank transaction. Python, cvc5 and the supported Catala backend
provide further checks of the encoded rules. Their agreement tests execution
of those rules, while the withheld source cases test the author's specific
source-to-rule expectations. An independently adjudicated accuracy study is
still a different experiment.

\subsection{What the executed increment establishes}

RESULTPARAGRAPH

The accepted execution followed a failed preliminary attempt. Seventy-seven
model reservations failed during CLI initialization and two more belonged to
an interrupted attempt; none supplied a usable interpretive judgment. An
incomplete manually reconstructed circular was also rejected and replaced with
the official bytes before the accepted proposals. Those failures remain in the
execution record and count against the original allowance. A circuit breaker
now stops dependent dispatch after a transport failure. Repairing the execution
machinery does not convert the rejected attempt into evidence about the source.

The exclusion challenge revisits every one of the 272 claim--reading pairs
previously omitted under two proposed control assignments. A new finding of
relevance restores the pair for source-fidelity work; an uncertain response
also restores it. Agreement that a pair is irrelevant remains a defeasible
judgment. The procedure prevents a routing decision from quietly becoming a
proof of interpretive completeness.

The PDF work preserves all 339 previously unresolved differences and their
source and raster identities. A narrowly defined resolution joins parser
tokens at a preserved hyphen only when the resulting printed word is uniquely
located in the page's retained glyph layout. It cannot remove a negation,
change an amount or unit, reassign a table column, or turn two ordinary words
into one. Cases outside that rule retain their uncertainty and locations.

These results provide an executable route from multiple proposed readings to
conditional decisions and explicit refusals. They leave two distinct kinds of
work. Specific source dependencies and failed correspondences require further
investigation. Estimating legal error rates, common failures across different
model families, or savings in professional review requires independently
supported reference judgments and observations of that review. Neither more
passing software tests nor repeated votes supplies those observations.
'''
    counts=pdf['counts'];matched=sum(r.get('matched',False) for r in new.get('matches',[]))
    reviews=[r['review']['judgment'] for r in live['repairs'] if r.get('review')]
    changes=reviews.count('CHANGES_MEANING')
    changes_noun='proposal' if changes==1 else 'proposals'
    paragraph=(f"The executed round retained all eight unencoded parents and produced {live['encoded_children']} "
        f"executable child proposals for inspection. Parent/child reviews classified "
        f"{changes} {changes_noun} as changing meaning, "
        f"{reviews.count('NOT_ESTABLISHED')} as not established, and "
        f"{reviews.count('PRESERVES_WITH_STATED_RESIDUALS')} as preserving meaning with stated residuals. "
        "None of these outcomes removes an unencoded parent. "
        f"The fresh circular produced {new.get('generated_candidates',0)} "
        f"readings, of which {new.get('compiled_candidates',0)} compiled; {matched} candidate--case comparisons "
        f"over {new.get('reference_case_count',0)} distinct cases matched the frozen development expectations. "
        f"The useful-decision criterion was "
        f"{'met' if new.get('useful_decision_criterion') else 'not met'}. "
        f"The exclusion challenge restored {live['restored_pairs']} pairs for further investigation. "
        f"Located typography resolved {counts.get('TYPOGRAPHY_RESOLVED',0)} additional PDF differences, "
        f"leaving {counts.get('MATERIALITY_UNRESOLVED',0)} with unresolved materiality. "
        f"Independent executable checks covered {verification['comparisons']} cases. "
        "These counts describe this retained development exercise; they are not an estimated legal accuracy rate.")
    text=text.replace('RESULTPARAGRAPH',paragraph)
    (book/'chapters/06d-invariant-decisions.tex').write_text(text)
    chapter=book/'chapters/06-ensemble.tex';inclusion='\n\\input{chapters/06d-invariant-decisions}\n'
    if inclusion not in chapter.read_text():chapter.write_text(chapter.read_text()+inclusion)
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'};commands=[]
    # The binder uses the document environment's PyMuPDF. Its JSON writer is
    # standard-library-only, avoiding an unrelated application dependency.
    citation_command=['/home/chakwong/miniconda3/envs/tfgpu/bin/python',str(ROOT/'scripts/resolution_citations.py')]
    with (out/'citation-binding.log').open('w') as log:
        subprocess.run(citation_command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    commands.append(citation_command)
    for script in ('build_reader_facing_monograph.py','check_monograph.py'):
        cmd=['/home/chakwong/miniconda3/envs/tfgpu/bin/python',str(ROOT/'scripts'/script)]
        with (out/(script+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
        commands.append(cmd)
    info=subprocess.check_output(['pdfinfo',str(book/'monograph.pdf')],text=True)
    pages=int(re.search(r'Pages:\s+(\d+)',info).group(1))
    if pages<base['monograph_pages'] or (book/'monograph.pdf').read_bytes()!=(ROOT/'docs/proposal/proposal.pdf').read_bytes():
        raise LegalMathError('E_INTEGRITY',details='Unified manuscript lost pages or alias differs')
    value={'status':'UNIFIED_MONOGRAPH_PRESERVED_AND_BUILT','previous_pages':base['monograph_pages'],'pages':pages,
           'commands':commands,'new_unit':'chapters/06d-invariant-decisions.tex','human_readability_review':'PENDING',
           'rendered_author_inspection':'REQUIRED_AFTER_BUILD','release_eligible':False}
    save(out/'result.json',value);return value
