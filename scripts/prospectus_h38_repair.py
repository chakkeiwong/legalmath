"""Source-numbered SchVG correction, bounded by the single master program."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,re,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_schvg_exact_redirect as prior
from scripts import prospectus_structural_integration as base
from scripts import prospectus_conditional_rebind as conditional
from scripts.prospectus_typed_delta import changes,apply,equal
from scripts.prospectus_structural_oracle import seal as predict_seal
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=base.AUTH;PREP=AUTH/'reviews/h38-numbered-repair-300';HERE=AUTH/'attempts/basf-references/attempt-041'
PLAN='docs/plans/prospectus-schvg-numbered-measures-2026-10-19.md'
METHOD='scripts/prospectus_h38_repair.py';WORKER='scripts/prospectus_h38_installed.py'
TEST='tests/prospectus_successor/test_statutory_numbered_measures.py'
PREFIX='src/legalmath/prospectus/successor/'
read,save,sha,rel=base.read,base.save,base.sha,base.rel
MEANINGS=['Change of maturity, reduction or exclusion of interest','Change of maturity of principal',
 'Reduction of principal','Subordination of note claims in the debtor insolvency proceedings',
 'Conversion or exchange of notes into shares, other securities or other promises of performance',
 'Exchange or release of collateral','Change of the currency of the notes','Waiver or restriction of holders termination rights']
STAGES=('install','tests','interpretation','downstream','consume','control-stale','package','installed','seal')

def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_040_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN,METHOD,WORKER,TEST));paths.add(AUTH/'revisions/0300.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_040_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-old) for n,old in start['production_bytes'].items())
    assert seconds<7200 and size<764*1024**2,'H38 cumulative026 bounds'
    return {'cumulative026_041_measured_seconds':seconds,'cumulative026_041_bytes':size,'prior_costs_reset':False,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':start['prior']['prior_unmeasured_preparation'],
        'seconds_bound':7200,'bytes_bound_including_4MiB_reserve':768*1024**2}

def retained(label):
    p,a=base.retained('answer');v=read(HERE/(label+'.json.gz'))
    p=apply(p,v['products_delta']);assert digest(p)==v['products_sha256']
    if 'answer_delta' in v:a=apply(a,v['answer_delta']);assert digest(a)==v['answer_sha256']
    return p,a

def retain(label,p,a=None):
    old,old_answer=base.retained('answer');v={'products_delta':changes(old,p),'products_sha256':digest(p)}
    if a is not None:v.update(answer_delta=changes(old_answer,a),answer_sha256=digest(a))
    save(HERE/(label+'.json.gz'),v)

def prediction(spec):
    old,old_answer=base.retained('answer');p=deepcopy(old);answer=deepcopy(old_answer)
    semantic=p['P3']['payload'];report=semantic['statutory_references']
    old_record=next(r for r in report['records'] if r['id']=='H38')
    new_record=deepcopy(old_record);new_source=next(r for r in spec['records'] if r['id']=='H38')
    for k in ('reviewed_reading','unresolved_application','numbered_measures'):new_record[k]=deepcopy(new_source[k])
    new_report=deepcopy(report);new_report.update(profile=spec['profile'],profile_sha256=digest(spec))
    new_report['records']=[new_record if r['id']=='H38' else r for r in new_report['records']]
    old_packet=semantic['interpretation_input']['statutory_references']
    new_packet={**deepcopy(old_packet),'profile':spec['profile'],'records':deepcopy(spec['records'])}
    def replace(value):
        if isinstance(value,dict):
            if value==report:return deepcopy(new_report)
            if value==old_packet:return deepcopy(new_packet)
            out={k:replace(v) for k,v in value.items()}
            if isinstance(out.get('id'),str) and out['id'].startswith('statutory-reference:'):
                out['profile_sha256']=digest(spec)
                if out['id']=='statutory-reference:H38':out['record_sha256']=digest(new_record)
            return out
        if isinstance(value,list):return [replace(v) for v in value]
        return value
    p=replace(p);answer=replace(answer);bundle=p['P1']['payload']['request']['bundle']
    for key,parents in [('P3',('P1','P2')),('P4',('P1','P3')),('P5',('P2','P3'))]:
        p[key]=predict_seal(key,bundle,{k:p[k]['sha256'] for k in parents},p[key]['payload'])
    answer['consumed_products']={k:v['sha256'] for k,v in p.items()}
    answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
    equal(answer['questions'],old_answer['questions'],'Question changed')
    save(PREP/'expected.json.gz',{'products_delta':changes(old,p),'products_sha256':digest(p),
        'answer_delta':changes(old_answer,answer),'answer_sha256':digest(answer)})
    return {'status':'PASS','candidate_consumers_invoked':False,'questions_unchanged':True,
        'products_sha256':digest(p),'answer_sha256':digest(answer)}

def expected():
    p,a=base.retained('answer');v=read(PREP/'expected.json.gz');p=apply(p,v['products_delta']);a=apply(a,v['answer_delta'])
    assert digest(p)==v['products_sha256'] and digest(a)==v['answer_sha256'];return p,a

def candidate():
    spec=read(ROOT/(PREFIX+'statutory_references_spec.json'));old_hash=digest(spec)
    record=next(r for r in spec['records'] if r['id']=='H38');source=record['legal_sources'][0]
    text=(ROOT/source['text_path']).read_text();assert sha(ROOT/source['text_path'])==source['text_sha256']
    excerpt=source['excerpts'][0];assert text[excerpt['start']:excerpt['end']]==excerpt['quote']
    block=excerpt['quote'];start=block.index('(3)');end=block.index('(4)')
    matches=list(re.finditer(r'(?m)^([1-9]|10)\.\n([^\n]+)',block[start:end]));assert [int(m[1]) for m in matches]==list(range(1,11))
    measures=[]
    for m,meaning in zip(matches[:8],MEANINGS):
        a=excerpt['start']+start+m.start();b=excerpt['start']+start+m.end()
        measures.append({'number':int(m[1]),'source_path':source['text_path'],'source_sha256':source['text_sha256'],
            'start':a,'end':b,'quote':text[a:b],'meaning':meaning})
    assert 'Verzicht auf das Kündigungsrecht' in measures[-1]['quote']
    old='The contract explicitly cites numbers1–8. Preserve all eight: maturity of\ninterest; reduction/exclusion of interest; maturity of principal; reduction of\nprincipal; subordination; conversion/exchange; exchange/release of security; and\ncurrency change.'
    new='The contract explicitly cites numbers1–8. Preserve the statutory numbering: '+ '; '.join(str(i+1)+'. '+m for i,m in enumerate(MEANINGS))+'.'
    for key in ('reviewed_reading','unresolved_application'):
        assert old in record[key];record[key]=record[key].replace(old,new)
    record['numbered_measures']=measures;spec['profile']='basf-statutory-reviewed-2026-10-19.v2'
    save(PREP/'candidate/statutory_references_spec.json',spec)
    text=(ROOT/(PREFIX+'statutory_references.py')).read_text();assert old_hash in text;text=text.replace(old_hash,digest(spec))
    validator='''
MEASURE_MEANINGS = MEANINGS_LITERAL

def validate_numbered_measures(spec):
    record = next(r for r in spec['records'] if r['id'] == 'H38')
    rows = record.get('numbered_measures')
    if (not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or [r.get('number') for r in rows] != list(range(1, 9))):
        raise ValueError('H38 requires exact ordered statutory measures1-8')
    source = record['legal_sources'][0]; excerpt = source['excerpts'][0]
    import re
    text = excerpt['quote']; start = text.index('(3)'); end = text.index('(4)')
    matches = list(re.finditer(r'(?m)^([1-9]|10)\\.\\n([^\\n]+)', text[start:end]))
    if [int(m[1]) for m in matches] != list(range(1, 11)):
        raise ValueError('H38 primary numbered source changed')
    for row, match, meaning in zip(rows, matches[:8], MEASURE_MEANINGS):
        a = excerpt['start'] + start + match.start(); b = excerpt['start'] + start + match.end()
        expected = {'number': int(match[1]), 'source_path': source['text_path'],
                    'source_sha256': source['text_sha256'], 'start': a, 'end': b,
                    'quote': text[a-excerpt['start']:b-excerpt['start']], 'meaning': meaning}
        if row != expected:
            raise ValueError('H38 numbered measure differs from complete primary source')
    return rows

'''.replace('MEANINGS_LITERAL',repr(MEANINGS))
    text=text.replace('\ndef specification():',validator+'\ndef specification():')
    text=text.replace('    return value\n','    validate_numbered_measures(value)\n    return value\n',1)
    (PREP/'candidate/statutory_references.py').write_text(text)
    installation=[]
    for name in ('statutory_references.py','statutory_references_spec.json'):
        target=PREFIX+name;path=PREP/'candidate'/name
        (PREP/'baseline').mkdir(exist_ok=True);shutil.copyfile(ROOT/target,PREP/'baseline'/name)
        installation.append({'target':target,'before':sha(ROOT/target),'candidate':rel(path),'after':sha(path)})
    save(PREP/'installation.json',installation)
    return spec,source

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==299
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==40 and any(e['kind']=='REJECT' and e.get('attempt')==rel(prior.HERE) for e in events)
    files=[PREFIX+'statutory_references.py',PREFIX+'statutory_references_spec.json']
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[x.name for x in (AUTH/'history').glob('*.json')],'production_bytes':{n:(ROOT/n).stat().st_size for n in files}})
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v
    spec,source=candidate();summary=prediction(spec);save(PREP/'prediction.json',summary)
    (PREP/'METHOD-REVIEW.md').write_text('''# Numbered source correction audit

PASS for reproduced omission8 and incorrect split of1. Eight exact numbered
German items and separate English meanings are required. Independent prediction
is saved before candidate service calls. Preserve all questions,uncertainty,
other sources and conditional192 decisions. Reject obsolete profiles explicitly;
sealed historical evidence remains. Build/install and compare complete output.
The pre-execution audit caught a binding defect: mutable production targets
were also frozen as immutable admission inputs. Follow the established036
installation contract: bind immutable candidate/baseline files and explicitly
validate each production target before/after installation; keep all other
authority inputs frozen. No controller bypass or sealed-evidence edits.
Focused pytest regressions independently check the primary source, unchanged
records, and all six adverse mutations. Counts remain explanatory only.
No acquisition or adviser. Same-task admission40 to41;all prior costs retained
under explicitly increased7200s/768MiB cumulative026 ceilings.
''')
    targets={r['target'] for r in read(PREP/'installation.json')}
    bindings={n:sha(ROOT/n) for n in (*CODE,PLAN,METHOD,WORKER,TEST,'scripts/prospectus_structural_integration.py',
        'scripts/prospectus_structural_oracle.py','scripts/prospectus_typed_delta.py','pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in targets})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file()})
    for p in (prior.HERE/'outputs.json',prior.HERE/'h38-reading-defect.json',base.HERE/'answer.json.gz',
        conditional.HERE/'answer-delta.json.gz',conditional.PREP/'profile.json',ROOT/source['text_path']):bindings[rel(p)]=sha(p)
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=300
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Repair reproduced H38 statutory item8 omission with exact numbered source coverage and full delivery',
        h38_repair={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':7200,'cumulative026_bytes_with_reserve':768*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in targets]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=41
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=300
    for r in routes['tasks']:
        if r['task']=='basf-references':r.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Correct numbered source reading through ordinary/installed consumers;continue conditional application',
            stop_condition='41 admissions;180s stages;7200s cumulative026;768MiB with4MiB reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in targets:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_041_measured_seconds']+1100,
        'bytes':costs()['cumulative026_041_bytes']+3*(AUTH/'program.json').stat().st_size+110*1024**2,'estimate_only':True}
    assert forecast['seconds']<7200 and forecast['bytes']<764*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Repair exact reproduced omission','Admission40 to41;6000 to7200s and640 to768MiB cumulative026;no reset'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Exact numbered source map;full predicted products/answer;conditional192 unchanged;installed delivery',
            'promotion_veto':['Source omission','Unexpected delta','Lost uncertainty','Conditional drift','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Historical applicability','Actual resolution','Whole task completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':40,'new_maximum':41,'retained_attempts':attempts,
            'reason':'Concrete local reading defect needs repair and delivery','next_discriminating_check':'Exact item8 reaches current answer',
            'stop_condition':'180s stages;7200s cumulative026;768MiB with reserve;no GETs',
            'same_scope_authorization':'User requested internally supported correct build and continuous repairs'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':300,'prediction':summary,'forecast':forecast}

def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):
        assert sha(ROOT/row['target'])==row['after' if installed else 'before'],row['target']

def install():
    for row in read(PREP/'installation.json'):
        assert sha(ROOT/row['target'])==row['before'];shutil.copyfile(ROOT/row['candidate'],ROOT/row['target'])
    return {'status':'PASS','production_files':2}

def tests():
    from legalmath.prospectus.successor import statutory_references as module
    spec=module.specification();rows=module.validate_numbered_measures(spec)
    assert [r['number'] for r in rows]==list(range(1,9))
    source=next(r for r in spec['records'] if r['id']=='H38')['legal_sources'][0]
    text=(ROOT/source['text_path']).read_text();assert sha(ROOT/source['text_path'])==source['text_sha256']
    for r in rows:assert text[r['start']:r['end']]==r['quote']
    refused={}
    for kind in ('omit8','duplicate1','wrong-number','quote','offset','meaning'):
        bad=deepcopy(spec);items=next(r for r in bad['records'] if r['id']=='H38')['numbered_measures']
        if kind=='omit8':items.pop()
        elif kind=='duplicate1':items[-1]=deepcopy(items[0])
        elif kind=='wrong-number':items[-1]['number']=9
        elif kind=='quote':items[-1]['quote']+=' changed'
        elif kind=='offset':items[-1]['start']+=1
        else:items[-1]['meaning']='Currency change'
        try:module.validate_numbered_measures(bad)
        except ValueError as e:refused[kind]=str(e)
        else:raise AssertionError(kind)
    save(HERE/'source-controls.json',{'status':'PASS','numbered_sources':8,'refusals':refused})
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',str(ROOT/TEST),'-q','--junitxml='+str(HERE/'pytest.xml')],45)
    return {'status':'PASS','source_items':8,'refusals':len(refused)}

def interpretation():
    from legalmath.prospectus.successor import service
    p,_=base.retained('answer');want,_=expected()
    p['P3']=service.interpretation_product(p['P1'],p['P2'],want['P3']['payload']['interpretation_input'])
    equal(p['P3'],want['P3'],'Actual interpretation differs from independent prediction');retain('interpretation',p)
    return {'status':'PASS','complete_P3_equal':True}

def downstream():
    from legalmath.prospectus.successor import service
    p,_=retained('interpretation');want,_=expected();law,finance=p['P4']['payload'],p['P5']['payload']
    p['P4']=service.law_product(p['P1'],p['P3'],law['cases'],law['law_input'])
    p['P5']=service.financial_product(p['P1'],p['P2'],p['P3'],finance['cases'],finance['scenario_input'])
    equal(p,want,'Complete products differ');retain('products',p)
    return {'status':'PASS','complete_products_equal':True}

def consume():
    from legalmath.prospectus.successor import service
    from legalmath.prospectus import basf_default_f_current as verifier
    p,_=retained('products');_,ordinary=expected();profile=read(conditional.PREP/'profile.json')
    profile.update(products_sha256=digest(p),ordinary_answer_sha256=digest(ordinary))
    save(HERE/'conditional-profile.json',profile)
    actual=service.consume(p,ROOT,mode='frozen',default_f_profile=profile,expected_default_f_profile_sha256=digest(profile))
    v=verifier.verify_answer(actual,ordinary,profile,expected_profile_sha256=digest(profile));assert v['checked_answers']==192
    old_delta=read(conditional.HERE/'answer-delta.json.gz');old=apply(base.retained('answer')[1],old_delta['answer_delta'])
    equal(actual['default_f_review']['scenarios'],old['default_f_review']['scenarios'],'Conditional decisions changed')
    retain('answer',p,actual);save(HERE/'conditional-verification.json',v)
    return {'status':'PASS','complete_ordinary_equal_prediction':True,'conditional_decisions_equal':192,'answer_sha256':digest(actual)}

def control_stale():
    from legalmath.prospectus.successor import service
    p,_=base.retained('answer')
    try:service.consume(p,ROOT,mode='frozen')
    except ValueError as e:
        assert str(e)=='Statutory reference requires the exact registered source reading and edition',str(e)
        save(HERE/'stale-control.json',{'status':'PASS','actual_consumer_refused':True,'error':str(e)})
    else:raise AssertionError('Obsolete profile accepted')
    return {'status':'PASS','stale_profile_refused':True}

def execute(name,command,timeout):
    folder=HERE/'commands';folder.mkdir(exist_ok=True)
    save(folder/(name+'.json'),{'command':command,'timeout_seconds':timeout})
    with (folder/(name+'.log')).open('x') as stream:
        r=subprocess.run(command,cwd=HERE,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    assert r.returncode==0,'Inspect '+name+'.log'

def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected_files=base.package_files(ROOT/'src/legalmath');python=read(base.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected_files
    execute('package-install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert base.package_files(HERE/'installed/legalmath')==expected_files
    save(HERE/'package.json',{'package':expected_files,'python':python,'wheel_sha256':sha(wheels[0])})
    return {'status':'PASS','package_files':len(expected_files)}

def installed():
    execute('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],165)
    return read(HERE/'installed-result.json')

def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'EXACT_H38_NUMBERED_SOURCE_REPAIR',
        'source_items':8,'source_adverse_controls':6,'complete_products_predicted':True,'ordinary_questions_unchanged':True,
        'conditional_decisions_equal':192,'installed_complete_equal':True,'stale_actual_consumer_refused':True,
        'resources':costs(),'historical_application':'UNKNOWN','attribution':'Local source-reading omission repaired;not an external package defect',
        'next_action':'Conditional statutory applications using corrected numbered source;preserve missing historical evidence'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','random_seeds':'N/A deterministic',
        'data_version':sha(base.HERE/'answer.json.gz'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Omitted statutory measure restored in the complete answer

H38 now preserves all eight numbered source items,including waiver/restriction
of termination rights. Item1 remains a single numbered provision with its
alternatives. Exact source spans and independently checked English meanings
reach current products and ordinary/installed consumers. Six adverse mutations
and the actual obsolete-profile consumer are refused. All questions and
uncertainties remain identical;all192 default(f) decisions remain identical.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain exact reading repair |8 sources,full predicted answer,installed equality |No unexplained delta;controls refused |Historical application and other legal meanings |Supported conditional application |Actual resolution or completed build |

The source omission was local transcription. Package installation reproduced
the correction. The strongest alternative explanation for later legal error
remains another incomplete supplied reading;this finite repair does not rule
that out. Historical2021 source acquisition remains failed and retained.
''')
    return result

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_h38_repair',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':180})
    begin=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('H38 stage bound')));signal.alarm(180)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage.replace('-','_')]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-begin);result['wall_seconds']=time.monotonic()-begin;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as e:save(folder/'failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-begin});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
