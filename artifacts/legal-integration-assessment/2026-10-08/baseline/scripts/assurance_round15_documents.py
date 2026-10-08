"""Append the observed round-15 result while preserving the preceding monograph."""
from pathlib import Path
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from resolution_support import read,save,sha

OUT=ROOT/'artifacts/interpretation/round15'
BOOK=ROOT/'docs/monograph'
BASE=OUT/'manuscript-baseline'
INCLUSION='\n\\input{chapters/06e-executed-assurance}\n'


def run():
    phases=read(OUT/'phase-results.json')
    fidelity,pdf,mutations=(phases[k]['result'] for k in ('P1','P4','P5'))
    assert read(OUT/'child-witnesses/result.json')['status']=='CHILD_LIMITATIONS_REPRODUCED'
    regression_directory=OUT
    if read(OUT/'full-regression-manifest.json')['status']!='PASS':
        regression_directory=OUT/'pre-summary-repair/regression'
    assert read(regression_directory/'full-regression-manifest.json')['status']=='PASS'
    count=sum(int(s.get('tests',0)) for s in ET.parse(regression_directory/'full-regression.xml').getroot().iter('testsuite'))
    baseline=read(BASE/'manifest.json')
    preserved=[]
    for name,h in baseline['files'].items():
        if Path(name).suffix not in ('.tex','.bib'):continue
        if name.startswith('docs/monograph/review/'):continue  # Rebuilt expanded diagnostics, not authored inputs.
        original=(BASE/name).read_text();current=(ROOT/name).read_text()
        assert sha(BASE/name)==h
        if name.endswith('/06-ensemble.tex'):current=current.replace(INCLUSION,'')
        assert current==original,'Existing source text changed: '+name
        preserved.append(name)
    text=r'''
\section{The errors that agreement can leave hidden}
\label{sec:executed-assurance}

The conditional decision in Section~\ref{sec:invariant-decisions} is useful only
if its retained readings still include the qualifications that matter to the
bank's question. A workflow can lose one before any formula is compiled. An
early reader might label a paragraph as background; later stages might then
compare several interpretations without ever testing that paragraph against
them. Their agreement would leave the exclusion unexamined.

The preceding investigation challenged 272 previously excluded claim--reading
pairs and restored 232 for further examination. A restored pair is a reason to
revisit the exclusion, not proof that the earlier reader was wrong. Of those
pairs, 231 had an executable reading and one still lacked a supported encoding.
Forty-eight of the executable pairs involved claims historically labelled as
context. An initial implementation would have filtered those claims out again.
Its review therefore caught a consequential procedural error: the program's
actual comparison universe was smaller than the one its plan promised.

The repaired procedure schedules every executable restored pair. It supplies
the complete retained source packet and the actual executable meaning while
withholding earlier routing and fidelity labels. Scheduling the comparison does
not assert that the claim governs the selected question. The reader must still
explain that relationship. A source quote, an executable quotation and an exact
pair identity make the judgment inspectable; they do not make it authoritative.
The one unencoded pair remains a separate obligation. Removing it would improve
the completion percentage by changing the question.

\subsection{A child's result may answer a smaller question}

The STR example makes another failure visible. Three proposed child rules
compile: a rule for urgent contact, a trigger for the XML-transition duties,
and a trigger for resubmission after an off-channel filing. The latter two
answer whether a duty is triggered. They contain no executable condition for
whether the required performance occurred. A firm intending to submit XML can
satisfy the trigger whether or not it has followed the schema or arranged the
technical liaison. Likewise, two histories with the same original off-channel
submission have the same trigger even when only one contains a linked
resubmission. The trigger can be correctly implemented while the broader
compliance question remains unanswered.

The urgent-contact child's fact definition records contact for the assessed STR
somewhere during the blackout. Suppose the instant being assessed is noon and
contact occurred at 13:00. A fact meaning ``contact occurred during the blackout''
can be true, while ``contact had occurred by noon'' is false. A before-noon
contact and an after-noon contact can therefore collapse to the same supplied
Boolean. If the selected question concerns performance by the assessed instant,
the data interface needs that distinction. This example identifies missing
information; it does not supply a legal deadline or decide what urgency means.

The generated children's version intervals expose a separate limitation. Each
begins on the development date in September 2026. When an assessment is instead
made for the January or February transition, the current evaluator returns a
version-time error. Nine targeted cases reproduce these refusals and the
children's positive and changed-condition results in Java, Python, cvc5 and
Catala. The refusal is correct for the stored interval. That interval does not
establish historical coverage of the circular. The next implementation must
separate source effectiveness, the time of the assessed event and the time when
the system learned the evidence, without inventing a source commencement date.

These observations explain why all eight unencoded parents remain retained.
The three executable children and fifteen unencoded children are partial
proposals. Backend conformance can support their stated computations. It cannot
establish that a child preserves every condition of its parent, or that contact,
trigger satisfaction and full performance mean the same thing.

\subsection{Preserving the threshold through the input interface}

The fund example supplies a repair that can be checked exactly. Its earlier
interface used whole basis points. An exposure of 9.999\% equals 999.9 basis
points. Rounding it to the nearest whole basis point gives 1000, which changes
the answer to an inclusive 10\% threshold test. A Java program can execute that
rounded comparison perfectly and still answer the wrong numerical question.

Let $p$ be the supplied decimal percentage, expressed in percentage units:
$p=10$ means 10\%, not a fraction of 0.10. Parse the decimal string exactly and
write $100p=n/d$ in basis points, where $n$ is an integer and $d$ is a positive
integer. The positivity condition is supplied by the rational adapter. Multiplying
an inequality by a positive denominator preserves its direction, so
\begin{equation}
  100p=\frac{n}{d},\quad d>0
  \qquad\Longrightarrow\qquad
  \left[\left(\frac{n}{d}\geq 1000\right)
  \Longleftrightarrow
  \left(n\geq 1000d\right)\right].
  \label{eq:exact-fractional-exposure}
\end{equation}
This transformation replaces division with exact integer multiplication and
comparison. It introduces no rounding rule. For 9.999\%, the adapter produces
$n=9999$ and $d=10$; the comparison is $9999\geq10000$, which is false. At 10\%,
it produces $n=1000$ and $d=1$, and equality satisfies the inclusive threshold.
At 10.000000000001\%, the exact numerator exceeds 1000 times the denominator.
The development checks also retain a value equally close below the threshold.

The generated policy accepts the two integer fields, and the current Python
adapter supplies them from a strict decimal string. Arbitrary externally
supplied denominators fall outside this checked interface. An operational Java
boundary must enforce the same positive-denominator and exact-decimal conditions
before accepting bank data. Missing, conflicting or unsupported inputs must
retain their explicit status instead of becoming a rounded number.

Seven numerical cases exercise this representation in the four backends. The
original whole-basis-point policy remains available as the comparator. Separate
mutations change OR to AND, change an inclusive comparison to a strict one, and
shift the threshold by one basis point. An objective-only case detects the first
mutation; the exact boundary detects the other two. All eleven original source
examples are preserved, and a conflicting-objective case checks that conflicting
evidence does not become a known Boolean result.

Asset classification remains a different question. Feeding tokenised securities
into the virtual-asset exposure field can change the decision even when every
backend agrees. The input-mutation witness demonstrates that consequence. It
does not automate the source-dependent classification of a real holding or
establish which edition governs a current transaction.

\subsection{What the completed execution can support}

RESULTS

The label ``not established'' requires careful reading. Some accepted responses
identify a separate advertising or certificate control whose implementation is
absent from a deliberately narrower trigger. That is not by itself an error in
the trigger. Others identify a missing qualification or an unresolved authority.
The current three-label contract does not distinguish these outcomes well enough
for automatic defect counting. The next revision must record source support,
relevance to the precise question and executable correspondence separately,
retaining the original rationale and quotations. Treating all these labels as
wrong interpretations would replace one misleading score with another.

Execution itself supplied a further counterexample to superficial testing. The
one-attempt provider wrapper existed, but its initializer had been placed outside
the reader class. An early fault test used an HTTP-error string that did not
exercise the inherited retry path, so it passed without detecting the wiring
error. Code inspection found the defect. The run was interrupted, the initializer
was moved, and fault tests were extended to overload, disconnection and timeout
conditions. Accepted responses were retained as earlier evidence; the interrupted
call and malformed responses still consumed their reservations. A repeated
response from the same request is never counted as a fresh independent judgment.

The PDF work keeps all 339 original difference identities and gives each an
inspectable context crop linked to the full page. A unique page-number phrase
may be classified as layout only when its exact words, footer position and
retained page image agree. A number in a paragraph, a changed unit, a negation or
an uncertain column relationship cannot be removed by that rule. IMAGECOUNTS
These are parser-discrepancy dispositions, not findings that the remaining text
has been interpreted correctly.

The source-acquisition step retrieves the official appendix for the tokenised
securities circular and the related fund-manager terms. ACQUISITIONS
The acquisition closes a missing-file task only. Certificate mechanics, the
separately supplied XML schema, transition and resubmission guidance, mixed-gift
classification, wider product provisions and incorporated authority remain
named questions until passages and scoped tests address them. A document hash
establishes which bytes were used; it cannot supply a missing legal premise.

The acquired 135-page appendix pack for circular 23EC44 contains clean October
2023 terms in Appendix 7 (PDF pages 74--94) and a separate version showing
amendments in Appendix 7a (pages 95--135). The latter retains deleted and inserted definitions on the same
printed page. Plain-text extraction captures both. This source structure needs
an explicit edition selection before the text is used for interpretation.
Concatenating the whole download can make a deleted definition appear to be a
second operative rule. The retained source-review record identifies the inspected
pages and leaves current effectiveness and supersession unresolved.

The system now retains reproducible counterexamples, explicit refusals and
source-linked concerns. Its legal error rate needs a separate study with
independently justified reference answers, a split by circular or provision,
another model family, and explicit accounting for abstentions and missing runs.
Existing comparison software supports that design. Same-family judgments and
author-made examples do not supply independent answers. Targeted judgments on
consequential unresolved questions may help create references without a
comprehensive external review of every rule.
'''
    labels=fidelity['label_counts']
    paragraph=(f"Round 15 completed {fidelity['completed_pairs']} of the 231 executable restored pair checks, "
        f"leaving {fidelity['pending_pairs']} pending and the separate unencoded pair retained. "
        f"Its accepted model judgments comprise {labels.get('ENTAILED',0)} labelled entailed, "
        f"{labels.get('CONTRADICTED',0)} contradicted and {labels.get('NOT_ESTABLISHED',0)} not established. "
        "These are the reader's scoped judgments, not a measured legal accuracy rate. "
        f"The regression suite passed {count} tests. The three encoded children passed their "
        "generic execution probes, and the targeted historical and condition cases exposed the "
        "limits described above. The numerical mutation witnesses were detected. "
        "None of these results authorizes legal release.")
    imagecounts=(f"The resulting record retains {pdf['materiality_unresolved']} unresolved materiality questions, "
        f"{pdf['status_counts'].get('TYPOGRAPHY_RESOLVED',0)} earlier typography resolutions and "
        f"{pdf['status_counts'].get('FOOTER_LAYOUT_RESOLVED',0)} footer resolutions.")
    acquisitions=phases['P3']['result']['new_acquisitions']
    acquired=sum(r['status']=='ACQUIRED_NOT_ADJUDICATED' for r in acquisitions)
    acquisition_text=("Both specified PDFs were acquired." if acquired==2 else
                      f"The executed requests acquired {acquired} of the two specified PDFs.")
    text=text.replace('RESULTS',paragraph).replace('IMAGECOUNTS',imagecounts).replace('ACQUISITIONS',acquisition_text)
    (BOOK/'chapters/06e-executed-assurance.tex').write_text(text)
    chapter=BOOK/'chapters/06-ensemble.tex'
    if INCLUSION not in chapter.read_text():chapter.write_text(chapter.read_text()+INCLUSION)
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'};commands=[];began=time.monotonic()
    out=OUT/'document-build';out.mkdir(exist_ok=True)
    for script in ('build_reader_facing_monograph.py','check_monograph.py'):
        cmd=['/home/chakwong/miniconda3/envs/tfgpu/bin/python',str(ROOT/'scripts'/script)]
        commands.append(cmd)
        with (out/(script+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    assert sha(BOOK/'monograph.pdf')==sha(ROOT/'docs/proposal/proposal.pdf')
    save(OUT/'document-build.json',{'status':'BUILT_RENDERED_REVIEW_PENDING','commands':commands,
        'wall_seconds':time.monotonic()-began,'baseline_pages':baseline['pages'],
        'preserved_source_files':preserved,'pdf_sha256':sha(BOOK/'monograph.pdf'),
        'new_source':'docs/monograph/chapters/06e-executed-assurance.tex',
        'reported_test_count':count,'test_count_basis':str(regression_directory.relative_to(ROOT)),
        'final_repaired_code_acceptance':'Requires final delivery verifier and full regression',
        'human_readability_review':'PENDING','release_eligible':False})
    print('Monograph built; rendered inspection remains required')


if __name__=='__main__':run()
