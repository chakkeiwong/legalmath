"""Join retained P14 decisions to actual context outcomes without relabeling."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/chakwong/python/legalmath')
HERE=ROOT/'artifacts/legal-mission-control/2026-10-23/p14-corrected-context'
RUNTIME=ROOT/'artifacts/legal-mission-control/2026-10-23/p14-deployment/context-isolated-live/arms/p14/baseline'

def read(path):
    return json.loads(path.read_text())

def ref(path):
    data=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest())

def report():
    original=ROOT/'artifacts/legal-mission-control/2026-10-23/p14-decisions/decisions.json'
    delta=HERE/'continuation-decisions.json'
    prior=read(original)
    new=read(delta)
    expected={r['id']:dict(population='ORIGINAL',decision=r['full_decision'],index=r['index'])
              for r in prior if r['verdict']=='UNRESOLVED'}
    assert len(expected)==672
    for row in new:
        if row['decision']['verdict']=='UNRESOLVED':
            assert row['assignment'] not in expected
            expected[row['assignment']]=dict(population='RECOVERED_52',decision=row['decision'],index=row['index'])
    assert len(expected)==696
    saved={}
    for path in RUNTIME.glob('context-review-*.json'):
        item=read(path)
        identity=item['item']['id']
        assert identity in expected and identity not in saved
        # The census stores grouped decisions; the product attaches the exact
        # assignment when importing them into an individual review. Compare
        # every decision field and independently require that correspondence.
        predecessor=dict(expected[identity]['decision'])
        assert predecessor.get('considered',[identity])==[identity]
        predecessor['considered']=[identity]
        assert item['original_review']['value']==predecessor
        saved[identity]=(item,path)
    rows=[]
    for identity,prior in expected.items():
        row=dict(assignment=identity,population=prior['population'],index=prior['index'],
                 original_verdict='UNRESOLVED',context_status='PENDING',
                 original_need_kinds=sorted({n['kind'] for n in prior['decision'].get('context_needs',[])}),
                 original_reason=prior['decision']['reason'])
        if identity in saved:
            retained,path=saved[identity]
            result=retained['result']
            row.update(context_status=result['status'],evidence=ref(path),
                       source_delivery_failures=retained.get('source_delivery_failures',{}))
            if result['status']=='VALIDATED':
                value=result['value']
                row.update(new_verdict=value['verdict'],reason=value['reason'],
                           need_dispositions=value['need_dispositions'],
                           necessary_context=value['context_needs'],issues=value['issues'],
                           source_gaps=value['source_gaps'],support=value['support'])
            else:
                row.update(error=result.get('error'),reason=result.get('reason'))
        rows.append(row)
    completed=[r for r in rows if r['context_status']!='PENDING']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    outcome=dict(at_utc=datetime.now(timezone.utc).isoformat(),
                 original_population=ref(original),additional_population=ref(delta),
                 expected_original=672,expected_additional=24,total=696,
                 context_statuses=dict(Counter(r['context_status'] for r in rows)),
                 validated_verdicts=dict(Counter(r['new_verdict'] for r in completed if 'new_verdict' in r)),
                 dispositions=dict(Counter(d['disposition'] for r in completed
                     for d in r.get('need_dispositions',[]))),
                 necessary_context_kinds=dict(Counter(n['kind'] for r in completed
                     for n in r.get('necessary_context',[]))),
                 retained_source_gap_occurrences=sum(len(r.get('source_gaps',[])) for r in completed),
                 source_delivery_failure_count=sum(len(r.get('source_delivery_failures',{}))
                     for r in completed),
                 original_verdicts_unchanged=True,legal_acceptance=False,rows=rows)
    directory=HERE/'decision-progress'
    directory.mkdir(exist_ok=True)
    target=directory/(stamp+'.json')
    with target.open('x') as output:
        json.dump(outcome,output,indent=2,ensure_ascii=False)
    print(json.dumps({k:v for k,v in outcome.items() if k!='rows'}|{'report':str(target.relative_to(ROOT))},indent=2))

if __name__=='__main__': report()
