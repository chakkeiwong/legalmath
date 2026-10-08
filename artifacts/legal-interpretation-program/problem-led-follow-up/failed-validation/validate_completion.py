"""Independent completeness/provenance checks for the bounded follow-up."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import collections
import hashlib
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import digest
from scripts import legal_interpretation_s4_execute as s4
OUT=Path(__file__).resolve().parent
DOC=ROOT/'docs/implementation/legal-interpretation-program/follow-up'
S4=ROOT/'artifacts/legal-interpretation-program/successor-s4/attempt-1'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):
    p=Path(p).resolve()
    return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def save(n,x):
    (OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\\n')
def main():
    started=time.monotonic()
    obs=read(S4/'obligations.json'); rs=read(S4/'reading-inventory.json')['readings']
    reg=read(OUT/'premise-register.json'); traces=read(OUT/'obligation-traces.json')
    table=read(OUT/'question-output-table.json'); qp=read(OUT/'question-provenance.json')
    assert [r['original_record'] for r in traces]==obs
    assert [r['retained_record'] for r in table]==rs
    original={m['id']:(o,m) for o in obs for m in o['missing_premises']}
    assert len(original)==len(reg['requests'])==224
    assert {r['original_premise']['id'] for r in reg['requests']}==set(original)
    parts=[]
    for r in reg['requests']:
        ob,m=original[r['original_premise']['id']]
        assert m==r['original_premise'] and ob['original_hash']==r['original_obligation_hash']
        assert ob['obligation_id']==r['obligation_id']
        assert r['atoms'] and set(r['linked_reading_ids'])<={x['reading_id'] for x in rs}
        parts.extend(a['id'] for a in r['atoms'])
    assert len(parts)==len(set(parts))==407
    assert sum(r['mixed_legal_factual'] for r in reg['requests'])==38
    assert sum(not r['direct_original_obligations'] for r in table)==21
    assert sum(len(r['role_records']) for r in rs)==70
    assert len(qp['readings'])==35 and sum(len(r['role_question_records']) for r in qp['readings'])==70
    assert reg['annotation_script_sha256']==sha(OUT/'normalize_inventory.py')
    for p,h in reg['sources'].items(): assert sha(ROOT/p)==h
    baseline=read(OUT/'baseline-verification.json')
    assert baseline['method']==s4.method()
    diag=read(OUT/'diagnostic-results.json'); manifest=read(OUT/'diagnostic-manifest.json')
    assert diag['summary']['status']=='PASS' and manifest['result_sha256']==sha(OUT/'diagnostic-results.json')
    assert manifest['script_sha256']==sha(OUT/'run_diagnostics.py')
    assert len(diag['scoped_cases'])==30 and len(diag['legacy_formula_results'])==11
    assert diag['scoped_cases'][0]['result']==read(S4/'development-computation.json')
    for case in diag['scoped_cases']:
        assert case['result']['release_eligible'] is False
    packet=read(S4/'development-inputs.json')['packet']
    units={u['unit_id']:u['text'] for u in packet['units']}
    spans=0
    for ob in obs:
        for s in ob['source_assertions']:
            assert units[s['unit_id']][s['start']:s['end']]==s['quote']
            spans+=1
    acquisition=ROOT/'artifacts/legal-interpretation-program/successor-s2/acquisition'
    sources=[]
    for identity in ('gatecoin-2023','gatecoin-2025'):
        p=acquisition/identity/'judgment-text.txt'
        sources.append({**ref(p),'characters':len(p.read_text()),'inspection':'Full reasons, operative conclusions and schedule/annexure/notes read in this execution'})
        sources.append(ref(acquisition/identity/'response.bin'))
        for name in ('text.txt','response.bin'):
            sources.append(ref(acquisition/(identity+'-official')/name))
    anchors=[
        ('gatecoin-2023-official','The principles on certainty of intention','2023 §65'),
        ('gatecoin-2023-official','Although Clause 10.1.1','2023 §71(4)'),
        ('gatecoin-2023-official','For the reasons discussed above','2023 §82'),
        ('gatecoin-2025-official','The transactions described in the 7','2025 §8(3)'),
        ('gatecoin-2025-official','The 5th to 7th scenarios','2025 §95(1)'),
        ('gatecoin-2025-official','Gatecoin does not hold','2025 §95(7)'),
    ]
    quoted=[]
    for identity,anchor,locator in anchors:
        p=acquisition/identity/'text.txt';t=p.read_text();offset=t.index(anchor)
        quoted.append({'source':ref(p),'locator':locator,'start':offset,'end':min(len(t),offset+1400),
            'excerpt':t[offset:offset+1400],'role':'Court reasons/operative conclusions; legal characterization remains reviewable'})
    save('source-investigation.json',{'sources':sources,'official_anchor_checks':quoted,
        'circular_packet':ref(S4/'development-inputs.json'),
        'new_retrievals':0,'treatment_completeness':'NOT_ESTABLISHED',
        'reading_record':'Full mirror reasons inspected; selected propositions checked against retained official extraction. Byte identity is not legal correctness.'})
    save('validation.json',{'status':'PASS','obligations_preserved':46,'premises_preserved':224,'question_parts_unique':407,
        'mixed_requests':38,'readings_preserved':35,'role_records':70,'source_assertion_spans_checked':spans,
        'official_anchors_checked':len(quoted),'diagnostic_variants':41,'method_unchanged':True,
        'wall_seconds':time.monotonic()-started,'script':ref(Path(__file__)),
        'scope':'Exact completeness/provenance and unchanged-method checks; annotations and legal interpretations are not certified'})
    outputs=[ref(p) for p in sorted(OUT.iterdir()) if p.is_file()]
    outputs += [ref(DOC/n) for n in ('execution-contract.md','package-a-findings.md','paragraph-10-dossier.md',
        'paragraph-14-dossier.md','gatecoin-dossier.md','intervention-audit.md','diagnostic-repair-review.md','final-decision.md')]
    plan=ROOT/'docs/plans/legal-interpretation-problem-led-follow-up.md'
    assert sha(plan)=='1db7d74b825f67fe41b921ea34891df0594bcbca0924c01e7a73a238415ba669'
    save('result.json',{'program':'legal-interpretation-problem-led-follow-up','version':1,
        'state':'COMPLETE_BOUNDED_DIAGNOSIS','completed_packages':['A','B','C','D'],
        'plan':ref(plan),'baseline':ref(OUT/'baseline-verification.json'),'decision':ref(DOC/'final-decision.md'),
        'validation':ref(OUT/'validation.json'),'diagnostic':ref(OUT/'diagnostic-results.json'),
        'intervention':'Additional duty-versus-fulfillment guard','intervention_decision':'REJECT_AS_UNNECESSARY_FOR_INSPECTED_ROUTE',
        'production_changes':0,'diagnostic_setup_repairs':1,'open_qualified_obligations':46,
        'english_fidelity':'NOT_ESTABLISHED','legal_correctness':'NOT_ESTABLISHED','release_eligible':False,
        'next_phase':None,'automatic_continuation':False,'provider_calls':0,'network_requests':0,
        'outputs':outputs,'completed_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'status':'PASS','result':ref(OUT/'result.json'),'validation':read(OUT/'validation.json')},indent=2))
if __name__=='__main__': main()
