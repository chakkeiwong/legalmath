"""Original-task Q1 scope repair with separate package and result directories."""
import argparse
from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from scripts.prospectus_fy2010_scope_program import require,read,sha,rel,save,inventory,authority

AUTH=ROOT/'docs/implementation/prospectus-execution-authority'
WORK=ROOT/'.localresources/prospectus-preparation/q1-scope'
PREP=AUTH/'reviews/q1-scope-437'
HERE=AUTH/'attempts/source-bes-dep-11/attempt-005'
OLD=AUTH/'attempts/source-bes-dep-11/attempt-004'
TASK='source-bes-dep-11'
SELF='scripts/prospectus_q1_scope_program.py'
PROBE='scripts/prospectus_q1_scope_probe.py'
PLAN='docs/plans/prospectus-q1-scope-reconciliation-2026-10-22.md'
TEST='tests/prospectus_successor/test_q1_statement_scope.py'
CHANGES=['prospectus/successor/bes_statement_scope.py','prospectus/successor/bes_q1_scope.py']
LIMITS={'bytes':256*1024**2,'reserve':2*1024**2,'seconds':600,'process_seconds':120,'unchanged_retries':0,'changed_recoveries':1}
SUCCESSFUL_CANDIDATE=WORK/'candidate-recovery-result'


def prepare():
    tick=time.monotonic(); a=authority(); p,_,_=a.spec()
    require(p['revision']==436 and not PREP.exists() and not HERE.exists(),'Fresh436required')
    require(read(WORK/'probe/result.json')['status']=='REPRODUCED','Actual financial-target omission required')
    event=next(e for e in reversed(a.events()) if e.get('task')=='source-bes-dep-08')
    require(event['kind']=='RECORD' and a.retained_evidence_valid(event),'Intact recorded436required')
    from scripts import prospectus_fy2010_scope_program as prior
    save(PREP/'accounting-start.json',{'prior436':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
         'program_bytes':(AUTH/'program.json').stat().st_size,'manual_time':'UNKNOWN','prior_source08_event':event['sha256']})
    shutil.copytree(ROOT/'src/legalmath',WORK/'candidate/src/legalmath',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    save(PREP/'baseline.json',{'production':inventory(ROOT/'src/legalmath'),'runtime':read(prior.PREP/'freeze.json')['runtime'],
         'seconds':time.monotonic()-tick})
    return {'status':'PREPARED'}


def costs():
    old=read(PREP/'accounting-start.json')
    paths={p for d in (WORK,PREP,HERE) if d.exists() for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths|={ROOT/n for n in (SELF,PROBE,PLAN,TEST)}|{ROOT/'src/legalmath'/n for n in CHANGES}|{AUTH/'revisions/0437.json'}
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in old['history_names'])
    size=sum(p.stat().st_size for p in paths if p.is_file())+max(0,(AUTH/'program.json').stat().st_size-old['program_bytes'])
    seconds=read(WORK/'probe/result.json')['seconds']+read(PREP/'baseline.json')['seconds']
    seconds+=sum(read(p)['seconds'] for d in (PREP,HERE) for p in d.glob('commands/*.json') if 'seconds' in read(p))
    return {'new_bytes':size,'new_measured_seconds':seconds,'prior':rel(PREP/'accounting-start.json'),'manual_time':'UNKNOWN',
            'limits':LIMITS,'allowed':size+LIMITS['reserve']<LIMITS['bytes'] and seconds<LIMITS['seconds']}


def command(name,argv,folder,seconds=120):
    usage=costs(); require(usage['allowed'] and usage['new_measured_seconds']+seconds<LIMITS['seconds'],'Resource ceiling')
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
         'PIP_NO_INDEX':'1','PIP_NO_CACHE_DIR':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    folder.mkdir(parents=True,exist_ok=True); tick=time.monotonic()
    with (folder/(name+'.log')).open('x') as log:
        child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        save(folder/(name+'-started.json'),{'argv':argv,'pid':child.pid,'time_ns':time.time_ns()})
        try: code=child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(); code=-1
    save(folder/(name+'.json'),{'argv':argv,'exit_code':code,'seconds':time.monotonic()-tick,
         'environment':{k:env[k] for k in ('CUDA_VISIBLE_DEVICES','PYTHONPATH','PIP_NO_INDEX')}})
    require(code==0,'Inspect retained '+name+' failure'); require(costs()['allowed'],'Post-command ceiling')


def source_units():
    return read(AUTH/'attempts/source-bes-dep-11/attempt-001/source-product.json.gz')['payload']['graph']


def controls(graph,assembly,packet):
    from legalmath.prospectus.successor import reviewed_references
    from legalmath.prospectus.successor.contracts import digest
    from legalmath.prospectus.successor.occurrences import anchor
    results=[]
    for name in ('one_unit','omit_amount','omit_page','partial_quote','duplicate','extra_cover','wrong_source','wrong_use',
                 'wrong_form','excluded_restriction','changed_selected_text','wrong_questions','missing_source_unit','changed_original_text','hidden_target'):
        g,asm,p=graph,assembly,deepcopy(packet); row=p['references'][0]
        if name=='one_unit': row['targets']=row['targets'][:1]
        elif name=='omit_amount': row['targets']=[v for v in row['targets'] if v['use']!='bes-release-q111:p36:l6']
        elif name=='omit_page': row['targets']=[v for v in row['targets'] if ':p36:' in v['use']]
        elif name=='partial_quote': row['targets'][0]['source']=anchor(next(u for u in graph['units'] if u['id']==row['targets'][0]['use']),0,5)
        elif name=='duplicate': row['targets'][-1]=deepcopy(row['targets'][0])
        elif name=='extra_cover':
            u=next(u for u in graph['units'] if u['id']=='bes-release-q111:p1:l0'); row['targets'].append({'source':anchor(u),'use':u['id'],'language':'en'})
        elif name=='wrong_source': row['targets'][0]['source']['source_sha256']='0'*64
        elif name=='wrong_use': row['targets'][0]['use']=row['targets'][1]['use']
        elif name=='wrong_form': row['form']='named'
        elif name in ('excluded_restriction','changed_selected_text','wrong_questions'):
            asm=deepcopy(assembly); key='bes-supplement-4:p3:l29' if name=='excluded_restriction' else row['targets'][-1]['use']
            u=next(u for u in asm['units'] if u['unit']==key)
            if name=='excluded_restriction': u['role']='EXCLUDED'
            elif name=='changed_selected_text': u['text']+=' changed'
            else: u['questions']=['Q1']
        else:
            g=deepcopy(graph); u=next(u for u in g['units'] if u['id']==row['targets'][-1]['use'])
            if name=='missing_source_unit': g['units'].remove(u)
            elif name=='hidden_target': u['visible']=False
            else: u['raw']+=' changed'; u['text_sha256']=digest(u['raw'].encode())
        p['assembly_sha256']=digest(asm)
        try: reviewed_references.admit(g,asm,p)
        except ValueError as exc: results.append({'case':name,'rejected':True,'reason':str(exc)})
        else: raise ValueError('Altered Q1 scope accepted: '+name)
    return results


def verify_answer(answer,baseline,graph):
    from legalmath.prospectus.successor.contracts import digest
    key='reviewed-reference:BES-DEP-11-conditional-statement-link'
    dep,=[d for d in answer['dependencies'] if d['id']==key]
    required={u['id'] for u in graph['units'] if u['document']=='bes-release-q111' and u['page'] in (36,37)}
    targets=[t['unit'] for t in dep['targets']]
    require(len(targets)==len(required)==299 and set(targets)==required,'Q1 target coverage')
    scope=dep['statement_scope_check']
    require(scope['target_units']==299 and scope['pages']==[36,37] and scope['source_authenticity']=='NOT_ESTABLISHED' and
            scope['incorporation_status']=='UNRESOLVED' and not scope['independent_legal_acceptance'],'Unsupported Q1 scope conclusion')
    def anchor(u): return {'unit':u['id'],'document':u['document'],'source_sha256':u['source_sha256'],'start':0,'end':len(u['raw']),'quote':u['raw']}
    raw={u['id']:u for u in graph['units']}
    restriction=[u for u in graph['units'] if u['document']=='bes-supplement-4' and u['page']==3 and
                 (u['raw'].startswith('Any information not listed in the cross reference list below but included in the unaudited March') or
                  u['raw']=='accounts incorporated by reference in this Supplement is given for information purposes only.')]
    require(len(restriction)==2 and scope['restriction']==[anchor(u) for u in restriction],'Q1 restriction changed')
    require(scope['release_identity_and_qualification']==[anchor(raw['bes-release-q111:p1:l'+str(i)]) for i in range(5)] and
            scope['context_pages_do_not_expand_incorporation'] is True,'Q1 context changed')
    stripped=deepcopy(answer); del next(d for d in stripped['dependencies'] if d['id']==key)['statement_scope_check']
    skip={'report_sha256','consumed_products'}
    require({k:v for k,v in stripped.items() if k not in skip}=={k:v for k,v in baseline.items() if k not in skip},'Unexplained complete Q1 answer change')
    cells=answer['source_statement_cells']; rows=cells['rows']
    require(len(rows)==78 and sum(len(r['cells']) for r in rows)==206 and
            sum(c['status']=='PRINTED_DASH_UNKNOWN' for r in rows for c in r['cells'])==22,'Q1 row/cell/dash denominator changed')
    memo=[r for r in rows if r['role']=='MEMORANDUM_QUANTITY']
    require(len(memo)==2 and len({r['parent_row'] for r in memo})==2 and
            sum(len(r['cells']) for r in memo)==6 and all(r['non_additive'] for r in memo) and
            all(c['status']=='MEMORANDUM_MAGNITUDE' and c['value'] is None and c['magnitude']>0 for r in memo for c in r['cells']),
            'Q1 unsigned ECB subset meaning changed')
    require(answer['questions']['Q3']['status']=='PARTIAL' and not answer['may_execute_transaction'] and not answer['independent_legal_acceptance'],'Q1 unsupported acceptance')
    return {'occurrences':299,'rows':78,'cells':206,'unknown_dashes':22,'unsigned_memorandum_magnitudes':6,'protected_answer_sha256':digest({k:v for k,v in stripped.items() if k not in skip}),
            'complete_source_meaning_preserved':True,'task_complete':False}


def oracle_controls(checker,answer,baseline,graph):
    caught=[]
    for name in ('omitted-target','duplicate-target','erased-restriction','invented-authenticity','changed-cell','dash-to-zero'):
        changed=deepcopy(answer); dep=next(d for d in changed['dependencies'] if d['id']=='reviewed-reference:BES-DEP-11-conditional-statement-link')
        if name=='omitted-target': dep['targets'].pop()
        elif name=='duplicate-target': dep['targets'][-1]=deepcopy(dep['targets'][0])
        elif name=='erased-restriction': dep['statement_scope_check']['restriction']=[]
        elif name=='invented-authenticity': dep['statement_scope_check']['source_authenticity']='AUTHENTICATED'
        elif name=='changed-cell': changed['source_statement_cells']['rows'][0]['cells'][0]['value']+=1
        else: next(c for r in changed['source_statement_cells']['rows'] for c in r['cells'] if c['status']=='PRINTED_DASH_UNKNOWN')['value']=0
        try: checker(changed,baseline,graph)
        except ValueError: caught.append(name)
        else: raise ValueError('Permissive checker: '+name)
    return caught


def worker(kind):
    candidate=kind in ('candidate','candidate-recovery')
    target=WORK/'candidate/src' if candidate else HERE/'installed-package' if kind=='installed' else ROOT/'src'
    sys.path.insert(0,str(target)); import legalmath.prospectus.successor.service
    from legalmath.prospectus.successor import service
    from scripts import prospectus_q1_scope_probe as probe, prospectus_fy2010_product as fy
    sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=ROOT/'src']
    folder=(SUCCESSFUL_CANDIDATE if kind=='candidate-recovery' else WORK/'candidate-result') if candidate else HERE/(kind+'-result')
    folder.mkdir(parents=True,exist_ok=False)
    ps=probe.products(); supplied=ps['P3']['payload']['interpretation_input']; graph=ps['P1']['payload']['graph']
    answer=service.consume(probe.rebuild(ps['P1'],supplied),ROOT,mode='frozen',include_artifacts=True)
    save(folder/'answer.json.gz',answer); baseline=read(WORK/'probe/baseline-answer.json.gz')
    proof=verify_answer(answer,baseline,graph)
    adverse=controls(graph,ps['P2']['payload']['assembly'],supplied['reference_admission'])
    try: service.consume(probe.rebuild(ps['P1'],read(WORK/'probe/omission-input.json.gz')),ROOT,mode='frozen',include_artifacts=True)
    except ValueError as exc: refusal={'rejected':True,'reason':str(exc)}
    else: raise ValueError('Actual omitted financial target accepted')
    oracle=oracle_controls(verify_answer,answer,baseline,graph)
    try: oracle_controls(lambda *_:True,answer,baseline,graph)
    except ValueError as exc: require(str(exc).startswith('Permissive checker:'),'Wrong permissive failure')
    else: raise ValueError('Permissive checker undetected')
    fyps=fy.load_products(AUTH/'attempts/source-bes-dep-08/attempt-006','after')
    fyanswer=service.consume(fy.products(fyps['P1'],fyps['P3']['payload']['interpretation_input']),ROOT,mode='frozen',include_artifacts=True)
    require(fyanswer==read(AUTH/'attempts/source-bes-dep-08/attempt-009/ordinary/answer.json.gz'),'Complete repaired FY answer changed')
    from legalmath.prospectus.successor.contracts import digest
    result={'status':'PASS','proof':proof,'controls':adverse,'actual_omission':refusal,'oracle_controls':oracle,
            'permissive_checker_detected':True,'fy2010_complete_answer_sha256':digest(fyanswer)}
    imports={}
    for name,module in sorted(sys.modules.items()):
        if name=='legalmath' or name.startswith('legalmath.'):
            value=getattr(module,'__file__',None)
            if value:
                path=Path(value).resolve(); require(path.is_relative_to((target/'legalmath').resolve()),'Wrong import: '+name)
                imports[name]={'path':str(path),'sha256':sha(path)}
    require(sys.flags.isolated==1,'Isolated worker required')
    if not candidate:
        require(result==read(SUCCESSFUL_CANDIDATE/'result.json') and answer==read(SUCCESSFUL_CANDIDATE/'answer.json.gz'),'Actual ordinary/installed result differs')
    save(folder/'result.json',result); save(folder/'imports.json',{'modules':imports,'sys_path':sys.path,'executable':sys.executable,'isolated':True})
    return {'status':'PASS','worker':kind}


def trial():
    code=('import sys; from pathlib import Path; r=Path.cwd(); sys.path[:0]=[str(r/".localresources/prospectus-preparation/q1-scope/candidate/src"),str(r)]; '
          'import pytest; raise SystemExit(pytest.main(["-q","-p","no:cacheprovider",'
          '"tests/prospectus_successor/test_q1_statement_scope.py","tests/prospectus_successor/test_fy2010_statement_scope.py",'
          '"tests/prospectus_successor/test_bes_statement_scope.py","tests/prospectus_successor/test_statement_cells.py",'
          '"--junitxml=.localresources/prospectus-preparation/q1-scope/tests.xml"]))')
    command('tests',[str(ROOT/'.venv/bin/python'),'-I','-B','-c',code],PREP/'commands',60)
    command('candidate',[str(ROOT/'.venv/bin/python'),'-I','-B',str(ROOT/SELF),'worker','--kind','candidate'],PREP/'commands')
    return {'status':'PASS','costs':costs()}


def recovery():
    require(read(PREP/'commands/candidate.json')['exit_code']==1 and
            'Q1 row/cell/unknown denominator changed' in (PREP/'commands/candidate.log').read_text(),'Expected retained oracle failure')
    command('candidate-recovery',[str(ROOT/'.venv/bin/python'),'-I','-B',str(ROOT/SELF),'worker','--kind','candidate-recovery'],PREP/'commands')
    return {'status':'PASS','changed_recovery_consumed':True,'costs':costs()}


def freeze():
    a=authority(); from legalmath.prospectus.execution_authority import digest
    old,_,_=a.spec(); require(old['revision']==436 and not a.status()['running'],'Current436required')
    require(all(read(PREP/'commands'/(n+'.json'))['exit_code']==0 for n in ('tests','candidate-recovery')),'Recovered candidate required')
    b=read(PREP/'baseline.json'); candidate=inventory(WORK/'candidate/src/legalmath')
    require(inventory(ROOT/'src/legalmath')==b['production'],'Baseline changed')
    require({n for n in set(candidate)|set(b['production']) if candidate.get(n)!=b['production'].get(n)}==set(CHANGES),'Unexpected source change')
    evidence={n:sha(ROOT/n) for n in (SELF,PROBE,PLAN,TEST,'scripts/prospectus_fy2010_scope_program.py','scripts/prospectus_fy2010_product.py')}
    evidence.update({rel(p):sha(p) for p in WORK.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    evidence.update({'src/legalmath/'+n:h for n,h in candidate.items()})
    save(PREP/'freeze.json',{'evidence':evidence,'baseline':b['production'],'candidate':candidate,'runtime':b['runtime'],'limits':LIMITS})
    proposal=deepcopy(old); proposal['revision']=437; task=next(t for t in proposal['tasks'] if t['id']==TASK)
    task.update(dossier=PLAN,pre_admission_review=PLAN,reason='Actual Q1 financial-target omission falsely resolves; enforce conditional complete selected scope',q1_scope_review=rel(PREP/'freeze.json'))
    task['inputs']=sorted(set(task['inputs'])|set(evidence)|{rel(PREP/'freeze.json')})
    attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==TASK]
    require(len(attempts)==old['budgets'][TASK]['maximum_new_attempts']==4,'Retain four original Q1 admissions')
    proposal['budgets'][TASK]['maximum_new_attempts']=5
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=437
    for row in routes['tasks']:
        if row['task']==TASK: row.update(task_sha256=digest(task),dossier=PLAN,phase=0,remaining='Actual298target reference resolves after dropping a printed amount; original legal/source obligations stay open.',next_action='Complete reviewed Q1 scope repair and current/installed comparison; then reconcile original sources and current finite criteria.',stop_condition='Admission005;600seconds256MiB;changed recovery consumed by oracle repair;no further retry.')
        elif row['task']=='source-bes-dep-08': row.update(phase=2,remaining='009recorded complete finite FY scope repair and original requirement matrix; authenticity/general recognition remain open.',next_action='Preserve009; continue only on a distinct reproduced gap or genuinely new source evidence.')
    save(PREP/'routes.json',routes); proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in CHANGES:
        if 'src/legalmath/'+n in proposal['continuation_review']['bindings']: proposal['continuation_review']['bindings']['src/legalmath/'+n]=candidate[n]
    proposal['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (SELF,PLAN,rel(PREP/'freeze.json'),rel(PREP/'routes.json'))})
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',{'baseline':digest(old),'scope_unchanged':True,'budget_unchanged':False,
         'changes':['Enforce Q1 selected statement scope on actual financial-target counterexample','Preserve source08/009 and source05/071 failure'],
         'skeptical_audit':{'verdict':'PASS','plan':PLAN,'probe':rel(WORK/'probe/result.json'),'tests':rel(WORK/'tests.xml'),
             'output_directories':'installed-package and installed-result are distinct; no436collision'},
         'evidence_contract':{'baseline':rel(OLD),'primary':'Original complete answer, conditional299target scope and faithful206cells; actual omission refuses',
             'promotion_veto':['Source/scope/meaning/import mismatch','Changed FY answer'],'continuation_veto':['Invalid authority','Corrupt shared evidence','Bound exhausted'],
             'explanatory':['Counts','Runtime'],'not_concluded':['Financial truth','General recognition','Original task/build complete']},
         'budget_revision':{'budget_key':TASK,'previous_maximum':4,'new_maximum':5,'retained_attempts':attempts,
             'reason':'Distinct actual omitted financial target remains resolved','next_discriminating_check':'Matched ordinary and isolated installed full answer plus every declared control',
             'stop_condition':LIMITS,'same_scope_authorization':'Recover and continue original prospectus build'}})
    forecast=costs()['new_bytes']+3*(PREP/'proposal.json').stat().st_size+3*sum((ROOT/'src/legalmath'/n).stat().st_size for n in b['production'])+2*(SUCCESSFUL_CANDIDATE/'answer.json.gz').stat().st_size+12*1024**2
    require(forecast+LIMITS['reserve']<LIMITS['bytes'],'Final artifacts exceed storage forecast')
    save(PREP/'forecast.json',{'bytes':forecast,'final_manifest_and_authority_allowance_included':True})
    return {'status':'FROZEN','forecast_bytes':forecast}


def cutover():
    a=authority()
    from legalmath.prospectus.execution_authority import digest
    f=read(PREP/'freeze.json'); require(digest(a.spec()[0])==read(PREP/'review.json')['baseline'],'Baseline revision changed')
    require(inventory(ROOT/'src/legalmath')==f['baseline'],'Production changed')
    for n in CHANGES: shutil.copyfile(WORK/'candidate/src/legalmath'/n,ROOT/'src/legalmath'/n)
    require(inventory(ROOT/'src/legalmath')==f['candidate'],'Cutover differs')
    save(PREP/'cutover.json',{'changed':CHANGES,'revision_required':437}); return {'status':'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def admitted():
    a=authority(); p,t,_=a.spec()
    require(p['revision']==437 and read(HERE/'admission.json')['binding']==a.binding(t[TASK]),'Current437admission required')
    require(next(e for e in reversed(a.events()) if e.get('task')==TASK)['kind']=='ADMIT','Attempt terminal')


def stage(kind):
    admitted(); f=read(PREP/'freeze.json')
    if kind=='package':
        source=HERE/'package-source'; source.mkdir(); shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
        shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        python=f['runtime']['package_python']
        command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(source)],HERE/'commands',60)
        wheel,=(HERE/'wheel').glob('*.whl')
        command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed-package'),str(wheel)],HERE/'commands',60)
        require(inventory(HERE/'installed-package/legalmath')==f['candidate'],'Installed inventory differs')
        save(HERE/'package.json',{'status':'PASS','files':f['candidate'],'wheel':{'path':rel(wheel),'sha256':sha(wheel)}})
    else:
        if kind=='installed': require(read(HERE/'package.json')['status']=='PASS','Package required')
        python=f['runtime']['package_python' if kind=='installed' else 'ordinary_python']
        command(kind,[python,'-I','-B',str(ROOT/SELF),'worker','--kind',kind],HERE/'commands')
    return {'status':'PASS','stage':kind,'costs':costs()}


def seal():
    admitted(); f=read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n,h in f['evidence'].items()),'Frozen evidence changed')
    require(inventory(ROOT/'src/legalmath')==f['candidate']==inventory(HERE/'installed-package/legalmath'),'Package changed')
    require(read(HERE/'ordinary-result/result.json')==read(HERE/'installed-result/result.json'),'Actual consumers differ')
    require((HERE/'RESULT.md').is_file(),'Substantive result required'); usage=costs()
    save(HERE/'result.json',{'task':TASK,'status':'PASS','task_complete':False,'whole_program_complete':False,'costs':usage,'plan':PLAN})
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],'commands':[rel(p) for p in (HERE/'commands').glob('*.json')],
         'environment':f['runtime'],'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','data_version':read(WORK/'probe/manifest.json')['data_version'],
         'random_seeds':'N/A deterministic','wall_seconds':usage['new_measured_seconds'],'plan':PLAN,'result':rel(HERE/'RESULT.md'),'frozen':rel(PREP/'freeze.json')})
    output={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    require(costs()['new_bytes']+len(str(output).encode())+1024**2+LIMITS['reserve']<LIMITS['bytes'],'Final manifest reserve')
    save(HERE/'outputs.json',output); require(costs()['allowed'],'Post-seal ceiling'); return {'status':'SEALED','costs':costs()}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['prepare','trial','recovery','worker','freeze','cutover','stage','seal'])
    p.add_argument('--kind',choices=['candidate','candidate-recovery','ordinary','package','installed']); args=p.parse_args()
    result=worker(args.kind) if args.action=='worker' else stage(args.kind) if args.action=='stage' else globals()[args.action]()
    print(result,flush=True)
