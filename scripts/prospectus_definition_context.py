"""Run source-reviewed definition contexts under the existing master program."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import ast, json, os, shutil, signal, sys, time
import xml.etree.ElementTree as ET
from scripts import prospectus_definition_binding as prior
from scripts import prospectus_definition_context_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/definition-contexts-332'
HERE=AUTH/'attempts/basf-references/attempt-071'
PLAN='docs/plans/prospectus-definition-contexts-2026-10-19.md'
METHOD='scripts/prospectus_definition_context.py'
WORKER='scripts/prospectus_definition_context_installed.py'
ORACLE='scripts/prospectus_definition_context_oracle.py'
TEST='tests/prospectus_successor/test_definition_contexts.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_definition_context_cases.py')
TARGETS=tuple('src/legalmath/prospectus/successor/'+n for n in
              ('definition_contexts.py','definition_contexts_spec.json','service.py','conditional_profiles.py'))
STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def baseline():
    products,_=prior.baseline()
    answer=read(prior.HERE/'ordinary-answer.json.gz')
    freeze=read(PREP/'cases-freeze.json')
    assert digest(products)==freeze['products_sha256'] and digest(answer)==freeze['ordinary_answer_sha256']
    return products,answer


def costs(extra=0):
    start=read(PREP/'accounting-start.json'); base=start['prior']
    measured=base['combined_measured_seconds']+read(PREP/'case-preparation.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            measured+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    charged=base['conservative_extra_seconds']
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0332.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert measured+charged<18000 and size<2684*1024**2,'Cumulative context resource bound'
    return {'combined_measured_seconds':measured,'conservative_extra_seconds':charged,
        'combined_accounted_seconds':measured+charged,'combined_bytes':size,'seconds_bound':18000,
        'bytes_bound_with_4MiB_reserve':2688*1024**2,'prior_costs_reset':False,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}


def testfiles():return [TEST,*prior.testfiles()]


def install():
    for row in read(PREP/'installation.json'):
        path=ROOT/row['target']
        assert (sha(path) if path.exists() else None)==row['before']
        shutil.copyfile(ROOT/row['candidate'],path)
    return {'status':'PASS','production_files':len(TARGETS)}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==331
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==70 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v
    for n,v in read(prior.PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(prior.PREP/'installation.json'):assert sha(ROOT/row['target'])==row['after']
    frozen=read(PREP/'cases-freeze.json')
    assert frozen['candidate_absent'] is True
    for name,key in [('source-decisions.json','source_decisions_sha256'),('expected-content.json','expected_file_sha256')]:
        assert sha(PREP/name)==frozen[key]
    assert sha(ROOT/PLAN)==frozen['plan_sha256'] and sha(ROOT/ORACLE)==frozen['oracle_sha256']
    spec={'version':oracle.VERSION,'products_sha256':frozen['products_sha256'],
        'ordinary_answer_sha256':frozen['ordinary_answer_sha256'],
        'expected_content_sha256':frozen['expected_content_sha256'],'decisions':read(PREP/'source-decisions.json')}
    save(PREP/'candidate/definition_contexts_spec.json',spec)
    module=PREP/'candidate/definition_contexts.py';body=module.read_text()
    assert body.count('SPEC_SHA256 = None')==1
    module.write_text(body.replace('SPEC_SHA256 = None','SPEC_SHA256 = '+repr(digest(spec))))
    profile={'version':oracle.VERSION,'products_sha256':frozen['products_sha256'],
        'ordinary_answer_sha256':frozen['ordinary_answer_sha256'],'specification_sha256':digest(spec),
        'whole_task_complete':False,'legal_truth_established':False}
    save(PREP/'profile.json',profile)
    manifest=read(prior.PREP/'profiles.json')
    manifest['profiles'].append({'name':'definition_contexts','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path,candidate=ROOT/target,PREP/'candidate'/(ROOT/target).name
        if candidate.suffix=='.py':ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,
            'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,*testfiles(),prior.METHOD,prior.WORKER,prior.ORACLE,
                                   'scripts/prospectus_residual_coverage.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for path in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PRODUCTS):bindings[rel(path)]=sha(path)
    for row in read(prior.PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for row in manifest['profiles']:bindings[row['path']]=row['file_sha256']
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    proposal=deepcopy(program);proposal['revision']=332
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Connect75issue/certificate/clearing/register occurrences with exact qualifications and each/both/heading distinctions',
        definition_context_review={'review':rel(PREP),'original_task_complete':False,
            'accounted_seconds_bound':18000,'bytes_bound_with_4MiB_reserve':2688*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=71
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=332
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify75source-context decisions through complete ordinary/installed answers; continue remaining507use associations and task acceptance',
            stop_condition='71admissions;900s/160MiBforecast;18000accounted seconds/2688MiBwith4MiBreserve;no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    snapshot=costs();forecast={'seconds':snapshot['combined_accounted_seconds']+900,
        'bytes':snapshot['combined_bytes']+160*1024**2,'estimate_only':True}
    assert forecast['seconds']<18000 and forecast['bytes']<2684*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Exact context links for75original uses with all612associations retained','No cumulative bound reset or new external prerequisite'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent complete source-context answer and fresh installed equality',
            'promotion_veto':['Wrong purpose or institution','Lost qualification','Heading promoted','Wrong each/both','Lost use','Wrong import'],
            'continuation_veto':['Corrupt baseline','Frozen drift','Cumulative bound'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Remaining507uses','Actual facts','Historical law','Legal truth','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':70,'new_maximum':71,
            'retained_attempts':attempts,'reason':'070exposes missing contextual links; inspected75uses of10records give a bounded next source repair',
            'next_discriminating_check':'Exact75source decisions with72bindings,2heading mentions,1full-name component and full612retention',
            'stop_condition':'900s/160MiBforecast;18000accounted seconds/2688MiBwith4MiBreserve;no unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continued general build without outside-adviser prerequisites'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':332,'candidate_evaluated':False,'forecast':forecast}


def tests():
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],
        '-q','--junitxml='+str(HERE/'pytest.xml')],150)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS',**counts}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(prior.PRODUCTS),'--repository',str(ROOT),
        '--output',str(HERE/output),'--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),
        '--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def consume():
    from legalmath.prospectus.successor import definition_contexts as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],330)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    result=oracle.verify(actual,ordinary,products,profile,read(PREP/'expected-content.json'))
    save(HERE/'independent-verification.json',result)
    save(HERE/'verification.json',module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile)))
    return {**result,'actual_cli':True,'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus.successor import definition_contexts as module
    products,ordinary=baseline();profile=read(PREP/'profile.json');content=read(PREP/'expected-content.json')
    actual=read(HERE/'ordinary-answer.json.gz');refused={}
    for kind in ('missing-use','false-heading','wrong-form','wrong-institution','plural-as-singular',
                 'lost-exchange-condition','lost-question','false-completion'):
        bad=deepcopy(actual);uses=bad[module.KEY]['uses']
        if kind=='missing-use':uses.pop()
        elif kind=='false-heading':next(u for u in uses if u['disposition']=='HEADING_MENTION')['disposition']='BOUND_CONTEXTUALLY'
        elif kind=='wrong-form':next(u for u in uses if u['record'].startswith('D05'))['context_binding']['concept']='PERMANENT_GLOBAL_NOTE'
        elif kind=='wrong-institution':next(u for u in uses if u['record'].startswith('D08'))['context_binding']['concept']='EUROCLEAR_BANK_SA_NV'
        elif kind=='plural-as-singular':next(u for u in uses if u['record'].startswith('D10') and u['quote']=='ICSDs')['context_binding']['number']='EACH_OR_RELEVANT_ICSD'
        elif kind=='lost-exchange-condition':next(u for u in uses if u['record'].startswith('D05'))['context_binding']['extra_meanings']=[]
        elif kind=='lost-question':bad['questions']['Q1']['unresolved']=[]
        else:bad[module.KEY]['all_governing_uses_established']=True
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        try:oracle.verify(bad,ordinary,products,profile,content)
        except AssertionError as e:refused[kind]=str(e)
        else:raise AssertionError('Accepted '+kind)
    for kind in ('rehashed-answer','rehashed-product','rehashed-spec','legal-truth'):
        oo,pp,pr=deepcopy(ordinary),deepcopy(products),deepcopy(profile)
        if kind=='rehashed-answer':oo['questions']['Q1']['status']='YES'
        elif kind=='rehashed-product':pp['P2']['payload']['assembly']['continuous_text']+='x'
        elif kind=='rehashed-spec':pr['specification_sha256']='0'*64
        else:pr['legal_truth_established']=True
        oo['report_sha256']=digest({k:v for k,v in oo.items() if k!='report_sha256'})
        pr['ordinary_answer_sha256'],pr['products_sha256']=digest(oo),digest(pp)
        try:module.evaluate(pp,oo,pr,ROOT,expected_profile_sha256=digest(pr))
        except ValueError as e:refused[kind]=str(e)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused})
    return {'status':'PASS','refused':len(refused)}


def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),str(PREP)],330)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result


def seal():
    answer=read(HERE/'ordinary-answer.json.gz')
    counts=dict(Counter(u['disposition'] for u in answer[oracle.KEY]['uses']))
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'EXACT_SOURCE_DEFINITION_CONTEXTS','associations':counts,
        'independent_whole_answer_equal':True,'installed_answer_equal':True,'resources':costs(),
        'next_action':'Continue507remaining governing uses, source-specific ambiguous scopes, typed agency classification and original-task acceptance'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(prior.PRODUCTS),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Issue, form, clearing and register occurrence links

Ten definitions and75original uses now have source-specific context decisions.
Seventy-two link to the full existing qualified meaning. Two inline headings
remain mentions without changing their operative source lines; one Euroclear
full-name component remains distinct from invoking its alias. Each/both ICSDs,
temporary/permanent certificates and the separate exchange prerequisites are
preserved. All612associations and the entire prior answer remain.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite context links|Frozen complete answer and installed equality|Source/identity/qualification/heading/plurality controls refused|507uses still need governing-scope reconciliation; actual and historical premises open|Continue original source work|Whole task, general recall, legal truth or whole build|

The baseline and installed outputs are equal as parsed complete JSON values;
their serialized file bytes can differ with object-key ordering. Prior wording
describing byte-for-byte equality was too strong. Independent source decisions
and whole-answer equality are the actual criteria. The strongest alternative
explanation remains a shared mistaken source interpretation, which these software
checks do not eliminate. An occurrence with another referent or missing source
qualification would require revisiting the finite decision table.
''')
    return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage=='prepare':
        save(PREP/'accounting-start.json',{'prior':prior.costs(),
            'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
            'program_bytes':(AUTH/'program.json').stat().st_size,
            'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    else:
        for s in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/s/'result.json')['status']=='PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    engine.PREP,engine.HERE,engine.PLAN,engine.METHOD,engine.WORKER,engine.TARGETS=PREP,HERE,PLAN,METHOD,WORKER,TARGETS
    engine.costs,engine.testfiles,engine.cli_arguments=costs,testfiles,cli_arguments
    bound=90 if stage=='prepare' else 360
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_context',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':bound})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Context stage bound')));signal.alarm(bound)
    try:
        if stage!='prepare':engine.frozen(stage!='install')
        result=(globals().get(stage) or getattr(engine,stage))()
        if stage!='prepare':engine.frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start
        save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as e:
        save(folder/'failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
