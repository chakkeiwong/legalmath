"""Retain original default target evidence before implementation."""
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
from scripts.prospectus_governance_references import retained
from legalmath.prospectus.successor.occurrences import anchor,segments,_DependencyLookup
from legalmath.prospectus.successor.contracts import digest

PREP=AUTH/'reviews/default-references-276'
SPEC=ROOT/'src/legalmath/prospectus/successor/basf_default_references_spec.json'
KEY='basf-base-september-2022-exchange'
IDS=('default-quorum-trigger','default-quorum-exceptions','default-notice-scope')


def prepare():
    from legalmath.prospectus.successor.reviewed_references import admit
    assert read(AUTH/'program.json')['revision']==275
    p,a=retained('candidate-answer')
    graph,assembly=p['P1']['payload']['graph'],p['P2']['payload']['assembly']
    raw={u['id']:u for u in graph['units']}
    units={u['unit']:u for u in assembly['units']}
    rows,roles=[],{}
    for identity,line,phrase,ranges in (
        (IDS[0],24,'Absatz (1)(b) und/oder (1)(c)',((126,46,75),(127,1,5))),
        (IDS[1],25,'Absatz (1)(a) und (1)(d) bis (g)',((126,44,45),(127,6,21))),
        (IDS[2],43,'Absatz (1)',((126,41,75),(127,1,23)))):
        u=raw[f'{KEY}:p127:l{line}']
        assert u['raw'].count(phrase)==1
        start=u['raw'].index(phrase)
        source=anchor(u,start,start+len(phrase))
        targets=[]
        for page,first,last in ranges:
            for n in range(first,last+1):
                target=raw[f'{KEY}:p{page}:l{n}']
                selected=units[target['id']]
                s=anchor(target,1 if page==126 and n==41 else 0)
                expected_role='UNKNOWN' if page==127 and 12<=n<=16 else 'OPERATIVE'
                assert selected['role']==expected_role and selected['text']==s['quote']
                assert segments(graph,selected,_raw=raw)==[{'source':s,'start':0,'end':len(s['quote'])}]
                roles[target['id']]=expected_role
                targets.append({'source':s,'use':target['id'],'language':target['language']})
        rows.append({'id':identity,'form':'relative','source':source,'from_use':u['id'],
            'language':u['language'],'targets':targets,'authority':source,'questions':['Q1','Q2'],
            'discovery_ids':[],'reason':'Complete original default paragraph targets; source identification does not decide unresolved default(f) meaning, actual default, cure, notice or quorum.'})
        assert not any(r['unit']==u['id'] for r in graph['references'])
    packet={'version':'reviewed-references.v2','assembly_sha256':digest(assembly),
        'review':{'reviewer':'Codex original pages126-127','kind':'DEVELOPMENT','reason':'Complete default targets and retained unknown meanings'},'references':rows}
    try:admit(graph,assembly,packet,_lookup=_DependencyLookup(graph,assembly))
    except ValueError as exc:
        assert 'not operative' in str(exc)
        refusal=str(exc)
    else:raise AssertionError('Expected v2 full-target refusal absent')
    malformed=deepcopy(packet)
    malformed['references'][0]['targets']=rows[0]['targets'][:-5]
    malformed['references'][1]['targets']=[r for r in rows[1]['targets'] if roles[r['use']]!='UNKNOWN']
    malformed['references'][2]['targets']=[r for r in rows[2]['targets'][:-2] if roles[r['use']]!='UNKNOWN']
    deps,_=admit(graph,assembly,malformed,_lookup=_DependencyLookup(graph,assembly))
    assert all(d['status']=='RESOLVED' for d in deps)
    packet['version']='reviewed-references.v3'
    printed=read(ROOT/'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    images={k:v for k,v in printed['images'].items() if k.endswith(('base-126.png','base-127.png'))}
    assert len(images)==2
    for name,checksum in images.items():assert sha(ROOT/name)==checksum
    for source in printed['sources']:assert sha(ROOT/source['path'])==source['sha256']
    contexts=[anchor(raw[f'{KEY}:p{page}:l{line}']) for page,line in ((126,40),(127,24),(127,42),(127,46),(127,53))]
    spec={'version':'basf-default-references.v1','sources':printed['sources'],'references':rows,
        'target_roles':roles,'contexts':contexts,'images':images,'automatic_discovery':False}
    save(PREP/'source-review.json',spec)
    save(SPEC,spec)
    save(PREP/'packet.json',packet)
    ledger=read(AUTH/'attempts/basf-references/attempt-016/candidate-answer-reconciliation.json.gz')
    for idx,row in zip((30,31,32),rows):
        record=next(r for r in ledger['records'] if r['family']=='historical_candidate_lines' and r['index']==idx)
        assert record['current_reference'] is None
        record['current_reference']=row
        record['current_status']='CURRENT_REVIEWED_LINK' if idx==30 else 'CURRENT_LINK_AND_UNRESOLVED_TARGET_MEANING'
    save(PREP/'reconciliation-proposed.json.gz',ledger)
    save(PREP/'pre-repair.json',{'complete_v2_refusal':refusal,'truncated_statuses':[d['status'] for d in deps],
        'lost_cross_page_qualification':True,'lost_default_f':True,'lost_cure':True,
        'baseline_products_sha256':digest(p),'baseline_answer_sha256':digest(a)})
    for name in ('src/legalmath/prospectus/successor/reviewed_references.py','src/legalmath/prospectus/successor/service.py'):
        dest=PREP/'pre-edit'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes())
    return {'status':'PASS','new_source_links':3,'target_lines':[35,18,58],'unknown_target_uses':5,
        'complete_v2_refused':True,'generic_truncation_accepted':True,'original_inventory_records':60}


def main():
    began=time.monotonic()
    save(PREP/'preparation-v2-started.json',{'command':sys.argv,'stage_bound_seconds':90,
        'started_at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU;GPU deliberately hidden'})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Default preparation90s')))
    signal.alarm(90)
    try:
        result={**prepare(),'wall_seconds':time.monotonic()-began}
        save(PREP/'preparation-v2-result.json',result)
        print(json.dumps(result))
    except BaseException as exc:
        save(PREP/'preparation-v2-failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-began})
        raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
