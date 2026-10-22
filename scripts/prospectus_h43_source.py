"""Bounded H43 source preparation; no production or historical-law promotion."""
from copy import deepcopy
from datetime import datetime, timezone
import json, re, resource, signal, subprocess, sys, time
from scripts import prospectus_affiliate_substitution as prior
from scripts.prospectus_statutory_sources_accounted import SourceHTML
from legalmath.prospectus.execution_authority import Authority, CODE, digest

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH/'reviews/h43-source-319'
HERE = AUTH/'attempts/basf-references/attempt-058'
PLAN = 'docs/plans/prospectus-h43-source-2026-10-19.md'
METHOD = 'scripts/prospectus_h43_source.py'
CONTRACT = 'docs/implementation/prospectus-basf-reference-repair/source-review-002/basf-base-september-2022-exchange.txt'
LEDGER = AUTH/'attempts/basf-references/attempt-025/original-ledger-reconciliation.json.gz'
URLS = {'section':'https://www.gesetze-im-internet.de/wphg/__50.html',
        'index':'https://www.gesetze-im-internet.de/wphg/index.html'}
read,save,sha,rel = prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior']['combined_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/p for p in (PLAN,METHOD));paths.add(AUTH/'revisions/0319.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<12600 and size<2044*1024**2
    assert seconds-start['prior']['combined_measured_seconds']<120
    assert size-start['prior']['combined_bytes']<16*1024**2
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'new_GETs':len(list(HERE.glob('requests/*/started.json'))),'maximum_new_GETs':2,
        'historical_GETs_reset':False,'unmeasured_authoring_and_older_time':'UNKNOWN'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==318
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==57
    assert [e['kind'] for e in events if e.get('attempt')==rel(prior.HERE)][-1]=='RECORD'
    for name,checksum in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/name)==checksum,name
    save(PREP/'accounting-start.json',{'prior':prior.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    bindings={p:sha(ROOT/p) for p in (*CODE,PLAN,METHOD,CONTRACT,
        'scripts/prospectus_statutory_sources_accounted.py',prior.METHOD)}
    for p in (LEDGER,prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',PREP/'accounting-start.json'):
        bindings[rel(p)]=sha(p)
    save(PREP/'freeze.json',{'bindings':bindings,'requests':URLS})
    proposal=deepcopy(program);proposal['revision']=319
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=PLAN,
        reason='Investigate original H43 source and edition separately from source receipt and legal application',
        h43_source={'review':rel(PREP),'original_task_complete':False,'production_changes':False,
            'maximum_new_GETs':2,'combined_seconds':12600,'combined_bytes':2048*1024**2})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=58
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=319
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=digest(task),
            next_action='Retain and inspect H43 primary source; review conditional downstream integration after source preparation',
            stop_condition='58 admissions;30s stages;120s/16MiB new;combined12600s/2048MiB;two added H43 GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+120,
              'bytes':costs()['combined_bytes']+16*1024**2,'estimate_only':True}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Investigate original H43 missing source','Retain all costs and user deferrals'],
        'skeptical_audit':{'verdict':'PASS','review':PLAN,'forecast':forecast},
        'evidence_contract':{'primary':'Original context and retained official provision with edition uncertainty',
            'promotion_veto':['Wrong source','Incomplete provision','False historical applicability','False closure'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Actual publication','Historical applicability','Product integration','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':57,'new_maximum':58,
            'retained_attempts':attempts,'reason':'Original H43 absent from twelve retained statutory readings',
            'next_discriminating_check':'Official provision against complete contractual publication alternative',
            'stop_condition':'Two new GETs;120s/16MiB new;combined12600s/2048MiB;no unchanged retry',
            'same_scope_authorization':'User requests refreshed master and continued internal general build'},
        'acquisition_revision':{'added_H43_GETs':2,'historical_allowances_reset':False,
            'schvg_allowance_still_exhausted':True,'server_web_locator_calls_maximum':2},'resources':costs()}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':319,'forecast':forecast}


def frozen():
    admission=read(HERE/'admission.json')
    assert digest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,checksum in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/name)==checksum,name


def local():
    text=(ROOT/CONTRACT).read_text();lines=text.split('\n')
    start=sum(len(line)+1 for line in lines[:8043]);end=sum(len(line)+1 for line in lines[:8064])
    context=text[start:end]
    assert '§ 50 Absatz 1' in context and '(d) Bekanntmachung' in context
    ledger=read(LEDGER)
    row=next(r for r in ledger['records'] if r['family']=='historical_candidate_lines' and r['index']==43)
    save(HERE/'contract-context.json',{'path':CONTRACT,'sha256':sha(ROOT/CONTRACT),
        'start':start,'end':end,'quote':context,'original_H43':row,'original_inventory_count':len(ledger['records'])})
    roots=[ROOT/'.localresources',AUTH/'attempts/law-applicability',AUTH/'attempts/basf-references/attempt-023']
    pattern=re.compile(r'WpHG|Wertpapierhandelsgesetz',re.IGNORECASE)
    scanned,skipped,hits,total=0,0,[],0
    for folder in roots:
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in {'.txt','.html','.xml','.md'}:continue
            size=path.stat().st_size
            if size>2*1024**2 or total+size>50*1024**2 or scanned>=2000:skipped+=1;continue
            body=path.read_text(errors='replace');matches=list(pattern.finditer(body));scanned+=1;total+=size
            if matches:hits.append({'path':rel(path),'sha256':sha(path),'matches':len(matches),
                'snippets':[body[max(0,m.start()-90):m.end()+160] for m in matches[:3]]})
    save(HERE/'local-search.json',{'roots':[rel(p) for p in roots],
        'extensions':['.txt','.html','.xml','.md'],'scanned_files':scanned,'scanned_bytes':total,
        'skipped_by_bounds':skipped,'hits':hits,'exhaustive_local_absence_established':False})
    return {'status':'PASS','scanned_files':scanned,'matching_files':len(hits),'skipped':skipped}


def acquire(key):
    assert key in URLS and costs()['new_GETs']<2
    folder=HERE/'requests'/key;folder.mkdir(parents=True,exist_ok=False)
    command=['curl','--silent','--show-error','--proto','=https','--max-time','20',
        '--connect-timeout','8','--max-filesize','2097152','--dump-header',str(folder/'headers'),
        '--output',str(folder/'body'),'--write-out','%{json}',URLS[key]]
    save(folder/'started.json',{'command':command,'url':URLS[key],
        'started_at':datetime.now(timezone.utc).isoformat(),'redirects':False,'retries':0})
    def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**2,2*1024**2))
    result=subprocess.run(command,capture_output=True,timeout=25,preexec_fn=cap)
    (folder/'curl-metadata').write_bytes(result.stdout);(folder/'curl-stderr').write_bytes(result.stderr)
    try:metadata=json.loads(result.stdout)
    except (ValueError,UnicodeDecodeError):metadata={}
    available=result.returncode==0 and metadata.get('http_code')==200
    receipt={'status':'RESPONSE_RETAINED' if available else 'UNAVAILABLE_RESPONSE_RETAINED',
        'url':URLS[key],'effective_url':metadata.get('url_effective'),'http_code':metadata.get('http_code'),
        'exit_code':result.returncode,'finished_at':datetime.now(timezone.utc).isoformat(),
        'files':{p.name:sha(p) for p in folder.iterdir() if p.is_file()},'historical_application_proved':False}
    save(folder/'receipt.json',receipt)
    return {'status':'PASS','acquisition':receipt['status'],'key':key,
            'http_code':receipt['http_code'],'curl_exit_code':result.returncode}


def extract():
    sources=[]
    for key in URLS:
        folder=HERE/'requests'/key;receipt=read(folder/'receipt.json')
        for name,checksum in receipt['files'].items():assert sha(folder/name)==checksum
        if receipt['status']!='RESPONSE_RETAINED':continue
        parser=SourceHTML();parser.feed((folder/'body').read_bytes().decode('utf-8'))
        extracted=re.sub(r'\n[ \t]*\n+','\n\n',''.join(parser.text))
        (folder/'text.txt').write_text(extracted)
        save(folder/'extraction.json',{'method':'SourceHTML;UTF-8;blank-line-normalization',
            'raw_sha256':sha(folder/'body'),'text_sha256':sha(folder/'text.txt'),
            'links':parser.links,'historical_application_proved':False})
        sources.append({'key':key,'characters':len(extracted),'path':rel(folder/'text.txt')})
    return {'status':'PASS','sources':sources,'actual_source_review_pending':True}


def seal():
    note=HERE/'SOURCE-REVIEW.md';assert note.is_file() and note.stat().st_size>600
    for stage in ('local','acquire-section','acquire-index','extract'):
        assert read(HERE/'stages'/stage/'result.json')['status']=='PASS'
    result={'status':'PASS','task':'basf-references','result_kind':'H43_SOURCE_PREPARATION',
        'original_task_complete':False,'production_changed':False,'historical_application_proved':False,
        'downstream_integration_complete':False,'source_review':rel(note),'source_review_sha256':sha(note),
        'resources':costs(),'next_action':'Review H43 downstream use with retained sources and open edition/applicability'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p)['command'] for p in sorted(HERE.glob('stages/*/started.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic source preparation','data_version':sha(LEDGER),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    return result


def main():
    stage=sys.argv[1];assert stage in {'prepare','local','acquire-section','acquire-index','extract','seal'}
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':frozen();costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m',METHOD[:-3].replace('/','.'),stage],
        'started_at':datetime.now(timezone.utc).isoformat()})
    started=time.monotonic()
    def stop(signum,frame):raise TimeoutError('Reviewed30second stage bound')
    signal.signal(signal.SIGALRM,stop);signal.alarm(30)
    try:
        result=acquire(stage.removeprefix('acquire-')) if stage.startswith('acquire-') else globals()[stage]()
        result['wall_seconds']=time.monotonic()-started;costs(result['wall_seconds'])
        save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p)
            for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result))
    except Exception as exc:
        save(folder/'failure.json',{'status':'FAIL','type':type(exc).__name__,
            'message':str(exc),'wall_seconds':time.monotonic()-started});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
