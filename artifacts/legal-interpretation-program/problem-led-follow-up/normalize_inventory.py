"""Reproduce package A from explicitly reviewed annotations; never classify by keywords.

Run from repository root with .venv/bin/python and CUDA_VISIBLE_DEVICES=-1.
This is an evidence-generation script, not a product or successor-phase runner.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'artifacts/legal-interpretation-program/successor-s4/attempt-1'
OUT = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    p = OUT / name
    text = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    if p.exists() and p.read_text() != text:
        raise ValueError('Preserve previous output before changing annotations: ' + name)
    p.write_text(text)

# Each code names a question/input specification. Reuse does NOT equate readings,
# legal tests, required evidence, or the truth of two occurrences of that question.
DEFS = [
 ('TL','authority/applicability','Which commencement, transition, succession, cessation and historical-record duties apply to each specified interval?', 'Identify instruments and provisions for the selected provider/product/period; do not infer commencement from an edition date.'),
 ('TP','factual input','What interval and knowledge cutoff is the assessment actually about?', 'Supply start, end, timezone/granularity and purpose of assessment; unknown period remains unknown.'),
 ('TE','factual input','Which dated appointments, transfers, migrations, terminations and custody events occurred?', 'Dated documents, actor/function mappings and validity intervals, including gaps; a snapshot is insufficient.'),
 ('SI','source interpretation','Does paragraph 10 test retained accountability, exercised conduct, achieved adequacy or a combination?', 'Source argument for the selected consequence, preserving allocation/conduct/outcome rivals; p10/fn1 and adjacent duties are distinct.'),
 ('NG','normative standard','What makes retention of powers and accountability effective rather than nominal?', 'State a sourced sufficient or necessary condition and its limits for each subject; do not assume contractual acceptance is enough.'),
 ('NC','normative standard','What supervision and corrective conduct is required for this role and arrangement?', 'Specify applicable information access, monitoring, expertise, intervention and cadence standards; no invented universal checklist.'),
 ('NO','normative standard','What counts as adequate management, operational soundness and proper records?', 'State the relevant outcome, scope and threshold separately for each subject; do not equate an incident with inadequacy.'),
 ('NI','normative standard','How do severity, duration, defects and remediation affect the selected standard over time?', 'Supply the materiality and temporal rule, including whether and how recovery affects an earlier deficiency; remediation is not automatic cure.'),
 ('FG','factual input','What powers, personnel, information access, monitoring and corrective actions actually existed or occurred?', 'Retain contracts, governance rights, staffing/experience records, access tests, monitoring logs and dated actions separately from adequacy judgments.'),
 ('FI','factual input','What incident, discrepancy, reconciliation and remediation events occurred?', 'Identify affected systems/records, times, extent, unresolved differences and recovery evidence; preserve contrary accounts.'),
 ('OL','authority/applicability','Which governing law and operative terms establish ownership, record priority and settlement finality?', 'Identify asset/right, jurisdiction, operative scheme/contract terms, acceptance and priority/finality provisions; Gatecoin is context, not an automatic transfer.'),
 ('OF','factual input','Whose legal and beneficial interests and which transactions/records are actually involved?', 'Supply actor-to-right relationships, transaction and ledger evidence, reconciliation differences, terms acceptance and dates; labels alone are insufficient.'),
 ('AV','authority/applicability','Which retained instrument versions and amendments apply to the specified activity and interval?', 'Trace only the relevant provisions through commencement/amendment/transition; a broad current-law chain is not a necessary precursor to conditional development.'),
 ('SC','authority/applicability','What actual product authorisation conditions, modifications or relaxations govern this scheme?', 'Supply the identified scheme decision/conditions, terms and effective dates; power to relax a requirement does not prove a relaxation occurred.'),
 ('DL','authority/applicability','Which provisions permit or restrict the particular delegation in this actor capacity?', 'Identify function, provider capacity, delegate and applicable provision; UT 6.8 is not blanket outsourcing permission.'),
 ('LB','question mismatch','What separate rule, if any, establishes liability, remedy or sanction?', 'Defer from the selected responsibility/fulfillment question unless a separate consequence is requested; retain original request, do not treat SHOULD as statutory liability.'),
 ('F5','source interpretation','How does footnote 5 attach to paragraph 14 request, object and standard?', 'Keep A/B/C and confirmation/demonstration separate; identify an authoritative reconciliation if claiming one.'),
 ('RQ','factual input','Was a request made for demonstration, audit/verification or legal opinion, and what did it cover?', 'Supply each request separately with issuer, subject, recipient, activity and effective interval; no request cannot establish fulfillment.'),
 ('RF','factual input','Who is the assessed provider, what product/activity is involved and which capacities are exercised?', 'Identify entities/product/activities and dated appointments; provider and intermediary are different roles.'),
 ('RM','authority/applicability','Which legal role requirements attach to the identified actor/activity?', 'Map the facts to the specific Product Provider, intermediary, register keeper or management-company rule without capacity transfer.'),
 ('RP','representation','How are unknown, conflicting and out-of-scope facts and qualified conclusions represented?', 'Use existing four-state evidence, explicit scope and qualifications first; reproduce loss before proposing a new representation.'),
 ('IN','factual input','Which components, interfaces, actors and ownership relationships can affect this selected assessment?', 'Bound the arrangement inventory by the selected claim; completeness is an explicit premise, not an unbounded demand for every possible fact.'),
 ('EX','representation','Is the retained Appendix text faithful to the underlying source and relevant layout?', 'Resolve the named extraction/visual qualification before relying on disputed text; it does not invalidate unrelated exact circular spans.'),
 ('CF','factual input','What confirmation was actually given and on what evidence?', 'Retain confirmation text, sender, recipient, covered subjects and dates separately from truth of its content.'),
 ('SA','factual input','What evidence establishes SFC satisfaction with the specified demonstration?', 'Supply relevant SFC correspondence and demonstration evidence; neither confirmation nor commissioning an audit establishes satisfaction.'),
]
ATOMS = {key: {'class': cls, 'question': q, 'input_or_warrant': spec} for key,cls,q,spec in DEFS}

# One entry per missing-premise request, in the immutable ordinal/order below.
# A comma separates genuinely different questions hidden in that request.
MAP = {
 1: 'TL;SC,TE;TL;TE,TP',
 2: 'SI;FI,NI;SI,NG,NC,NO;NI',
 3: 'SC;DL;AV;LB;RF,SC,DL;AV',
 4: 'TL,TP,TE;F5;NI;TP,TL,FI;F5',
 5: 'SI,NI;OF,FI;SI;NI',
 6: 'AV;SC;SI,NI,LB,AV;AV,SC;AV,SI',
 7: 'SI,NG,NC,NO;NI;SI,NG,NC,NO;RP',
 8: 'TL;TP,NI;TL,TP;TE,TL;NI,FI',
 9: 'SI;NI;SI;NG,NC,NO,NI;FG,FI,OF',
 10:'AV;SC,OL;IN,RQ;AV;RF,SC,OL;F5',
 11:'TL,TP;TL;NI;TL;TP,TE;NI',
 12:'SI,NI;OL;OF,FI;SI;NI;OL,SC,OF',
 13:'DL,AV;SC;OL,SI;DL,AV;SC,OL;RF,TP,AV',
 14:'NC,NO,NI;IN,FG,FI,OF;RP;SI,NI;IN,RF,OF,TP;NC,NO,FG,FI,RP',
 15:'TL;TE,TL;TP;TL;SC,TE,AV',
 16:'SI;NG,NC,NO;FI,FG,RQ,OF,RP;SI;NI',
 17:'SC;AV;SC,DL;AV;AV;SC;AV,DL,LB',
 18:'TL,TP;TL;TL;NI;TP,TL;NI',
 19:'SI;NO;NI;SI;SI,NO',
 20:'AV;SC;SI,LB;AV;AV,SC;SI,LB',
 21:'TL,NI;F5;TL,NI,TE',
 22:'SI,NC,NO;NI,OL;SI,NI',
 23:'AV;SC;EX;SI,AV,SC',
 24:'TL;TE;TP,TE,TL',
 25:'NG,NC;SI,NI;FG;NG,FG,SI,NI',
 26:'DL;SC,AV;SI,NI;SI,NI,SC,DL,AV',
 27:'TL;TE;TL;TL;TL;TP,TE',
 28:'SI,NG,NC,NO;NI;SI;NI',
 29:'SC;DL,LB;AV;AV;AV,DL;SC;OL,LB',
 30:'TP;TL;AV;TL;TE;AV,TP',
 31:'SI;NI;NG;SI;NI',
 32:'SC,DL;LB;AV;AV;SC;DL,LB',
 33:'AV;TL,TE;TL;TE,AV',
 34:'SI,NG,NC,NO;NG,NC,NO;SI,NG,NC,NO;NI',
 35:'SC;DL,LB,AV;RF,SC,DL,AV;SI,LB',
 36:'TL;SC,TP;TL;TL,TE',
 37:'SI;FG,FI,NG,NC,NO;SI;FI,NI',
 38:'AV;SC;DL,LB;RF,AV;SC,LB,AV',
 39:'TL;TE,TL;NI,TP;TL,TP,TE;NI',
 40:'SI;NI;SI,NC,NO;NI',
 41:'DL,LB,AV;SC;AV;AV,SC;LB,SI',
 42:'SI,NG,NC,NO;FG,FI,CF,RQ,SA;SI,NG,NC,NO,FG,FI;F5',
 43:'RF,TP;NC;TL,NI;NC,TL;FI,TP',
 44:'NG,NC,NO;OL;FI,OF;NG,NC;SI,NI',
 45:'RF,RM;SC,AV;DL;RF,RM;SC,DL,OL,AV',
 46:'NC;FG;NI;SI,NG,NC,NO;FG,FI,OF,RP',
}
EXHAUSTIVE = {(7,3),(25,1),(44,4),(46,1)}
BROAD = {(3,3),(6,1),(14,2),(14,5),(17,7),(20,4),(23,4),(29,3),(30,3),(38,1)}

# Individual review notes: these supplement, never replace, original statements.
NOTES = [
 'Effective governance can coexist with a defect; nominal acceptance is insufficient.',
 'Substantive discharge remains unspecified between conduct and outcomes; no conjunction selects it.',
 'Conduct-focused stewardship is not an outcome guarantee; adjacent safeguards are contextual.',
 'Allocation rival retained against substantive failure; powers and actual conduct still need differentiation.',
 'Allocation expressed within Section B; separate performance/evidential duties continue.',
 'Existing arrangement_sound/ownership_records_proper facts cannot measure stewardship during recovery.',
 'Proposed R=true, records=false distinguishes formulas only under aligned supplied definitions.',
 'Paragraph 19 gives staffing context without an exhaustive oversight/remediation test.',
 'Single responsibility_retained summarizes a disputed judgment, not an observed event.',
 'Effective exercise can fail under nominal acceptance even when current outcomes succeed.',
 'Retains oversight rival without personally performing every operation or guaranteeing no incident.',
 'Explicit SHOULD and subject-specific continuing conduct; undefined standards prevent legal execution.',
 'Separate records breach is compatible with proposed limited allocation satisfaction.',
 'Possessing powers, exercising powers and achieving outcomes are three distinct tests.',
 'Three-condition conjunction is only the supplied outcome variant; conduct remains unrepresented by those facts.',
 'Unknown standards/evidence cannot be turned into failure; incident alone does not establish inadequacy.',
 'Three allocation facts cannot answer adequate discharge even though each responsibility subject is separate.',
 'Substantive deficiency beyond undisclaimed responsibility needs an actual conduct/outcome criterion.',
 'Continued supervision and corrective capability differ from nominal authority and current outcomes.',
 'Only an assessed outcome failure defeats this rival; an incident is not an automatic inadequacy label.',
 'Outsourcing/approval attachments are shared assumptions; dispute remains effective discharge.',
 'Per-subject and per-interval retention; another actor can have duties without releasing this provider.',
 'Affirmative assurance could add to accountability; neighboring duties do not settle its standard.',
 'Existing conjunction uses supplied adequacy judgments; same scope and fact meanings must be established for comparison.',
 'Component interfaces and actual ownership relations add coverage dependencies beyond three period-wide facts.',
 'Actor/performer distinction and fn1 reference attachment; operational success does not establish retained authority.',
 'Assessed material unreliability defeats outcome proposal despite diligent conduct; threshold and period remain required.',
 'Stewardship requires component/ownership evidence; no antecedent model or complete conduct/outcome test supplied.',
 'Effective governance may suffice despite registrar defect under this proposal; not mere contractual acceptance.',
 'Existing one-fact allocation formula leaves effective-retention meaning and scope judgments supplied.',
 'Existing three-component retention formula can detect a partial allocation failure but needs period-wide judgments.',
 'Provider identity and primary-dealing scope are independent; qualitative accountability test is still absent.',
 'Exceptions attached narrowly: UT6.8 illustration, Appendix applicability and fn8 do not release p10 responsibility.',
 'Shares outsourcing-exemption rejection but adds substantive discharge; strict liability is not inferred.',
 'Effective exercise across functions requires conduct, interfaces and cadence; no automated judgment threshold.',
]

def main():
    obligations = json.loads((BASE/'obligations.json').read_text())
    readings = json.loads((BASE/'reading-inventory.json').read_text())['readings']
    computation = json.loads((BASE/'development-computation.json').read_text())
    rules = {r['rule_id']:r for r in computation['evaluation']['results']}
    assert len(obligations)==46 and len(readings)==len(NOTES)==35
    normalized=[]; traces=[]
    for ob in obligations:
        ordinal=ob['ordinal']; annotations=MAP[ordinal].split(';')
        assert len(annotations)==len(ob['missing_premises']), ordinal
        for n,(m,keys) in enumerate(zip(ob['missing_premises'],annotations),1):
            codes=keys.split(','); assert len(codes)==len(set(codes)) and set(codes)<=ATOMS.keys()
            critiques=[]
            if (ordinal,n) in EXHAUSTIVE:
                critiques.append('Demand for a complete necessary-and-sufficient Boolean test is not justified by the retained sources. Seek a bounded sufficient/necessary relation or retain judgment, rather than require exhaustive codification.')
            if (ordinal,n) in BROAD:
                critiques.append('Narrow this broad request to provisions, actors/components and intervals affecting the selected question before any retrieval or client-data request.')
            if 'LB' in codes:
                critiques.append('Separate liability/remedy claim deferred; no liability conclusion is needed to compare the selected conditional fulfillment proposals.')
            if 'RP' in codes:
                critiques.append('Existing four-state and scope machinery is the comparator. Representation repair requires a reproduced loss; missing facts alone are not a representation defect.')
            atoms=[{'id':m['id']+'.part.'+str(i+1),'topic':c,**ATOMS[c],
                    'disposition':'DEFER_SEPARATE_CONSEQUENCE' if c=='LB' else
                      ('SPECIFY_VARIABLE_WITHOUT_REQUESTING_PRIVATE_DATA' if ATOMS[c]['class']=='factual input' else 'QUALIFY_OR_CHECK_NAMED_DEPENDENCY')}
                    for i,c in enumerate(codes)]
            normalized.append({'obligation_ordinal':ordinal,'obligation_id':ob['obligation_id'],
                'original_obligation_hash':ob['original_hash'],'original_premise':m,
                'linked_reading_ids':sorted({rr['reading_id'] for rr in ob['role_responses']} |
                    set(ob['original']['obligation']['candidate_ids'])),
                'atoms':atoms,'mixed_legal_factual':any(a['class']=='factual input' for a in atoms) and
                    any(a['class']!='factual input' for a in atoms),'request_critique':critiques,
                'meaning_status':'REVIEWED_PLANNING_DECOMPOSITION; not proved source equivalence'})
        dim=ob['original']['obligation']['dimension']
        first={'time':'The interval and applicable temporal rule are missing before full-period classification.',
               'definition':'The source-to-fulfillment standard is unresolved before observations can be classified.',
               'authority':'The target-specific authority/applicability bridge is missing before a duty or consequence applies.',
               'output':'Fulfillment criteria are missing before an executable result can answer the retained question; unknown representation already exists.'}[dim]
        traces.append({'ordinal':ordinal,'original_record':ob,'first_unresolved_step':first,
            'actual_conditional_outputs':[rules[k] for k in ob['relevant_conditional_rules']],
            'answer_to_original':'OPEN_QUALIFIED; conditional rule application is not fulfillment',
            'normalized_premise_ids':[m['id'] for m in ob['missing_premises']]})
    assert len(normalized)==224 and len({r['original_premise']['id'] for r in normalized})==224
    reading_traces=[]
    for i,r in enumerate(readings):
        cid=r['reading_id']
        direct=[o['obligation_id'] for o in obligations if cid in o['original']['obligation']['candidate_ids']]
        role=[o['obligation_id'] for o in obligations if any(x['reading_id']==cid for x in o['role_responses'])]
        deps=sorted({a['topic'] for n in normalized if cid in n['linked_reading_ids'] for a in n['atoms']})
        # For alternatives these are explicitly new planning links, never original obligations.
        proposed=['SI','NG','TP','RF','AV']
        if r['category'] in ('allocation-and-conduct','unresolved-discharge'): proposed += ['NC','NI','FG']
        if r['category'] in ('allocation-and-adequacy','unresolved-discharge'): proposed += ['NO','NI','FI','OL','OF']
        reading_traces.append({'ordinal':i+1,'retained_record':r,'individual_review':NOTES[i],
            'original_questions':r['original_reading'].get('questions',[]),
            'direct_original_obligations':direct,'role_response_obligations':role,
            'dependency_topics_from_original_requests':deps,
            'proposed_diagnostic_topics':sorted(set(proposed)),
            'equivalence_status':'NOT_ESTABLISHED; preserve identity, original distinctions, assumptions and role records',
            'source_to_rule':'NOT_ESTABLISHED',
            'actual_output':{'rule_id':'p10-responsibility','result':rules['p10-responsibility'],
                'relationship':'Related duty subquestion only; no proven equivalence to this reading or its fulfillment question'},
            'legacy_formula':r['original_reading'].get('formalization'),
            'first_unresolved_step':'Source-to-selected-fulfillment-rule relation and evaluative standards; scope/fact judgments also absent',
            'discriminating_scenarios':['registrar-defect-with-effective-supervision','nominal-acceptance-without-supervision','unknown-assessment-interval']})
    summary={'obligations':len(obligations),'premise_requests':len(normalized),
        'distinct_verbatim_requests':len({x['original_premise']['statement'] for x in normalized}),
        'normalized_question_parts':sum(len(x['atoms']) for x in normalized),
        'mixed_requests':sum(x['mixed_legal_factual'] for x in normalized),
        'readings':len(readings),'role_records':sum(len(r['role_records']) for r in readings),
        'without_direct_original_obligations':sum(not r['direct_original_obligations'] for r in reading_traces),
        'topic_occurrences':dict(sorted(collections.Counter(a['topic'] for n in normalized for a in n['atoms']).items())),
        'substantive_closures':0,'interpretation_accuracy':'NOT_MEASURED',
        'normalization_status':'Review decomposition, not legal equivalence or an exhaustive legal issue taxonomy'}
    save('premise-register.json',{'sources':{str(BASE.relative_to(ROOT)/n):sha(BASE/n) for n in ('obligations.json','reading-inventory.json','development-computation.json')},
        'annotation_script_sha256':sha(Path(__file__)),'topic_definitions':ATOMS,'summary':summary,'requests':normalized})
    save('obligation-traces.json',traces)
    save('question-output-table.json',reading_traces)
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
