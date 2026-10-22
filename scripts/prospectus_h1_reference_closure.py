"""Reviewed optional H1 reference view, serialized and bounded by authority."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import prospectus_h1_relationship_runner_repair as prior
from scripts import prospectus_h1_reference_mapping as mapping

base=prior.base
common=prior.common
read,save,require,sha,digest,rel=common.read,common.save,common.require,common.sha,common.digest,common.rel
AUTH,BASE=prior.AUTH,prior.BASE
HERE=BASE/'attempt-066'
PREP=AUTH/'reviews/h1-reference-closure-429'
AUDIT=mapping.source.TEMP
SELF='scripts/prospectus_h1_reference_closure.py'
MAPPING='scripts/prospectus_h1_reference_mapping.py'
PLAN=mapping.source.PLAN
TESTS=base.TESTS
MUTABLE={mapping.MODULE,mapping.WRAPPER}
DEPENDENCIES={'source':[],'implement':['source'],'tests':['implement'],
    'ordinary':['tests'],'compare':['ordinary'],'legacy':['compare'],
    'package':['legacy'],'installed':['package'],'installed-compare':['installed'],
    'installed-legacy':['installed-compare']}
for case in mapping.CASES:
    DEPENDENCIES['control-'+case]=['compare']
    DEPENDENCIES['installed-control-'+case]=['installed-compare','control-'+case]
DEPENDENCIES['coverage']=[]


def costs(reserve=0,seconds_reserve=0):
    start=read(PREP/'accounting-start.json')
    paths={p for folder in (PREP,HERE,AUDIT,mapping.source.previous.TEMP) if folder.exists()
        for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (SELF,MAPPING,PLAN,'scripts/prospectus_h1_reference_map.py',
        'scripts/prospectus_h1_reference_state_audit.py','docs/plans/prospectus-h1-reference-state-audit-2026-10-22.md',mapping.MODULE))
    paths.add(AUTH/'revisions/0429.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(ROOT/mapping.WRAPPER).stat().st_size-start['wrapper_bytes'])
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds=sum(r['wall_seconds'] for folder in (PREP,HERE) for p in folder.glob('commands/*.json')
        if (r:=read(p)).get('accounting_role')!='NESTED_IN_PARENT')
    return {'new_bytes':size,'new_measured_seconds':seconds,'new_control_seconds':60,
        'prior_known_bytes':start['prior_known_bytes'],'prior_known_seconds':start['prior_known_seconds'],
        'known_cumulative_bytes':start['prior_known_bytes']+size,
        'known_cumulative_seconds':start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs':'UNKNOWN; retained inspections are not zero-cost evidence',
        'execution_allowed':size+reserve<252*1024**2 and seconds+seconds_reserve<1800}


def load_inputs():
    profiles=read(base.prior.HERE/'profiles.json.gz')
    profiles['relationships']=read(prior.OLD_PREP/'profile.json')
    return (read(base.prior.HERE/'products.json.gz'),profiles,read(PREP/'profile.json.gz'),
        read(prior.OLD_HERE/'ordinary-answer.json.gz'),read(AUDIT/'reference-closure-065.json.gz'))


def candidate_module():
    name='legalmath.prospectus._candidate_reference_availability'
    spec=importlib.util.spec_from_file_location(name,PREP/'candidate/h1_reference_availability.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare():
    tick=time.monotonic()
    auth=common.authority()
    old=read(AUTH/'program.json')
    require(old['revision']==428 and not PREP.exists() and not HERE.exists(),'Fresh revision428 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==65,'Retain65admissions')
    for folder in (prior.OLD_HERE,prior.HERE):
        manifest=folder/'outputs.json'
        require(any(e.get('attempt')==rel(folder) and e.get('outputs_sha256')==sha(manifest) for e in events),'Recorded predecessor required')
        require(all(sha(folder/n)==v for n,v in read(manifest).items()),'Changed sealed predecessor')
    require(read(prior.HERE/'result.json')['status']=='PASS','Successful065required')
    production=common.production()
    require(production==read(prior.PREP/'freeze.json')['production'],'065production changed')
    require(not (ROOT/mapping.MODULE).exists(),'Reference module already exists')
    audit=read(AUDIT/'reference-closure-065.json.gz')
    for key in ('method','source_review','baseline_audit','direct_reference_snapshot','original_graph','actual_answer'):
        require(sha(ROOT/audit[key]['path'])==audit[key]['sha256'],'Changed reference audit '+key)
    failed=read(AUDIT/'diagnostic-failure.json')
    require(sha(AUDIT/'failed-reference-map.py')==failed['method']['sha256'],'Lost failed preparation method')
    require(read(mapping.source.STATE)['production_changed'] is False and audit['production_changed'] is False,'Preparation changed production')
    previous=prior.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,'wrapper_bytes':(ROOT/mapping.WRAPPER).stat().st_size})
    for name,receipt in [('reference-state',read(mapping.source.STATE)),('reference-map-failure',failed),('reference-map-recovery',audit)]:
        save(PREP/'commands'/f'{name}.json',{'wall_seconds':receipt['seconds'],'command':'Retained bounded '+name+' diagnostic','status':receipt['status']})
    config=read(prior.PREP/'config.json')
    require(sha(config['package_python'])==config['python_sha256'] and
        sha(config['ordinary_python'])==config['ordinary_python_sha256'],'Interpreter changed')
    save(PREP/'config.json',config)
    products=read(base.prior.HERE/'products.json.gz')
    baseline=prior.checked_answer('ordinary')
    require(baseline==prior.checked_answer('installed'),'Whole065baseline differs')
    value=mapping.profile(products['P1']['payload']['graph'],baseline,audit)
    save(PREP/'profile.json.gz',value)
    candidate_hashes={}
    for name,text in mapping.candidates(value).items():
        ast.parse(text)
        target=PREP/'candidate'/Path(name).name
        target.parent.mkdir(exist_ok=True)
        with target.open('x') as stream:
            stream.write(text)
        candidate_hashes[name]=sha(target)
    candidate_production=production|candidate_hashes
    save(PREP/'candidate-production.json',candidate_production)
    shutil.copyfile(ROOT/mapping.WRAPPER,PREP/'baseline-wrapper.py')
    sys.path.insert(0,str(ROOT/'src'))
    module=candidate_module()
    result=module.evaluate(products['P1']['payload']['graph'],baseline,value,expected_profile_sha256=digest(value))
    proof=mapping.verify(baseline|{'h1_reference_availability_review':result,
        'h1_reference_availability_explanation':module.explain(result)},baseline,value,audit)
    require(common.production()==production,'Candidate preparation changed production')
    save(PREP/'preparation-check.json',{'status':'PASS','checks':proof,'production_changed':False})
    bindings={n:v for n,v in read(prior.PREP/'freeze.json')['bindings'].items() if n not in MUTABLE}
    bindings.update({rel(prior.HERE/n):v for n,v in read(prior.HERE/'outputs.json').items()})
    names=[SELF,MAPPING,PLAN,'scripts/prospectus_h1_reference_map.py','scripts/prospectus_h1_reference_state_audit.py',
        'docs/plans/prospectus-h1-reference-state-audit-2026-10-22.md','pyproject.toml',*TESTS,rel(prior.HERE/'outputs.json')]
    for folder in (AUDIT,mapping.source.previous.TEMP,PREP):
        names.extend(rel(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts
            and 'commands' not in p.parts and p.name!='accounting-start.json')
    bindings.update({n:sha(ROOT/n) for n in names})
    require(all(sha(ROOT/n)==v for n,v in bindings.items()),'Stale inherited input')
    save(PREP/'freeze.json',{'bindings':bindings,'baseline_production':production,
        'candidate_production':candidate_production,'mutable_files':sorted(MUTABLE),
        'implementation_window':'Once in admitted implement stage'})
    new=deepcopy(old)
    new['revision']=429
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver133explicit reference occurrences and11current historical-status explanations while preserving whole065')
    task['inputs']=sorted((set(task['inputs'])-MUTABLE)|set(bindings)|{rel(PREP/'freeze.json')})
    bounds={'measured_seconds':1800,'control_seconds':60,'new_bytes':256*1024**2,
        'failure_reserve':4*1024**2,'worker_seconds':120,'large_file_bytes':32*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],
        'unchanged_retries':0,'changed_recovery_requires_review':True}
    task['current_h1_reference_availability']={'version':mapping.VERSION,'freeze':rel(PREP/'freeze.json'),
        'bounds':bounds,'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=66
    routes=read(ROOT/old['continuation_review']['routes'])
    routes['baseline_revision']=429
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=common.compact_digest(task),dossier=PLAN,phase=0,
                remaining='065passed;133reference occurrences and11historical states reviewed; public delivery and wider original source meaning remain.',
                next_action='Execute optional reference availability public/installed checks; record, refresh and continue original source obligations.',
                stop_condition='Retain65admissions;attempt66only;256MiB and1800+60seconds;no unchanged retry;finite availability is not original acceptance.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for name in MUTABLE:
        new['continuation_review']['bindings'].pop(name,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline-wrapper.py'))})
    require(new['obligations']==old['obligations'] and new['build_contract']==old['build_contract'],'Original scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum((ROOT/n).stat().st_size for n in production)
    forecast=costs()['new_bytes']+2*len(raw)+4*source_bytes+2*32*1024**2+8*1024**2
    public_seconds=read(prior.OLD_HERE/'commands/ordinary.json')['wall_seconds']
    time_forecast=32*(public_seconds+12)+220
    require(forecast<252*1024**2 and time_forecast<1800,'Forecast exceeds reviewed allowance')
    with (PREP/'proposal.json').open('xb') as stream:
        stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Whole065preserved','76source addresses and133explicit occurrences','11historical states explained without replacing history',
            'Two printed discrepancies preserved','13actual adverse public cases per environment'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'forecast_measured_seconds':time_forecast,'supplied_map_is_not_general_interpretation':True,
            'preparation_failure_retained':True,'source_method':common.ref(AUDIT/'reference-closure-065.json.gz')},
        'evidence_contract':{'question':'Can current reference addresses and historical limits reach ordinary/installed public answers?',
            'baseline':rel(prior.OLD_HERE/'ordinary-answer.json.gz'),
            'primary':'Whole065and48links unchanged; exact original references/current fields; public delivery and matched corruption refusals',
            'promotion_veto':['Wrong source or target','Lost prior or history','Accepted re-pinned corruption','Incorrect installed origin'],
            'continuation_veto':['Invalid authority','Corrupt common originals','Exhausted cumulative reservation'],
            'not_concluded':['Complete financial/legal meaning','Source authenticity','Implicit-reference completeness','General automation','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':65,'new_maximum':66,
            'retained_attempts':attempts,'reason':'Original explicit-reference and historical-state representation gap reviewed across finite inventory',
            'next_discriminating_check':'Actual ordinary/installed optional public call with prior preservation and adverse inputs',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original prospectus build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_reference_closure','prepare']})
    return {'status':'PREPARED','revision':429,'forecast_new_bytes':forecast,
        'forecast_measured_seconds':time_forecast,'resources':costs()}


def source_worker():
    products,_,value,baseline,audit=load_inputs()
    graph=products['P1']['payload']['graph']
    units={u['id']:u for u in graph['units']}
    expected=mapping.source.build(units,baseline,read(mapping.source.STATE),read(mapping.source.SNAPSHOT))
    mapping.source.compare_map(value['map'],expected)
    module=candidate_module()
    reviewed=module.evaluate(graph,baseline,value,expected_profile_sha256=digest(value))
    proof=mapping.verify(baseline|{'h1_reference_availability_review':reviewed,
        'h1_reference_availability_explanation':module.explain(reviewed)},baseline,value,audit)
    save(HERE/'source.json',{'status':'PASS','checks':proof,'audit':common.ref(AUDIT/'reference-closure-065.json.gz')})


def compare_worker(kind):
    importlib.import_module('legalmath.prospectus.h1_reference_availability')
    answer=base.checked_answer('installed' if kind.startswith('installed') else 'ordinary')
    _,_,value,baseline,audit=load_inputs()
    proof=mapping.verify(answer,baseline,value,audit)
    if kind.startswith('installed'):
        require(answer==base.checked_answer('ordinary'),'Installed answer differs')
    refusals=[]
    for case in ('lost-prior','missing-reference','changed-history','hidden-discrepancy','changed-explanation'):
        bad=dict(answer)
        if case=='lost-prior':
            del bad['h1_source_relationship_review']
        elif case=='changed-explanation':
            bad['h1_reference_availability_explanation']={**answer['h1_reference_availability_explanation'],'remaining':'All resolved.'}
        else:
            bad['h1_reference_availability_review']=deepcopy(answer['h1_reference_availability_review'])
            b=bad['h1_reference_availability_review']['map']
            if case=='missing-reference': b['references'].pop()
            elif case=='changed-history': b['historical_states'][0]['historical_flag']['value']=True
            else: b['discrepancies'].pop()
        try:
            mapping.verify(bad,baseline,value,audit)
        except ValueError as exc:
            require(str(exc) in ('Complete065 answer changed','Current reference result differs','Current reference explanation differs'),'Unexpected comparison refusal')
            refusals.append({'case':case,'refused':True,'reason':str(exc)})
        else: raise ValueError('Accepted comparison corruption '+case)
    save(HERE/(kind+'.json'),{'status':'PASS','checks':proof,'refusals':refusals,'imports':base.imports(kind)})


def legacy_worker(kind):
    products,profiles,_,baseline,_=load_inputs()
    answer=mapping.links.consume(products,profiles,profiles['relationships'])
    require(answer==baseline,'Existing065public call changed')
    earlier=base.prior.support.consume(products,profiles)
    require(earlier==read(base.prior.HERE/'ordinary-answer.json.gz'),'Existing063public call changed')
    save(HERE/(kind+'.json'),{'status':'PASS','whole_065_preserved':True,'whole_063_preserved':True,
        'answer_sha256':digest(answer),'imports':base.imports(kind)})


def coverage_worker():
    rows=deepcopy(read(prior.HERE/'requirements.json')['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT'):
            row.update(status='RETAINED_FINITE_DELIVERY',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Explicit references and explanations of11historical statuses',
        'status':'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,
        'next_discriminating_work':'Review remaining original source-to-answer meanings and actual acceptance criteria; counts and supplied maps cannot close them.'})
    save(HERE/'remaining.json',{'finite_scope':'76declarations,133explicit occurrences,11historical states,2discrepancies',
        'remaining':['Implicit references and substantive completeness','Source authority and Portuguese priority',
            'Clipped equity values and unit conflicts','Financial reconciliation and legal effect','Original source acceptance and general automation'],
        'external_adviser_opinion_required':False})


def configure():
    for key,value in {'HERE':HERE,'PREP':PREP,'SELF':SELF,'PLAN':PLAN,'mapping':mapping,'MUTABLE':MUTABLE,
        'DEPENDENCIES':DEPENDENCIES,'costs':costs,'load_inputs':load_inputs,'source_worker':source_worker,
        'compare_worker':compare_worker,'legacy_worker':legacy_worker,'coverage_worker':coverage_worker}.items():
        setattr(base,key,value)


def stage(name):
    tick=time.monotonic()
    result=base.stage(name)
    measured=read(HERE/'commands'/(name+'.json'))['wall_seconds']
    save(HERE/'commands'/(name+'-control.json'),{'wall_seconds':max(0,time.monotonic()-tick-measured),
        'command':'Admission, bindings and resource verification for '+name,'accounting_role':'MEASURED_STAGE_CONTROL'})
    return result|{'resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    for started in (HERE/'stages').glob('*/started.json'):
        require((started.parent/'result.json').exists(),'Collect or recover started worker first')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists()
        else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    if passed: base.frozen()
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Current H1 reference availability\n\n'+
        ('The optional public consumer delivered the reviewed76declarations,133explicit references and11historical-status explanations in ordinary and installed calls. '
         'The whole065answer and its48links remain unchanged; calls without the optional view preserve065and063. '
         'Thirteen adverse public cases per environment and five comparator corruptions were rejected.\n\n' if passed else
         'The trial did not pass. Retained stage results identify failed and blocked work.\n\n')+
        'The printed policy2.23 heading/body discrepancy and policy2.6/Note23 description mismatch remain explicit. '
        'Available references do not prove financial reconciliation, legal effect or source truth.\n\n'
        '|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'+
        ('|Retain finite delivery|' if passed else '|Retain diagnosed failure|')+
        'Whole065preservation and reviewed source/target associations|Actual stages retained|Shared supplied interpretation and implicit references|'
        'Record,refresh,review original substantive acceptance obligations|General automation,financial/legal correctness or whole build|\n\n'
        'Post-run red-team review: a whitelist can preserve shared interpretive errors. The original-source review and separate finite parser constrain '
        'these addresses; they do not prove complete meaning. A wrong target, lost history, hidden discrepancy or accepted corruption overturns the finite verdict. '
        'The preparation identity defect was our adapter using a reconstructed line ID for an OCR occurrence; the failed method and changed recovery remain. '
        'No evidence here establishes a fundamental third-party package defect.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':read(PREP/'config.json'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':common.ref(PREP/'freeze.json'),
        'plan':PLAN,'result':rel(HERE/'RESULT.md'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}


def main():
    action=sys.argv[1]
    if action=='prepare': return prepare()
    configure()
    if not action.startswith('worker-'):
        return finalize() if action=='finalize' else stage(action)
    kind=action.removeprefix('worker-')
    require(kind in DEPENDENCIES,'Unreviewed worker')
    sys.path.insert(0,str(HERE/'installed') if kind.startswith('installed') else str(ROOT/'src'))
    if kind!='package':
        def forbidden(*args,**kwargs): raise RuntimeError('No native/network child in reference worker')
        base.subprocess.Popen=forbidden
    if kind in ('ordinary','installed'): base.answer_worker(kind)
    elif kind in ('compare','installed-compare'): compare_worker(kind)
    elif kind in ('legacy','installed-legacy'): legacy_worker(kind)
    elif kind.startswith(('control-','installed-control-')): base.control_worker(kind)
    else: {'source':source_worker,'implement':base.implement_worker,'package':base.package_worker,'coverage':coverage_worker}[kind]()
    return {'status':'PASS','worker':kind}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    print(json.dumps(main()),flush=True)
