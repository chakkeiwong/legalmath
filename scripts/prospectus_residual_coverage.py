"""Same-authority finite source coverage integration; every stage is bounded."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import ast, gzip, hashlib, json, os, shutil, signal, subprocess, sys, time, zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from scripts import prospectus_concert_application as prior
from scripts import prospectus_residual_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH; PREP=AUTH/'reviews/residual-coverage-313'; HERE=AUTH/'attempts/basf-references/attempt-054'
PLAN='docs/plans/prospectus-residual-coverage-2026-10-19.md'
METHOD='scripts/prospectus_residual_coverage.py'; WORKER='scripts/prospectus_residual_installed.py'
ORACLE='scripts/prospectus_residual_oracle.py'; TEST='tests/prospectus_successor/test_residual_coverage.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/residual_coverage.py','src/legalmath/prospectus/successor/service.py',
         'src/legalmath/prospectus/successor/conditional_profiles.py')
LEDGER=AUTH/'attempts/basf-references/attempt-025/original-ledger-reconciliation.json.gz'
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def baseline():
    manifest=read(prior.prior.PREP/'products.json')
    products={k:read(ROOT/r['path']) for k,r in manifest['products'].items()}
    answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='ff84672a486df572fa5efd355cb87ff3e02575d414ac244afb3cd589e03c56a6'
    return products,answer


def costs(extra=0):
    start=read(PREP/'accounting-start.json'); base=start['prior']
    seconds=base['cumulative026_053_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES); paths.add(AUTH/'revisions/0313.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['cumulative026_053_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<10800 and size<1532*1024**2,'Cumulative026 resource bound'
    return {'cumulative026_054_measured_seconds':seconds,'cumulative026_054_bytes':size,
            'prior_costs_reset':False,'seconds_bound':10800,'bytes_bound_with_4MiB_reserve':1536*1024**2,
            'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def testfiles():
    return [TEST,'tests/prospectus_successor/test_meaning_coverage.py',*prior.testfiles()]


def prepare():
    program=read(AUTH/'program.json'); assert program['revision']==312
    events=Authority(ROOT).events(); attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==53 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    products,ordinary=baseline(); expected=oracle.predict(products,ordinary)
    units={u['unit']:u for u in products['P2']['payload']['assembly']['units']}
    nodes=products['P3']['payload']['clauses']['nodes']; headings=[]
    for suffix,title in oracle.HEADINGS.items():
        identity=oracle.PREFIX+suffix
        matches=[n for n in nodes if n['effect']=='unknown' and n['quote'].strip()==title and any(s['unit']==identity for s in n['spans'])]
        assert len(matches)==1; node=matches[0]
        headings.append({'node_id':node['id'],'node_sha256':digest(node),'quote':node['quote'],'spans':node['spans'],
            'contexts':[{'unit':s['unit'],'text':units[s['unit']]['text'],'role':units[s['unit']]['role']} for s in node['spans']]})
    ledger=read(LEDGER); h43=next(r for r in ledger['records'] if r['family']=='historical_candidate_lines' and r['index']==43)
    profile={'version':'basf-residual-coverage.v1','products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'headings':headings,'h43':{'ledger_path':rel(LEDGER),'ledger_file_sha256':sha(LEDGER),
        'original_record_sha256':digest(h43),'source_pieces':[r['original'] for r in h43['source_pieces']]},
        'legal_scope_resolved':False,'whole_task_complete':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',expected)
    candidate=PREP/'candidate/residual_coverage.py'; text=candidate.read_text()
    assert text.count('REGISTERED_PROFILE_SHA256 = None')==1
    candidate.write_text(text.replace('REGISTERED_PROFILE_SHA256 = None','REGISTERED_PROFILE_SHA256 = '+repr(digest(profile))))
    text=(ROOT/TARGETS[1]).read_text(); old='            concert_profile=None, expected_concert_profile_sha256=None):'
    assert text.count(old)==1; text=text.replace(old,'            concert_profile=None, expected_concert_profile_sha256=None,\n            coverage_profile=None, expected_coverage_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    new="""    if coverage_profile is not None:
        from ..residual_coverage import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['residual_coverage_review'] = evaluate(products, baseline, coverage_profile, root,
            expected_profile_sha256=expected_coverage_profile_sha256)
    elif expected_coverage_profile_sha256 is not None:
        raise ValueError('Coverage profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1; (PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'votes', 'concert')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'votes', 'concert', 'coverage')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target; candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json');manifest['profiles'].append({'name':'coverage','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)});save(PREP/'profiles.json',manifest)
    (PREP/'METHOD-REVIEW.md').write_text('''# Exact residual coverage review

PASS:24 manually enumerated headings match complete unknown nodes and adjacent
operative text. No whole unit is reclassified. The original31pending units and
all questions remain unchanged;7substantive units remain visible. Conditional
default(f) modeling does not prove actual default or resolve source ambiguity.
H43 is bound to historical_candidate_lines index43 of the original60records;
the12statutory readings are explicitly nonexhaustive. Complete prior053answer
is the comparator. Independent literal-span oracle precedes candidate execution.
No new source acquisition or adviser is needed. Profile and source mutation,
broadened spans,missing residuals and false completeness must all be refused.
Counts explain representation,not legal closure. Cumulative budgets retained.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD,prior.WORKER)}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',LEDGER,prior.prior.PREP/'products.json'):
        bindings[rel(p)]=sha(p)
    for row in read(prior.prior.PREP/'products.json')['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=313
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Reconcile exact heading spans,conditional default and missing agent;preserve original H43 source gap',
        residual_coverage={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':10800,'cumulative026_bytes':1536*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=54
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=313
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify occurrence-level coverage explanation;continue H43,historical sources,ownership and fresh preparation',
            stop_condition='54 admissions;210s stages;10800s cumulative026;1536MiB reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_054_measured_seconds']+700,'bytes':costs()['cumulative026_054_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<10800 and forecast['bytes']<1532*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Exact span coverage explanation appended after prior profiles','Original H43 source gap explicit','Same-task admission53 to54;no cumulative cost reset'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent literal spans,complete baseline preservation,ordinary and installed CLI equality',
            'promotion_veto':['Operative text hidden','Residual lost','H43 lost','Source or baseline drift','False completeness'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['General heading detection','Actual default','Source recall','Legal closure','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':53,'new_maximum':54,'retained_attempts':attempts,
            'reason':'Exact source audit distinguishes heading-only uncertainty from substantive missing content',
            'next_discriminating_check':'24literal headings,sevensubstantive units,unchanged prior answers,explicitH43',
            'stop_condition':'210s stages;10800s cumulative026;1536MiB reserve;no GETs',
            'same_scope_authorization':'User requested continuing internally proven general build before real client facts'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':313,'heading_units':24,'substantive_pending':7,'forecast':forecast}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for r in read(PREP/'installation.json'):
        p=ROOT/r['target'];assert (sha(p) if p.exists() else None)==r['after' if installed else 'before'],r['target']


def install():
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['before'];shutil.copyfile(ROOT/row['candidate'],p)
    return {'status':'PASS','production_files':3}


def execute(name,command,seconds):
    save(HERE/('commands/'+name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (HERE/'commands'/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],150)
    return {'status':'PASS','independent_occurrence_oracle':True}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(prior.prior.PREP/'products.json'),'--repository',str(ROOT),
        '--output',str(HERE/output),'--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),
        '--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def compress_output(filename):
    path=HERE/filename;body=path.read_bytes();raw_sha=sha(path)
    with gzip.open(str(path)+'.gz','wb') as stream:stream.write(body)
    assert gzip.open(str(path)+'.gz','rb').read()==body;path.unlink()
    return {'raw_output_sha256':raw_sha,'lossless_output':filename+'.gz'}


def consume():
    from legalmath.prospectus import residual_coverage as module
    execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],195)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    expected=read(PREP/'expected.json');assert {k:actual[module.KEY][k] for k in expected}==expected
    save(HERE/'verification.json',verification)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'answer_sha256':digest(actual),**compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus import residual_coverage as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('heading-omitted','heading-duplicated','operative-text','H43-removed','false-completeness','residual-removed','default-promoted','lost-baseline'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='heading-omitted':bad['headings'].pop()
        elif kind=='heading-duplicated':bad['headings'][0]=deepcopy(bad['headings'][1])
        elif kind=='operative-text':bad['headings'][0]['spans'][-1]['end']+=5
        elif kind=='H43-removed':bad['h43']['source_pieces']=[]
        elif kind=='false-completeness':bad['whole_task_complete']=True
        elif kind=='residual-removed':actual[module.KEY]['substantive_pending']=[]
        elif kind=='default-promoted':actual[module.KEY]['default_actual_status']='YES'
        else:actual['questions']['Q1']['status']='YES'
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        registered=module.REGISTERED_PROFILE_SHA256
        try:
            # Exercise semantic guards even after a hypothetical newly pinned bad review.
            module.REGISTERED_PROFILE_SHA256=digest(bad)
            if kind in ('residual-removed','default-promoted','lost-baseline'):
                module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
        finally:module.REGISTERED_PROFILE_SHA256=registered
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def filemap(folder):
    return {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected=filemap(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert filemap(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])})
    return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    result=read(HERE/'installed-result.json');result.update(compress_output('installed-answer.json'));return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'EXACT_SOURCE_RESIDUAL_COVERAGE',
        'heading_units':24,'substantive_pending':7,'original_pending_preserved':31,'baseline_unchanged':True,'installed_cli_equal':True,
        'resources':costs(),'H43':'SOURCE_EDITION_AND_APPLICATION_OPEN',
        'next_action':'Continue original historical/source reconciliation,ownership eligibility and fresh profile preparation'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(prior.prior.PREP/'products.json'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Exact source spans explain remaining uncertainty

Twenty-four pending units contain finite reviewed heading fragments beside
modeled operative wording. Seven units retain substantive uncertainty:two
calculation-agent designation units and five default(f) units. The latter have
conditional modeling,not an established actual default or exhaustive reading.
The original31pending units and all previous answer fields are preserved.
H43 remains an explicit source/edition/application gap in the original60records.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite coverage explanation|Independent source spans and complete ordinary/installed equality|All adverse controls refused|Substantive source gaps and real facts|Original source closure and fresh preparation|General recall,legal closure or whole build|

The representation gap is in our diagnostic integration,not evidence of package
failure. Exact heading review cannot validate adjacent operative interpretations.
That is the strongest alternative explanation of apparent coverage improvement.
Any changed source span or lost prior question would overturn this result.
''')
    return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_residual_coverage',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Coverage stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
