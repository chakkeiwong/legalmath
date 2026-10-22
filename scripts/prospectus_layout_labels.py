"""Existing layout and lexical tools composed under retained accounting."""
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib.util, json, shutil, signal, sys, time
from scripts import prospectus_payment_categories as prior
from scripts import prospectus_layout_label_oracle as oracle
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH,engine=prior.ROOT,prior.AUTH,prior.engine
PREP=AUTH/'reviews/layout-labels-324'
HERE=AUTH/'attempts/basf-references/attempt-063'
PLAN='docs/plans/prospectus-layout-labels-2026-10-19.md'
METHOD='scripts/prospectus_layout_labels.py';WORKER='scripts/prospectus_layout_labels_installed.py'
ORACLE='scripts/prospectus_layout_label_oracle.py';TEST='tests/prospectus_successor/test_layout_labels.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST,'scripts/prospectus_layout_label_cases.py','docs/implementation/prospectus-execution-authority/reviews/post-323-gap-analysis.md')
TARGETS=('src/legalmath/prospectus/successor/layout_labels.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
PRODUCTS=prior.PRODUCTS;STAGES=prior.STAGES
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel



def baseline():
    manifest=read(PRODUCTS);products={}
    for key,row in manifest['products'].items():
        path=ROOT/row['path'];assert sha(path)==row['sha256'];products[key]=read(path)
    assert digest(products)==read(prior.PREP/'profile.json')['products_sha256']
    answer=read(prior.HERE/'ordinary-answer.json.gz')
    assert digest(answer)=='9e9025891b4aff7d14fb257e372ef42d3b860631b2ebb383c7abaca8fee6607d'
    return products,answer

def testfiles():return [TEST,*prior.testfiles()]


def tests():
    import xml.etree.ElementTree as ET
    engine.execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',
        *[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],150)
    suites=list(ET.parse(HERE/'pytest.xml').getroot().iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped'))
    return {'status':'PASS','independent_source_mapping_oracle':True,**counts}


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['combined_measured_seconds']+read(PREP/'case-preparation.json')['wall_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0324.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['combined_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in read(PREP/'production-bytes.json').items() if (ROOT/n).exists())
    assert seconds<14400 and size<2300*1024**2,'Combined retained resource bound'
    return {'combined_measured_seconds':seconds,'combined_bytes':size,'prior_costs_reset':False,
        'seconds_bound':14400,'bytes_bound_with_4MiB_reserve':2304*1024**2,
        'unmeasured_authoring_and_older_office_time':'UNKNOWN; never treated as zero'}



def prepare():
    program=read(AUTH/'program.json');assert program['revision']==323
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==62 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    freeze=read(PREP/'cases-freeze.json')
    assert sha(PREP/'cases.json')==freeze['cases_sha256']
    assert sha(ROOT/freeze['authoring_method'])==freeze['authoring_method_sha256']
    assert sha(ROOT/freeze['plan'])==freeze['plan_sha256']
    for path,checksum in freeze['source_files'].items():assert sha(ROOT/path)==checksum
    save(PREP/'production-bytes.json',{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS})
    candidate=PREP/'candidate/layout_labels.py';candidate.parent.mkdir(exist_ok=True)
    shutil.copyfile(PREP/'candidate.py',candidate)
    spec=importlib.util.spec_from_file_location('legalmath.prospectus.successor._layout_labels_candidate',candidate)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    products,ordinary=baseline();cases=read(PREP/'cases.json')['cases'];original=cases[0]
    from scripts import prospectus_layout_label_cases as authored
    row={'id':original['id'],'product_path':rel(authored.PRODUCT),'product_file_sha256':sha(authored.PRODUCT),
        'pdf_path':rel(authored.PDF),'source_sha256':authored.PDF_HASH,
        'image_path':rel(authored.IMAGE),'image_sha256':authored.IMAGE_HASH,'document':'bes-2010-en','page':190,
        'raw_units_sha256':digest(original['raw_units']),'language':original['language'],
        'quotation_convention':original['quotation_convention'],'layout':deepcopy(original['layout']),
        'review_reason':'Inspected original image: two vertical margin labels and190 are outside body;line26 body retained from offset4'}
    actual_request=module.source_request(row,ROOT);assert actual_request['raw_units']==original['raw_units']
    profile={'version':module.VERSION,'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),
        'sources':[row],'scope_admitted':False,'meaning_admitted':False}
    save(PREP/'profile.json',profile)
    old_labels=next(r for r in ordinary['unicode_label_review']['sources'] if r['source']['id']=='audit-code-names')
    assert any('Annual Report BES Group' in r['label'] for r in old_labels['report']['names'])
    save(PREP/'baseline-gap.json',{'classification':'VERTICAL_MARGIN_INTERLEAVED_IN_LINEAR_DERIVATIVE',
        'legacy_names':[r['label'] for r in old_labels['report']['names']],
        'raw_derivative_preserved':True,'candidate_label_evaluated':False,
        'original_page_units':len(original['raw_units'])})
    text=(ROOT/TARGETS[1]).read_text();old='            payment_categories_profile=None, expected_payment_categories_profile_sha256=None):'
    assert text.count(old)==1
    text=text.replace(old,'            payment_categories_profile=None, expected_payment_categories_profile_sha256=None,'+chr(10)+
        '            layout_labels_profile=None, expected_layout_labels_profile_sha256=None):')
    old='    return {**result, "report_sha256": digest(result)}'+chr(10)*3+'def assess('
    new="""    if layout_labels_profile is not None:
        from .layout_labels import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['layout_label_review'] = evaluate(products, baseline, layout_labels_profile, root,
            expected_profile_sha256=expected_layout_labels_profile_sha256)
    elif expected_layout_labels_profile_sha256 is not None:
        raise ValueError('Layout label profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;(PREP/'candidate/service.py').write_text(text.replace(old,new))
    text=(ROOT/TARGETS[2]).read_text();old="'labels', 'payment_categories')";assert text.count(old)==1
    (PREP/'candidate/conditional_profiles.py').write_text(text.replace(old,"'labels', 'payment_categories', 'layout_labels')"))
    (PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    manifest=read(prior.PREP/'profiles.json')
    manifest['profiles'].append({'name':'layout_labels','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,prior.METHOD,prior.WORKER,prior.ORACLE,engine.METHOD,engine.WORKER,'pyproject.toml')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',PRODUCTS):
        bindings[rel(p)]=sha(p)
    for row in read(PRODUCTS)['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    bindings.update(freeze['source_files'])
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=324
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Compose existing raw-word layout projection with Unicode labels; preserve mixed body/margin line and complete previous answer',
        layout_labels={'review':rel(PREP),'original_task_complete':False,
                       'combined_seconds':14400,'combined_bytes':2304*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=63
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=324
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify exact layout-to-name provenance and full answers;continue original scope,source authority and generalization obligations',
            stop_condition='63 admissions;300s stages;combined14400s/2304MiB;no GETs or unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
        rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['combined_measured_seconds']+900,
              'bytes':costs()['combined_bytes']+100*1024**2,'estimate_only':True}
    assert forecast['seconds']<14400 and forecast['bytes']<2300*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Existing layout and lexical tools composed with exact provenance','Original raw derivative and prior answer retained'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Authored source spans, exact character accounting, ordinary/installed complete answers',
            'promotion_veto':['Lost body word','Unrecorded margin deletion','Wrong map','Cross-region quotation','Prior answer loss'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Automatic margin classification','Legal meaning','Source authority','Translation equivalence','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':62,'new_maximum':63,'retained_attempts':attempts,
            'reason':'Inspected original BES margin and page number interrupt a lexical name; existing exact projection lacks label provenance composition',
            'next_discriminating_check':'Correct original name with exact two-line source pieces and every excluded character retained',
            'stop_condition':'300s stages;combined14400s/2304MiB;no GETs or unchanged retry',
            'same_scope_authorization':'User requested refreshed master and continued internally established general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':324,'cases':len(cases),'forecast':forecast}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(PRODUCTS),'--repository',str(ROOT),'--output',str(HERE/output),
        '--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]



def consume():
    from legalmath.prospectus.successor import layout_labels as module
    engine.execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],270)
    products,ordinary=baseline();actual=read(HERE/'ordinary-answer.json');profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,products,ROOT,expected_profile_sha256=digest(profile))
    report=actual[module.KEY]['sources'][0]['report']
    source_verification=oracle.verify(read(PREP/'cases.json')['cases'][0],report)
    save(HERE/'verification.json',verification);save(HERE/'source-verification.json',source_verification)
    save(HERE/'names.json',[r for region in report['regions'] for r in region['name_provenance']])
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,
        'answer_sha256':digest(actual),**engine.compress_output('ordinary-answer.json')}


def controls():
    from legalmath.prospectus.successor import layout_labels as module
    products,ordinary=baseline();answer=read(HERE/'ordinary-answer.json.gz');profile=read(PREP/'profile.json');refused={}
    for kind in ('source-bytes','product-bytes','image-bytes','page','scope','meaning',
                 'candidate-text','crop-word','duplicate','false-result','lost-prior'):
        bad=deepcopy(profile);actual=deepcopy(answer);row=bad['sources'][0]
        if kind=='source-bytes':row['source_sha256']='0'*64
        elif kind=='product-bytes':row['product_file_sha256']='0'*64
        elif kind=='image-bytes':row['image_sha256']='0'*64
        elif kind=='page':row['page']=191
        elif kind=='scope':bad['scope_admitted']=True
        elif kind=='meaning':bad['meaning_admitted']=True
        elif kind=='candidate-text':row['layout']['texts'][0]['text']=row['layout']['texts'][0]['text'].replace('Ordem','Other',1)
        elif kind=='crop-word':row['layout']['texts'][0]['prov'][0]['bbox']['l']=42
        elif kind=='duplicate':bad['sources'].append(deepcopy(row))
        elif kind=='false-result':actual[module.KEY]['sources'][0]['report']['raw_replaced']=True
        else:actual['unicode_label_review']['meaning_admitted']=True
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('false-result','lost-prior'):
                module.verify_answer(actual,ordinary,bad,products,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(products,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused})
    return {'status':'PASS','refused':len(refused)}

def installed():
    engine.execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],270)
    result=read(HERE/'installed-result.json');result.update(engine.compress_output('installed-answer.json'));return result



def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'LAYOUT_TO_LEXICAL_SOURCE_PROVENANCE','baseline_unchanged':True,
        'installed_cli_equal':True,'source_authority_established':False,'resources':costs(),
        'next_action':'Continue original scope,source authority and generalization obligations'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PREP/'cases.json'),'wall_time':costs(),
        'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# Source layout and lexical labels are composed

The inspected BES page supplies four quoted names from an explicit body view.
The name Ordem dos Revisores Oficiais de Contas maps to its original two body
lines; the190prefix and both vertical margin labels remain in the excluded
source inventory. The old raw derivative and every prior answer field remain.
Inserted line separators are formatting, never fabricated PDF characters.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional source-map composition|Authored source names and complete character accounting; normal/installed equality|Source,geometry,candidate and answer misuse refused|New-source region selection,legal scope and authority|Original substantive obligations|Automatic page interpretation or whole build|

This was our missing integration between existing layout and lexical tools.
The trial supplies no evidence of a fundamental package defect. A wrong crop
on a different page could still omit operative language while keeping exact
provenance; this finite reviewed page cannot establish automatic segmentation.
""")
    return result

def bind_runner():
    engine.PREP=PREP;engine.HERE=HERE;engine.PLAN=PLAN;engine.METHOD=METHOD;engine.WORKER=WORKER
    engine.TARGETS=TARGETS;engine.costs=costs;engine.testfiles=testfiles;engine.cli_arguments=cli_arguments


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs();bind_runner()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_layout_labels',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':300})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Layout label stage bound')));signal.alarm(300)
    try:
        if stage!='prepare':engine.frozen(stage!='install')
        result=(globals().get(stage) or getattr(engine,stage))()
        if stage!='prepare':engine.frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
