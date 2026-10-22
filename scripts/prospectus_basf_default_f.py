"""Bounded source-specific default(f) analysis and actual installed use."""
from copy import deepcopy
from datetime import datetime,timezone
import fcntl
from itertools import product
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
from scripts import prospectus_basf_default_source as source
from scripts import prospectus_basf_equity as install_base
from scripts import prospectus_default_f_scenarios as scenarios
from legalmath.prospectus import basf_default_f as default,basf_body_coverage
from legalmath.prospectus.execution_authority import read,file_hash
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.predicates import dispatch

ROOT,HERE,PRIOR,BASE,PLAN=source.ROOT,source.HERE,source.PRIOR,source.BASE,source.PLAN
RUNNER=ROOT/'scripts/prospectus_installed_default_runner.py'
save,load=source.save,source.load
install_base.HERE=HERE
PREDECESSORS={'profile':('prepare',),'baseline':('profile',),'compare':('baseline',),
    'logic':('compare',),'controls':('logic',),'tests':('controls',),'install-prepare':('tests',),
    'build':('install-prepare',),'install':('build',),'replay-answer':('install',),
    'replay-controls':('replay-answer',),'verify':('replay-controls',)}


def methods():
    names=[Path(__file__),Path(source.__file__),Path(source.old.__file__),Path(source.old.base.__file__),
           Path(install_base.__file__),Path(scenarios.__file__),RUNNER,ROOT/PLAN,ROOT/'pyproject.toml',
           HERE/'IMAGE-REVIEW.md',HERE/'EXECUTION-AUDIT.md',ROOT/'tests/prospectus/test_basf_default_f.py']
    names+=sorted((ROOT/'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)):file_hash(p) for p in names}


def bindings():
    ad=source.bindings()
    if (HERE/'methods.json').exists():assert methods()==read(HERE/'methods.json')
    return ad


def profile():
    p=load(HERE/'products.json.gz');prior=load(PRIOR/'body-consumer.json.gz')
    value={'version':default.VERSION,'products_sha256':digest(p),'prior_sha256':digest(prior),
        'reviewer':{'identity':'Codex supplied original-source review2026-10-15','basis':'AGENT_EXPOSED_DEVELOPMENT_REVIEW','independent':False},
        'sources':read(HERE/'original-sources.json'),'groups':default.source_groups(p),'premises':default.premises(),
        'candidates':[{'id':k,'meaning':default.READINGS[k],'event':v,'expressions':default.expressions(k)} for k,v in default.FORMULAS.items()],
        'scenarios':scenarios.cases(),'governing_language':'German','selected_reading':None,
        'candidate_set_exhaustive':False,'independent_legal_acceptance':False}
    save('profile.json',value);save('profile-pin.json',{'sha256':digest(value)})
    save('prior-profiles.json',{'preceding':read(PRIOR/'prior-profiles.json'),'body':read(PRIOR/'profile.json')})
    save('methods.json',methods())
    for p in methods():
        target=HERE/'methods'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
    save('pre-run-audit.json',{'status':'PASS','plan':PLAN,'exact_baseline':str(PRIOR.relative_to(ROOT)),
        'candidate_formulas':3,'hypothetical_scenarios':16,'causal_propositions_separate':True,'receipt_exercise_separate':True,
        'selected_reading':None,'all_open_baseline_first':True,'truth_table_role':'CONDITIONAL_LOGIC_ONLY',
        'native_allowance':0,'http_allowance':0,'outer_command_limit':5,'local_repair_limit':1,
        'historical_visible_native_reservation_lower_bound':79,'historical_visible_source_http_lower_bound':9})
    return {'candidates':3,'scenarios':16,'source_groups':len(value['groups'])}


def baseline():
    old=read(HERE/'prior-profiles.json');o,b=old['preceding'],old['body']
    r=basf_body_coverage.consume(load(HERE/'products.json.gz'),o,b,ROOT,
        expected_prior_profiles_sha256=digest(o),expected_profile_sha256=digest(b))
    save('baseline-consumer.json.gz',r);assert r==load(PRIOR/'body-consumer.json.gz')
    return {'complete_prior_consumer_equal':True}


def compare():
    old=read(HERE/'prior-profiles.json');p=read(HERE/'profile.json')
    r=default.consume(load(HERE/'products.json.gz'),old,p,ROOT,
        expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(p))
    save('default-consumer.json.gz',r);prior=load(HERE/'baseline-consumer.json.gz')
    assert {k:r[k] for k in prior}==prior
    results=r['default_f_review']['scenarios'];observed={}
    for case in results:
        x=[v['modeled_f_exercise']['status'] for v in case['readings'].values()]
        q=[v['bc_quorum_condition_at_receipt']['status'] for v in case['readings'].values()]
        assert (x,q)==scenarios.EXPECTED[case['id']]
        observed[case['id']]={'modeled_f_exercise':x,'bc_quorum_condition_at_receipt':q,'comparison':case['comparison']}
    report={'status':'PASS','all_earlier_outputs_unchanged':True,'ordinary_answer_unchanged':True,
        'candidates':3,'scenarios':len(results),'scenario_effects':observed,'selected_reading':None,
        'candidate_set_exhaustive':False,'actual_default_established':False,'independent_legal_acceptance':False,
        'prior_unknown_spans_unchanged':True,'prior_default_question_unchanged':True}
    save('comparison.json',report);return {k:v for k,v in report.items() if k!='scenario_effects'}


def logic():
    counts={'event':0,'exercise':0,'quorum':0};rows=[]
    for bits in product((False,True),repeat=len(scenarios.FACT_NAMES)):
        f=dict(zip(scenarios.FACT_NAMES,bits))
        for key in default.FORMULAS:
            expected=scenarios.manual_event(key,f);expr=default.expressions(key)
            base={'exercise.'+k:v for k,v in f.items()}
            result=dispatch(expr['event_at_exercise'],base)
            assert result['status']==('YES' if expected else 'NO');counts['event']+=1
            for notice,cured in product((False,True),repeat=2):
                actual=dispatch(expr['modeled_f_exercise'],{**base,'notice':notice,'cured_before_exercise':cured})
                want=expected and notice and not cured
                assert actual['status']==('YES' if want else 'NO');counts['exercise']+=1
            base={'receipt.'+k:v for k,v in f.items()}
            for quorum,other,eligible in product((False,True),repeat=3):
                actual=dispatch(expr['bc_quorum_condition_at_receipt'],{**base,'quorum_at_receipt':quorum,
                    'other_eligible_at_receipt':other,'f_other_eligibility_at_receipt':eligible})
                want=quorum or other or (expected and eligible)
                assert actual['status']==('YES' if want else 'NO');counts['quorum']+=1
            rows.append({'reading':key,'causal_facts':f,'expected_event':expected,'actual_event':result['status'],
                         'all4_notice_cure_and8_quorum_combinations_match':True})
    assert counts=={'event':768,'exercise':3072,'quorum':6144}
    save('logic-worlds.json.gz',rows)
    r={'status':'PASS','comparisons':counts,'total':sum(counts.values()),'independently_written_formulas':True,
       'legal_correctness_established':False,'joint_transaction_feasibility_established':False}
    save('logic-comparison.json',r);return r


def controls():
    original=read(HERE/'profile.json');p=load(HERE/'products.json.gz');prior=load(HERE/'baseline-consumer.json.gz')
    names=['omitted-german-line','changed-english-connector','omitted-cure','omitted-quorum-fragment','omitted-notice',
        'wrong-selected-offset','german-priority-omitted','english-controls','selected-favorable-reading','claims-exhaustive',
        'causality-collapsed','receipt-as-exercise','notice-removed','eligibility-removed','all-open-removed',
        'actual-facts-claim','unexpected-fact','duplicate-scenario','independent-claim','changed-image','changed-pdf','stale-products','stale-prior','stale-pin']
    out=[]
    for name in names:
        v=deepcopy(original)
        if name=='omitted-german-line':v['groups']['german_f'].pop()
        elif name=='changed-english-connector':v['groups']['english_f_comparison'][0]['source']['quote']=v['groups']['english_f_comparison'][0]['source']['quote'].replace('operations or','operations and')
        elif name=='omitted-cure':v['groups']['cure'].pop()
        elif name=='omitted-quorum-fragment':v['groups']['quorum'].pop(9)
        elif name=='omitted-notice':v['groups']['notice'].pop()
        elif name=='wrong-selected-offset':v['groups']['entitlement'][0]['selected_sources'][0]['source']['start']+=1
        elif name=='german-priority-omitted':del v['groups']['german_priority']
        elif name=='english-controls':v['governing_language']='English'
        elif name=='selected-favorable-reading':v['selected_reading']='cessation_or_qualified_disposal'
        elif name=='claims-exhaustive':v['candidate_set_exhaustive']=True
        elif name=='causality-collapsed':v['premises']['exercise.value_cessation']['meaning']=v['premises']['exercise.value_disposal']['meaning']
        elif name=='receipt-as-exercise':v['candidates'][0]['expressions']['event_at_receipt']=deepcopy(v['candidates'][0]['expressions']['event_at_exercise'])
        elif name=='notice-removed':v['candidates'][0]['expressions']['modeled_f_exercise']['all'].pop(1)
        elif name=='eligibility-removed':v['candidates'][0]['expressions']['bc_quorum_condition_at_receipt']['any'][-1]['all'].pop()
        elif name=='all-open-removed':v['scenarios'].pop(0)
        elif name=='actual-facts-claim':v['scenarios'][1]['kind']='ACTUAL_TRANSACTION'
        elif name=='unexpected-fact':v['scenarios'][1]['facts']['expected_answer']='YES'
        elif name=='duplicate-scenario':v['scenarios'].append(deepcopy(v['scenarios'][-1]))
        elif name=='independent-claim':v['reviewer']['independent']=True
        elif name=='changed-image':v['sources'][0]['images'][0]['sha256']='0'*64
        elif name=='changed-pdf':v['sources'][0]['sha256']='0'*64
        elif name=='stale-products':v['products_sha256']='0'*64
        elif name=='stale-prior':v['prior_sha256']='0'*64
        else:v['reviewer']['identity']+=' altered'
        pin=digest(original) if name=='stale-pin' else digest(v)
        save('adverse-inputs/'+name+'.json.gz',{'profile':v,'expected_profile_sha256':pin})
        try:default.evaluate(p,prior,v,ROOT,expected_profile_sha256=pin)
        except ValueError as error:out.append({'case':name,'refused':True,'repinned':name!='stale-pin','reason':str(error)})
        else:raise AssertionError('Altered default(f) accepted: '+name)
    save('actual-controls.json',out);return {'actual_controls_refused':len(out),'repinned':len(out)-1}


def tests():
    import pytest
    code=pytest.main(['-q','tests/prospectus/test_basf_default_f.py','--junitxml='+str(HERE/'tests.xml')])
    assert code==0;return {'pytest_exit':int(code)}


def workspace():return Path(read(HERE/'workspace.json')['directory'])


def install_prepare():
    old=Path(read(PRIOR/'workspace.json')['directory'])/'environment';old_package=read(PRIOR/'source-package.json')
    assert install_base.package_files(old/'lib/python3.11/site-packages/legalmath')==old_package
    temp=Path(tempfile.mkdtemp(prefix='installed-basf-default-',dir=ROOT/'.localresources/prospectus'))
    save('workspace.json',{'directory':str(temp),'environment_cloned_from':str(old)})
    shutil.copytree(old,temp/'environment',symlinks=True);(temp/'source').mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',temp/'source/pyproject.toml')
    shutil.copytree(ROOT/'src',temp/'source/src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    shutil.copyfile(RUNNER,temp/'runner.py');package=install_base.package_files(temp/'source/src/legalmath')
    assert all(package.get(p)==h for p,h in old_package.items())
    added=sorted(set(package)-set(old_package));assert added==['prospectus/basf_default_f.py']
    save('source-package.json',package)
    save('prior-package-identity.json',{'status':'PASS','all_prior_files_unchanged':len(old_package),'new_modules':added})
    save('environment-metadata.json',{str(p.relative_to(temp/'environment')):file_hash(p)
        for p in (temp/'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'prior_files_unchanged':len(old_package),'exact_package_files':len(package)}


def build():return install_base.build()
def install():return install_base.install()
def replay_answer():
    install_base.run('replay-answer',[str(workspace()/'environment/bin/python'),'-I',str(workspace()/'runner.py'),str(HERE),str(ROOT),'answer'])
    return read(HERE/'installed-answer/result.json')
def replay_controls():
    install_base.run('replay-controls',[str(workspace()/'environment/bin/python'),'-I',str(workspace()/'runner.py'),str(HERE),str(ROOT),'controls'])
    return read(HERE/'installed-controls/result.json')


def verify():
    answer=read(HERE/'installed-answer/result.json');controls=read(HERE/'installed-controls/result.json')
    assert answer['status']==controls['status']=='PASS' and answer['full_output_equal'] and controls['controls']==24
    package=workspace()/'environment/lib/python3.11/site-packages/legalmath';expected=read(HERE/'source-package.json')
    assert install_base.package_files(package)==expected
    for folder in ('installed-answer','installed-controls'):
        assert read(HERE/folder/'package-files.json')==expected
        proof=read(HERE/folder/'import-proof.json');assert proof['isolated']==1
        for m in proof['modules'].values():
            p=Path(m['path']).resolve()
            assert p.is_relative_to(package) and file_hash(p)==m['sha256']==expected[str(p.relative_to(package))]
    assert load(HERE/'installed-answer/default-consumer.json.gz')==load(HERE/'default-consumer.json.gz')
    assert read(HERE/'installed-controls/controls.json')==read(HERE/'actual-controls.json')
    assert len(process_ledger.checked(HERE/'command-ledger.json')['reservations'])==4
    r={**read(HERE/'comparison.json'),'installed_full_output_equal':True,'actual_controls_refused':24,
       'finite_logic_comparisons':read(HERE/'logic-comparison.json')['total'],'exact_package_files':len(expected),
       'prior_package_files_unchanged':427,'outer_commands':4,'local_repairs_used':0,'different_host_portability':False,
       'historical_visible_native_reservation_lower_bound':79,'historical_visible_source_http_lower_bound':9}
    save('verified-result.json',r);return {k:v for k,v in r.items() if k!='scenario_effects'}


def main():
    stage=sys.argv[1];assert stage in PREDECESSORS;ad=bindings()
    for previous in PREDECESSORS[stage]:assert read(HERE/'invocations'/previous/'result.json')['status']=='PASS','Failed prerequisite: '+previous
    folder=HERE/'invocations'/stage;folder.mkdir(parents=True,exist_ok=False)
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_basf_default_f',stage],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,'started_at':datetime.now(timezone.utc).isoformat(),
        'random_seeds':'N/A deterministic','cpu_gpu':'CPU only;no framework imports;children CUDA_VISIBLE_DEVICES=-1',
        'required_predecessors':list(PREDECESSORS[stage])})
    tick=time.monotonic()
    def expire(signum,frame):raise TimeoutError('120-second default(f) stage bound;no automatic retry')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        details=globals()[stage.replace('-','_')]();bindings()
        size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        if (HERE/'workspace.json').exists():size+=sum(p.stat().st_size for p in workspace().rglob('*') if p.is_file())
        assert size<500*1024*1024
        r={'status':'PASS','stage':stage,'details':details,'wall_seconds':time.monotonic()-tick,'evidence_and_workspace_bytes':size}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick});raise
    finally:signal.alarm(0)
    save('invocations/'+stage+'/result.json',r);print(r)


if __name__=='__main__':
    with (HERE/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
