"""Bounded full archive consumers using typed lossless product deltas."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts import prospectus_archive_consumer_execution as old
from scripts.prospectus_typed_delta import changes, apply, equal, self_check
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as adigest
from legalmath.prospectus.successor import service, corrections, archive_observations
from legalmath.prospectus.successor.contracts import digest

PLAN = 'docs/plans/prospectus-archive-lossless-repair-2026-10-18.md'
SCRIPT = 'scripts/prospectus_archive_lossless.py'
DELTA = 'scripts/prospectus_typed_delta.py'
REVIEW = REL + '/reviews/archive-lossless-267'
ATTEMPT = REL + '/attempts/source-authority/attempt-008'
PRIOR = REL + '/attempts/source-authority/attempt-007'
PROPOSAL = REL + '/proposals/archive-lossless-267.json'
ROUTES = REL + '/closure-routes-2026-10-18-archive-lossless-267.json'
BOUNDS = {'preparation_seconds': 60, 'stage_seconds': 240, 'new_seconds': 560,
    'aggregate_accounted_seconds': 1100, 'new_bytes': 40*1024**2,
    'aggregate006plus_bytes': 180*1024**2, 'reserve_bytes': 2*1024**2}
require = old.require


def budget():
    names = {PLAN, SCRIPT, DELTA, PROPOSAL, ROUTES, REL + '/revisions/0267.json'}
    files = {ROOT / p for p in names}
    files |= {p for f in (ROOT / REVIEW, ROOT / ATTEMPT) for p in f.rglob('*') if p.is_file()}
    added = sum(p.stat().st_size for p in files if p.is_file())
    prior = read(ROOT / old.ACQUISITION / 'result.json')['budget']['retained_bytes_before_seal']
    for f in (ROOT / PRIOR, ROOT / old.REVIEW, ROOT / REL / 'reviews/source-archive-consumers-265'):
        prior += sum(p.stat().st_size for p in f.rglob('*') if p.is_file())
    prior += sum((ROOT / n).stat().st_size for n in (old.PROPOSAL, old.ROUTES,
        REL + '/proposals/source-archive-consumers-265.json', REL + '/revisions/0265.json', REL + '/revisions/0266.json'))
    require(added < BOUNDS['new_bytes']-BOUNDS['reserve_bytes'], 'New archive storage ceiling')
    require(added+prior < BOUNDS['aggregate006plus_bytes']-BOUNDS['reserve_bytes'], 'Cumulative archive storage ceiling')
    return {'new_bytes': added, 'aggregate006plus_bytes': added+prior}


def prepare():
    tick = time.monotonic()
    auth = Authority(ROOT)
    base, tasks, _ = auth.spec()
    require(base['revision'] == 266, 'Wrong lossless repair baseline')
    event = next(e for e in reversed(auth.events()) if e.get('task') == 'source-authority')
    require(event['kind'] == 'REJECT' and event['attempt'] == PRIOR, 'Preserve failed007 first')
    old.frozen()
    manifest = read(ROOT / PRIOR / 'outputs.json')
    require(all(file_hash(ROOT / PRIOR / n) == h for n, h in manifest.items()), 'Partial attempt changed')
    count = self_check()
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    files = set(old.inputs()) | {PLAN, SCRIPT, DELTA, old.PLAN, old.SCRIPT,
        PRIOR + '/outputs.json', PRIOR + '/result.json', PRIOR + '/report-2008/prior-query.json.gz',
        old.REVIEW + '/frozen.json', old.REVIEW + '/preparation.json'}
    files |= set(read(ROOT / old.REVIEW / 'frozen.json')['inputs'])
    methods = read(ROOT / old.REVIEW / 'frozen.json')['methods']
    files |= set(methods)
    frozen = {n: file_hash(ROOT / n) for n in sorted(files)}
    write(folder / 'frozen.json', frozen, exclusive=True)
    new = deepcopy(base)
    new['revision'] = 267
    task = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    task.update(dossier=PLAN, reason='Repair reproduced duplicated archive evidence once; reuse first completed case and finish exact consumers',
                archive_lossless={'version':'archive-lossless.v1','review':REVIEW,'bounds':BOUNDS})
    task['inputs'] = sorted(set(task['inputs']) | files | {REVIEW+'/frozen.json', REVIEW+'/preparation.json'})
    attempts = [e['attempt'] for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
    require(len(attempts)==base['budgets'][task['budget_key']]['maximum_new_attempts']==7, 'Original admission lineage differs')
    new['budgets'][task['budget_key']]['maximum_new_attempts'] = 8
    routes = read(ROOT / base['continuation_review']['routes'])
    routes['baseline_revision'] = 267
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=adigest(task), dossier=PLAN, mode='local', phase=0,
                remaining=task['reason'], next_action='Finish exact source consumers; further harness failure routes to independent substantive source task',
                stop_condition=BOUNDS)
    write(ROOT / ROUTES, routes, exclusive=True)
    new['continuation_review'].update(plan=PLAN, routes=ROUTES)
    for n in (PLAN,SCRIPT,DELTA,ROUTES): new['continuation_review']['bindings'][n]=file_hash(ROOT/n)
    seconds = time.monotonic()-tick
    require(seconds<60, 'Preparation ceiling')
    write(folder/'preparation.json', {'status':'PASS','seconds':seconds,'typed_delta_roundtrips':count,
        'prior_accounted_seconds':229.325846+29.043038407806307+5.87290280777961+240,
        'historical_unmeasured_overhead':'UNKNOWN','failed_attempt_retained':PRIOR}, exclusive=True)
    review={'baseline':adigest(base),'changes':task['reason'],'scope_unchanged':True,'budget_unchanged':False,
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'reproduced_cause':'Repeated complete clauses/questions in first12.5MB compressed output'},
        'evidence_contract':{'question':'Complete exact source archive cases without duplicate evidence',
            'baseline':[old.PT08,old.PT09,PRIOR],'primary':'Typed lossless complete equality, date classifications and all16 real refusals',
            'veto':'Source drift, invalid comparison, incomplete controls or exhausted bound',
            'not_concluded':['authenticity','publication','legal availability','whole task']},
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':7,'new_maximum':8,
            'retained_attempts':attempts,'reason':task['reason'],'next_discriminating_check':'Lossless complete source answers and original date/control matrix',
            'stop_condition':BOUNDS,'same_scope_authorization':'User-authorized build continuation; bounded local harness repair'}}
    auth.validate_program(new)
    write(ROOT/PROPOSAL,new,exclusive=True); write(folder/'review.json',review,exclusive=True)
    print({'revision':267,'seconds':seconds,'roundtrips':count},flush=True)


def freeze():
    for n,h in read(ROOT/REVIEW/'frozen.json').items():
        require(file_hash(ROOT/n)==h, 'Lossless frozen method/input changed: '+n)


def build(original, known, packet=None):
    req=deepcopy(original['P1']['payload']['request'])
    graph={**original['P1']['payload']['graph']}
    req['bundle']['known_at']=known
    graph['context']={**graph['context'],'known_at':known}
    graph['bundle_sha256']=digest(req['bundle'])
    if 'correction_admission' in req:
        previous=graph.pop('corrections')
        req['correction_admission']['graph_sha256']=digest(graph)
        graph['corrections']=corrections.admit(graph,req['correction_admission'])
        equal(previous['entries'],graph['corrections']['entries'],'Corrections changed')
    req['source_report_readings']['graph_sha256']=digest(graph)
    if packet is not None: req['archive_observations']=packet
    p1=service.seal('P1',req['bundle'],{'request':digest(req)},{'request':req,'graph':graph})
    p2=service.construction_product(p1,ROOT)
    ip=deepcopy(original['P3']['payload']['interpretation_input'])
    ip['source_report_scope']['readings_sha256']=digest(p2['payload']['source_report_readings'])
    p3=service.interpretation_product(p1,p2,ip)
    a,b=original['P4']['payload'],original['P5']['payload']
    ps={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3,a.get('cases'),a.get('law_input')),
        'P5':service.financial_product(p1,p2,p3,b.get('cases'),b.get('scenario_input'))}
    return ps,service.consume(ps,ROOT)


def check_pair(base,candidate,before,after,packet):
    equal(base['P2']['payload'],{k:v for k,v in candidate['P2']['payload'].items() if k!='archive_observations'},'Construction changed')
    for s in ('P3','P4','P5'): equal(base[s]['payload'],candidate[s]['payload'],s+' unrelated payload changed')
    stripped={k:v for k,v in after.items() if k!='source_archive_observations'}
    stripped['source_reports']=[{k:v for k,v in r.items() if k!='archive_observations'} for r in after['source_reports']]
    for k in ('consumed_products','request_sha256','report_sha256'): stripped[k]=before[k]
    equal(stripped,before,'Unrelated whole answer changed')
    row=packet['captures'][0]; dt=datetime.fromisoformat
    known=candidate['P1']['payload']['request']['bundle']['known_at']
    expected=('EVIDENCE_NOT_YET_KNOWN' if dt(known)<dt(row['retrieved_at']) else
        'NOT_ESTABLISHED_BY_THIS_CAPTURE' if dt(packet['query_at'])<dt(row['capture_at']) else 'ARCHIVE_RECORDED_BY_QUERY_DATE')
    obs,=after['source_archive_observations']['observations']
    require(obs['as_of_query']==expected,'Independent date ordering failed')
    require(obs['publication_date']==obs['edition_authenticity']=='UNKNOWN','Source unknown promoted')
    require(obs['legal_availability_established'] is False and obs['earlier_absence_established'] is False,'Archive overclaim')
    require(len(after['source_reports'])>=2 and all(r['archive_observations']==[obs] for r in after['source_reports']),'Original reports omitted')
    require(after['may_execute_transaction'] is False and after['independent_legal_acceptance'] is False,'Authority promotion')
    return expected


def encode(before,after):
    delta=changes(before,after)
    restored=apply(before,delta)
    equal(restored,after,'Lossless reconstruction differs')
    actual_hash=digest(after)
    require(digest(restored)==actual_hash,'Canonical complete reconstruction hash differs')
    return {'delta':delta,'complete_sha256':actual_hash}


def reuse(original):
    record=old.load(ROOT/PRIOR/'report-2008/prior-query.json.gz')
    for name in ('baseline','candidate'):
        packed=record[name]
        ps=packed['products']
        for ref in packed['references'].values():
            oldnode,node=original,ps
            for k in ref['path'][:-1]: oldnode,node=oldnode[k],node[k]
            key=ref['path'][-1]
            require(digest(oldnode[key])==ref['sha256'],'Retained large reference differs')
            node[key]=oldnode[key]
        require(digest(ps)==packed['complete_sha256'],'Completed case reconstruction differs')
        for s,p in ps.items(): service.verify(p,s)
        record[name]=ps
    packet=record['candidate']['P1']['payload']['request']['archive_observations']
    check_pair(record['baseline'],record['candidate'],record['baseline_answer'],record['candidate_answer'],packet)
    return record


def controls(base,candidate,packet):
    bundle=candidate['P1']['payload']['request']['bundle']
    results=[]
    for name in ('document','source-hash','record-index','capture-date','retrieval-date','content-binding'):
        p=deepcopy(packet); r=p['captures'][0]
        key,value={'document':('document','wrong-edition'),'source-hash':('source_sha256','0'*64),
            'record-index':('record_index',True),'capture-date':('capture_at','2011-01-01T00:00:00+00:00'),
            'retrieval-date':('retrieved_at','2011-01-01T00:00:00+00:00'),'content-binding':('content',{'path':r['content']['path'],'sha256':'0'*64})}[name]
        r[key]=value
        try: archive_observations.admit(bundle,p,ROOT)
        except ValueError as error: results.append({'case':name,'rejected':True,'reason':str(error)})
        else: raise ValueError('Invalid archive packet accepted: '+name)
    payload={**candidate['P2']['payload'],'archive_observations':deepcopy(candidate['P2']['payload']['archive_observations'])}
    payload['archive_observations']['observations'][0]['publication_date']='2011-01-01'
    cases=[('resealed-publication',{**candidate,'P2':service.seal('P2',bundle,{'P1':candidate['P1']['sha256']},payload)}),
        ('observation-without-request',{**base,'P2':service.seal('P2',base['P1']['payload']['request']['bundle'],
            {'P1':base['P1']['sha256']},candidate['P2']['payload'])})]
    for name,ps in cases:
        try: service.consume(ps,ROOT)
        except ValueError as error:
            require('Archive observation' in str(error),'Wrong adverse rejection reason')
            results.append({'case':name,'rejected':True,'reason':str(error)})
        else: raise ValueError('Forged archive observation accepted')
    return results


def run(year):
    tick=time.monotonic()
    def expired(_a,_b): raise TimeoutError('Lossless archive report ceiling')
    signal.signal(signal.SIGALRM,expired); signal.alarm(240)
    folder=ROOT/ATTEMPT/('report-'+year); folder.mkdir(exist_ok=False)
    result={'status':'FAIL','year':year}
    try:
        auth=Authority(ROOT); p,t,_=auth.spec(); adm=read(ROOT/ATTEMPT/'admission.json')
        require(adm['program_sha256']==adigest(p) and adm['binding']==auth.binding(t['source-authority']),'Admission drift')
        freeze(); budget()
        original,retained=old.original(year); original_hash=digest(original)
        before=old.reference_answer(retained)
        equal(service.consume(original,ROOT),before,'Original full consumer changed')
        doc,=original['P1']['payload']['request']['bundle']['documents']
        packet=old.packet(year,doc['id']); r=packet['captures'][0]
        known=datetime.fromisoformat(r['retrieved_at']); capture=datetime.fromisoformat(r['capture_at'])
        outcomes=[]; cache={}
        if year=='2008':
            previous=reuse(original); cache[known.isoformat()]=(previous['baseline'],previous['baseline_answer'])
            old.save(folder/'prior-query.json.gz',{'retained_case':PRIOR+'/report-2008/prior-query.json.gz',
                'sha256':file_hash(ROOT/PRIOR/'report-2008/prior-query.json.gz'),'verified_complete_reconstruction':True})
            outcomes.append({'case':'prior-query','expected':'NOT_ESTABLISHED_BY_THIS_CAPTURE','reused_complete_case':True})
            print({'year':year,'case':'prior-query','status':'VERIFIED_REUSE'},flush=True)
        cases=[('prior-query',known,capture-timedelta(seconds=1)),('at-capture',known,capture),
            ('before-knowledge',known-timedelta(microseconds=1),capture),
            ('2011-query',known,datetime(2011,7,15,tzinfo=timezone.utc))]
        for name,k,q in cases:
            if year=='2008' and name=='prior-query': continue
            key=k.isoformat()
            if key not in cache: cache[key]=build(original,key)
            base,baseline=cache[key]
            pk=deepcopy(packet); pk['query_at']=q.isoformat()
            candidate,answer=build(original,key,pk)
            expected=check_pair(base,candidate,baseline,answer,pk)
            old.save(folder/(name+'.json.gz'),{'original_products_sha256':original_hash,
                'original_answer_sha256':before['report_sha256'],
                'baseline':encode(original,base),'candidate':encode(original,candidate),
                'baseline_answer':encode(before,baseline),'candidate_answer':encode(before,answer),'expected':expected})
            outcomes.append({'case':name,'expected':expected,'answer_sha256':answer['report_sha256']})
            budget(); print({'year':year,'case':name,'status':'PASS'},flush=True)
        adversaries=controls(base,candidate,pk)
        old.save(folder/'adverse.json',adversaries)
        require(digest(original)==original_hash,'Immutable original changed in memory')
        freeze()
        result.update(status='PASS',cases=outcomes,adverse_cases=len(adversaries),source_document=doc['id'],
            complete_original_answer_equal=True,storage=budget(),current_extraction_claimed=False)
    except Exception as error: result.update(error=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0); result.update(seconds=time.monotonic()-tick,environment=sys.executable,
            cpu_gpu='CPU only; GPU intentionally hidden before imports',seeds='N/A deterministic',plan=PLAN,
            command=['.venv/bin/python','-m','scripts.prospectus_archive_lossless','run','--year',year],
            recorded_at=datetime.now(timezone.utc).isoformat())
        write(folder/'result.json',result,exclusive=True)
    print({k:result[k] for k in ('status','year','seconds')}|{'error':result.get('error')},flush=True)
    return 0 if result['status']=='PASS' else 1


def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=('prepare','run')); p.add_argument('--year',choices=('2008','2009')); a=p.parse_args()
    if a.action=='prepare': prepare(); return 0
    return run(a.year)


if __name__=='__main__': raise SystemExit(main())
