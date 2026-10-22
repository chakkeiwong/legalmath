"""Bounded official source-history continuation; no production changes."""
from copy import deepcopy
from datetime import datetime,timezone
import json,os,resource,subprocess,sys,time
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';sys.dont_write_bytecode=True
from scripts import prospectus_predicate_reconciliation as previous
from legalmath.prospectus.execution_authority import Authority,CODE,digest
read,save,sha,rel=previous.read,previous.save,previous.sha,previous.rel
AUTH=previous.AUTH;PREP=AUTH/'reviews/schvg-history-298'
HERE=AUTH/'attempts/basf-references/attempt-039'
OLD=AUTH/'attempts/law-applicability/attempt-002'
PLAN='docs/plans/prospectus-schvg-history-chain-2026-10-19.md'
METHOD='scripts/prospectus_schvg_history.py'
HOSTS={'www.bundesfinanzministerium.de','www.bgbl.de','www.recht.bund.de',
       'www.gesetze-im-internet.de','www.bundestag.de','www.bundesbank.de'}

def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior']['cumulative026_038_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json','requests/*/receipt.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file()}
    paths.update(ROOT/n for n in (PLAN,METHOD))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0298.json')
    size=start['prior']['cumulative026_038_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<6000 and size<636*1024**2,'Cumulative026 historical-source bound'
    return {'cumulative026_039_measured_seconds':seconds,'cumulative026_039_bytes':size,
        'prior_costs_reset':False,'manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior']['prior_unmeasured_preparation'],
        'seconds_bound':6000,'bytes_bound_including_4MiB_reserve':640*1024**2}

def prepare():
    p=read(AUTH/'program.json');assert p['revision']==297
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==38 and any(e['kind']=='RECORD' and e.get('attempt')==rel(previous.HERE) for e in events)
    save(PREP/'accounting-start.json',{'prior':previous.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[x.name for x in (AUTH/'history').glob('*.json')]})
    bindings={n:sha(ROOT/n) for n in (*CODE,PLAN,METHOD,'scripts/prospectus_predicate_reconciliation.py')}
    for folder,names in ((previous.HERE,['outputs.json','result.json','gap-map.json']),
        (OLD,['outputs.json','schvg.html','schvg-utf8.txt','change2024.pdf','change2024.txt',
              'HISTORY-REVIEW.md','SOURCE-REVIEW.md','historical-reconstruction.json','result.json'])):
        manifest=read(folder/'outputs.json')
        for n in names:
            if n!='outputs.json':assert sha(folder/n)==manifest[n],n
            bindings[rel(folder/n)]=sha(folder/n)
    (PREP/'METHOD-REVIEW.md').write_text('''# Historical source-chain audit

PASS for original-source investigation only. The retained2024 act cites2021
as the preceding amendment. Acquire and inspect that exact act and effective
date; do not use current text as proof of2022 wording or legal application.
Compare lossless change operations and distinguish derived reconstruction from
an official historical consolidation. Existing legal/ratio/calendar trials stay
retained. Source authenticity and exact operations are primary;counts are not.

The existing512MiB bound cannot hold another10MiB proposal and revision plus
source evidence. Explicitly extend cumulative026 to640MiB and6000 measured
seconds,retaining all prior costs. One additional admission is necessary for
the same original task. At most8 GETs,no redirects/retries,20seconds each,
8MiB per response. No production changes,installation,adviser or real facts.
''')
    bindings[rel(PREP/'METHOD-REVIEW.md')]=sha(PREP/'METHOD-REVIEW.md')
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(p);proposal['revision']=298
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Acquire missing primary2021 SchVG amendment and establish supported historical source chain before application',
        schvg_history={'review':rel(PREP),'original_task_complete':False,'production_changes':False,
            'cumulative026_seconds':6000,'cumulative026_bytes_with_reserve':640*1024**2,'maximum_GETs':8})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=39
    routes=read(ROOT/p['continuation_review']['routes']);routes['baseline_revision']=298
    for r in routes['tasks']:
        if r['task']=='basf-references':r.update(dossier=PLAN,task_sha256=digest(task),
            next_action='Establish primary historical SchVG chain and conditional application evidence,then integrate supported dated rules',
            stop_condition='39 admissions;8 GETs;20second requests;6000s cumulative026;640MiB with4MiB reserve;no automatic retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_039_measured_seconds']+300,
        'bytes':costs()['cumulative026_039_bytes']+3*(AUTH/'program.json').stat().st_size+24*1024**2,'estimate_only':True}
    assert forecast['seconds']<6000 and forecast['bytes']<636*1024**2
    review={'baseline':digest(p),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Same-task historical statutory source work','Admission38 to39','Cumulative026 limits5400 to6000seconds and512 to640MiB;prior usage retained'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Official original bytes,exact relevant articles/effectivity and checked source-change derivation',
            'promotion_veto':['Wrong publication','Missing effective-date exception','Unexplained source delta','Unsupported application'],
            'continuation_veto':['Corrupt evidence','Method drift','Exhausted bounds'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Authenticated derivative','Actual resolution','Exhaustive law','Whole build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':38,'new_maximum':39,'retained_attempts':attempts,
            'reason':'Missing primary law history is substantive;source acquisition and authority snapshots need explicit additional allowance',
            'next_discriminating_check':'Original2021 article and effective date against2024 cited amendment chain',
            'stop_condition':'8 GETs;6000s cumulative026;640MiB including4MiB reserve;no unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continuing internally supported general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':298,'forecast':forecast}

def frozen():
    a=read(HERE/'admission.json');assert digest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n

def acquire(key,url,rationale):
    frozen();costs()
    parsed=urlsplit(url)
    assert parsed.scheme=='https' and parsed.hostname in HOSTS and not parsed.username and not parsed.password
    assert parsed.port in (None,443) and not parsed.fragment and rationale
    assert key.isascii() and key.replace('-','').isalnum()
    assert len(list((HERE/'requests').glob('*/started.json')))<8
    folder=HERE/'requests'/key;folder.mkdir(parents=True,exist_ok=False)
    cmd=['curl','--silent','--show-error','--proto','=https','--max-time','20','--connect-timeout','8',
        '--max-filesize',str(8*1024**2),'--dump-header',str(folder/'headers'),'--output',str(folder/'body'),'--write-out','%{json}',url]
    save(folder/'started.json',{'command':cmd,'rationale':rationale,'url':url,'started_at':datetime.now(timezone.utc).isoformat(),
        'automatic_retries':0,'redirects':False})
    start=time.monotonic()
    def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2))
    try:
        run=subprocess.run(cmd,capture_output=True,timeout=25,preexec_fn=cap)
        code,out,err=run.returncode,run.stdout,run.stderr
    except subprocess.TimeoutExpired as e:code,out,err=124,e.stdout or b'',e.stderr or b''
    (folder/'curl-metadata').write_bytes(out);(folder/'curl-stderr').write_bytes(err)
    try:meta=json.loads(out)
    except ValueError:meta={}
    result={'status':'RESPONSE_RETAINED' if code==0 else 'FAILED_RETAINED','curl_exit':code,
        'http_status':meta.get('http_code'),'content_type':meta.get('content_type'),'redirect_url':meta.get('redirect_url'),
        'body_bytes':(folder/'body').stat().st_size if (folder/'body').exists() else 0,
        'body_sha256':sha(folder/'body') if (folder/'body').exists() else None,'wall_seconds':time.monotonic()-start,
        'source_accepted':False,'acquired_at':datetime.now(timezone.utc).isoformat()}
    save(folder/'receipt.json',result);costs();return result

def main():
    if sys.argv[1]=='acquire':print(json.dumps(acquire(*sys.argv[2:5])));return
    assert sys.argv[1]=='prepare'
    folder=PREP/'stages/prepare';assert not (folder/'started.json').exists()
    save(folder/'started.json',{'command':sys.argv,'started_at':datetime.now(timezone.utc).isoformat()})
    start=time.monotonic()
    try:r=prepare();r['wall_seconds']=time.monotonic()-start;save(folder/'result.json',r);print(json.dumps(r))
    except BaseException as e:save(folder/'failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-start});raise

if __name__=='__main__':main()
