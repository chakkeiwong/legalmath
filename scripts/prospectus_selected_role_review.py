"""Source packet for exact selected header-role review; no production mutation."""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_question_integrity as prior
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;BASE=prior.BASE
PREP=AUTH/'reviews/selected-role-review-294'
HERE=AUTH/'attempts/basf-references/attempt-035'
METHOD='scripts/prospectus_selected_role_review.py'
PLAN='docs/plans/prospectus-selected-source-role-reconciliation-2026-10-18.md'
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_034_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for f in (PREP,HERE) for p in f.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (METHOD,PLAN))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0294.json')
    size=start['prior_resources']['cumulative026_034_bytes']+start['prior_extra_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<3600 and size<380*1024**2,'Cumulative source-review bound'
    return {'cumulative026_035_measured_seconds':seconds,'cumulative026_035_bytes':size,
        'seconds_bound':3600,'bytes_bound_including_4MiB_reserve':384*1024**2,
        'prior_costs_reset':False,'manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior_resources']['prior_unmeasured_preparation']}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==293
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==34 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for name,value in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/name)==value,name
    assert read(prior.HERE/'valid.json')['complete_answer_equal031']
    helper=ROOT/'scripts/prospectus_question_integrity_solver_check.py'
    receipt=read(prior.HERE/'stages/solver-compatibility/result.json')
    assert sha(helper)==receipt['method_sha256']
    save(PREP/'accounting-start.json',{'prior_resources':prior.costs(),'prior_extra_bytes':helper.stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    bindings={n:sha(ROOT/n) for n in (*CODE,METHOD,PLAN,prior.SERVICE,prior.METHOD)}
    for folder,names in ((BASE,('complete-products.json.gz','complete-expected-answer.json.gz','complete-inputs.json','outputs.json')),
                         (prior.HERE,('outputs.json',)),(prior.prior.HERE,('exceptional-source-readings.json.gz','source-analysis.json','outputs.json'))):
        bindings.update({rel(folder/n):sha(folder/n) for n in names})
    bindings[rel(PREP/'METHOD-REVIEW.md')]=sha(PREP/'METHOD-REVIEW.md')
    save(PREP/'freeze.json',{'bindings':bindings,'pdftoppm_sha256':sha(Path('/usr/bin/pdftoppm'))})
    proposal=deepcopy(program);proposal['revision']=294
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Review actual selected structural source and bound-profile consequences before legal-role migration',
        selected_role_review={'review':rel(PREP),'production_changes':False,'original_task_complete':False,
            'seconds_bound_cumulative026':3600,'bytes_bound_with_reserve':384*1024**2})
    proposal['budgets']['basf-references']['maximum_new_attempts']=35
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=294
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Read original layout and every affected source clause; retain concrete migration plan and explicit remaining-resource decision',
            stop_condition='35 admissions;180s stages;3600s cumulative026 onward;384MiB with4MiB reserve')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    resources=costs();forecast={'seconds':resources['cumulative026_035_measured_seconds']+40,
        'bytes':resources['cumulative026_035_bytes']+3*(AUTH/'program.json').stat().st_size+8*1024**2,'estimate_only':True}
    assert forecast['seconds']<3600 and forecast['bytes']<380*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Actual source-role review before implementation; original obligations preserved','Admission34 to35; cumulative time and storage unchanged'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Every proposed structural unit tied to inspected PDF layout and source; all affected nodes and profile bindings retained',
            'promotion_veto':['Lost substantive text','Unreviewed heading inference','Scope exclusion from membership alone'],
            'continuation_veto':['Missing exact provenance','Changed source','Exhausted limits'],
            'explanatory_only':['Counts','Time'],'not_concluded':['Legal completion','Automatic role recognition']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':34,'new_maximum':35,'retained_attempts':attempts,
            'reason':'Question consistency repaired; return to44 selected structural source candidates',
            'next_discriminating_check':'Original layout, mixed-clause inventory and precise migration consequences',
            'stop_condition':'180s stages;3600s cumulative;384MiB including4MiB reserve',
            'same_scope_authorization':'User requested refreshed master and continued internally supported general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':294,'forecast':forecast}


def frozen():
    admission=read(HERE/'admission.json')
    assert adigest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,value in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/name)==value,name
    assert sha(Path('/usr/bin/pdftoppm'))==read(PREP/'freeze.json')['pdftoppm_sha256']


def packet():
    p=read(BASE/'complete-products.json.gz')
    readings=read(prior.prior.HERE/'exceptional-source-readings.json.gz')
    withheld={'p127:l12','p127:l13','p127:l14','p127:l15','p127:l16','p124:l43','p124:l44'}
    candidates=[r for r in readings['selected_unknown_units'] if r['unit']['unit'].split(':',1)[1] not in withheld]
    assert len(candidates)==44
    ids={r['unit']['unit'] for r in candidates}
    nodes=p['P3']['payload']['clauses']['nodes']
    affected=[{'index':i,'node':n,'only_candidate_units':set(n['units'])<=ids} for i,n in enumerate(nodes) if ids.intersection(n['units'])]
    raw={u['id']:u for u in p['P1']['payload']['graph']['units']}
    for row in candidates:
        for segment in row['exact_segments']:
            source=segment['source'];u=raw[source['unit']]
            assert u['raw'][source['start']:source['end']]==source['quote']
            assert row['unit']['text'][segment['start']:segment['end']]==source['quote']
    doc=next(d for d in p['P1']['payload']['request']['bundle']['documents'] if d['id']=='basf-base-september-2022-exchange')
    assert sha(ROOT/doc['path'])==doc['sha256']
    pages=sorted({r['unit']['source']['page'] for r in candidates})
    assert len(pages)<=14
    renders=[]
    for page in pages:
        target=HERE/'pages'/('base-'+str(page));target.parent.mkdir(parents=True,exist_ok=True)
        command=['/usr/bin/pdftoppm','-f',str(page),'-l',str(page),'-singlefile','-scale-to','1600','-png',str(ROOT/doc['path']),str(target)]
        started=time.monotonic()
        result=subprocess.run(command,capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stderr
        renders.append({'page':page,'path':rel(target.with_suffix('.png')),'sha256':sha(target.with_suffix('.png')),
            'command':command,'wall_seconds':time.monotonic()-started})
    assembly=p['P2']['payload']['assembly'];old_digest=digest(assembly)
    bindings=[]
    def walk(value,path):
        if isinstance(value,dict):
            for k,v in value.items():walk(v,path+[k])
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,path+[i])
        elif value==old_digest:bindings.append(path)
    walk(p,[])
    save(HERE/'source-packet.json.gz',{'candidates':candidates,'affected_clauses':affected,
        'protected_unknown_ids':['basf-base-september-2022-exchange:'+i for i in sorted(withheld)],
        'direct_assembly_bindings':bindings,'source_document':doc,'renders':renders,
        'original_header_objects':readings['missing_selected_occurrences'],
        'production_changes':False,'roles_changed':False})
    save(HERE/'summary.json',{'candidates':len(candidates),'pages':pages,'affected_nodes':len(affected),
        'mixed_nodes':sum(not r['only_candidate_units'] for r in affected),
        'assembly_binding_paths':bindings,'source_sha256':doc['sha256'],'production_changes':False})
    return {'status':'PASS','candidates':len(candidates),'pages':len(pages),'affected_nodes':len(affected),
        'mixed_nodes':sum(not r['only_candidate_units'] for r in affected)}


def seal():
    review=read(HERE/'source-review.json');assert review['status']=='PASS'
    assert review['source_packet_sha256']==sha(HERE/'source-packet.json.gz')
    assert review['next_plan'] and (ROOT/review['next_plan']).is_file()
    save(HERE/'result.json',{'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SELECTED_STRUCTURAL_SOURCE_REVIEW','summary':read(HERE/'summary.json'),
        'review':review,'resources':costs(),'production_changes':False})
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in ('packet','seal')],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':read(HERE/'summary.json')['source_sha256'],
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json'),'manual_source_reading_seconds':'UNKNOWN'})
    return {'status':'PASS','source_review_retained':True,'original_task_complete':False,'resources':costs()}


def main():
    stage=sys.argv[1];assert stage in ('prepare','packet','seal')
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_selected_role_review',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Role review stage bound')));signal.alarm(180)
    try:
        if stage!='prepare':frozen()
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-started);result['wall_seconds']=time.monotonic()-started;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
