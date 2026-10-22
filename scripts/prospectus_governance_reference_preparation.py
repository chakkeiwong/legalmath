"""Original page-bound preparation for two remaining governance references."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import sys
import time
import json

os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from scripts.prospectus_margin_preparation import AUTH,read,save,sha,relative
from scripts.prospectus_reference_integrity import retained
from legalmath.prospectus.successor.occurrences import anchor,segments,_DependencyLookup
from legalmath.prospectus.successor.contracts import digest

PREP=AUTH/'reviews/governance-references-275'
SPEC=ROOT/'src/legalmath/prospectus/successor/basf_governance_references_spec.json'
KEY='basf-base-september-2022-exchange'
IDS=('governance-majority','governance-registration-proof')


def prepare():
    from legalmath.prospectus.successor.reviewed_references import admit
    assert read(AUTH/'program.json')['revision']==274
    p,a=retained('candidate-answer')
    graph,assembly=p['P1']['payload']['graph'],p['P2']['payload']['assembly']
    raw={u['id']:u for u in graph['units']}
    units={u['unit']:u for u in assembly['units']}
    rows=[]
    contexts=[]
    for identity,page,line,phrase,target_page,first,last in (
        (IDS[0],129,57,'Absatz 2',129,63,68),
        (IDS[1],130,70,'Absatz (a)(ii) und (iii)',130,46,65)):
        u=raw[f'{KEY}:p{page}:l{line}']
        assert u['raw'].count(phrase)==1
        start=u['raw'].index(phrase)
        source=anchor(u,start,start+len(phrase))
        targets=[]
        for n in range(first,last+1):
            target=raw[f'{KEY}:p{target_page}:l{n}']
            selected=units[target['id']]
            s=anchor(target)
            assert selected['role']=='OPERATIVE' and selected['text']==target['raw']
            assert segments(graph,selected,_raw=raw)==[{'source':s,'start':0,'end':len(s['quote'])}]
            targets.append({'source':s,'use':target['id'],'language':target['language']})
        rows.append({'id':identity,'form':'relative','source':source,'from_use':u['id'],
            'language':u['language'],'targets':targets,'authority':source,'questions':['Q1','Q2'],
            'discovery_ids':[],'reason':'Complete original section11 target, preserving all conditions and statutory qualifications; actual votes, registration and legal applicability remain unknown.'})
        contexts.extend(anchor(raw[f'{KEY}:p{target_page}:l{n}']) for n in (first-1,last+1))
        assert not any(r['unit']==u['id'] for r in graph['references'])
    packet={'version':'reviewed-references.v2','assembly_sha256':digest(assembly),
        'review':{'reviewer':'Codex original pages129-130','kind':'DEVELOPMENT',
            'reason':'Original majority and registration/proof target paragraphs'},'references':rows}
    malformed=deepcopy(packet)
    malformed['references'][0]['targets']=rows[0]['targets'][:2]
    malformed['references'][1]['targets']=rows[1]['targets'][:7]
    deps,_=admit(graph,assembly,malformed,_lookup=_DependencyLookup(graph,assembly))
    assert all(d['status']=='RESOLVED' for d in deps)
    printed=read(ROOT/'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    images={k:v for k,v in printed['images'].items() if k.endswith(('base-129.png','base-130.png'))}
    assert len(images)==2
    for name,checksum in images.items():assert sha(ROOT/name)==checksum
    for source in printed['sources']:assert sha(ROOT/source['path'])==source['sha256']
    spec={'version':'basf-governance-references.v1','sources':printed['sources'],
        'references':rows,'contexts':contexts,'images':images,'automatic_discovery':False}
    save(PREP/'source-review.json',spec)
    save(SPEC,spec)
    save(PREP/'packet.json',packet)
    ledger=read(AUTH/'attempts/basf-references/attempt-014/candidate-answer-reconciliation.json.gz')
    for idx,row in ((37,rows[0]),(41,rows[1])):
        record=next(r for r in ledger['records'] if r['family']=='historical_candidate_lines' and r['index']==idx)
        assert record['current_reference'] is None
        record['current_reference']=row
        record['current_status']='CURRENT_REVIEWED_LINK'
    save(PREP/'reconciliation-proposed.json.gz',ledger)
    save(PREP/'pre-repair.json',{'generic_statuses':[d['status'] for d in deps],
        'lost_majority_exception':True,'lost_participation_proof':True,
        'baseline_products_sha256':digest(p),'baseline_answer_sha256':digest(a)})
    for name in ('src/legalmath/prospectus/successor/reviewed_references.py','src/legalmath/prospectus/successor/service.py'):
        dest=PREP/'pre-edit'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes())
    return {'status':'PASS','new_source_links':2,'target_lines':[6,20],
        'original_inventory_records':60,'generic_truncation_accepted':True}


def main():
    began=time.monotonic()
    save(PREP/'preparation-started.json',{'command':sys.argv,'stage_bound_seconds':90,
        'started_at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU;GPU deliberately hidden'})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Governance preparation90s')))
    signal.alarm(90)
    try:
        result={**prepare(),'wall_seconds':time.monotonic()-began}
        save(PREP/'preparation-result.json',result)
        print(json.dumps(result))
    except BaseException as exc:
        save(PREP/'preparation-failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-began})
        raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
