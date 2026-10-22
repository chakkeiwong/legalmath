"""One explicit continuation to a retained official PDF Location."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import json,resource,subprocess,time
from scripts import prospectus_schvg_history as prior
ROOT,AUTH,read,save,sha,rel=prior.ROOT,prior.AUTH,prior.read,prior.save,prior.sha,prior.rel
PREP=AUTH/'reviews/schvg-redirect-299';HERE=AUTH/'attempts/basf-references/attempt-040'
PLAN='docs/plans/prospectus-schvg-exact-redirect-2026-10-19.md'
METHOD='scripts/prospectus_schvg_exact_redirect.py'
URL='https://www.bgbl.de/xaver/bgbl/media/D87C77FB96FB51CAD96044EB2996A3C7/bgbl121s1423_79694.pdf'

def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_039_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json','requests/*/receipt.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file()}
    paths.update(ROOT/n for n in (PLAN,METHOD));paths.add(AUTH/'revisions/0299.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_039_bytes']+start['prior_extra_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<6000 and size<636*1024**2
    return {'cumulative026_040_measured_seconds':seconds,'cumulative026_040_bytes':size,'prior_costs_reset':False,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':start['prior']['prior_unmeasured_preparation'],
        'seconds_bound':6000,'bytes_bound_including_4MiB_reserve':640*1024**2,'cumulative_source_GETs':9}

def prepare():
    p=read(AUTH/'program.json');assert p['revision']==298
    events=prior.Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==39 and any(e['kind']=='REJECT' and e.get('attempt')==rel(prior.HERE) for e in events)
    assert read(prior.HERE/'result.json')['status']=='PARTIAL'
    extras=read(prior.HERE/'accounting-addendum.json')['extra_files']
    for row in extras:assert sha(ROOT/row['path'])==row['sha256']
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'prior_extra_bytes':sum(r['bytes'] for r in extras),
        'program_bytes':(AUTH/'program.json').stat().st_size,'history_names':[x.name for x in (AUTH/'history').glob('*.json')]})
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    header=prior.HERE/'requests/gazette-original-session/headers'
    assert 'Location: '+URL in header.read_text()
    bindings={n:sha(ROOT/n) for n in (*prior.CODE,PLAN,METHOD,'scripts/prospectus_schvg_history.py',rel(PREP/'PREPARATION-REPAIR.md'))}
    for path in (header,prior.HERE/'outputs.json',prior.HERE/'result.json',prior.HERE/'RESULT.md',prior.HERE/'accounting-addendum.json'):
        bindings[rel(path)]=sha(path)
    (PREP/'METHOD-REVIEW.md').write_text('''# Exact redirect continuation review

PASS for one changed official-source request to the retained302 Location.
The eight requests remain counted;one additional GET raises the bound to9.
No unchanged retry,redirect or new guessed URL. The same6000second/640MiB
cumulative026 ceilings apply. No production changes. Primary evidence is
matching original act bytes and complete relevant articles,not a download
status. Review source dates,scope and conditional application independently.
A refusal or wrong PDF ends this route;preserve historical uncertainty.
''')
    bindings[rel(PREP/'METHOD-REVIEW.md')]=sha(PREP/'METHOD-REVIEW.md');save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(p);proposal['revision']=299
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Follow exact official PDF redirect discovered by repaired anonymous archive session;preserve all earlier requests',
        schvg_redirect={'review':rel(PREP),'original_task_complete':False,'maximum_cumulative_GETs':9,
            'cumulative026_seconds':6000,'cumulative026_bytes_with_reserve':640*1024**2})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=40
    routes=read(ROOT/p['continuation_review']['routes']);routes['baseline_revision']=299
    for r in routes['tasks']:
        if r['task']=='basf-references':r.update(dossier=PLAN,task_sha256=prior.digest(task),
            next_action='Retrieve exact gazette PDF,review historical chain,then integrate supported conditional statutory applications',
            stop_condition='40 admissions;9 cumulative source GETs;6000s cumulative026;640MiB with4MiB reserve')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_040_measured_seconds']+150,
        'bytes':costs()['cumulative026_040_bytes']+3*(AUTH/'program.json').stat().st_size+10*1024**2,'estimate_only':True}
    assert forecast['seconds']<6000 and forecast['bytes']<636*1024**2
    review={'baseline':prior.digest(p),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Follow exact retained302 Location','Admission39 to40 and cumulativeGET8 to9;time/storage ceilings unchanged'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Authenticated exact original act and checked historical change derivation',
            'promotion_veto':['Wrong PDF','Unsupported historical/legal inference'],'continuation_veto':['Failed exact source route','Method drift','Exhausted limits'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Actual resolution','Exhaustive law','Whole task completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':39,'new_maximum':40,'retained_attempts':attempts,
            'reason':'Exact official download location emerged on last allowed request;one explicit follow-up',
            'next_discriminating_check':'Authenticate original PDF at exact retained Location','stop_condition':'One GET;6000s cumulative026;640MiB',
            'same_scope_authorization':'User requested continued internally supported general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review);return {'status':'PASS','revision':299,'forecast':forecast}

def frozen():
    a=read(HERE/'admission.json');assert prior.digest(read(AUTH/'program.json'))==a['program_sha256']
    assert prior.Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n

def acquire():
    frozen();costs();folder=HERE/'requests/original';folder.mkdir(parents=True,exist_ok=False)
    cmd=['curl','--silent','--show-error','--proto','=https','--max-time','20','--connect-timeout','8',
        '--max-filesize',str(8*1024**2),'--dump-header',str(folder/'headers'),'--output',str(folder/'body'),'--write-out','%{json}',URL]
    save(folder/'started.json',{'command':cmd,'started_at':datetime.now(timezone.utc).isoformat(),'automatic_retries':0,'redirects':False})
    begin=time.monotonic()
    def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2))
    try:r=subprocess.run(cmd,capture_output=True,timeout=25,preexec_fn=cap);code,out,err=r.returncode,r.stdout,r.stderr
    except subprocess.TimeoutExpired as e:code,out,err=124,e.stdout or b'',e.stderr or b''
    (folder/'curl-metadata').write_bytes(out);(folder/'curl-stderr').write_bytes(err)
    try:meta=json.loads(out)
    except ValueError:meta={}
    result={'status':'RESPONSE_RETAINED' if code==0 else 'FAILED_RETAINED','curl_exit':code,'http_status':meta.get('http_code'),
        'content_type':meta.get('content_type'),'body_bytes':(folder/'body').stat().st_size if (folder/'body').exists() else 0,
        'body_sha256':sha(folder/'body') if (folder/'body').exists() else None,'wall_seconds':time.monotonic()-begin,
        'source_accepted':False,'acquired_at':datetime.now(timezone.utc).isoformat()}
    save(folder/'receipt.json',result);costs();return result

def main():
    import sys
    if sys.argv[1]=='acquire':print(json.dumps(acquire()));return
    assert sys.argv[1]=='prepare-reviewed';folder=PREP/'stages/prepare-reviewed';assert not (folder/'started.json').exists()
    save(folder/'started.json',{'command':sys.argv});start=time.monotonic()
    try:r=prepare();r['wall_seconds']=time.monotonic()-start;save(folder/'result.json',r);print(json.dumps(r))
    except BaseException as e:save(folder/'failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-start});raise

if __name__=='__main__':main()
