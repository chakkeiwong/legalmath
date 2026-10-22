"""Reviewed source-application repair under the sole prospectus authority."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_definition_integration as old
from scripts import prospectus_definition_controls as previous
from scripts import prospectus_definition_applications_oracle as oracle
from scripts.prospectus_typed_delta import changes, apply, equal
from legalmath.prospectus.successor.contracts import digest

AUTH=old.AUTH
PREP=AUTH/'reviews/definition-scope-repair-289'
HERE=AUTH/'attempts/basf-references/attempt-030'
METHOD='scripts/prospectus_definition_applications.py'
ORACLE='scripts/prospectus_definition_applications_oracle.py'
PLAN='docs/plans/prospectus-definition-scope-repair-2026-10-18.md'
REVIEW=old.rel(PREP/'METHOD-REVIEW.md')
DEST='src/legalmath/prospectus/successor/'
read,save,sha,rel=old.read,old.save,old.sha,old.rel
STAGES=('install','tests','variants',
        *sum((('build-'+v,'downstream-'+v,'consume-'+v,'verify-'+v) for v in oracle.LABELS),()),
        *('controls-'+str(i) for i in range(5)),'reconcile','seal')
SCRIPTS=(METHOD,ORACLE,'scripts/prospectus_definition_variant_preparation.py',
         'scripts/prospectus_definition_application_preparation.py',
         'scripts/prospectus_definition_application_expectations.py')


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_029_measured_seconds']+extra
    seconds+=sum(read(PREP/n)['wall_seconds'] for n in
                 ('source-preparation.json','application-preparation.json'))
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (*SCRIPTS,PLAN))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0289.json')
    size=start['prior_resources']['cumulative026_029_bytes']
    size+=sum(p.stat().st_size for p in paths if p.exists())
    for row in read(PREP/'installation.json')['files'] if (PREP/'installation.json').exists() else ():
        p=ROOT/row['target']
        if p.exists():
            size+=max(0,p.stat().st_size-row['before_bytes'])
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<3600 and size<220*1024**2,'Cumulative026–030 resource bound exhausted'
    return {'cumulative026_030_measured_seconds':seconds,'cumulative026_030_bytes':size,
        'seconds_bound':3600,'bytes_bound_including_4MiB_reserve':224*1024**2,
        'historical_manual_controller_seconds':'UNKNOWN','prior_costs_reset':False,
        'expectation_freeze_command_wall_seconds':'UNKNOWN; short source-only preparation, not counted as zero',
        'prior_snapshot_sha256':sha(PREP/'accounting-start.json')}


def prepare():
    from legalmath.prospectus.execution_authority import Authority,CODE,digest as authority_digest
    program=read(AUTH/'program.json')
    assert program['revision']==288
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==29 and read(previous.HERE/'result.json')['full_trial_complete']
    assert any(e['kind']=='RECORD' and e.get('attempt')==rel(previous.HERE) for e in events)
    for folder in (old.HERE,previous.HERE):
        for name,value in read(folder/'outputs.json').items():
            assert sha(folder/name)==value,name
    for name,value in read(PREP/'source-freeze.json').items():
        assert sha(PREP/name)==value,name
    for name,value in read(PREP/'application-expected-freeze.json').items():
        assert sha(PREP/name)==value,name
    for name,value in read(PREP/'supplement-expectation-freeze.json')['bindings'].items():
        assert sha(PREP/name)==value,name
    save(PREP/'accounting-start.json',{'prior_resources':previous.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    candidate=PREP/'candidate'
    template=candidate/'definition_applications.py'
    text=template.read_text()
    assert text.count('REPLACE_WITH_APPLICATION_SPEC_DIGEST')==1
    template.write_text(text.replace('REPLACE_WITH_APPLICATION_SPEC_DIGEST',digest(read(PREP/'candidate-spec.json.gz'))))
    with (candidate/'definition_applications_spec.json.gz').open('xb') as stream:
        stream.write((PREP/'candidate-spec.json.gz').read_bytes())
    base=(ROOT/(DEST+'definition_scopes.py')).read_text()
    original="fields(value, {'profile', 'profile_sha256'}, {'profile', 'profile_sha256'})"
    replacement="fields(value, {'profile', 'profile_sha256', 'applications'}, {'profile', 'profile_sha256'})"
    assert base.count(original)==1
    staged=base.replace(original,replacement)
    original="if value != {'profile': spec['profile'], 'profile_sha256': PROFILE_SHA256}:"
    replacement="if {k:value[k] for k in ('profile','profile_sha256')} != {'profile': spec['profile'], 'profile_sha256': PROFILE_SHA256}:"
    assert staged.count(original)==1
    staged=staged.replace(original,replacement)
    original="return {'version':'definition-source-review.v1'"
    assert staged.count(original)==1
    staged=staged.replace(original,"report = {'version':'definition-source-review.v1'")
    original="        'provenance_gaps_repaired':False}\n"
    replacement=original+"""    if 'applications' in value:
        from . import definition_applications
        report['application_supplement'] = definition_applications.admit(text,value['applications'],report)
    return report
"""
    assert staged.count(original)==1
    staged=staged.replace(original,replacement)
    with (candidate/'definition_scopes.py').open('x') as stream:
        stream.write(staged)
    rows=[]
    for name in ('definition_forms.py','definition_applications.py','definition_applications_spec.json.gz','definition_scopes.py'):
        target=ROOT/(DEST+name)
        path=candidate/name
        if path.suffix=='.py':
            ast.parse(path.read_text())
        row={'target':rel(target),'candidate':rel(path),'after_sha256':sha(path),
             'before_sha256':sha(target) if target.exists() else None,
             'before_bytes':target.stat().st_size if target.exists() else 0}
        if target.exists():
            snapshot=PREP/'baseline'/name
            snapshot.parent.mkdir(parents=True,exist_ok=True)
            with snapshot.open('xb') as stream:
                stream.write(target.read_bytes())
            row['snapshot']=rel(snapshot)
        rows.append(row)
    save(PREP/'installation.json',{'files':rows,'changes':'Optional source-application supplement; other source files unchanged'})
    # Source-only complete expectation and retention audit, never evaluate candidate.
    base_products,base_answer=oracle.baseline()
    expected,expected_answer=oracle.expected('assisted')
    delta=changes(base_products,expected)
    equal(apply(base_products,delta),expected,'Expected product retention is lossy')
    equal(apply(base_answer,changes(base_answer,expected_answer)),expected_answer,'Expected answer retention is lossy')
    assert len(expected['P3']['payload']['definition_sources']['application_supplement']['applications'])==25
    for case in oracle.CONTROLS:
        altered=oracle.mutate(case,expected)
        assert digest(altered)!=digest(expected['P3']['payload']),case
    binding_names=[*CODE,*SCRIPTS,PLAN,REVIEW]
    binding_names += [rel(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    binding_names += [rel(old.HERE/'outputs.json'),rel(previous.HERE/'outputs.json'),
                      rel(old.PREP/'freeze.json'),rel(previous.PREP/'freeze.json')]
    bindings={n:sha(ROOT/n) for n in dict.fromkeys(binding_names)}
    # Bind installed dependencies other than the four files intentionally changed.
    targets={r['target'] for r in rows}
    bindings.update({rel(p):sha(p) for p in (ROOT/DEST).glob('*.py') if rel(p) not in targets})
    save(PREP/'freeze.json',{'bindings':bindings,'candidate_evaluated':False})
    resource=costs()
    # Measured 028 build/downstream/consume/compare ~200–220s per route;
    # five four-control batches ~50s each; extra 200s covers setup and sealing.
    projected_seconds=resource['cumulative026_030_measured_seconds']+3*225+5*60+200
    projected_bytes=resource['cumulative026_030_bytes']+4*(AUTH/'program.json').stat().st_size+12*1024**2
    assert projected_seconds<3600 and projected_bytes<220*1024**2
    save(PREP/'resource-forecast.json',{'status':'PASS','candidate_evaluated':False,
        'prior_resources':resource,'projected_measured_seconds':projected_seconds,
        'projected_bytes':projected_bytes,'runtime_basis':'028 complete routes;029 measured four-control batches',
        'retention':'Reversible typed deltas against checked complete028 answer',
        'estimate_only':True,'no_time_extension':True})
    proposal=deepcopy(program)
    proposal['revision']=289
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=[p for p in task['inputs'] if p not in targets]
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+
                                   [rel(PREP/'freeze.json'),rel(PREP/'resource-forecast.json')]))
    task.update(dossier=PLAN,pre_admission_review=REVIEW,
        reason='Repair reproduced split-line source omission and retain25 conditional source-application decisions through ordinary answers',
        definition_application_repair={'review':rel(PREP),'installation':rel(PREP/'installation.json'),
            'source':rel(old.SOURCE),'comparator':rel(old.HERE),'decisions':25,
            'original_task_complete':False,'cumulative026_030_seconds':3600,
            'cumulative026_030_bytes_including_4MiB_reserve':224*1024**2,
            'no_external_adviser_prerequisite':True})
    proposal['budgets']['basf-references']['maximum_new_attempts']=30
    routes=read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision']=289
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(dossier=PLAN,task_sha256=authority_digest(task),
                next_action='Execute frozen omission and conditional-source application repair, retain complete comparisons; then missing-source and historical-law work',
                stop_condition='30 admissions;180s stages;3600s cumulative026 onward;224MiB with4MiB reserve;no unchanged retries')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),REVIEW:sha(ROOT/REVIEW),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Repair one reproduced missing source occurrence with mapped supplied forms',
            '25 conditional assisted applications with explicit scope premises;retain all original records and uncertainties',
            'Keep cumulative3600s;storage160 to224MiB with4MiB reserve;admissions29 to30'],
        'skeptical_audit':{'verdict':'PASS','review':REVIEW,
            'pre_run_flaws_repaired':['Bound output amplification','Reject split-line dash components'],
            'source_freeze':rel(PREP/'source-freeze.json'),'expectation_freeze':rel(PREP/'supplement-expectation-freeze.json'),
            'actual_method_freeze':rel(PREP/'freeze.json'),'resource_forecast':rel(PREP/'resource-forecast.json')},
        'evidence_contract':{'primary':'Exact5 amount occurrences,25 source decisions,three complete product/answer comparisons and20 actual consumer refusals',
            'baseline':'Sealed028 complete assisted products and answer;completed029 controls retained',
            'promotion_veto':['Accepted forgery','Wrong exception origin','Scope leakage','Lost uncertainty','Changed financial/statutory payload'],
            'continuation_veto':['Corrupt inputs','Method drift','Missing results','Exhausted cumulative limits'],
            'explanatory_only':['Counts','Runtime','Regression tests'],
            'not_concluded':['General recall','Automatic legal reasoning','External-package limitation','Whole-build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':29,'new_maximum':30,
            'retained_attempts':attempts,'reason':'New source omission and source-explicit conditional application question after completed finite integration',
            'next_discriminating_check':'Independent source gold and complete ordinary answers with20 validly resealed controls',
            'stop_condition':'180s stages;3600s cumulative;224MiB with4MiB reserve;no unchanged retries',
            'same_scope_authorization':'User requested refreshed master and continued internal supported-behavior build'},
        'resource_revision':{'prior_seconds':3600,'new_seconds':3600,'prior_bytes':160*1024**2,
            'new_bytes':224*1024**2,'reserve_bytes':4*1024**2,'prior_costs_retained':True},
        'original_obligations_preserved':True,'candidate_evaluated':False}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':289,'resources':costs(),
        'projected_measured_seconds':projected_seconds,'candidate_evaluated':False}


def frozen(installed=True):
    from legalmath.prospectus.execution_authority import Authority,digest as authority_digest
    admission=read(HERE/'admission.json')
    assert authority_digest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,value in read(PREP/'freeze.json')['bindings'].items():
        assert sha(ROOT/name)==value,name
    for folder in (old.HERE,previous.HERE):
        for name,value in read(folder/'outputs.json').items():
            assert sha(folder/name)==value,name
    for row in read(PREP/'installation.json')['files']:
        path=ROOT/row['target']
        assert (sha(path) if path.exists() else None)==row['after_sha256' if installed else 'before_sha256'],row['target']


def install():
    frozen(installed=False)
    for row in read(PREP/'installation.json')['files']:
        target=ROOT/row['target']
        temporary=target.with_name(target.name+'.application-install')
        with temporary.open('xb') as stream:
            stream.write((ROOT/row['candidate']).read_bytes())
        temporary.replace(target)
    frozen()
    return {'status':'PASS','installed_reviewed_files':4}


def tests():
    command=[sys.executable,'-m','pytest','-q',
        'tests/prospectus_successor/test_reference_consumer_integrity.py',
        'tests/prospectus_successor/test_law_assistance_mode.py',
        'tests/prospectus_successor/test_unavailable_references.py']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=150)
    save(HERE/'checks/regressions.json',{'command':command,'returncode':result.returncode,
        'stdout':result.stdout,'stderr':result.stderr,'role':'ENGINEERING_REGRESSION_ONLY'})
    assert result.returncode==0,'Focused regression failed'
    return {'status':'PASS','tests':result.stdout.strip()[-200:]}


def retain(label,products,answer=None):
    base,base_answer=oracle.baseline()
    delta=changes(base,products)
    equal(apply(base,delta),products,'Lossy retained products')
    row={'base':rel(old.HERE/'assisted-answer.json.gz'),
         'base_file_sha256':sha(old.HERE/'assisted-answer.json.gz'),
         'products_delta':delta,'products_sha256':digest(products)}
    if answer is not None:
        delta=changes(base_answer,answer)
        equal(apply(base_answer,delta),answer,'Lossy retained answer')
        row.update(answer_delta=delta,answer_sha256=digest(answer))
    save(HERE/(label+'.json.gz'),row)


def retained(label):
    row=read(HERE/(label+'.json.gz'))
    assert row['base']==rel(old.HERE/'assisted-answer.json.gz') and sha(ROOT/row['base'])==row['base_file_sha256']
    base,answer=oracle.baseline()
    products=apply(base,row['products_delta'])
    assert digest(products)==row['products_sha256']
    answer=apply(answer,row['answer_delta']) if 'answer_delta' in row else None
    assert answer is None or digest(answer)==row['answer_sha256']
    return products,answer


def build(label):
    from legalmath.prospectus.successor import service,definition_applications
    base,_=oracle.baseline()
    p=dict(base)
    value=deepcopy(p['P3']['payload']['interpretation_input'])
    if label!='absent':
        packet=deepcopy(value['definition_sources'])
        packet['applications']=definition_applications.packet()
        if label=='assisted':
            value['definition_sources']=packet
        else:
            assert label=='request-route'
            del value['definition_sources']
            payload=deepcopy(p['P1']['payload'])
            payload['request']['definition_sources']=packet
            service.validate_request(payload['request'])
            p['P1']=service.seal('P1',payload['request']['bundle'],{'request':digest(payload['request'])},payload)
            p['P2']=service.seal('P2',payload['request']['bundle'],{'P1':p['P1']['sha256']},base['P2']['payload'])
    p['P3']=service.interpretation_product(p['P1'],p['P2'],value)
    retain(label+'-p3',p)
    return {'status':'PASS','label':label,'actual_p3_retained':True}


def downstream(label):
    from legalmath.prospectus.successor import service
    p,_=retained(label+'-p3')
    law,finance=p['P4']['payload'],p['P5']['payload']
    p['P4']=service.law_product(p['P1'],p['P3'],law['cases'],law['law_input'])
    p['P5']=service.financial_product(p['P1'],p['P2'],p['P3'],finance['cases'],finance['scenario_input'])
    retain(label+'-products',p)
    return {'status':'PASS','label':label,'actual_downstream_products_retained':True}


def consume(label):
    from legalmath.prospectus.successor import service
    p,_=retained(label+'-products')
    answer=service.consume(p,ROOT,mode='frozen')
    retain(label+'-answer',p,answer)
    return {'status':'PASS','label':label,'complete_ordinary_answer_retained':True}


def compare(label):
    p,answer=retained(label+'-answer')
    predicted,predicted_answer=oracle.expected(label)
    equal(p,predicted,'Complete products differ: '+label)
    equal(answer,predicted_answer,'Complete ordinary answer differs: '+label)
    base,base_answer=oracle.baseline()
    for key in ('P4','P5'):
        equal(p[key]['payload'],base[key]['payload'],'Protected downstream payload changed')
    report=answer['definition_sources']
    equal(report['records'],base_answer['definition_sources']['records'],'Original source records changed')
    assert len(report['records'])==62 and sum(len(r['uses']) for r in report['records'])==610
    equal(answer['questions'],base_answer['questions'],'Original questions or uncertainties changed')
    save(HERE/(label+'-comparison.json'),{'status':'PASS','complete_products_equal':True,
        'complete_answer_equal':True,'expected_products_sha256':digest(predicted),
        'expected_answer_sha256':digest(predicted_answer),'actual_answer_sha256':digest(answer),
        'original_source_records_retained':62,'protected_payloads_equal':True,
        'expected_from_candidate':False})
    return {'status':'PASS','label':label,'complete_products_equal':True,'complete_answer_equal':True}


def controls(batch):
    from legalmath.prospectus.successor import service
    p,_=retained('assisted-products')
    cases=oracle.CONTROLS[batch*4:(batch+1)*4]
    for case in cases:
        forged=oracle.transport.reseal(p,oracle.mutate(case,p))
        assert digest(forged)!=digest(p)
        retain('control-'+case,forged)
        restored,_=retained('control-'+case)
        equal(restored,forged,'Retained forgery changed')
        try:
            service.consume(restored,ROOT,mode='frozen')
        except ValueError as exc:
            save(HERE/('controls/'+case+'-actual.json'),{'type':type(exc).__name__,'message':str(exc)})
            error,function,module=oracle.refusal_expectation(case)
            receipt=oracle.transport.refusal(exc,error,function,module)
            save(HERE/('controls/'+case+'.json'),{'case':case,'validly_resealed':True,**receipt})
        else:
            raise ValueError('Resealed application forgery accepted: '+case)
    return {'status':'PASS','batch':batch,'actual_consumer_refusals':len(cases)}


def reconcile():
    for stage in STAGES[:-2]:
        assert read(HERE/'stages'/stage/'result.json')['status']=='PASS',stage
    for label in oracle.LABELS:
        comparison=read(HERE/(label+'-comparison.json'))
        assert comparison['complete_products_equal'] and comparison['complete_answer_equal']
    for case in oracle.CONTROLS:
        row=read(HERE/('controls/'+case+'.json'))
        error,function,module=oracle.refusal_expectation(case)
        assert row['message']==error and row['origin']['module']==module and row['origin']['function']==function
    save(HERE/'reconciliation.json.gz',{
        'prior':read(previous.HERE/'reconciliation.json.gz'),
        'source_supplement':read(PREP/'source-supplement.json.gz'),
        'applications':read(PREP/'application-spec.json.gz'),
        'original_records':62,'original_use_associations':610,'original_references':60,
        'new_occurrence_count':1,'new_associations':2,'denominator_replaced':False,
        'original_task_complete':False})
    return {'status':'PASS','complete_product_answer_comparisons':3,
        'actual_consumer_refusals':20,'conditional_source_decisions':25,
        'source_omission_repaired':True,'original_task_complete':False}


def seal():
    result={**read(HERE/'stages/reconcile/result.json'),'task':'basf-references',
        'result_kind':'FINITE_CONDITIONAL_DEFINITION_APPLICATION','resources':costs(),
        'next_action':'Missing definition, provenance, calculation-date and historical-law source analysis',
        'remaining':['Unresolved source meanings','Historical statutory application','General discovery',
                     'Original whole-build acceptance'],'external_adviser_prerequisite':False}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'commands':[read(HERE/'stages'/stage/'started.json')['command'] for stage in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':sha(old.SOURCE/'bound-inventory.json.gz'),
        'wall_time':result['resources'],'plan':PLAN,'review':REVIEW,'result':rel(HERE/'result.json')})
    with (HERE/'RESULT.md').open('x') as stream:
        stream.write("""# Missing phrase repaired; conditional source applications checked

The supplied-form mechanism finds all five independently fixed early-amount
occurrences, including the omitted split-line declaration in section 5(10)(b).
It preserves exact offsets and rejects the declared whitespace, boundary and
amplification failures. The optional supplement records 25 source-reviewed
decisions, distinguishing tax and make-whole amounts, holder and issuer dates,
section 10 affiliation and section 14(4) custody. It remains assisted.

Three complete product/ordinary-answer comparisons and 20 actual consumer
refusals passed. Original 62 records, 610 associations and 60 references remain;
the new occurrence and two possible associations are a versioned supplement.
All original question uncertainties and financial/statutory payloads remain.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain finite conditional applications | Exact source gold, complete comparisons and actual refusals pass | No finite-trial veto | Further source omissions, unresolved meaning and dated law | Continue source analysis | Automatic legal interpretation, universal recall or completed build |

The failures were local authored enumeration and lexical boundary handling.
No finding establishes a fundamental limitation of an external package.
The express source premises justify these conditional readings; actual client
facts, valuation inputs and historical statutory applicability remain separate.
The strongest alternative explanation is further shared source-reading error;
contrary source text would require a revised reading, not hidden uncertainty.
""")
    return {'status':'PASS','finite_trial_complete':True,'original_task_complete':False,'resources':costs()}


def main():
    assert len(sys.argv)==2
    stage=sys.argv[1]
    if stage=='remaining':
        for name in STAGES:
            folder=HERE/'stages'/name
            if (folder/'result.json').exists():
                assert read(folder/'result.json')['status']=='PASS'
                continue
            assert not (folder/'started.json').exists(),'Unchanged stage retry refused: '+name
            result=subprocess.run([sys.executable,'-m','scripts.prospectus_definition_applications',name],
                                  cwd=ROOT,timeout=195)
            if result.returncode:
                raise SystemExit(result.returncode)
        return
    assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged stage retry refused'
    if stage!='prepare':
        for name in STAGES[:STAGES.index(stage)]:
            assert read(HERE/'stages'/name/'result.json')['status']=='PASS',name
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_applications',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Definition application stage limit')))
    signal.alarm(180)
    try:
        if stage=='prepare':
            result=prepare()
        else:
            frozen(installed=stage!='install')
            if stage=='variants':
                result=oracle.variants(sys.modules[__name__])
            elif stage.startswith('controls-'):
                result=controls(int(stage.split('-')[1]))
            elif any(stage.startswith(prefix+'-') for prefix in ('build','downstream','consume','verify')):
                prefix,label=stage.split('-',1)
                result=(compare if prefix=='verify' else globals()[prefix])(label)
            else:
                result=globals()[stage]()
            frozen()
        costs(time.monotonic()-started)
        result['wall_seconds']=time.monotonic()-started
        save(folder/'result.json',result)
        if stage=='seal':
            save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
        print(old.json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    main()
