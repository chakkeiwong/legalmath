"""Retain original substitution target evidence before implementation."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from scripts.prospectus_margin_preparation import AUTH,read,save,sha,relative
from scripts.prospectus_default_references import retained
from legalmath.prospectus.successor.occurrences import anchor,segments,_DependencyLookup
from legalmath.prospectus.successor.contracts import digest

PREP=AUTH/'reviews/substitution-references-277'
SPEC=ROOT/'src/legalmath/prospectus/successor/basf_substitution_references_spec.json'
KEY='basf-base-september-2022-exchange'
IDS=('substitution-certification','substitution-amendments')


def prepare():
    from legalmath.prospectus.successor.reviewed_references import admit
    assert read(AUTH/'program.json')['revision']==276
    p,a=retained('candidate-answer')
    graph,assembly=p['P1']['payload']['graph'],p['P2']['payload']['assembly']
    raw={u['id']:u for u in graph['units']}
    units={u['unit']:u for u in assembly['units']}
    rows,roles=[],{}
    for identity,line,phrase,ranges in (
        (IDS[0],35,'vorstehenden Unterabsätzen (a), (b), (c) und (d)',((128,75,81),(129,1,4),(129,12,22))),
        (IDS[1],14,'§ 11',((129,54,76),(130,1,2),(130,10,11),(130,23,74),(131,1,31)))):
        u=raw[f'{KEY}:p129:l{line}']
        assert u['raw'].count(phrase)==1
        start=u['raw'].index(phrase)
        source=anchor(u,start,start+len(phrase))
        targets=[]
        for page,first,last in ranges:
            for n in range(first,last+1):
                target=raw[f'{KEY}:p{page}:l{n}']
                selected=units[target['id']]
                left=1 if (page,n) in ((129,12),(130,10)) else 0
                right=len(target['raw'])-1 if (page,n) in ((129,22),(130,11)) else len(target['raw'])
                s=anchor(target,left,right)
                expected_role='UNKNOWN' if (page==130 and (n==2 or 31<=n<=38 or n==66)) or (page==131 and n in (5,13,24)) else 'OPERATIVE'
                assert selected['role']==expected_role and selected['text']==s['quote']
                assert segments(graph,selected,_raw=raw)==[{'source':s,'start':0,'end':len(s['quote'])}]
                roles[target['id']]=expected_role
                targets.append({'source':s,'use':target['id'],'language':target['language']})
        rows.append({'id':identity,'form':'relative','source':source,'from_use':u['id'],
            'language':u['language'],'targets':targets,'authority':source,'questions':['Q1','Q2'],
            'discovery_ids':[r['id'] for r in graph['references'] if r['unit']==u['id']],
            'reason':'Complete original selected substitution conditions and amendment provisions; actual fulfillment and legal application remain unknown.'})
        assert len(rows[-1]['discovery_ids'])==(1 if identity==IDS[1] else 0)
    packet={'version':'reviewed-references.v3','assembly_sha256':digest(assembly),
        'review':{'reviewer':'Codex original pages128-131','kind':'DEVELOPMENT','reason':'Complete substitution conditions and amendment targets'},'references':rows}
    malformed=deepcopy(packet)
    malformed['references'][0]['targets']=rows[0]['targets'][:11]
    malformed['references'][1]['targets']=rows[1]['targets'][:9]
    deps,_=admit(graph,assembly,malformed,_lookup=_DependencyLookup(graph,assembly))
    assert all(d['status']=='RESOLVED' for d in deps)
    printed=read(ROOT/'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    images={k:v for k,v in printed['images'].items() if k.endswith(('base-128.png','base-129.png','base-130.png','base-131.png'))}
    assert len(images)==4
    for name,checksum in images.items():assert sha(ROOT/name)==checksum
    for source in printed['sources']:assert sha(ROOT/source['path'])==source['sha256']
    contexts=[anchor(raw[f'{KEY}:p{page}:l{line}']) for page,line in ((128,74),(129,5),(129,23),(129,33),(129,53),(131,32))]
    spec={'version':'basf-substitution-references.v1','sources':printed['sources'],'references':rows,
        'target_roles':roles,'contexts':contexts,'images':images,'automatic_discovery':False}
    save(PREP/'source-review.json',spec)
    save(SPEC,spec)
    save(PREP/'packet.json',packet)
    ledger=read(AUTH/'attempts/basf-references/attempt-017/candidate-answer-reconciliation.json.gz')
    for fam,idx,row in (('additional_explicit_review_findings',6,rows[0]),('historical_candidate_lines',33,rows[1])):
        record=next(r for r in ledger['records'] if r['family']==fam and r['index']==idx)
        assert record['current_reference'] is None
        record['current_reference']=row
        record['current_status']='CURRENT_REVIEWED_LINK' if idx==6 else 'CURRENT_LINK_AND_UNRESOLVED_TARGET_MEANING'
    save(PREP/'reconciliation-proposed.json.gz',ledger)
    save(PREP/'pre-repair.json',{'truncated_statuses':[d['status'] for d in deps],
        'lost_condition_d':True,'lost_amendment_procedures':True,
        'baseline_products_sha256':digest(p),'baseline_answer_sha256':digest(a)})
    for name in ('src/legalmath/prospectus/successor/reviewed_references.py','src/legalmath/prospectus/successor/service.py'):
        dest=PREP/'pre-edit'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes())
    return {'status':'PASS','new_source_links':2,'target_lines':[22,110],
        'unknown_target_uses':13,'generic_truncation_accepted':True,'original_inventory_records':60}


def main():
    began=time.monotonic()
    save(PREP/'preparation-started.json',{'command':sys.argv,'stage_bound_seconds':90,
        'started_at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU;GPU deliberately hidden'})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Substitution preparation90s')))
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
