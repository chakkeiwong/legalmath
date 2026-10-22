"""Bounded paragraph discovery with full prior-answer preservation under one authority."""
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,shutil,signal,sys,time
import xml.etree.ElementTree as ET
from scripts import prospectus_requirement_order_repair as prior
from scripts import prospectus_cycle_disposition as baseline_run
from scripts import prospectus_paragraph_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/paragraph-discovery-342';HERE=AUTH/'attempts/basf-references/attempt-081'
PLAN='docs/plans/prospectus-paragraph-discovery-2026-10-19.md'
METHOD='scripts/prospectus_paragraph_discovery.py';WORKER='scripts/prospectus_paragraph_installed.py'
TEST='tests/prospectus_successor/test_paragraph_references.py';ORACLE='scripts/prospectus_paragraph_oracle.py'
FILES=(PLAN,METHOD,WORKER,TEST,ORACLE,'scripts/prospectus_paragraph_cases.py')
TARGETS=tuple('src/legalmath/prospectus/successor/'+name for name in
    ('paragraph_references.py','paragraph_references_spec.json','service.py','conditional_profiles.py'))
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
PRODUCTS=baseline_run.PRODUCTS

def baseline():
    manifest=read(PRODUCTS);products={k:read(ROOT/r['path']) for k,r in manifest['products'].items()}
    answer=read(baseline_run.HERE/'ordinary-answer.json.gz');freeze=read(PREP/'source-freeze.json')
    assert digest(products)==freeze['products_sha256'] and digest(answer)==freeze['ordinary_answer_sha256']
    return products,answer

def costs(extra=0):
    start=read(PREP/'accounting-start.json');base=start['prior']
    seconds=base['combined_measured_seconds']+read(PREP/'source-freeze.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0342.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-start['production_bytes'][n]) for n in TARGETS if (ROOT/n).exists())
    charged=base['conservative_extra_seconds']
    assert seconds+charged<21600 and size<3196*1024**2,'Cumulative paragraph resource bound'
    return {'combined_measured_seconds':seconds,'conservative_extra_seconds':charged,
        'combined_accounted_seconds':seconds+charged,'combined_bytes':size,'seconds_bound':21600,
        'bytes_bound_with_4MiB_reserve':3200*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN;never treated as zero'}

def testfiles():return [TEST,'tests/prospectus_successor/test_conditional_profiles_cli.py']

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==341
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==80 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    for n,v in read(prior.PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for r in read(prior.PREP/'installation.json'):assert sha(ROOT/r['target'])==r['after']
    frozen=read(PREP/'source-freeze.json');assert frozen['candidate_absent'] is True
    assert sha(PREP/'expected.json')==frozen['expected_sha256'] and sha(ROOT/PLAN)==frozen['plan_sha256']
    spec={'version':'paragraph-reference-discovery.v1','products_sha256':frozen['products_sha256'],
        'ordinary_answer_sha256':frozen['ordinary_answer_sha256'],
        'source_expressions':read(PREP/'expected.json')['source_expressions']}
    save(PREP/'candidate/paragraph_references_spec.json',spec)
    candidate=PREP/'candidate/paragraph_references.py';body=candidate.read_text();assert body.count('SPEC_SHA256 = None')==1
    candidate.write_text(body.replace('SPEC_SHA256 = None','SPEC_SHA256 = '+repr(digest(spec))))
    profile={'version':spec['version'],'products_sha256':spec['products_sha256'],
        'ordinary_answer_sha256':spec['ordinary_answer_sha256'],'specification_sha256':digest(spec),
        'whole_task_complete':False,'legal_truth_established':False}
    save(PREP/'profile.json',profile);manifest=read(baseline_run.PREP/'profiles.json')
    manifest['profiles'].append({'name':'paragraph_references','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest);(PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name
        if candidate.suffix=='.py':ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,*testfiles(),'pyproject.toml',prior.METHOD,baseline_run.METHOD,'scripts/prospectus_residual_coverage.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',baseline_run.HERE/'outputs.json',baseline_run.HERE/'ordinary-answer.json.gz',PRODUCTS):bindings[rel(p)]=sha(p)
    for r in read(PRODUCTS)['products'].values():bindings[r['path']]=r['sha256']
    for r in manifest['profiles']:bindings[r['path']]=r['file_sha256']
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    proposal=deepcopy(program);proposal['revision']=342;task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Discover literal German paragraph expressions with raw source mapping while retaining unresolved targets and complete prior answers',
        paragraph_discovery_review={'review':rel(PREP),'original_task_complete':False,'accounted_seconds_bound':21600,'bytes_bound_with_4MiB_reserve':3200*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=81
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=342
    for r in routes['tasks']:
        if r['task']=='basf-references':r.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify exact30source expressions and21grammar cases through ordinary/installed consumers;continue semantic reference scope and implicit discovery',
            stop_condition='81admissions;900s/140MiBforecast;21600accounted seconds/3200MiBwith4MiBreserve;no unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs();forecast={'seconds':snapshot['combined_accounted_seconds']+900,'bytes':snapshot['combined_bytes']+140*1024**2,'estimate_only':True}
    assert forecast['seconds']<21600 and forecast['bytes']<3196*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Add explicit paragraph syntax proposals with exact source mapping','Preserve all original sources,answers and unresolved target/semantic requirements'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Frozen literal source/grammar expectations,independent source mapping,complete ordinary/installed equality',
            'promotion_veto':['Source offset/token differs','Incomplete syntax promoted','Target invented','Prior answer changed','Installed mismatch'],
            'continuation_veto':['Corruption','Frozen drift','Cumulative bound'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['General recall','Target resolution','Legal interpretation','Actual facts','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':80,'new_maximum':81,'retained_attempts':attempts,
            'reason':'Original selected text contains explicit relative paragraph references missed by section-only discovery',
            'next_discriminating_check':'Exact30expressions,malformed grammar diagnostics,complete prior-answer preservation and fresh installed equality',
            'stop_condition':'900s/140MiBforecast;21600seconds/3200MiB cumulative;no unchanged retry',
            'same_scope_authorization':'User requested complete internally supported build and continued source-specific repairs'},
        'resource_accounting':{'retained_costs':snapshot,'seconds_bound':21600,'bytes_with_reserve':3200*1024**2,'limits_extended':False}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':342,'candidate_evaluated':False,'forecast':forecast}

def install():
    for r in read(PREP/'installation.json'):
        p=ROOT/r['target'];assert (sha(p) if p.exists() else None)==r['before'];shutil.copyfile(ROOT/r['candidate'],p)
    return {'status':'PASS','production_files':len(TARGETS)}

def tests():
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],120)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS',**counts}

def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]

def consume():
    from legalmath.prospectus.successor import paragraph_references as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],330)
    p,old=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    independent=oracle.verify(actual,old,p,read(PREP/'expected.json'));save(HERE/'independent-verification.json',independent)
    save(HERE/'verification.json',module.verify_answer(actual,old,profile,p,ROOT,expected_profile_sha256=digest(profile)))
    return {**independent,'actual_cli':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}

def controls():
    p,old=baseline();actual=read(HERE/'ordinary-answer.json.gz');expected=read(PREP/'expected.json');refused={}
    for kind in ('candidate-delete','token-change','source-shift','path-change','connector-change','source-piece-delete','false-target','false-completion','prior-answer'):
        bad=deepcopy(actual);r=bad[oracle.KEY];c=r['discovery']['candidates'][0]
        if kind=='candidate-delete':r['discovery']['candidates'].pop()
        elif kind=='token-change':c['tokens'][0]['value']='99'
        elif kind=='source-shift':c['start']+=1
        elif kind=='path-change':c['paths']=[['99']]
        elif kind=='connector-change':r['discovery']['candidates'][19]['connectors']=['und']
        elif kind=='source-piece-delete':r['source_candidates'][0]['source_pieces'].pop()
        elif kind=='false-target':c['target']='approved-target'
        elif kind=='false-completion':r['whole_task_complete']=True
        else:bad['questions']['Q1']['status']='YES'
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        try:oracle.verify(bad,old,p,expected)
        except AssertionError:refused[kind]=True
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}

def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),str(PREP)],330)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result

def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'SOURCE_PARAGRAPH_DISCOVERY',
        'source_expressions':30,'target_resolution_established':False,'ordinary_installed_equal':True,'resources':costs(),
        'next_action':'Continue source-scoped target resolution and implicit anaphora while preserving lexical proposal/meaning distinction'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Printed paragraph expressions reach the normal answer

Thirty independently frozen source expressions retain their exact printed
offsets,labels,compound paths and list/range connectors. Source projections and
overlaps with full reviewed references are independently checked. Overlap is
not target resolution. All original076answer fields remain identical,and the
fresh isolated package reproduces the complete ordinary answer.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional lexical proposals|Exact frozen source/grammar cases and installed equality|Altered source,tokens,targets,completion and old answers refused|Implicit anaphora,unknown grammar and semantic target scope|Source-scoped reference resolution|General recall,legal meaning or whole build|

The strongest alternative explanation is a missed form outside the declared
grammar. Unsupported forms remain explicit; no legal answer is promoted by
increased candidate count. This repairs local discovery coverage,not the PDF
package. All prior admissions,failed assessors and costs remain retained.
''')
    return result

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage;assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage=='prepare':save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    else:
        for s in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/s/'result.json')['status']=='PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    engine.PREP,engine.HERE,engine.PLAN,engine.METHOD,engine.WORKER,engine.TARGETS=PREP,HERE,PLAN,METHOD,WORKER,TARGETS
    engine.costs,engine.testfiles,engine.cli_arguments=costs,testfiles,cli_arguments
    bound=90 if stage=='prepare' else 360
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_paragraph_discovery',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':bound})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Paragraph stage bound')));signal.alarm(bound)
    try:
        if stage!='prepare':engine.frozen(stage!='install')
        result=(globals().get(stage) or getattr(engine,stage))()
        if stage!='prepare':engine.frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as e:
        save(folder/'failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
